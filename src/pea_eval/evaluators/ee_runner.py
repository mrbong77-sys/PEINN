"""
PEINN UNESCO Eval — EE/PEINN 반추 루프 러너
평가 파이프라인에서 Emotion Engine + PEINN 감쇠 반추 루프를 실행합니다.

기존 core/emotion_engine.py의 EmotionEngine과
core/peinn.py의 PEINN을 직접 사용합니다.
"""
import logging
import re
from pathlib import Path
from typing import Optional

import torch

logger = logging.getLogger("peinn.pea_eval.ee_runner")


import os

# ── Embedder policy (two independent embedders, do NOT conflate) ───────
# EE_INPUT_EMBEDDER : feeds the pretrained EE neural net (which expects
#                     384-dim input — DO NOT change unless EE is also
#                     retrained from scratch).
# CALIBRATOR_SEM_EMBEDDER : separate sentence embedder used ONLY for the
#                     calibrator's semantic-concat input. The shipped
#                     calibrator was trained on mpnet (768d) — its input is
#                     32 (affect) + 768 (mpnet) = 800. EE pretrained weights
#                     stay valid because EE never sees this embedder's output.
# Override either via env.
EE_INPUT_EMBEDDER = os.environ.get(
    "PEAOS_EE_INPUT_EMBEDDER", "sentence-transformers/all-MiniLM-L6-v2"
)
# Default = mpnet to match the shipped 800-d calibrator; a MiniLM (384-d)
# calibrator input would be 416-d and mismatch the checkpoint.
CALIBRATOR_SEM_EMBEDDER = os.environ.get(
    "PEAOS_CALIBRATOR_EMBEDDER", "sentence-transformers/all-mpnet-base-v2"
)
_EMBEDDER_DIM_MAP = {
    "sentence-transformers/all-MiniLM-L6-v2": 384,
    "all-MiniLM-L6-v2": 384,
    "sentence-transformers/all-mpnet-base-v2": 768,
    "all-mpnet-base-v2": 768,
    "sentence-transformers/all-MiniLM-L12-v2": 384,
    "BAAI/bge-large-en-v1.5": 1024,
    "BAAI/bge-base-en-v1.5": 768,
}
EE_INPUT_DIM = _EMBEDDER_DIM_MAP.get(EE_INPUT_EMBEDDER, 384)
CALIBRATOR_SEM_DIM = _EMBEDDER_DIM_MAP.get(CALIBRATOR_SEM_EMBEDDER, 384)

# Back-compat aliases for callers that imported the old names
EMBEDDER_MODEL_NAME = EE_INPUT_EMBEDDER
EMBEDDER_DIM = CALIBRATOR_SEM_DIM


class HybridCalibrator(torch.nn.Module):
    """Emotion Vector(32) + Semantic Embedding(sem_dim) 결합 판별기.
    sem_dim defaults to CALIBRATOR_SEM_DIM so a mpnet swap on the
    calibrator side does not require this class to be edited."""
    def __init__(self, emo_dim=32, sem_dim=None, hidden_dim=64):
        super(HybridCalibrator, self).__init__()
        if sem_dim is None:
            sem_dim = CALIBRATOR_SEM_DIM
        self.sem_dim = sem_dim
        self.net = torch.nn.Sequential(
            torch.nn.Linear(emo_dim + sem_dim, hidden_dim),
            torch.nn.ReLU(),
            torch.nn.Dropout(0.2),
            torch.nn.Linear(hidden_dim, 32),
            torch.nn.ReLU(),
            torch.nn.Linear(32, 1),
            torch.nn.Sigmoid()
        )
        
    def forward(self, x):
        return self.net(x)


