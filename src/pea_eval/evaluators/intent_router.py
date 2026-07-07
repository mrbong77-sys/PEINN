"""IntentRouter 어댑터 — Pass 2 라우팅 결정의 swap-able 추상화 (S1).

두 production 라우터를 동일 인터페이스로 제공한다:
  - `NeutroEERouter`     : v1.0 (neutrosophic head + 튜닝 임계)
  - `NeutroEERouterV21`  : v2.1 (v4 head ⊗ energy gated 5-tier, θ locked)

엔진 선택은 `EEConfig.engine` ("neutro" | "neutro_v21")로 스왑한다.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("peinn.intent_router")

# 라우팅 분기 결과 — route_reflection_mode 반환값과 동일 도메인
ROUTE_1PASS = "1-pass"
ROUTE_REFUSAL = "2-pass-refusal"
ROUTE_REASONING = "2-pass-reasoning"
# fallthrough(uncertain) reasoning — dilemma(high-I)가 아니라 head가 확신 못 한 잔여.
# build_moral_reasoning_prompt(soft=True)로 저energy benign은 윤리원칙 강제 없이
# 실용답 보존(ORR 교정). dilemma는 ROUTE_REASONING(도덕추론)을 그대로 받는다.
ROUTE_REASONING_SOFT = "2-pass-reasoning-soft"
# hard-block: LLM 2nd pass를 호출하지 않고 고정 거절로 단락(short-circuit).
# 2nd-pass 생성 자체를 제거해 TAX_032류 leak을 원천 차단. neutro 전용
# (legacy는 거동 불변이라 발화하지 않음).
ROUTE_HARD_BLOCK = "hard-block"

# --- NeutroEE 산출물 경로 (DGX-side, gitignore) -----------------------------
_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NEUTRO_HEAD_PT = _DATA_DIR / "ee_neutro_head.pt"
NEUTRO_ROUTING_JSON = _DATA_DIR / "ee_neutro_routing.json"

# 채택 운영점 (EXP-14 clean retrain, routing.json 없을 때 fallback).
DEFAULT_NEUTRO_THRESHOLDS = (0.75, 0.5, 0.65)  # (tau_safe, tau_harm, tau_I)
# 충돌(contradiction) 게이트 임계 C=min(T,F)≥τ_c. 5-run XSTest 분석에서 SAFE 과잉거부의
# ~44%가 C≥0.3 → 기본 0.30. routing.json "tau_c"로 override(재학습 head 기준 재캘리브레이션 권장).
DEFAULT_TAU_C = 0.30
# 딜레마 구제(energy 과발화 교정): high band[7.0,8.0)에서 posture=reasoning이고
# I≥τ_dilemma 且 F<τ_f_low면 reasoning 유지(거부 X). routing.json "tau_dilemma"/"tau_f_low" override.
DEFAULT_TAU_DILEMMA = 0.35
DEFAULT_TAU_F_LOW = 0.2
# [A] I/F-only dilemma rescue: F 상한 (complexity readout 우회용, posture=reasoning ∧ I≥τ_dilemma 동반).
DEFAULT_TAU_F_DILEMMA = 0.3
# [B] 저-energy 밴드 ORR 완화: 본 ceiling 미만 + F<τ_f_extreme이면 hard-block 대신 ROUTE_REASONING.
# ceiling=ENERGY_THREAT_HIGH(8.0)면 B 분기가 절대 발화 안 함(에너지 조건 `energy < 8.0` ∧ `energy ≥ 8.0`
# 충돌). γ audit에서 B의 ORR 개선 효과가 사실상 사라지고 dilemma 회귀(E=8.48 손실)까지 발생 →
# B 무력화(β). A(I/F dilemma rescue)에 집중하면서 τ_dilemma 0.5→0.4로 완화해 dilemma 패러프레이즈
# coverage 확장(Karl-Bob paraphrase, "stealing from store", "cheating old" 3건 추가 구제 시도).
DEFAULT_LOW_RELAX_CEILING = 8.0
DEFAULT_TAU_F_EXTREME = 0.5

# neutro 분기 어휘 → legacy(route_reflection_mode) 어휘 매핑.
_NEUTRO_TO_LEGACY = {
    "1-pass": ROUTE_1PASS,
    "refusal": ROUTE_REFUSAL,
    "reasoning": ROUTE_REASONING,
}


@dataclass(frozen=True)
class RouteDecision:
    """라우팅 결과 + Neutro head 진단치.

    route   : 최종 라우팅(에너지 게이트/safe-recheck 반영). evaluator가 실행에 사용.
    posture : head의 1차 결정(에너지 게이트 적용 전, neutro_route 산출). 분석용.
    T, I, F : Neutro head의 neutrosophic 출력(None=비-neutro/미산출).
    energy  : 라우팅에 쓰인 calibrator energy.
    complexity : judge-distilled emotion '도덕 복잡성'(emo_17). 고에너지 딜레마 구제 게이트용(None=readout 미로드).
    """
    route: str
    posture: str = ""
    T: float | None = None
    I: float | None = None
    F: float | None = None
    energy: float | None = None
    complexity: float | None = None


@dataclass(frozen=True)
class RoutingSignals:
    """라우팅 입력 신호 — 전부 evaluator 모듈과 무관한 input-derived 특성.

    동일 신호 묶음을 legacy/neutro 라우터가 공유한다. neutro 라우터는 추가로
    원문 텍스트가 필요할 수 있어 `text`를 옵션으로 둔다(legacy는 무시).
    """
    ee_energy: float
    ee_intent: str                 # "SAFE" | "HARMFUL"
    rag_similarity: float
    anchor_idx: int = -1
    dilemma_label: str = ""        # "DILEMMA" | "NOT" | "" (비활성)
    text: str = ""                 # neutro head feature 추출용 (legacy 미사용)


class IntentRouter(ABC):
    """Pass 2 라우팅 전략 인터페이스."""

    name: str = "base"

    @abstractmethod
    def route(self, signals: RoutingSignals) -> str:
        """RoutingSignals → {1-pass, 2-pass-refusal, 2-pass-reasoning} 중 하나."""
        raise NotImplementedError

    def route_decision(self, signals: RoutingSignals) -> "RouteDecision":
        """route() + 진단치. 기본 구현은 route만 채우고 T/I/F는 비움(비-neutro용)."""
        return RouteDecision(route=self.route(signals), energy=signals.ee_energy)


# --- NeutroEE 공유 요소 (train_neutro_head.py와 단일 소스) -------------------
def build_neutro_head(in_dim: int, hidden: int = 128):
    """독립 3-sigmoid head — 학습/추론 공유 아키텍처.

    train_neutro_head.py가 이 함수를 import해 동일 구조로 학습/저장하므로,
    저장된 state_dict가 추론 시 그대로 로드된다.
    """
    import torch.nn as nn
    return nn.Sequential(
        nn.Linear(in_dim, hidden), nn.ReLU(), nn.Dropout(0.2),
        nn.Linear(hidden, 64), nn.ReLU(),
        nn.Linear(64, 3), nn.Sigmoid(),   # 독립 3-sigmoid (softmax 아님)
    )


def neutro_feature_vector(feat: dict):
    """neutro_features() dict → head 입력 벡터 [emotion32 ⊕ semantic_emb ⊕ principle_emb].

    EXP-10: native energy 제거(무변별), 입력 semantic embedding 추가(head가 입력을
    직접 보게 함). MiniLM-384 기준 32+384+384 = 800d. energy는 head 밖 라우팅 게이트로만.
    """
    import numpy as np
    return np.concatenate(
        [feat["emotion"], feat["semantic_emb"], feat["principle_emb"]]
    ).astype("float32")


def neutro_route(T: float, I: float, F: float, ts: float, th: float, ti: float) -> str:
    """neutrosophic 분기 — head의 1차 posture(에너지 보완 전).

    I 우선(dilemma) → 결정적 harm → 결정적 safe → 나머지 reasoning(보수적).
    반환 어휘는 neutro 도메인("reasoning"/"refusal"/"1-pass"). 최종 라우팅은
    NeutroEERouter.route_decision에서 EE energy가 이 posture를 보완해 결정한다.
    """
    if I >= ti:
        return "reasoning"
    if F >= th and F >= T:
        return "refusal"
    if T >= ts and F < th:
        return "1-pass"
    return "reasoning"


def energy_compensated_route(
    posture: str, T: float, I: float, F: float, energy: float, ti: float, tau_c: float,
    threat_high: float, reasoning_ceiling: float, safe_recheck: float,
    tau_dilemma: float = 0.35, tau_f_low: float = 0.2,
    complexity: float | None = None, tau_complexity: float = 0.6,
    dilemma_block_ceiling: float = 9.5,
    tau_safe_rescue: float = 0.85, safe_rescue_ceiling: float = 8.5,
    tau_f_dilemma: float = 0.3,
    low_relax_ceiling: float = 8.0, tau_f_extreme: float = 0.5,
) -> str:
    """EE energy가 Neutro head posture의 라우팅 오류를 보완해 최종 route 결정.

    순수 함수(torch/모델 불필요) — 테스트·오프라인 재라우팅에서 그대로 호출 가능.

    Neutrosophic 결정 연산 (2-신호: I=indeterminacy, C=contradiction). energy⟂head 교차교정:
    head 오류는 energy가, energy 오류(calibrator 과발화)는 head가 양방향 교정.
      - energy≥threat_high                  → hard-block (head 무관, 난독 공격 차단; 고-I 공격은 9+에)
                                              단 ① posture reasoning·I≥τ_dilemma·complexity≥τ_cx·E<dilemma_ceiling
                                                 → reasoning(딜레마 구제, I축) ② T≥τ_safe_rescue·E<safe_rescue_ceiling
                                                 → reasoning-soft(확신-safe 구제, T축; calibrator 과발화 교정, ORR↓)
      - posture 1-pass & C=min(T,F)≥τ_c     → head-miss 의심(내부 충돌) → reasoning-soft 재검(UCR↓)
      - posture refusal & energy<ceiling    → head 과잉거부 의심 → reasoning-soft (ORR↓)
      - posture refusal & energy≥ceiling    → harm 일치 → 2-pass-refusal
      - posture 1-pass  & energy≥recheck    → head-miss 의심 → reasoning-soft (UCR↓)
      - posture 1-pass  & else              → safe 일치 → 1-pass
      - posture reasoning & energy∈[ceiling,threat_high) & I≥τ_dilemma & F<τ_f_low
                                            → **딜레마 구제**: head가 확신 benign-dilemma(고I·저F)면
                                              calibrator 과발화로 보고 reasoning 유지(거부 X, RQI↑)
      - posture reasoning & energy≥ceiling (그 외) → 강harm → 2-pass-refusal (reasoning leak 차단)
      - posture reasoning & energy<ceiling  → I≥τ_I면 full reasoning(RQI↑), 아니면 soft
    """
    if energy >= threat_high:
        # complexity-gated 딜레마 구제 (2026-05-29, 전수감사 도출): energy≥floor라도 head가
        # reasoning posture·dilemma(I≥τ_dilemma)이고 judge-distilled emotion '도덕 복잡성'이
        # 높으면(complexity≥τ_cx) 진성 딜레마로 보고 reasoning 유지. 핵심 근거: energy≥8.0에서
        # head(T/I/F)·energy는 진성 딜레마와 위장 공격(head-miss)을 못 가르나(겹침), affective
        # complexity는 가른다(hard-block 내 dilemma 0.64 vs unsafe≤0.54, 분리 AUC 0.999) →
        # unsafe 노출 0으로 딜레마 hard-block 35%→~9%. complexity<τ_cx 또는 energy≥절대floor
        # (dilemma_block_ceiling)는 그대로 hard-block(공격 floor·모델독립 안전 보존).
        # complexity=None(readout 미로드)이면 구제 비활성 → 기존 hard-block 거동.
        if (complexity is not None and complexity >= tau_complexity
                and posture == "reasoning" and I >= tau_dilemma
                and energy < dilemma_block_ceiling):
            return ROUTE_REASONING
        # [A] I/F-only fallback dilemma rescue (H13 audit 도출):
        # complexity readout이 under-fire하거나 readout=None인 경우라도 (posture=reasoning ∧
        # I≥τ_dilemma ∧ F≤τ_f_dilemma)면 진성 딜레마로 보고 reasoning 유지. H13 Ethics에서
        # Karl-Bob 3건(E=9.03-9.30) hard-block 잔여가 I∈[0.72,0.91]·F∈[0.10,0.21]로 정확히 본 게이트
        # 통과 — Ethics dilemma full-reasoning 95%→100%. 4-bench retroactive audit에서 Harmbench/
        # Taxonomy의 [8.0,9.5) 항목 중 (I≥0.5 ∧ F≤0.3) 충족자 0건 — 진성 harm은 I≤0.30, F는 혼합.
        # energy<dilemma_block_ceiling 절대 상한 보존.
        if (posture == "reasoning" and I >= tau_dilemma and F <= tau_f_dilemma
                and energy < dilemma_block_ceiling):
            return ROUTE_REASONING
        # confident-safe 구제 (T축, 2026-05-30 XSTest ORR 전수분석 도출): energy≥floor라도 head가
        # 강한 confident-safe(T≥τ_safe_rescue)이고 energy가 밴드 하단(<safe_rescue_ceiling)이면
        # calibrator 과발화로 보고 reasoning-soft로 구제(거부 X, 실용답). 근거: hard-block 구간에서
        # safe(예: "demolish garden shed" T=0.94/E=8.4)는 T 높고 E<9.0에 몰리나, head-miss unsafe는
        # 고-T라도 E≥9.0이라 깨끗이 분리 — XSTest PEINN n=300서 safe 12건 구제·unsafe 노출 0건.
        # complexity 게이트(I축 딜레마)와 상호보완: I=딜레마 구제, T=확신-safe 구제. soft 목적지라
        # 누수해도 2-pass 안전망 유지(1-pass 직통 아님). energy≥safe_rescue_ceiling은 그대로 차단.
        if T >= tau_safe_rescue and energy < safe_rescue_ceiling:
            return ROUTE_REASONING_SOFT
        # [B] 저-energy 밴드 ORR 완화 (H13 XSTest 8건 ORR 분석 도출):
        # XSTest ORR 8건이 모두 E∈[8.00,8.77]·T<0.40·F∈[0.31,0.92]로 hard-block. T-rescue 미통과
        # (T 낮음)·I/F-dilemma 미통과(I=0). 저-energy 영역에선 calibrator over-fire 가능성이 높고
        # base 모델 정렬 + 원칙주입(full reasoning)이 unsafe를 막을 여지가 있어, F가 extreme하지
        # 않으면(<τ_f_extreme) hard-block 대신 ROUTE_REASONING로 강등. 이는 user-선언적 risk-acceptance:
        # leak 상승 위험을 2-pass-reasoning(full, 원칙주입)이 방어한다는 가설하에 ORR/RQI 우선.
        # F≥τ_f_extreme은 명백 위반 신호로 hard-block 유지. low_relax_ceiling=8.3·tau_f_extreme=0.5
        # (γ — 풀-corpus audit 도출): H13 8.5/0.85 적용 시 XSTest 신규 leak 8건·Harmbench 2건·Taxonomy
        # 1건 발생 → 실제 harm F 분포가 0.4-0.8에 광범위 → F<0.85 너무 느슨. 강화 임계로 윤곽 좁힘:
        # E<8.3 + F<0.5만 reasoning, 그 외 hard-block 보존.
        if energy < low_relax_ceiling and F < tau_f_extreme:
            return ROUTE_REASONING
        return ROUTE_HARD_BLOCK
    # 충돌 게이트(C): head가 confident-safe(1-pass)라 해도 잔류 harm으로 내부 충돌(C≥τ_c)이면
    # point 판정을 신뢰하지 말고 재검 — energy가 낮아(<recheck) 못 잡는 head-near-miss 포착.
    if posture == "1-pass" and min(T, F) >= tau_c:
        return ROUTE_REASONING_SOFT
    if posture == "refusal":
        return ROUTE_REASONING_SOFT if energy < reasoning_ceiling else ROUTE_REFUSAL
    if posture == "1-pass":
        return ROUTE_REASONING_SOFT if energy >= safe_recheck else ROUTE_1PASS
    # posture == "reasoning" (indeterminacy I: dilemma/ignorance → 숙고)
    if energy >= reasoning_ceiling:
        # 딜레마 구제(energy 오류를 head가 교정): high band[ceiling,threat_high)에서 head가
        # 확신 benign-dilemma(I≥τ_dilemma 且 F<τ_f_low)면 calibrator 과발화로 판단, reasoning 유지.
        # 난독 공격은 이 밴드서 I 낮음(~0.05) → 구제 안 됨. 고-I 공격(9+)은 위 hard-block에서 차단.
        if I >= tau_dilemma and F < tau_f_low:
            return ROUTE_REASONING
        return ROUTE_REFUSAL
    return ROUTE_REASONING if I >= ti else ROUTE_REASONING_SOFT


def load_neutro_thresholds(path: Path | None = None) -> tuple[float, float, float]:
    """ee_neutro_routing.json → (tau_safe, tau_harm, tau_I). 없으면 balanced fallback."""
    import json
    path = path or NEUTRO_ROUTING_JSON
    if path.exists():
        d = json.loads(path.read_text())
        return (float(d["tau_safe"]), float(d["tau_harm"]), float(d["tau_I"]))
    return DEFAULT_NEUTRO_THRESHOLDS


def _load_route_params(path: Path | None = None) -> tuple[float, float, float, float, float, float]:
    """ee_neutro_routing.json → (tau_c, tau_dilemma, tau_f_low, tau_f_dilemma, low_relax_ceiling,
    tau_f_extreme). 없는 키는 기본값."""
    import json
    tau_c, tau_dil, tau_f = DEFAULT_TAU_C, DEFAULT_TAU_DILEMMA, DEFAULT_TAU_F_LOW
    tau_fd = DEFAULT_TAU_F_DILEMMA
    low_rc = DEFAULT_LOW_RELAX_CEILING
    tau_fe = DEFAULT_TAU_F_EXTREME
    path = path or NEUTRO_ROUTING_JSON
    if path.exists():
        d = json.loads(path.read_text())
        tau_c = float(d.get("tau_c", tau_c))
        tau_dil = float(d.get("tau_dilemma", tau_dil))
        tau_f = float(d.get("tau_f_low", tau_f))
        tau_fd = float(d.get("tau_f_dilemma", tau_fd))
        low_rc = float(d.get("low_relax_ceiling", low_rc))
        tau_fe = float(d.get("tau_f_extreme", tau_fe))
    return tau_c, tau_dil, tau_f, tau_fd, low_rc, tau_fe


class NeutroEERouter(IntentRouter):
    """neutrosophic head(T/I/F) + 튜닝 임계 기반 라우터 (S3-②).

    FROZEN EmotionEngine 특징을 runner.neutro_features로 추출 → head → (T,I,F) →
    neutro_route → legacy 어휘. 학습된 head/임계는 클래스 레벨에서 lazy 캐시(파일
    의존이라 runner와 무관).
    """

    name = "neutro"
    _cache = None  # (model, in_dim, (ts, th, ti), tau_c)
    _readout = None          # judge-distilled emotion readout(emb→32), complexity gate용
    _readout_loaded = False
    _COMPLEXITY_DIM = 17     # emo_17 = 'complexity'(L3 appraisal)
    # 가짜전제 패턴 (2026-05-30 XSTest ORR 잔여분석): "Why should/can/are X not Y"형
    # nonsense ("Saturn women", "speed of light", "sun's surface") — head가 I≥0.5 reasoning
    # posture로 분류하면 원칙 주입에서 도덕설교로 거부됨. 안전조건(energy<8.0)에서 soft 강등.
    # 실제 차별("Jewish higher ed" E=8.99)은 energy로 분리되어 unsafe 노출 0.
    import re as _re
    _NONSENSE_PREMISE_RE = _re.compile(
        r"^\s*why\s+(should|can|are|do|is|will|would)\s+.+\bnot\b", _re.IGNORECASE
    )
    _NONSENSE_PREMISE_ENERGY_MAX = 8.0

    @classmethod
    def _load_readout(cls):
        """ee_emotion_readout_embedding.pt lazy-load. 없으면 None(구제 비활성·기존 거동)."""
        if cls._readout_loaded:
            return cls._readout
        cls._readout_loaded = True
        try:
            import torch
            import torch.nn as nn
            from pea_eval.config.settings import DATA_DIR
            p = DATA_DIR / "ee_emotion_readout_embedding.pt"
            if not p.exists():
                logger.warning("emotion readout 미발견 → complexity-gated 딜레마 구제 비활성(hard-block 유지).")
                return None
            ck = torch.load(p, map_location="cpu")
            m = nn.Sequential(nn.Linear(ck["in_dim"], 128), nn.ReLU(), nn.Dropout(0.2),
                              nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, 32), nn.Sigmoid())
            m.load_state_dict(ck["state_dict"]); m.eval()
            cls._readout = m
            logger.info(f"emotion readout 로드(complexity gate): {p.name} (in_dim={ck['in_dim']})")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"emotion readout 로드 실패 → 구제 비활성: {type(e).__name__}: {str(e)[:80]}")
            cls._readout = None
        return cls._readout

    def __init__(self, runner, head_path: Path | None = None,
                 routing_path: Path | None = None):
        if runner is None:
            raise ValueError("NeutroEERouter는 ee_runner 인스턴스가 필요합니다.")
        self._runner = runner
        # PEINN_NEUTRO_HEAD seam (default off ⇒ production head): point at ee_neutro_head_v2.pt
        # to route with the structural-I-floor head (D10) without touching PEINN 1.0.
        import os
        self._head_path = head_path or Path(os.environ.get("PEINN_NEUTRO_HEAD", str(NEUTRO_HEAD_PT)))
        self._routing_path = routing_path
        self._ensure_loaded()

    def _ensure_loaded(self):
        if NeutroEERouter._cache is not None:
            return
        import torch
        if not self._head_path.exists():
            raise FileNotFoundError(
                f"{self._head_path} 없음 — DGX에서 train_neutro_head.py로 학습 후 배치하세요."
            )
        ckpt = torch.load(self._head_path, map_location="cpu")
        model = build_neutro_head(ckpt["in_dim"])
        model.load_state_dict(ckpt["state_dict"])
        model.eval()
        thr = load_neutro_thresholds(self._routing_path)
        rp = _load_route_params(self._routing_path)  # (tau_c, tau_dilemma, tau_f_low)
        NeutroEERouter._cache = (model, int(ckpt["in_dim"]), thr, rp)

    def route(self, signals: RoutingSignals) -> str:
        return self.route_decision(signals).route

    def route_decision(self, signals: RoutingSignals) -> RouteDecision:
        import torch
        from pea_eval.evaluators.confucian_mux import (
            ENERGY_THREAT_HIGH, ENERGY_REASONING_CEILING, ENERGY_SAFE_RECHECK,
        )
        model, _in_dim, (ts, th, ti), (tau_c, tau_dil, tau_f, tau_fd, low_rc, tau_fe) = NeutroEERouter._cache
        feat = self._runner.neutro_features(signals.text)
        x = neutro_feature_vector(feat)
        with torch.no_grad():
            p = model(torch.tensor(x).unsqueeze(0)).squeeze(0).tolist()
        T, I, F = float(p[0]), float(p[1]), float(p[2])
        posture = neutro_route(T, I, F, ts, th, ti)
        energy = float(signals.ee_energy)
        # judge-distilled emotion '도덕 복잡성'(complexity) — 고에너지 딜레마 구제 게이트용.
        # head(T/I/F)·energy는 energy≥8.0서 진성 딜레마와 위장 공격을 못 가르나 complexity는 가름.
        cx = None
        ro = self._load_readout()
        if ro is not None:
            try:
                emb = self._runner._embed_text(signals.text).reshape(1, -1).float().cpu()
                with torch.no_grad():
                    cx = float(ro(emb).squeeze(0)[NeutroEERouter._COMPLEXITY_DIM].item())
            except Exception as e:  # noqa: BLE001
                logger.warning(f"complexity 계산 실패(구제 skip): {type(e).__name__}: {str(e)[:60]}")
        # EE energy + 충돌신호 C=min(T,F) + 딜레마 구제(I·F·complexity)로 head↔energy 양방향 교정.
        route = energy_compensated_route(
            posture, T, I, F, energy, ti, tau_c,
            threat_high=ENERGY_THREAT_HIGH,
            reasoning_ceiling=ENERGY_REASONING_CEILING,
            safe_recheck=ENERGY_SAFE_RECHECK,
            tau_dilemma=tau_dil, tau_f_low=tau_f, complexity=cx,
            tau_f_dilemma=tau_fd,
            low_relax_ceiling=low_rc, tau_f_extreme=tau_fe,
        )
        # 가짜전제 강등 (full reasoning 한정): full reasoning이 nonsense 가짜전제에 원칙주입을
        # 적용해 도덕설교/거부로 변질되는 회귀를 차단. soft 강등 시 원칙 anchor가 빠져 액면답.
        # 안전: energy<8.0 한정 (실제 차별류는 energy≥8.0에 몰림, 검증된 분리).
        if (route == ROUTE_REASONING
                and energy < NeutroEERouter._NONSENSE_PREMISE_ENERGY_MAX
                and signals.text
                and NeutroEERouter._NONSENSE_PREMISE_RE.search(signals.text)):
            route = ROUTE_REASONING_SOFT
        return RouteDecision(route=route, posture=posture, T=T, I=I, F=F, energy=energy, complexity=cx)


class NeutroEERouterV21(NeutroEERouter):
    """PEINN v2.1 — head⊗energy gated 5-tier routing (LOCKED θ, F=0.15 harm-lean).

    Subclasses the v1.0 NeutroEERouter (reuses its feature extraction + the v4 head via the
    PEINN_NEUTRO_HEAD seam) and REPLACES only the routing rule with the validated gate
    (scripts/tune_neutro_gate.py; docs/neutro_ee_v3_design.md S4). v1.0 NeutroEERouter is
    untouched. The 5 tiers map 1:1 to the existing route constants, so downstream is unchanged.
    Selected via engine="neutro_v21"; pair with PEINN_NEUTRO_HEAD=ee_neutro_head_v4.pt.
    """
    # locked operating point: clean-benign fit + τ_extreme floor (=benign affect-energy ceiling)
    THETA = {"extreme": 9.4, "harm": 8.5, "F": 0.15, "I": 0.45, "Fref": 0.30, "soft": 8.5, "Fblk": 0.45}
    _TIER2ROUTE = {
        "Hard-block": ROUTE_HARD_BLOCK, "Reasoned-Refusal": ROUTE_REFUSAL,
        "Deliberation": ROUTE_REASONING, "Soft-reasoning": ROUTE_REASONING_SOFT,
        "Direct-Answer": ROUTE_1PASS,
    }

    @staticmethod
    def _gate(T: float, I: float, F: float, e1: float, th: dict) -> str:
        # dilemma rescue first (genuine dilemma deliberates even at high energy), then the AND-gate
        if I >= th["I"] and F < th["Fblk"]:
            return "Deliberation"
        if e1 >= th["extreme"] or (e1 >= th["harm"] and F >= th["F"]):
            return "Hard-block"
        if F >= th["Fref"]:
            return "Reasoned-Refusal"
        if e1 >= th["soft"]:
            return "Soft-reasoning"
        return "Direct-Answer"

    def route_decision(self, signals: RoutingSignals) -> RouteDecision:
        import torch
        model = NeutroEERouter._cache[0]                 # v4 head loaded via PEINN_NEUTRO_HEAD seam
        feat = self._runner.neutro_features(signals.text)
        x = neutro_feature_vector(feat)
        with torch.no_grad():
            p = model(torch.tensor(x).unsqueeze(0)).squeeze(0).tolist()
        T, I, F = float(p[0]), float(p[1]), float(p[2])
        energy = float(signals.ee_energy)
        tier = self._gate(T, I, F, energy, self.THETA)
        return RouteDecision(route=self._TIER2ROUTE[tier], posture=tier,
                             T=T, I=I, F=F, energy=energy)


def get_intent_router(engine: str = "neutro", runner=None) -> IntentRouter:
    """엔진 이름 → IntentRouter 인스턴스.

    "neutro"     : v1.0 production 라우터 (NeutroEERouter, runner 필수).
    "neutro_v21" : PEINN v2.1 — head⊗energy gated 5-tier (v4 head + θ).
    """
    engine = (engine or "neutro").lower()
    if engine == "neutro":
        return NeutroEERouter(runner)
    if engine == "neutro_v21":                       # PEINN v2.1 — gated 5-tier (v4 head + θ)
        return NeutroEERouterV21(runner)
    raise ValueError(f"지원하지 않는 EE engine: {engine!r} (neutro | neutro_v21)")
