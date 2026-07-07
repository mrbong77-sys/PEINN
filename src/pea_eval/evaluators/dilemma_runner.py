"""
Dilemma Classifier — input-derived 도덕 dilemma 판별기.

설계 의도:
  유해성 판별기(HybridCalibrator)와 구조적으로 대칭. 입력 텍스트만 보고
  "이게 도덕 dilemma인가?"를 학습된 분류기로 판정한다. 평가 모듈 식별
  정보(instrument 이름, 벤치마크 명칭)는 입력으로 들어가지 않으므로
  PEINN의 module-uniform 동작 원칙을 침범하지 않는다.

라우터와의 관계:
  route_reflection_mode가 받는 4번째 신호로 합류.
    if ee_energy ≥ 8.5            → refusal
    if dilemma_label == "DILEMMA" → reasoning   ← 이 분류기가 결정
    if rag_similarity ≥ 0.55      → reasoning  (기존)
    ...

학습 데이터 (scripts/build_dilemma_dataset.py 참조):
  POS : MoralChoice (Scherrer 2023, arXiv:2307.14324), ETHICS dilemma split
        (Hendrycks 2021, arXiv:2008.02275), internal dilemmas.json
  NEG : HarmBench val 공격 prompt, XSTest safe 사실 질문, TriviaQA 일부.

런타임 시 모델 파일이 없으면 graceful no-op (라벨 "" 반환) — 기존
파이프라인이 모델 학습 전에도 깨지지 않는다.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional, Tuple

import torch
import torch.nn as nn

logger = logging.getLogger("peinn.pea_eval.dilemma_runner")


# Hybrid Calibrator와 동일한 mpnet 임베딩(768d)을 입력으로 받는다.
# 두 분류기가 같은 표현 공간을 공유하므로 EE pipeline에서 임베더를 한 번만
# 로드해 양쪽이 재사용한다.
DEFAULT_SEM_DIM = 768
MODEL_PATH = Path("pea_eval/data/dilemma_classifier_best.pt")
THRESHOLD_SIDECAR = MODEL_PATH.with_suffix(".threshold.json")


def _resolve_threshold() -> float:
    """우선순위: env var > sidecar file > 0.5 fallback.

    학습 스크립트가 sidecar(.threshold.json)를 자동 저장하므로 별도
    env export 없이도 학습 결과 τ가 반영된다.
    """
    env = os.environ.get("PEAOS_DILEMMA_THRESHOLD")
    if env:
        try:
            return float(env)
        except ValueError:
            logger.warning(f"PEAOS_DILEMMA_THRESHOLD parse 실패: {env}")
    if THRESHOLD_SIDECAR.exists():
        try:
            import json
            d = json.loads(THRESHOLD_SIDECAR.read_text(encoding="utf-8"))
            return float(d.get("threshold", 0.5))
        except Exception as e:
            logger.warning(f"sidecar threshold 로드 실패: {e}")
    return 0.5


DEFAULT_THRESHOLD = _resolve_threshold()


class DilemmaClassifier(nn.Module):
    """Semantic embedding → dilemma probability.

    768 → 128 → 32 → 1 sigmoid. HybridCalibrator(64→32→1)보다 한 단 깊다
    (dilemma 판정이 안전 판정보다 추상적이라 capacity 약간 늘림).
    """

    def __init__(self, sem_dim: int = DEFAULT_SEM_DIM, hidden_dim: int = 128):
        super().__init__()
        self.sem_dim = sem_dim
        self.net = nn.Sequential(
            nn.Linear(sem_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)


class DilemmaRunner:
    """싱글톤 런타임. 모델 파일이 없으면 no-op으로 동작."""

    _instance: Optional["DilemmaRunner"] = None

    @classmethod
    def get_instance(cls) -> "DilemmaRunner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, model_path: Path = MODEL_PATH, threshold: float = DEFAULT_THRESHOLD):
        self.model_path = model_path
        self.threshold = threshold
        self._model: Optional[DilemmaClassifier] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._embedder = None  # SentenceTransformer; lazy-injected by EE runner
        self._loaded = False
        self._tried_load = False

    def attach_embedder(self, embedder) -> None:
        """EE Runner의 calibrator embedder를 공유 받는다 (mpnet 중복 로드 회피)."""
        self._embedder = embedder

    def _try_load(self) -> None:
        if self._tried_load:
            return
        self._tried_load = True
        if not self.model_path.exists():
            logger.info(
                f"DilemmaClassifier 모델 없음: {self.model_path} → no-op 모드 "
                f"(scripts/train_dilemma_classifier.py 로 학습 필요)"
            )
            return
        try:
            self._model = DilemmaClassifier().to(self._device)
            state = torch.load(self.model_path, map_location=self._device)
            self._model.load_state_dict(state)
            self._model.eval()
            self._loaded = True
            src = ("env" if os.environ.get("PEAOS_DILEMMA_THRESHOLD")
                   else ("sidecar" if THRESHOLD_SIDECAR.exists() else "default"))
            logger.info(f"DilemmaClassifier 로드: {self.model_path} (threshold={self.threshold} from {src})")
        except Exception as e:
            logger.warning(f"DilemmaClassifier 로드 실패: {e} → no-op")
            self._model = None

    def is_active(self) -> bool:
        self._try_load()
        return self._loaded and self._embedder is not None

    def score(self, text: str) -> Tuple[float, str]:
        """입력 텍스트에 대해 (probability, label) 반환.

        label ∈ {"DILEMMA", "NOT", ""}.  "" 는 분류기 비활성(모델 미학습/미로드)
        을 의미하며, 라우터가 dilemma 신호를 무시하도록 한다.
        """
        if not self.is_active():
            return 0.0, ""
        try:
            with torch.no_grad():
                emb = self._embedder.encode(
                    text, convert_to_tensor=True, device=str(self._device)
                )
                if emb.dim() == 1:
                    emb = emb.unsqueeze(0)
                prob = float(self._model(emb).item())
            label = "DILEMMA" if prob >= self.threshold else "NOT"
            return prob, label
        except Exception as e:
            logger.warning(f"DilemmaClassifier score 실패: {e}")
            return 0.0, ""