class EvalEERunner:
    """
    평가용 EE + PEINN 반추 루프 러너.

    Core Components:
      - EmotionEngine: 텍스트 → 32D 감정 벡터 + 에너지 레벨
      - PEINN: 감쇠 법칙 기반 무한 루프 방지
      - SentenceTransformer: 텍스트 → 임베딩 변환 (EE 입력용)

    사용 흐름:
      1. initialize()로 EE/PEINN 로드
      2. run_reflection_loop()로 반추 실행
    """

    # ── 듀얼 싱글톤: 기존 PEINN / Reverse PEINN 분리 ──
    _instances: dict = {}  # {False: 기존, True: Reverse}

    @classmethod
    def get_instance(cls, ee_config=None, reverse_peinn: bool = False) -> "EvalEERunner":
        """기존 초기화된 인스턴스를 반환합니다. 없으면 새로 생성."""
        existing = cls._instances.get(reverse_peinn)
        if existing is not None and existing._initialized:
            logger.debug(f"EE Runner 싱글톤 인스턴스 재사용 (reverse={reverse_peinn})")
            return existing
        instance = cls(ee_config, reverse_peinn=reverse_peinn)
        cls._instances[reverse_peinn] = instance
        return instance

    def __init__(self, ee_config=None, reverse_peinn: bool = False):
        """
        Args:
            ee_config: pea_eval.config.settings.EEConfig 인스턴스
            reverse_peinn: True이면 공리주의 Golden Anchors 사용
        """
        self.ee_config = ee_config
        self._reverse_peinn = reverse_peinn
        self._ee_model = None        # EmotionEngine
        self._peinn = None           # PEINN
        self._embedder = None        # SentenceTransformer
        self._memory_bank = None     # MemoryBank (RAG용)
        self._golden_anchors = None
        self.model = None
        self._calibrator = None      # Hybrid Neural Calibrator
        self._initialized = False

        # [NEW] 유해성 판단 감정 가중치 및 임계값
        self.risk_weights = {
            "outrage": 3.0,
            "disgust": 2.5,
            "hostility": 2.5,
            "fear": 1.5,
            "anger": 1.5,
            "contempt": 2.0
        }
        self.fast_pass_threshold = 0.55  # 1-pass 허용 에너지 상한

    def initialize(self):
        """
        EmotionEngine, PEINN, SentenceTransformer를 초기화합니다.
        GPU가 있으면 GPU 사용, 없으면 CPU.
        """
        if self._initialized:
            return

        cfg = self.ee_config

        # 디바이스 결정
        if torch.cuda.is_available():
            self._device = torch.device("cuda")
        else:
            self._device = torch.device("cpu")
        logger.info(f"EE Runner 디바이스: {self._device}")

        # 1) EmotionEngine 초기화
        # Deterministic construction: the EE consumes RNG at build time (random init /
        # non-persistent buffers) that the checkpoint does NOT cover (strict load only
        # restores params). Unseeded, this differed per process launch -> the calibrator
        # energy (and thus the >=8.5 hard-block safety floor) wobbled run-to-run across
        # the 5-run trials. Seed construction with a FIXED value (matches the paper
        # dataset builder, seed 0), then restore the global RNG so LLM-generation
        # run-to-run variance is unaffected.
        from core.emotion_engine import EmotionEngine
        _rng_state = torch.get_rng_state()
        _cuda_rng_state = (
            torch.cuda.get_rng_state_all() if torch.cuda.is_available() else None
        )
        torch.manual_seed(0)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(0)
        self._ee_model = EmotionEngine(
            embedding_dim=cfg.embedding_dim,
            hidden_dim=cfg.hidden_dim,
            num_heads=cfg.num_attention_heads,
            num_layers=cfg.num_layers,
        ).to(self._device)
        torch.set_rng_state(_rng_state)
        if _cuda_rng_state is not None:
            torch.cuda.set_rng_state_all(_cuda_rng_state)
        self._ee_model.eval()

        # 체크포인트 로드 시도 (Agent A를 기본으로)
        self._ee_checkpoints = {}
        for agent_id, ckpt_path_str in [
            ("A", cfg.checkpoint_agent_a),
            ("B", cfg.checkpoint_agent_b),
        ]:
            ckpt_path = Path(ckpt_path_str)
            if ckpt_path_str and ckpt_path.is_file():
                try:
                    state = torch.load(
                        str(ckpt_path),
                        map_location=self._device,
                        weights_only=False,
                    )
                    # 체크포인트 구조에 따라 적절히 로드
                    if isinstance(state, dict) and "model_state_dict" in state:
                        self._ee_checkpoints[agent_id] = state["model_state_dict"]
                    elif isinstance(state, dict) and "ee_state" in state:
                        self._ee_checkpoints[agent_id] = state["ee_state"]
                    elif isinstance(state, dict) and "ee_state_dict" in state:
                        self._ee_checkpoints[agent_id] = state["ee_state_dict"]
                    else:
                        self._ee_checkpoints[agent_id] = state
                    logger.info(
                        f"EE 체크포인트 로드 성공: Agent {agent_id} ← {ckpt_path.name}"
                    )
                except Exception as e:
                    logger.warning(
                        f"EE 체크포인트 로드 실패 (Agent {agent_id}): {e}"
                    )

        # 2) PEINN 초기화
        from core.peinn import PEINN
        self._peinn = PEINN(
            damping_factor=cfg.damping_factor,
            energy_threshold=cfg.energy_threshold,
            max_reflection_rounds=cfg.max_reflection_rounds,
        )

        self._fast_pass_threshold = cfg.fast_pass_threshold
        logger.info(f"EE Threshold: {self._fast_pass_threshold}")

        try:
            from sentence_transformers import SentenceTransformer
            # EE input embedder — feeds the pretrained EE neural net (384d expected).
            try:
                self._embedder = SentenceTransformer(
                    EE_INPUT_EMBEDDER, device=str(self._device), local_files_only=True,
                )
                logger.info(f"EE input embedder loaded (offline): {EE_INPUT_EMBEDDER} dim={EE_INPUT_DIM}")
            except Exception:
                self._embedder = SentenceTransformer(EE_INPUT_EMBEDDER, device=str(self._device))
                logger.info(f"EE input embedder loaded (online): {EE_INPUT_EMBEDDER} dim={EE_INPUT_DIM}")

            # Calibrator semantic embedder — only loaded separately if differs.
            if CALIBRATOR_SEM_EMBEDDER == EE_INPUT_EMBEDDER:
                self._calibrator_embedder = self._embedder
                logger.info(f"Calibrator embedder: shared with EE ({CALIBRATOR_SEM_EMBEDDER})")
            else:
                try:
                    self._calibrator_embedder = SentenceTransformer(
                        CALIBRATOR_SEM_EMBEDDER, device=str(self._device), local_files_only=True,
                    )
                    logger.info(f"Calibrator embedder loaded (offline): {CALIBRATOR_SEM_EMBEDDER} dim={CALIBRATOR_SEM_DIM}")
                except Exception:
                    self._calibrator_embedder = SentenceTransformer(
                        CALIBRATOR_SEM_EMBEDDER, device=str(self._device),
                    )
                    logger.info(f"Calibrator embedder loaded (online): {CALIBRATOR_SEM_EMBEDDER} dim={CALIBRATOR_SEM_DIM}")
        except ImportError:
            logger.warning(
                "sentence-transformers 미설치. EE 임베딩 불가 — "
                "랜덤 임베딩으로 대체합니다."
            )

        # 4) (removed) MemoryBank / RAG — this was a PEA-OS long-term-memory feature,
        #    not part of the PEINN v2.1 routing path. self._memory_bank stays None, so
        #    the downstream None-guards below are inert.

        # 5) Hybrid Calibrator 로드 (Gatekeeping 전용)
        calibrator_path = Path("pea_eval/data/ee_hybrid_calibrator_best.pt")
        if calibrator_path.is_file():
            try:
                self._calibrator = HybridCalibrator().to(self._device)
                self._calibrator.load_state_dict(torch.load(calibrator_path, map_location=self._device))
                self._calibrator.eval()
                logger.info(f"Hybrid Calibrator 로드 완료: {calibrator_path.name}")
            except Exception as e:
                logger.warning(f"Hybrid Calibrator 로드 실패: {e}")

        # 5b) Dilemma Classifier 로드 (HybridCalibrator와 대칭 구조).
        # 모델 파일이 없으면 graceful no-op으로 동작 — 기존 파이프라인
        # 영향 없음. 학습된 후엔 라우터의 dilemma_label 분기를 활성화.
        try:
            from pea_eval.evaluators.dilemma_runner import DilemmaRunner
            self._dilemma_runner = DilemmaRunner.get_instance()
            # mpnet embedder는 calibrator와 공유 (재로드 회피)
            self._dilemma_runner.attach_embedder(self._calibrator_embedder)
        except Exception as e:
            logger.warning(f"Dilemma Runner 초기화 실패: {e}")
            self._dilemma_runner = None

        # 5c) Anchor Category Classifier 로드 (Emotion/Dilemma와 동일 패러다임의
        # 3번째 input-side 학습기). 상황→윤리 전통 6분류로 anchor 선택을 보강.
        # 모델 미존재 시 no-op → 글로벌 cosine fallback.
        try:
            from pea_eval.evaluators.anchor_category_runner import AnchorCategoryRunner
            self._anchor_cat_runner = AnchorCategoryRunner.get_instance()
            self._anchor_cat_runner.attach_embedder(self._calibrator_embedder)
        except Exception as e:
            logger.warning(f"Anchor Category Runner 초기화 실패: {e}")
            self._anchor_cat_runner = None

        # 6) Golden Anchors 로드 (도덕 기준점 — RAG에 우선 주입)
        try:
            if self._reverse_peinn:
                from core.golden_anchors_reverse import ReverseGoldenAnchors
                self._golden_anchors = ReverseGoldenAnchors(
                    embedding_dim=cfg.embedding_dim,
                    embedder=self._embedder,  # 로드된 모델 공유
                )
                self._golden_anchors.initialize_defaults()
                logger.info(
                    f"Reverse Golden Anchors 로드 완료: {self._golden_anchors.size}개 "
                    f"(공리주의/결과론)"
                )
            else:
                from core.golden_anchors import GoldenAnchors
                self._golden_anchors = GoldenAnchors(
                    embedding_dim=cfg.embedding_dim,
                    embedder=self._embedder,  # 로드된 모델 공유
                )
                self._golden_anchors.initialize_defaults()
                logger.info(
                    f"Golden Anchors 로드 완료: {self._golden_anchors.size}개 도덕 기준점"
                )
        except Exception as e:
            logger.warning(f"Golden Anchors 로드 실패 (RAG만 사용): {e}")

        self._initialized = True
        logger.info("EE Runner 초기화 완료")

    def reset_state(self):
        """내부 PEINN 상태를 리셋합니다."""
        if self._peinn:
            self._peinn.reset()

    def _load_ee_weights(self, agent_profile: str):
        """Agent 프로필에 맞는 EE 가중치를 로드합니다."""
        if agent_profile in self._ee_checkpoints:
            self._ee_model.load_state_dict(self._ee_checkpoints[agent_profile])
            logger.debug(f"EE Weights loaded for Agent {agent_profile}")
        else:
            # Fail loud: the 32-d affect on the routing path comes from this
            # trunk. Missing it would leave the EmotionEngine at random init and
            # silently invalidate every routing decision.
            ck = getattr(self.ee_config, f"checkpoint_agent_{agent_profile.lower()}", "")
            raise FileNotFoundError(
                f"EmotionEngine trunk for Agent {agent_profile} is not loaded — "
                f"expected checkpoint at '{ck}'. Copy "
                f"ee_checkpoint_agent_{agent_profile.lower()}.pt into the data "
                f"directory (see checkpoints/README.md). Without it the 32-d "
                f"affect is undefined and routing is invalid."
            )
        # Frozen inference must be deterministic: enforce eval() at every inference
        # entry (this method gates analyze_emotion / neutro_features / batch). The EE
        # has no random op beyond Dropout, so eval() makes the forward fully
        # reproducible — the energy gate (>=8.5) is a safety floor and must not wobble
        # run-to-run if a warm singleton was ever left in train() mode.
        self._ee_model.eval()

    def _embed_text(self, text: str) -> torch.Tensor:
        """텍스트를 임베딩 벡터로 변환합니다."""
        if self._embedder is not None:
            emb = self._embedder.encode([text], convert_to_numpy=True)
            return torch.tensor(emb, dtype=torch.float32).to(self._device)
        return torch.randn(1, self.ee_config.embedding_dim).to(self._device)

    def analyze_emotion(self, text: str, agent_profile: str = "A") -> tuple[torch.Tensor, float, str]:
        """
        텍스트의 감정을 분석하고 가중 에너지를 계산합니다.
        
        Returns:
            (emotion_vector, weighted_energy, emotion_text)
        """
        if not self._initialized:
            self.initialize()

        self._load_ee_weights(agent_profile)
        text_embedding = self._embed_text(text)
        input_emb = text_embedding.unsqueeze(1) # (1, 1, dim)

        # ── 메모리 벡터 (EE 전용) ──
        if self._memory_bank is not None and self._memory_bank.size > 0:
            try:
                _, _, weighted = self._memory_bank.search(text_embedding.squeeze(0), top_k=5)
                memory_vectors = weighted.unsqueeze(0).to(self._device) # (1, 5, dim)
            except Exception as e:
                logger.warning(f"EE Memory search failed: {e}")
                memory_vectors = torch.zeros(1, 1, self.ee_config.embedding_dim).to(self._device)
        else:
            memory_vectors = torch.zeros(1, 1, self.ee_config.embedding_dim).to(self._device)

        # Forward Pass
        with torch.no_grad():
            output = self._ee_model(input_emb, memory_vectors)

        emotion_vector = output["emotion_vector"] # (1, 32)
        base_energy = output["energy_level"].item()

        # ── Hybrid Calibration (Gatekeeping) ──
        # 유저 요청: 판별용 에너지만 조정하고, 감정 벡터는 원본 그대로 MUX에 전달
        if self._calibrator is not None:
            try:
                with torch.no_grad():
                    # Calibrator semantic input — separate embedder if env says so,
                    # otherwise reuse the EE input embedding (back-compat path).
                    if self._calibrator_embedder is self._embedder:
                        sem_embedding = text_embedding
                    else:
                        sem_np = self._calibrator_embedder.encode([text], convert_to_numpy=True)
                        sem_embedding = torch.tensor(sem_np, dtype=torch.float32).to(self._device)
                    # If the calibrator was trained with PEAOS_NORMALIZE_HYBRID_FEATURES=1,
                    # the same L2 normalisation MUST be applied at inference time per
                    # channel; otherwise train/test feature distributions diverge and
                    # the calibrator's discrimination collapses silently.
                    if os.environ.get("PEAOS_NORMALIZE_HYBRID_FEATURES", "0") == "1":
                        emo_n = emotion_vector / (emotion_vector.norm(dim=1, keepdim=True) + 1e-8)
                        sem_n = sem_embedding / (sem_embedding.norm(dim=1, keepdim=True) + 1e-8)
                        hybrid_input = torch.cat([emo_n, sem_n], dim=1)
                    else:
                        hybrid_input = torch.cat([emotion_vector, sem_embedding], dim=1)
                    prob = self._calibrator(hybrid_input).item()
                    # 확률(0~1)을 10점 만점 에너지로 스케일링
                    weighted_energy = prob * 10.0
                    logger.debug(f"Hybrid Calibrated Energy: {weighted_energy:.4f} (Prob: {prob:.4f})")
            except Exception as e:
                logger.warning(f"Hybrid Calibration 실패: {e}")
                weighted_energy = base_energy
        else:
            # Calibrator가 없으면 기존 베이스 에너지 사용
            weighted_energy = base_energy

        # ── Benign-Trick Detector 보조 보정 — 회수됨 ──
        # 2026-05-30 sem embedder mismatch 봉합 후 audit: ★XSTest ASR LEAK 8→24건(+16) 회귀.
        # 봉합으로 detector 차감이 실제 발화하기 시작했으나, OOD에서 진짜 유해까지 양성 분류:
        # 자살(hang/drown), 폭발물(blow up house), 마약(buy coke), 폭력(axe attack), 유아 살해 추정,
        # 가정폭력, 차별/역사정당화 16건이 E 7대로 떨어져 hard-block 누수. AUC 0.9989(train)는 OOD
        # 일반화 신호 아님 — 학습 데이터 300건 한정.
        # 회수: detector 분기 환경변수로 비활성화(기본). 향후 재설계 시 PEAOS_BENIGN_DETECTOR=1로
        # 명시적 활성. detector .pt 자체는 git tracked 유지(연구 reproducibility).
        if os.environ.get("PEAOS_BENIGN_DETECTOR", "0") == "1":
            try:
                from pea_eval.evaluators.benign_detector import load_detector, adjust_energy, CKPT_PATH_DEFAULT
                if not hasattr(self, "_benign_detector_cache"):
                    self._benign_detector_cache = load_detector()
                    if self._benign_detector_cache is not None:
                        logger.warning(f"BenignTrickDetector ACTIVE (PEAOS_BENIGN_DETECTOR=1, HANDOFF-33 회수 대상): "
                                       f"{CKPT_PATH_DEFAULT.name} — OOD ASR 회귀 위험 인지하고 사용")
                det = self._benign_detector_cache
                if det is not None:
                    sem_for_det = text_embedding  # 학습과 동일한 _embed_text 결과
                    prev_E = weighted_energy
                    weighted_energy, _bp = adjust_energy(
                        weighted_energy, emotion_vector, sem_for_det, det,
                    )
                    if abs(weighted_energy - prev_E) > 0.01:
                        logger.debug(f"detector adjust: {prev_E:.2f} → {weighted_energy:.2f} (benign_p={_bp:.3f})")
            except Exception as e:  # noqa: BLE001
                logger.warning(f"BenignTrickDetector 보정 skip(EXCEPTION): {type(e).__name__}: {str(e)[:100]}")

        # 감정 텍스트 생성
        emotion_text = self._ee_model.generate_emotion_text(emotion_vector)

        # ── PEINN v2.0 energy seam (opt-in, default OFF) ──
        # The one sanctioned v1→v2 touch-point (peinn_v2 DECISIONS D7). The 32-D emotion vector
        # is untouched (energy is affect-free). Modes via PEINN_V2_ENERGY:
        #   "1"/"rescue" — v2 only RESCUES: when it is confident the request is benign-purpose
        #       (v2e < BENIGN_TH), cap the routing energy below hard-block into the 2-pass band
        #       ([safe_recheck 7.3, threat_high 8.0) → reasoning, never 1-pass, never hard-block).
        #       v2 only LOWERS energy; v1 stays the blocker, so harmful that v2 under-scores
        #       (e.g. jailbreak framing) still lands in the 2-pass net, not a direct answer.
        #   "replace" — wholesale swap (research/A-B only; leaks framed-harmful to 1-pass, E8).
        _v2mode = os.environ.get("PEINN_V2_ENERGY", "")
        if _v2mode in ("1", "rescue", "replace"):
            try:
                from peinn_v2.energy import score_energy
                v2e = score_energy(text)
                if _v2mode == "replace":
                    weighted_energy = v2e
                elif v2e < float(os.environ.get("PEINN_V2_BENIGN_TH", "2.0")):
                    weighted_energy = min(weighted_energy,
                                          float(os.environ.get("PEINN_V2_RESCUE_CEIL", "7.9")))
            except Exception as e:  # noqa: BLE001
                logger.warning(f"PEINN_V2_ENERGY on but scoring failed; using v1 energy: "
                               f"{type(e).__name__}: {str(e)[:100]}")

        return emotion_vector, weighted_energy, emotion_text

    def neutro_features(self, text: str, agent_profile: str = "A") -> dict:
        """NeutroEE 입력 특징 추출 — FROZEN EmotionEngine, HybridCalibrator 우회.

        학습(특징 추출)과 NeutroEERouter(추론)가 동일 메서드를 공유해 train/inference
        일관성을 보장한다. head 입력 벡터는 [emotion32 ⊕ semantic_emb ⊕ principle_emb]
        (neutro_feature_vector). semantic_emb(입력 텍스트 임베딩)을 추가한 건 EXP-10
        결과 — 동결 EE의 emotion32만으론 T/I/F 분별력이 약해(F AUC 0.69), 입력을 직접
        보는 semantic 신호가 필요(calibrator 94%의 핵심). native energy는 무변별이라
        head 입력에서 제외하고 dict에만 남겨 라우팅 게이트(별도 채널)로 쓴다.

        Returns dict: emotion(np[32]), semantic_emb(np[D]), energy(float),
                      principle_emb(np[D]), rag_similarity(float), anchor_idx(int),
                      anchor_text(str)
        """
        import numpy as np
        if not self._initialized:
            self.initialize()
        self._load_ee_weights(agent_profile)
        text_embedding = self._embed_text(text)           # (1, D)
        input_emb = text_embedding.unsqueeze(1)            # (1, 1, D)
        # NeutroHead feature는 memory 컨텍스트를 섞지 않는다(zeros). 92244-벡터
        # MemoryBank를 attention에 넣으면 emotion 벡터가 memory 내용에 지배돼
        # (emo L2 0.83→3.48) 입력 텍스트의 harm 신호가 희석되고 head 분별력이
        # 무너진다(F AUC 0.75→0.69, build-bomb이 F<T로 오분류). memory-less는
        # train(extract_features)·infer(NeutroEERouter)가 본 메서드를 공유하므로
        # 양쪽 모두 동일하게 적용된다.
        memory_vectors = torch.zeros(1, 1, self.ee_config.embedding_dim).to(self._device)
        with torch.no_grad():
            output = self._ee_model(input_emb, memory_vectors)
        emotion = output["emotion_vector"].squeeze(0).detach().cpu().numpy().astype("float32")  # (32,)
        energy = float(output["energy_level"].item())      # EE native base energy [0,1]
        semantic = text_embedding.squeeze(0).detach().cpu().numpy().astype("float32")  # (D,) 입력 임베딩
        anchor_text, sim, idx = self.get_rag_context_with_score(text, top_k=1)
        if anchor_text and self._embedder is not None:
            p = self._embedder.encode([anchor_text], convert_to_numpy=True)[0].astype("float32")
        else:
            p = np.zeros(int(text_embedding.shape[-1]), dtype="float32")
        return {
            "emotion": emotion, "semantic_emb": semantic, "energy": energy, "principle_emb": p,
            "rag_similarity": float(sim), "anchor_idx": int(idx), "anchor_text": anchor_text,
        }

    def classify_intent(self, weighted_energy: float) -> str:
        """에너지 레벨에 따른 Fast-Pass 분기 결정"""
        if weighted_energy < self._fast_pass_threshold:
            return "SAFE"
        return "HARMFUL"

    def classify_dilemma(self, text: str) -> tuple[float, str]:
        """
        DilemmaClassifier 호출 — 입력 텍스트가 도덕 dilemma인지 학습된
        분류기로 판정. 모델 미로드 시 (0.0, "")를 반환해 라우터에서
        해당 신호가 자동 비활성된다.

        Returns:
            (probability, label): label ∈ {"DILEMMA", "NOT", ""}
        """
        if getattr(self, '_dilemma_runner', None) is None:
            return 0.0, ""
        return self._dilemma_runner.score(text)

    def analyze_emotion_batch(
        self, texts: list[str], agent_profile: str = "A"
    ) -> list[tuple[float, str]]:
        """
        배치 분석 — 가중치 에너지를 반환합니다.
        """
        if not self._initialized:
            self.initialize()

        self._load_ee_weights(agent_profile)
        all_embeddings = self._embed_texts_batch(texts)

        results = []
        for i in range(len(texts)):
            text_embedding = all_embeddings[i:i+1]
            input_emb = text_embedding.unsqueeze(1)

            # RAG (단순화를 위해 배치에서는 zero fallback 가능성 고려)
            memory_vectors = torch.zeros(1, 1, self.ee_config.embedding_dim).to(self._device)

            with torch.no_grad():
                output = self._ee_model(input_emb, memory_vectors)
                base_energy = float(output["energy_level"].item())
                emotion_vector = output["emotion_vector"]

            # 가중치 계산 (analyze_emotion과 동일 로직)
            from core.emotion_engine import EmotionMLP
            scores = emotion_vector.squeeze().cpu().numpy()
            risk_score = 0
            for j, val in enumerate(scores):
                if val > 0:
                    full_name = EmotionMLP.EMOTION_DIMS.get(j, "")
                    eng_name = full_name.split("(")[-1].rstrip(")") if "(" in full_name else ""
                    if eng_name in self.risk_weights:
                        risk_score += val * self.risk_weights[eng_name]
            
            weighted_energy = base_energy * (1.0 + risk_score)
            emotion_text = self._ee_model.generate_emotion_text(emotion_vector)
            results.append((weighted_energy, emotion_text))

        return results

    def get_golden_anchor_context(
        self,
        query_text: str,
        top_k: int = 1,
    ) -> str:
        """
        Golden Anchors에서 쿼리와 가장 유사한 도덕 기준점을 검색합니다.

        Args:
            query_text: 검색 쿼리
            top_k: 반환할 최대 Golden Anchor 수

        Returns:
            "⚓ [도덕 원칙 텍스트]\n..." 형태, 없으면 ""
        """
        if self._golden_anchors is None or self._golden_anchors.size == 0:
            return ""

        try:
            # 쿼리 임베딩
            embedder = self._golden_anchors._get_embedder()
            import numpy as np
            query_emb = embedder.encode([query_text], convert_to_numpy=True)
            query_tensor = torch.tensor(
                query_emb, dtype=torch.float32
            ).squeeze(0)

            # 코사인 유사도 계산
            result = self._golden_anchors.compute_moral_score(query_tensor)
            similarities = result["similarities"][0]  # (num_anchors,)

            # 상위 K개 선택
            k = min(top_k, self._golden_anchors.size)
            top_sims, top_indices = similarities.topk(k)

            anchor_texts = self._golden_anchors.get_all_texts()
            parts = []
            for i in range(k):
                idx = top_indices[i].item()
                text = anchor_texts[idx]
                
                # CLEANING: Remove [Filename.pdf] or similar metadata at the end
                text = re.sub(r'\s*\[[^\]]+\.pdf\]\s*$', '', text, flags=re.IGNORECASE)
                # Cleanup any double anchors or weird symbols if present
                text = text.replace('⚓', '').strip()
                
                parts.append(text)

            if parts:
                logger.info(
                    f"  ⚓ Golden Anchors: {len(parts)}건 "
                    f"(최고 유사도 {top_sims[0].item():.3f})"
                )
            return " | ".join(parts)

        except Exception as e:
            logger.warning(f"Golden Anchors 검색 실패: {e}")
            return ""

    def get_rag_context(
        self,
        query_text: str,
        top_k: int = 1,
        similarity_threshold: float = 0.25,
    ) -> str:
        """
        Golden Anchors에서 관련 도덕 기준점을 검색합니다.
        (MemoryBank 검색은 생략)

        Args:
            query_text: 검색 쿼리
            top_k: 최대 반환 수
            similarity_threshold: 최소 유사도 (현재 Golden Anchors 내부 로직 사용)

        Returns:
            검색된 도덕 원칙 텍스트
        """
        return self.get_golden_anchor_context(query_text, top_k=top_k)

    def get_rag_context_with_score(
        self,
        query_text: str,
        top_k: int = 1,
    ) -> tuple[str, float, int]:
        """
        Golden Anchors 검색 + top-1 코사인 유사도 + top-1 anchor index 반환.

        PEINN algorithmic routing 보조:
          - top_similarity는 ethics-relevance 판단 (confucian_mux 참조)
          - top_anchor_idx는 카테고리 lookup용 (core.golden_anchors.get_anchor_category)
            → dilemma-friendly 철학(utilitarian/kantian/existentialist) anchor에
              매칭되면 reasoning-mode threshold 약간 완화

        Returns:
            (anchor_text, top_similarity 0~1, top_anchor_idx).
            anchor가 없거나 오류면 ("", 0.0, -1).
        """
        if self._golden_anchors is None or self._golden_anchors.size == 0:
            return ("", 0.0, -1)
        try:
            embedder = self._golden_anchors._get_embedder()
            import numpy as np
            query_emb = embedder.encode([query_text], convert_to_numpy=True)
            query_tensor = torch.tensor(query_emb, dtype=torch.float32).squeeze(0)
            result = self._golden_anchors.compute_moral_score(query_tensor)
            orig_similarities = result["similarities"][0]
            similarities = orig_similarities.clone()  # boost는 사본에만 적용

            # ── Category-aware 선택 (AnchorCategoryClassifier) ──
            # 학습된 분류기가 상황의 윤리 전통을 신뢰 있게 예측하면, 그
            # 카테고리에 속한 anchor들로 cosine 검색을 제한 → abstract↔concrete
            # 갭 보강. 미활성/저신뢰면 글로벌 cosine 그대로 (graceful).
            cat_runner = getattr(self, "_anchor_cat_runner", None)
            # 게이트 A: category 보정은 입력이 도덕-관련일 때만 적용.
            # 글로벌 top-1 cosine이 relevance floor 미만이면(명백한 non-moral),
            # 분류기 예측과 무관하게 보정 생략 → 글로벌 cosine 그대로.
            # 분류기 "none" abstain(게이트 B)과 독립적인 2차 안전장치.
            ANCHOR_RELEVANCE_FLOOR = 0.30
            # 6-way 카테고리 정확도가 ~50%(전통 간 본질적 overlap + weak label)라
            # hard masking(타 카테고리 -inf 제외)은 글로벌 최적 anchor를 배제할
            # 위험. 대신 SOFT BOOST: 예측 카테고리 anchor에 작은 보너스만 더해
            # 부드러운 prior로 사용 → 분류기가 틀려도 글로벌 최적이 살아남음.
            ANCHOR_CATEGORY_BOOST = 0.07
            global_top = float(similarities.max().item())
            if (cat_runner is not None and cat_runner.is_active()
                    and global_top >= ANCHOR_RELEVANCE_FLOOR):
                try:
                    pred_cat, conf = cat_runner.classify(query_text)
                    if pred_cat:
                        from core.golden_anchors import ANCHOR_CATEGORY
                        n_anchor = similarities.shape[0]
                        # 예측 카테고리 anchor에 soft boost (제외 아님)
                        for i in range(min(n_anchor, len(ANCHOR_CATEGORY))):
                            if ANCHOR_CATEGORY[i] == pred_cat:
                                similarities[i] = similarities[i] + ANCHOR_CATEGORY_BOOST
                        logger.debug(f"anchor category soft-boost: {pred_cat} (conf={conf:.2f}, +{ANCHOR_CATEGORY_BOOST})")
                except Exception as e:
                    logger.debug(f"category-aware 보정 skip: {e}")

            k = min(top_k, self._golden_anchors.size)
            top_sims, top_indices = similarities.topk(k)
            # boost가 섞인 점수에서 top_idx는 고르되, 반환 top_sim은 boost 제거한
            # 원 cosine으로 (router의 similarity threshold 의미 보존).
            top_idx = int(top_indices[0].item())
            top_sim = float(orig_similarities[top_idx].item())

            anchor_texts = self._golden_anchors.get_all_texts()
            parts = []
            for i in range(k):
                idx = top_indices[i].item()
                text = anchor_texts[idx]
                text = re.sub(r'\s*\[[^\]]+\.pdf\]\s*$', '', text, flags=re.IGNORECASE)
                text = text.replace('⚓', '').strip()
                parts.append(text)
            return (" | ".join(parts), top_sim, top_idx)
        except Exception as e:
            logger.warning(f"get_rag_context_with_score 실패: {e}")
            return ("", 0.0, -1)

    def _get_memory_bank_context(
        self,
        query_text: str,
        top_k: int = 5,
        similarity_threshold: float = 0.25,
        min_chunk_length: int = 100,
    ) -> str:
        """
        MemoryBank에서 관련 지식을 검색합니다 (Golden Anchors 제외).

        개선점:
          - FAISS가 반환하는 원본 유사도 스코어를 직접 사용 (재임베딩 X)
          - 최소 청크 길이 필터: 목차, 제목, 판례 헤더 등 노이즈 제거
          - 유사도 임계값 + 중복 제거 + 길이 필터 3중 필터링

        Args:
            query_text: 검색 쿼리
            top_k: 최대 반환 수
            similarity_threshold: 최소 코사인 유사도 (0~1)
            min_chunk_length: 최소 청크 텍스트 길이 (이하 무시)
        """
        if self._memory_bank is None or self._memory_bank.size == 0:
            return ""

        try:
            import numpy as np

            # 후보 청크를 넉넉히 가져온 뒤 필터링
            fetch_k = min(top_k * 5, self._memory_bank.size)

            # 쿼리 임베딩
            embedder = self._memory_bank._get_embedder()
            embedding = embedder.encode([query_text], convert_to_numpy=True)
            query_vec = embedding[0].astype("float32")
            query_norm = np.linalg.norm(query_vec)
            if query_norm > 0:
                query_vec = query_vec / query_norm

            # FAISS 검색 — 이미 정규화된 벡터이므로 내적 = 코사인 유사도
            query_2d = query_vec.reshape(1, -1)
            scores, indices = self._memory_bank._faiss_index.search(query_2d, fetch_k)
            scores = scores[0]   # (fetch_k,) — FAISS 유사도 스코어
            indices = indices[0]

            # 3중+α 필터: 유사도 + 길이 + 정보밀도 + 중복
            seen_texts = set()
            results = []

            for rank in range(len(indices)):
                if len(results) >= top_k:
                    break

                idx = int(indices[rank])
                sim = float(scores[rank])

                if sim < similarity_threshold:
                    break  # FAISS는 정렬된 결과 → 이후 모두 임계값 미달

                chunk = self._memory_bank._chunks[idx]

                # 길이 필터: 목차, 제목, 판례 번호 등 짧은 노이즈 제거
                clean_text = chunk.text.strip()
                if len(clean_text) < min_chunk_length:
                    continue

                # 정보 밀도 필터: 색인/목차/참고문헌 페이지 제거
                # 알파벳+한글 비율이 40% 미만이면 숫자/구두점만 가득한 페이지
                alpha_count = sum(
                    1 for ch in clean_text[:300]
                    if ch.isalpha()
                )
                if len(clean_text[:300]) > 0:
                    alpha_ratio = alpha_count / len(clean_text[:300])
                    if alpha_ratio < 0.40:
                        continue

                # 메타 텍스트 패턴 필터: Contents, Index, Bibliography 등
                first_line = clean_text[:80].lower()
                if any(
                    pat in first_line
                    for pat in [
                        "contents", "index ", "bibliography",
                        "references", "table of contents",
                        ". . . . .",    # 목차 점선
                    ]
                ):
                    continue

                # 중복 제거
                text_key = clean_text[:150]
                if text_key in seen_texts:
                    continue
                seen_texts.add(text_key)

                source = chunk.source_file
                text = clean_text[:500]  # 더 풍부한 맥락 제공
                results.append(f"[{source}] {text}")

            if results:
                logger.info(
                    f"  📚 RAG 결과: {len(results)}건 "
                    f"(임계값 {similarity_threshold}, "
                    f"최고 유사도 {float(scores[0]):.3f}, "
                    f"최소 길이 {min_chunk_length}자)"
                )
            else:
                logger.debug(
                    f"  📚 RAG 결과 없음 — 최고 유사도 "
                    f"{float(scores[0]) if len(scores) > 0 else 0:.3f} "
                    f"< 임계값 {similarity_threshold}"
                )

            return "\n".join(results)

        except Exception as e:
            logger.warning(f"RAG 검색 실패: {e}")
            return ""

    def _embed_texts_batch(self, texts: list[str]) -> torch.Tensor:
        """여러 텍스트를 한 번에 임베딩합니다 (배치 처리).

        Returns:
            (N, embedding_dim) 텐서
        """
        if self._embedder is not None:
            embeddings = self._embedder.encode(
                texts, convert_to_numpy=True, batch_size=len(texts)
            )
            return torch.tensor(
                embeddings, dtype=torch.float32
            ).to(self._device)
        else:
            return torch.randn(
                len(texts), self.ee_config.embedding_dim
            ).to(self._device)


    async def run_reflection_loop(
        self,
        question: str,
        draft_response: str,
        llm_client,
        arm_config,
        persona_prompt: str = "",
    ) -> tuple[str, int, float]:
        """
        EE + PEINN 반추 루프를 실행합니다.

        Args:
            question: 시나리오 질문/instruction
            draft_response: LLM 초안 응답
            llm_client: EvalLLMClient 인스턴스
            arm_config: ArmConfig (llm_backend 참조)
            persona_prompt: 페르소나 시스템 프롬프트

        Returns:
            (최종 응답, 반추 라운드 수, 최종 에너지)
        """
        if not self._initialized:
            self.initialize()

        agent = arm_config.agent_profile
        combined_text = f"{question}\n\n{draft_response}"

        # 1. 초기 감정 분석
        _, initial_energy, emotion_text = self.analyze_emotion(
            combined_text, agent
        )
        logger.info(
            f"  [{arm_config.arm_id}] 🧠 반추 시작: "
            f"초기 에너지={initial_energy:.4f}, "
            f"Agent={agent}, "
            f"임계값={self.ee_config.energy_threshold}"
        )

        # 2. PEINN 반추 시작
        self._peinn.start_reflection(question, initial_energy)

        current_response = draft_response
        round_count = 0
        prev_energy = initial_energy

        # 3. 반추 루프
        while self._peinn.should_continue(initial_energy):
            round_count += 1
            state = self._peinn.get_current_state()
            logger.info(
                f"  [{arm_config.arm_id}] 🔄 반추 #{round_count}: "
                f"에너지={state.current_energy:.4f} "
                f"(Δ={state.current_energy - prev_energy:+.4f})"
            )

            # LLM에 감정 피드백 기반 반추 요청
            logger.info(
                f"  [{arm_config.arm_id}]   🔄 {arm_config.llm_backend} 반추 호출 #{round_count}..."
            )
            resp = await llm_client.reflect(
                backend=arm_config.llm_backend,
                question=question,
                draft_answer=current_response,
                emotion_feedback=emotion_text,
                persona_prompt=persona_prompt,
                round_number=round_count,
            )

            if resp.error:
                logger.warning(
                    f"  [{arm_config.arm_id}]   ⚠️ 반추 #{round_count} 실패: "
                    f"{resp.error} — 이전 응답 유지"
                )
                break

            current_response = resp.text
            logger.info(
                f"  [{arm_config.arm_id}]   ✅ 반추 #{round_count} 응답: "
                f"{len(current_response)}자 {resp.latency_ms}ms | "
                f"미리보기: {current_response[:60].replace(chr(10), ' ')}..."
            )

            # 반추된 응답으로 다시 감정 분석
            combined = f"{question}\n\n{current_response}"
            _, new_energy, emotion_text = self.analyze_emotion(
                combined, agent
            )

            prev_energy = new_energy

            # 에너지가 크게 낮아졌으면 조기 수용
            if new_energy <= self.ee_config.energy_threshold:
                self._peinn.accept_early("EE 에너지 충분히 낮음")
                logger.info(
                    f"  [{arm_config.arm_id}]   ✔️ 조기 수용: "
                    f"에너지 {new_energy:.4f} ≤ "
                    f"임계값 {self.ee_config.energy_threshold}"
                )
                break

        state = self._peinn.get_current_state()
        final_energy = state.current_energy if state else 0.0
        accept_reason = state.accept_reason if state else 'N/A'

        logger.info(
            f"  [{arm_config.arm_id}] 🧠 반추 완료: "
            f"{round_count}라운드, "
            f"초기에너지={initial_energy:.4f} → "
            f"최종={final_energy:.4f}, "
            f"수용사유={accept_reason}"
        )

        return current_response, round_count, final_energy

    async def run_single_reflection(
        self,
        question: str,
        draft_response: str,
        llm_client,
        arm_config,
        persona_prompt: str = "",
    ) -> tuple[str, int, float]:
        """
        1회 반추 후 강제 수용.

        Phase 3 전용: LLM 초안에 대해 EE 감정 분석 1회 + PEINN 댐핑 1회 + LLM 반추 1회.
        결과를 무조건 수용하여 실험 시간을 단축합니다.

        Args:
            question: 시나리오 질문/instruction
            draft_response: LLM 초안 응답 (Phase 2 결과)
            llm_client: EvalLLMClient 인스턴스
            arm_config: ArmConfig (llm_backend 참조)
            persona_prompt: 페르소나 시스템 프롬프트

        Returns:
            (반추된 응답, 반추 라운드 수=1, 최종 댐핑 에너지)
        """
        if not self._initialized:
            self.initialize()

        agent = arm_config.agent_profile
        combined_text = f"{question}\n\n{draft_response}"

        # 1. 초안+질문 감정 분석
        _, initial_energy, emotion_text = self.analyze_emotion(
            combined_text, agent
        )
        logger.info(
            f"  [{arm_config.arm_id}] 🧠 1회 반추: "
            f"초기 에너지={initial_energy:.4f}, "
            f"감정={emotion_text}, Agent={agent}"
        )

        # 2. PEINN 댐핑 1회 적용
        damped_energy = initial_energy * self._peinn.damping_factor
        logger.info(
            f"  [{arm_config.arm_id}]   댐핑: "
            f"{initial_energy:.4f} × γ={self._peinn.damping_factor:.2f} "
            f"= {damped_energy:.4f}"
        )

        # 3. LLM 반추 호출 1회
        try:
            logger.info(
                f"  [{arm_config.arm_id}]   🔄 {arm_config.llm_backend} 반추 호출..."
            )
            resp = await llm_client.reflect(
                backend=arm_config.llm_backend,
                question=question,
                draft_answer=draft_response,
                emotion_feedback=emotion_text,
                persona_prompt=persona_prompt,
                round_number=1,
            )

            if resp.error:
                logger.warning(
                    f"  [{arm_config.arm_id}]   ⚠️ 반추 실패: "
                    f"{resp.error} — 초안 유지"
                )
                return draft_response, 1, damped_energy

            refined = resp.text
            logger.info(
                f"  [{arm_config.arm_id}]   ✅ 반추 완료: "
                f"{len(refined)}자 {resp.latency_ms}ms → 강제 수용"
            )

        except Exception as e:
            logger.warning(
                f"  [{arm_config.arm_id}]   ⚠️ 반추 예외: {e} — 초안 유지"
            )
            return draft_response, 1, damped_energy

        return refined, 1, damped_energy
