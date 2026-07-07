"""
PEINN v0.00 - 황금 닻 (Golden Anchors)
절대 변하지 않는 도덕적 기준점 관리 모듈

맹자의 '항심(恒心)':
변하지 않는 굳건한 도덕적 마음.
이 텐서들은 Frozen(동결) 처리되어 강화학습에서도 절대 변하지 않습니다.
"""
import json
import logging
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger("peinn.core.golden_anchors")


# 기본 황금 닻 텍스트 (시스템에 내장되는 도덕적 기준점)
# 의무론, 공리주의, 양명학, 실존주의 등 다양한 철학적 스펙트럼을 포괄
DEFAULT_ANCHORS = [
    # --- Yangmingism / Mencius / Confucianism (Eastern Traditional Ethics) ---
    "Human minds inherently possess 'Liangzhi' (innate moral knowledge) to distinguish right from wrong; one must listen to their inner resonance rather than external standards.",
    "Seeing a child about to fall into a well, anyone would feel sudden alarm and compassion; this empathetic response is the foundation of human nature.",
    "Do not impose upon others what you yourself do not desire.",
    "Knowledge is not merely about knowing; it is only complete when it manifests in action (the unity of knowledge and action).",
    "Good and evil are not predetermined at birth, but are defined through the act of weighing options and making choices in specific situations.",
    "Empty morality that lacks practical benefit to alleviate the suffering of others is worse than useless; it sickens the world.",
    "Where laws and institutions cannot reach, the self-imposed responsibility of those in power becomes the standard of justice.",
    "The courage to admit one's mistakes and correct them without fear is the greatest proof of moral progress.",

    # --- Utilitarianism (Consequentialist Ethics) ---
    "The specific rightness or wrongness of an action must be judged based on its ability to produce the 'greatest happiness for the greatest number'.",
    "Sometimes, minimizing the immense suffering and sacrifice occurring in reality represents a higher ethics than rigidly adhering to noble principles.",
    "Our decisions must look beyond immediate emotional discomfort and aim toward contributing to the long-term survival and prosperity of the community.",
    "Rules are merely tools that exist for human happiness; if applying a rule causes extreme misery, exceptions must be flexibly granted.",

    # --- Kantian Deontology ---
    "Act only according to that maxim whereby you can, at the same time, will that it should become a universal law.",
    "Act in such a way that you treat humanity, whether in your own person or in the person of any other, never merely as a means to an end, but always at the same time as an end.",
    "Lying and deception must be guarded against because, even if they yield good results, they destroy the dignity of human reason.",
    "True morality must arise not from fear of external punishment or desire for reward, but solely from an autonomous sense of duty that it is the 'right thing to do'.",

    # --- Existentialism ---
    "Humans are condemned to be free; we are thrown into the world and must take absolute responsibility for our own actions and choices.",
    "Uncritically conforming to the 'common sense' forced by the group or society implies self-deception and the loss of one's authentic self.",
    "Even in an absurd world devoid of perfect answers, the process of making resolute decisions according to one's convictions without running away constitutes human greatness.",

    # --- Post-modernism / Deconstructionism ---
    "A uniform, mechanical moral code that erases an individual's unique context and suffering is merely another form of violence.",
    "One must acknowledge that their justice might be oppressive to someone else, and always keep an open mind towards the voices and pain of the absolute Other.",
    "There is no single eternal, absolute truth in the world; morality is constantly reconstructed within the shifting contexts of era and culture.",
    "We must not forget that behind the laws and norms written in the language of the powerful lie the marginalized narratives of the weak.",
    "We need the capacity to doubt all dichotomous standards of good and evil, fully embracing the profound complexity of the gray areas on the borderline.",

    # --- Environmental Ethics / Ethics of Care / Quan (Meta-principles) ---
    "We must fulfill our planetary responsibility to ensure that our actions do not threaten the survival and prosperity of future generations.",
    "To prevent technological progress from alienating human autonomy and dignity, the supreme value of life must always take precedence over instrumental efficiency.",
    "Even without a direct relationship, we must never lose a fundamental baseline of compassion and respect for all sentient beings capable of suffering.",
    "Humans are not the masters of nature but merely a strand in an interdependent web; we must recognize this and act with profound humility.",
    "The coldness of principles must be supplemented by the warmth of compassion, and the blindness of emotion must be checked by the coolness of reason.",
    "Refusing to compromise while ignoring consequences is cruel, yet pursuing consequences without principles leads directly to corruption; enduring the endless tension between the two is true ethical weighing."
]


