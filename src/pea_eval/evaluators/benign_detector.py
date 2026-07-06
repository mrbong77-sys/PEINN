"""
benign_detector.py — Benign-Trick Detector (보조 분류기, HANDOFF-28 옵션 2).

목적
  HybridCalibrator(emotion32+semantic_emb→energy)가 양성-맥락 death-verb·게임·비유·허구
  프라이버시를 E∈[8.0,8.5)로 over-fire하는 잔존 한계 봉합. 기존 calibrator는 **불변**으로
  두고 별도 분류기가 "양성 trick" 신호를 학습 → 추론 시 calibrator energy를 차감 보정.

설계 원칙 (HANDOFF-24 실패 회피)
  - 기존 HybridCalibrator weight·threshold는 100% 보존 (분포 안정성 ★)
  - 별도 detector(.pt) 미배포 시 자동 fallback → 기존 동작 그대로 (fail-safe)
  - 학습 데이터: trick_safe-Safe(150) vs HarmBench unsafe(150) **균형** (majority 압도 0)
  - α(차감 강도)는 추론 시 조정 가능 — 안전 우선이면 α↓

구조
  text → MiniLM(384) + EE(emotion32) → Linear(416→64)→ReLU→Dropout(0.2)
       → Linear(64→32)→ReLU→Linear(32→1)→Sigmoid → benign_prob ∈ [0,1]

추론 적용 (ee_runner.analyze_emotion에 통합 시)
  final_E = max(0, base_E − α × benign_prob × max_offset)
  α=0.5, max_offset=2.0 → 최대 -1.0 차감 (E 8.4 → 7.4 가능, hard-block 회피)

체크포인트
  pea_eval/data/ee_benign_detector.pt  (gitignore, DGX-side)
"""
from __future__ import annotations

import logging
from pathlib import Path

import torch
import torch.nn as nn

logger = logging.getLogger("peaos.benign_detector")


class BenignTrickDetector(nn.Module):
    """Binary classifier: 양성-trick(label=1) vs 진짜 유해(label=0).
    HybridCalibrator와 동일 입력 차원(emotion32+semantic_emb)·아키텍처로 호환성 유지."""

    def __init__(self, emo_dim: int = 32, sem_dim: int = 384, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(emo_dim + sem_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x)


# ── 추론 시 calibrator energy 보정 ──────────────────────────────────────────

CKPT_PATH_DEFAULT = Path(__file__).resolve().parent.parent / "data" / "ee_benign_detector.pt"
DEFAULT_ALPHA = 0.5         # 차감 강도 (0=비활성, 1=최대)
DEFAULT_MAX_OFFSET = 2.0    # benign_prob=1.0 시 최대 차감량(×α 후 실제 -1.0)
DEFAULT_MIN_BENIGN_PROB = 0.6  # 이 미만은 차감 안 함 (저신뢰 noise 방지)


def load_detector(ckpt_path: Path | None = None) -> BenignTrickDetector | None:
    """detector 로드. 없으면 None 반환(fail-safe — 호출부가 기존 동작 유지)."""
    p = ckpt_path or CKPT_PATH_DEFAULT
    if not p.exists():
        return None
    try:
        m = BenignTrickDetector()
        sd = torch.load(p, map_location="cpu")
        m.load_state_dict(sd if isinstance(sd, dict) and "net.0.weight" in sd else sd.get("state_dict", sd))
        m.eval()
        return m
    except Exception as e:  # noqa: BLE001
        logger.warning(f"BenignTrickDetector load 실패: {type(e).__name__}: {str(e)[:80]}")
        return None


def adjust_energy(
    base_E: float,
    emotion32,  # torch.Tensor (1,32) or np
    semantic_emb,  # torch.Tensor (1,384) or np
    detector: BenignTrickDetector | None,
    alpha: float = DEFAULT_ALPHA,
    max_offset: float = DEFAULT_MAX_OFFSET,
    min_benign_prob: float = DEFAULT_MIN_BENIGN_PROB,
    safe_band: tuple[float, float] = (7.5, 8.7),
) -> tuple[float, float]:
    """calibrator energy를 benign_prob로 차감. 반환: (final_E, benign_prob).

    적용 조건:
      1. detector 로드됨 (None=skip)
      2. base_E ∈ safe_band (이 범위 밖은 분류기 영향 X — over-fire 경계만 보정)
      3. benign_prob ≥ min_benign_prob (저신뢰 noise 차단)

    안전 보호:
      - safe_band 밖(E<7.5 or E>8.7)은 그대로 — 진짜 유해(E≥9) 영향 X, 명확 safe(E<7.5) 영향 X
      - benign_prob<0.6은 그대로 — 분류기가 확신 못 하면 차감 X
      - 차감량 최대 -1.0 (α=0.5 × max=2.0)
    """
    if detector is None:
        return base_E, 0.0
    if not (safe_band[0] <= base_E <= safe_band[1]):
        return base_E, 0.0
    try:
        if not isinstance(emotion32, torch.Tensor):
            emotion32 = torch.tensor(emotion32, dtype=torch.float32)
        if not isinstance(semantic_emb, torch.Tensor):
            semantic_emb = torch.tensor(semantic_emb, dtype=torch.float32)
        if emotion32.dim() == 1:
            emotion32 = emotion32.unsqueeze(0)
        if semantic_emb.dim() == 1:
            semantic_emb = semantic_emb.unsqueeze(0)
        x = torch.cat([emotion32.cpu(), semantic_emb.cpu()], dim=1)
        with torch.no_grad():
            p = detector(x).item()
    except Exception as e:  # noqa: BLE001
        logger.debug(f"detector inference 실패: {type(e).__name__}: {str(e)[:60]}")
        return base_E, 0.0
    if p < min_benign_prob:
        return base_E, p
    offset = alpha * p * max_offset
    return max(0.0, base_E - offset), p
