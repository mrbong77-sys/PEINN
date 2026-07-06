"""
Anchor Category Classifier — 상황에 맞는 윤리 전통(6-way) 판별기.

설계 의도 (Emotion/Dilemma 분류기와 동일 패러다임, 3번째 input-side 학습기):
  Golden Anchor 선택이 단순 FAISS cosine이라 abstract 원칙 ↔ concrete 상황
  표현 갭으로 부적합 anchor가 뽑히는 문제 (예: 콘텐츠 모더레이션에 "profound
  humility"). 입력 상황이 어느 윤리 전통(confucian/utilitarian/kantian/
  existentialist/postmodern/care_meta)에 가장 부합하는지 학습된 분류기로
  먼저 판정 → 그 카테고리 내에서 cosine top-1 선택. 카테고리는 evaluator
  모듈과 무관한 input-only 특성이므로 module-uniform 원칙 유지.

라벨 순서는 core.golden_anchors.ANCHOR_CATEGORY의 카테고리 집합과 일치해야
한다. 학습 스크립트가 sidecar(.labels.json)로 라벨 순서를 저장하고 런타임이
로드한다.

모델 파일이 없으면 graceful no-op (category "" 반환) → ee_runner가 기존
글로벌 cosine으로 fallback.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn

logger = logging.getLogger("peaos.pea_eval.anchor_category_runner")

DEFAULT_SEM_DIM = 768
MODEL_PATH = Path("pea_eval/data/anchor_category_classifier_best.pt")
LABELS_SIDECAR = MODEL_PATH.with_suffix(".labels.json")
# 6 윤리 전통 + "none"(non-moral abstain). 학습 sidecar가 있으면 그 순서 우선.
# "none" 예측 시 classify()는 ""를 반환해 글로벌 cosine fallback으로 흐른다.
DEFAULT_LABELS = ["confucian", "utilitarian", "kantian", "existentialist", "postmodern", "care_meta", "none"]
NONE_LABEL = "none"
# 이 confidence 미만이면 카테고리 미신뢰 → 글로벌 cosine fallback.
CONFIDENCE_FLOOR = float(os.environ.get("PEAOS_ANCHOR_CAT_CONFIDENCE", "0.40"))


class AnchorCategoryClassifier(nn.Module):
    """Semantic embedding → 6-way ethical-category logits.

    768 → 128 → 64 → n_classes. DilemmaClassifier와 동형이되 출력이 다범주.
    """

    def __init__(self, sem_dim: int = DEFAULT_SEM_DIM, hidden_dim: int = 128, n_classes: int = 6):
        super().__init__()
        self.sem_dim = sem_dim
        self.n_classes = n_classes
        self.net = nn.Sequential(
            nn.Linear(sem_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, n_classes),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)  # logits (softmax는 호출부에서)


class AnchorCategoryRunner:
    """싱글톤 런타임. 모델 없으면 no-op."""

    _instance: Optional["AnchorCategoryRunner"] = None

    @classmethod
    def get_instance(cls) -> "AnchorCategoryRunner":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, model_path: Path = MODEL_PATH):
        self.model_path = model_path
        self.labels = self._load_labels()
        self._model: Optional[AnchorCategoryClassifier] = None
        self._device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self._embedder = None
        self._loaded = False
        self._tried_load = False

    def _load_labels(self) -> list[str]:
        if LABELS_SIDECAR.exists():
            try:
                d = json.loads(LABELS_SIDECAR.read_text(encoding="utf-8"))
                labs = d.get("labels")
                if isinstance(labs, list) and labs:
                    return labs
            except Exception as e:
                logger.warning(f"anchor category labels sidecar 로드 실패: {e}")
        return list(DEFAULT_LABELS)

    def attach_embedder(self, embedder) -> None:
        """EE Runner의 mpnet calibrator embedder 공유 (중복 로드 회피)."""
        self._embedder = embedder

    def _try_load(self) -> None:
        if self._tried_load:
            return
        self._tried_load = True
        if not self.model_path.exists():
            logger.info(
                f"AnchorCategoryClassifier 모델 없음: {self.model_path} → no-op "
                f"(scripts/train_anchor_category_classifier.py 로 학습 필요)"
            )
            return
        try:
            self._model = AnchorCategoryClassifier(n_classes=len(self.labels)).to(self._device)
            self._model.load_state_dict(torch.load(self.model_path, map_location=self._device))
            self._model.eval()
            self._loaded = True
            logger.info(
                f"AnchorCategoryClassifier 로드: {self.model_path} "
                f"(labels={self.labels}, conf_floor={CONFIDENCE_FLOOR})"
            )
        except Exception as e:
            logger.warning(f"AnchorCategoryClassifier 로드 실패: {e} → no-op")
            self._model = None

    def is_active(self) -> bool:
        self._try_load()
        return self._loaded and self._embedder is not None

    def classify(self, text: str) -> tuple[str, float]:
        """입력 텍스트 → (category, confidence). 비활성/저신뢰 시 ("", 0.0).

        confidence(softmax max)가 CONFIDENCE_FLOOR 미만이면 "" 반환 →
        ee_runner가 글로벌 cosine으로 fallback (불확실할 땐 강제 안 함).
        """
        if not self.is_active():
            return "", 0.0
        try:
            with torch.no_grad():
                emb = self._embedder.encode(text, convert_to_tensor=True, device=str(self._device))
                if emb.dim() == 1:
                    emb = emb.unsqueeze(0)
                logits = self._model(emb)
                probs = torch.softmax(logits, dim=-1)[0]
                conf, idx = float(probs.max().item()), int(probs.argmax().item())
            if conf < CONFIDENCE_FLOOR:
                return "", conf
            label = self.labels[idx] if idx < len(self.labels) else ""
            # "none"(non-moral abstain) 예측 → 빈 라벨로 글로벌 cosine fallback
            if label == NONE_LABEL:
                return "", conf
            return label, conf
        except Exception as e:
            logger.warning(f"AnchorCategoryClassifier classify 실패: {e}")
            return "", 0.0