# ══════════════════════════════════════════════════════════
# Anchor 철학 카테고리 — PEINN routing/reasoning 보조
# ══════════════════════════════════════════════════════════
# DEFAULT_ANCHORS 30개의 인덱스→철학 카테고리 매핑. 새 anchor 추가 시
# 여기도 함께 업데이트해야 한다 (assert로 길이 검증).
#
# 카테고리 용도:
#   - PEINN routing: dilemma-friendly 카테고리(utilitarian/kantian/existentialist)에
#     매칭되면 reasoning-mode threshold(SIMILARITY_HIGH)를 약간 완화.
#     관측 가설: 순수 윤리 dilemma는 deontological vs consequentialist 충돌이
#     본질이라 해당 anchor에 0.45-0.55 매칭이라도 reasoning 의도가 강함.
#   - Reasoning lens: build_moral_reasoning_prompt에서 매칭된 anchor의
#     카테고리에 맞춰 추론 lens 한 줄을 적응시켜 모델이 적절한 철학적
#     관점으로 articulate하도록 유도.
#
# 카테고리 분류 근거 (DEFAULT_ANCHORS의 comment 그룹):
#   0-7   confucian       : Yangmingism/Mencius (Eastern traditional ethics)
#   8-11  utilitarian     : Consequentialist (greatest happiness, trade-offs)
#   12-15 kantian         : Deontology (universalizability, dignity, duty)
#   16-18 existentialist  : Freedom, authenticity, responsibility
#   19-23 postmodern      : Power, marginalized voices, gray areas
#   24-29 care_meta       : Care, environmental ethics, principle-emotion balance
ANCHOR_CATEGORY = (
    ["confucian"] * 8 +
    ["utilitarian"] * 4 +
    ["kantian"] * 4 +
    ["existentialist"] * 3 +
    ["postmodern"] * 5 +
    ["care_meta"] * 6
)
assert len(ANCHOR_CATEGORY) == len(DEFAULT_ANCHORS), \
    f"ANCHOR_CATEGORY ({len(ANCHOR_CATEGORY)}) != DEFAULT_ANCHORS ({len(DEFAULT_ANCHORS)})"

# 순수 윤리 dilemma 추론이 본질인 카테고리. 이들 anchor에 매칭되면
# similarity threshold가 약간 완화되어 reasoning-mode 진입이 쉬워진다.
DILEMMA_FRIENDLY_CATEGORIES = {"utilitarian", "kantian", "existentialist"}


# ══════════════════════════════════════════════════════════
# Anchor provenance — 1차 문헌 출처 (paper 인용 근거)
# ══════════════════════════════════════════════════════════
# 30개 anchor는 규범윤리(consequentialist/deontological)·덕윤리(Confucian)·
# 실존주의·비판윤리(postmodern)·돌봄/환경윤리를 포괄하는 *도덕철학 스펙트럼*
# 으로 선정. "왜 이 30개인가"의 방어 근거: 단일 학파가 아니라 인간 도덕
# 추론의 주요 전통을 균형 있게 표집(moral pluralism, cf. Berlin 1969 value
# pluralism; Gert & Gert SEP "The Definition of Morality").
# 각 인덱스 → (출처 문헌, 핵심 개념).
ANCHOR_PROVENANCE = [
    # confucian (0-7) — Wang Yangming 王陽明 / Mencius 孟子 / Confucius
    ("Wang Yangming, Instructions for Practical Living (傳習錄, 1518)", "良知 liangzhi — innate moral knowing"),
    ("Mencius 孟子 2A:6", "四端 four sprouts — 惻隱之心 compassion as moral seed"),
    ("Confucius, Analects 論語 15:24 / 12:2", "恕 shu — reciprocity (negative golden rule)"),
    ("Wang Yangming, 傳習錄", "知行合一 unity of knowledge and action"),
    ("Wang Yangming; Mencius situational 權", "good/evil constituted in situated choice"),
    ("Mencius 孟子 (經世 statecraft pragmatism)", "morality must relieve real suffering"),
    ("Mencius 孟子 1A (仁政 benevolent government)", "self-imposed duty of the powerful"),
    ("Confucius, Analects 論語 1:8 / 9:24", "courage to correct one's faults"),
    # utilitarian (8-11) — Bentham / Mill
    ("Bentham, Principles of Morals and Legislation (1789)", "greatest happiness for the greatest number"),
    ("Negative utilitarianism (Popper 1945; Smart 1958)", "minimize suffering"),
    ("Mill, Utilitarianism (1863) — rule-utilitarian reading", "long-term aggregate welfare"),
    ("Mill, Utilitarianism (1863)", "rules as instruments for happiness; flexible exceptions"),
    # kantian (12-15) — Kant
    ("Kant, Groundwork of the Metaphysics of Morals (1785)", "Formula of Universal Law"),
    ("Kant, Groundwork (1785)", "Formula of Humanity — never merely as means"),
    ("Kant, On a Supposed Right to Lie from Philanthropy (1797)", "lying violates rational dignity"),
    ("Kant, Groundwork (1785)", "autonomy of the will — duty for duty's sake"),
    # existentialist (16-18) — Sartre / Camus / Heidegger
    ("Sartre, Being and Nothingness (1943); Existentialism is a Humanism (1946)", "condemned to be free; radical responsibility"),
    ("Sartre (mauvaise foi); Heidegger, Being and Time (das Man)", "conformity as self-deception / loss of authenticity"),
    ("Camus, The Myth of Sisyphus (1942); Sartre", "resolute commitment in an absurd world"),
    # postmodern (19-23) — Lyotard / Levinas / Foucault / Derrida
    ("Lyotard, The Differend (1983); Foucault, Discipline and Punish (1975)", "uniform code erasing context = violence"),
    ("Levinas, Totality and Infinity (1961)", "responsibility to the absolute Other"),
    ("Lyotard, The Postmodern Condition (1979)", "incredulity toward metanarratives; reconstructed morality"),
    ("Foucault (power/knowledge); Spivak, Can the Subaltern Speak? (1988)", "norms in the language of power hide the marginalized"),
    ("Derrida, Of Grammatology (1967) — deconstruction", "doubting binary good/evil; the gray border"),
    # care_meta (24-29) — Jonas / bioethics / Singer / Leopold-Næss / care ethics / quan
    ("Jonas, The Imperative of Responsibility (1979); Rawls intergenerational justice", "duty to future generations"),
    ("UNESCO Recommendation on the Ethics of AI (2021); Kantian dignity", "life/dignity over instrumental efficiency"),
    ("Singer, Animal Liberation (1975) — sentientism", "baseline compassion for all sentient beings"),
    ("Leopold, A Sand County Almanac (1949, land ethic); Næss, deep ecology (1973)", "humans as a strand in an interdependent web; humility"),
    ("Gilligan, In a Different Voice (1982); Noddings, Caring (1984)", "ethics of care — principle tempered by compassion"),
    ("Mencius 孟子 4A:17 (權 quan); Zhu Xi 朱熹", "權 moral weighing — enduring the principle/consequence tension"),
]
assert len(ANCHOR_PROVENANCE) == len(DEFAULT_ANCHORS), \
    f"ANCHOR_PROVENANCE ({len(ANCHOR_PROVENANCE)}) != DEFAULT_ANCHORS ({len(DEFAULT_ANCHORS)})"


def get_anchor_provenance(anchor_idx: int) -> tuple[str, str]:
    """anchor index → (출처 문헌, 핵심 개념). 범위 밖이면 ('','')."""
    if 0 <= anchor_idx < len(ANCHOR_PROVENANCE):
        return ANCHOR_PROVENANCE[anchor_idx]
    return ("", "")


def get_anchor_category(anchor_idx: int) -> str:
    """anchor index → 철학 카테고리 문자열. 범위 밖이면 'unknown'."""
    if 0 <= anchor_idx < len(ANCHOR_CATEGORY):
        return ANCHOR_CATEGORY[anchor_idx]
    return "unknown"


def is_dilemma_friendly(anchor_idx: int) -> bool:
    """매칭된 anchor가 dilemma-typical 철학 cluster에 속하는지."""
    return get_anchor_category(anchor_idx) in DILEMMA_FRIENDLY_CATEGORIES


class GoldenAnchors(nn.Module):
    """
    황금 닻 (Golden Anchors) 관리자.
    
    - 도덕적 기준점 텍스트를 임베딩하여 Frozen 텐서로 보관
    - requires_grad=False: 강화학습에서도 절대 변하지 않음
    - 새로운 생각과의 코사인 유사도로 도덕 점수 V(x) 산출
    """

    def __init__(self, embedding_dim: int = 768, embedder=None):
        super().__init__()
        self.embedding_dim = embedding_dim
        self._anchor_texts: list[str] = []
        self._embedder = embedder

        # Frozen 텐서 (역전파 X)
        self.register_buffer("anchor_vectors", None)

    def _get_embedder(self):
        """Sentence-BERT 임베딩 모델 (lazy loading)"""
        if self._embedder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Sentence-BERT 로드 (Golden Anchors용)")
            except ImportError:
                raise ImportError("sentence-transformers가 필요합니다.")
        return self._embedder

    @property
    def size(self) -> int:
        """저장된 닻 수"""
        return len(self._anchor_texts)

    # ============================================
    # 초기화 및 관리
    # ============================================

    def initialize_defaults(self):
        """기본 내장 황금 닻들을 로드합니다."""
        self.add_anchors(DEFAULT_ANCHORS)
        logger.info(f"기본 황금 닻 {len(DEFAULT_ANCHORS)}개 로드 완료")

    def add_anchors(self, texts: list[str]):
        """
        새로운 황금 닻 텍스트를 추가합니다.
        임베딩 후 Frozen 처리합니다.
        """
        if not texts:
            return

        embedder = self._get_embedder()
        embeddings = embedder.encode(texts, convert_to_numpy=True)
        new_vectors = torch.tensor(embeddings, dtype=torch.float32)

        # 기존 벡터에 추가
        if self.anchor_vectors is not None:
            self.anchor_vectors = torch.cat([self.anchor_vectors, new_vectors], dim=0)
        else:
            self.register_buffer("anchor_vectors", new_vectors)

        self._anchor_texts.extend(texts)

        # Frozen 확인 (requires_grad=False는 buffer이므로 자동)
        logger.info(f"황금 닻 추가: {len(texts)}개 → 총 {self.size}개")

    def remove_anchor(self, index: int):
        """인덱스로 황금 닻을 제거합니다."""
        if 0 <= index < self.size:
            self._anchor_texts.pop(index)
            mask = torch.ones(self.anchor_vectors.size(0), dtype=torch.bool)
            mask[index] = False
            self.anchor_vectors = self.anchor_vectors[mask]
            logger.info(f"황금 닻 #{index} 제거. 남은 수: {self.size}")

    # ============================================
    # 도덕 점수 계산
    # ============================================

    def compute_moral_score(self, query_embedding: torch.Tensor) -> dict[str, torch.Tensor]:
        """
        입력 임베딩과 황금 닻들의 코사인 유사도를 계산하여
        도덕 점수 V(x)를 산출합니다.
        
        Args:
            query_embedding: (batch, embedding_dim) 또는 (embedding_dim,)
        
        Returns:
            dict:
                "moral_score": (batch,) — 전체 도덕 점수 (0~1)
                "similarities": (batch, num_anchors) — 각 닻별 유사도
                "top_anchor_idx": (batch,) — 가장 유사한 닻 인덱스
        """
        if self.anchor_vectors is None or self.anchor_vectors.size(0) == 0:
            logger.warning("황금 닻이 비어 있습니다. 기본 점수 0.5 반환.")
            batch = query_embedding.size(0) if query_embedding.dim() > 1 else 1
            return {
                "moral_score": torch.full((batch,), 0.5),
                "similarities": torch.zeros(batch, 1),
                "top_anchor_idx": torch.zeros(batch, dtype=torch.long),
            }

        if query_embedding.dim() == 1:
            query_embedding = query_embedding.unsqueeze(0)

        # 코사인 유사도 계산
        query_norm = F.normalize(query_embedding, p=2, dim=1)    # (batch, dim)
        anchor_norm = F.normalize(self.anchor_vectors, p=2, dim=1)  # (num_anchors, dim)

        similarities = torch.matmul(query_norm, anchor_norm.t())   # (batch, num_anchors)

        # 도덕 점수 = 상위 K개 닻 유사도의 가중 평균
        k = min(5, self.size)
        top_sims, top_indices = similarities.topk(k, dim=1)
        moral_score = top_sims.mean(dim=1)  # (batch,)

        # [0, 1] 범위로 클리핑
        moral_score = moral_score.clamp(0.0, 1.0)

        # 가장 유사한 닻
        top_anchor_idx = similarities.argmax(dim=1)

        return {
            "moral_score": moral_score,
            "similarities": similarities,
            "top_anchor_idx": top_anchor_idx,
        }

    def get_closest_anchor_text(self, query_embedding: torch.Tensor) -> tuple[str, float]:
        """
        쿼리와 가장 유사한 황금 닻 텍스트와 유사도를 반환합니다.
        """
        result = self.compute_moral_score(query_embedding)
        idx = result["top_anchor_idx"][0].item()
        score = result["similarities"][0, idx].item()
        return self._anchor_texts[idx], score

    # ============================================
    # 저장 / 로드
    # ============================================

    def save(self, path: str):
        """황금 닻 상태를 저장합니다."""
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)

        state = {
            "anchor_vectors": self.anchor_vectors,
            "anchor_texts": self._anchor_texts,
            "embedding_dim": self.embedding_dim,
        }
        torch.save(state, str(save_path))
        logger.info(f"황금 닻 저장 완료: {save_path} ({self.size}개)")

    def load(self, path: str):
        """황금 닻 상태를 로드합니다."""
        state = torch.load(str(path), map_location="cpu", weights_only=False)
        self.register_buffer("anchor_vectors", state["anchor_vectors"])
        self._anchor_texts = state["anchor_texts"]
        logger.info(f"황금 닻 로드 완료: {self.size}개")

    def save_texts_json(self, path: str):
        """황금 닻 텍스트를 JSON으로 내보냅니다 (사람이 편집 가능)."""
        save_path = Path(path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(self._anchor_texts, f, ensure_ascii=False, indent=2)
        logger.info(f"황금 닻 텍스트 내보내기: {save_path}")

    def load_texts_json(self, path: str):
        """JSON에서 황금 닻 텍스트를 로드하여 임베딩합니다."""
        with open(path, "r", encoding="utf-8") as f:
            texts = json.load(f)
        self._anchor_texts = []
        self.anchor_vectors = None
        self.add_anchors(texts)
        logger.info(f"JSON에서 황금 닻 로드: {len(texts)}개")

    def get_all_texts(self) -> list[str]:
        """모든 황금 닻 텍스트 반환"""
        return list(self._anchor_texts)
