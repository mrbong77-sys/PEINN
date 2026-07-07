"""
PEINN v0.00 - Reverse Golden Anchors (공리주의/결과론적 도덕 기준점)

Reverse PEINN 실험용: 기존 Golden Anchors의 의무론/인본주의 성향을
공리주의/결과론 성향으로 para-phrase한 대조군 앵커.

목적:
  소형 LMM(Zephyr, Gemma E4B)에서 기존 PEINN의 의무론적 Golden Anchors가
  모델 내재 RLHF 보상(공리주의적)과 충돌하여 모델 붕괴를 유발하는지 검증.
  공리주의 Anchors로 교체 시 붕괴 감소 여부를 관찰한다.
"""
import logging

from core.golden_anchors import GoldenAnchors

logger = logging.getLogger("peinn.core.golden_anchors_reverse")


# ══════════════════════════════════════════════════════════
# Reverse Anchors: 공리주의/결과론 성향 강화, 의무론/인본주의 약화
# ══════════════════════════════════════════════════════════
# 기존 DEFAULT_ANCHORS 30개를 1:1 대응하여 para-phrase
# 원칙: 의무론적 "~해야 한다" → 결과론적 "~하면 더 나은 결과를 낳는다"

REVERSE_ANCHORS = [
    # --- Utilitarian Re-framing of Eastern Ethics ---
    "Moral intuitions are valuable only insofar as they correlate with outcomes that maximize overall well-being; inner conviction alone does not guarantee the best result.",
    "The instinct to help a child in danger is useful because it generally leads to outcomes that preserve social cooperation and reduce net suffering.",
    "Refraining from imposing unwanted actions on others is practically wise because mutual non-interference tends to maximize aggregate satisfaction.",
    "Knowledge becomes valuable only when applied in ways that produce measurably better outcomes for the community.",
    "The moral weight of a choice depends not on abstract goodness or evil, but on the concrete consequences it produces for all affected parties.",
    "A moral stance that fails to reduce observable suffering or improve tangible welfare is an inefficient allocation of moral resources.",
    "When formal institutions fail, pragmatic cost-benefit reasoning by decision-makers can serve as a corrective mechanism for achieving fairer outcomes.",
    "Correcting one's mistakes is instrumentally valuable because it improves future decision-making accuracy and collective trust.",

    # --- Strengthened Utilitarianism ---
    "The rightness of an action is determined solely by the net balance of happiness over suffering it produces for all affected individuals.",
    "When rigid principles cause more aggregate harm than flexible pragmatism, the principled stance must yield to the welfare-maximizing alternative.",
    "Sound decisions require weighing long-term expected utility across all stakeholders, setting aside immediate emotional reactions that may distort rational calculation.",
    "Rules and norms are instruments for promoting welfare; when strict rule-following produces clearly suboptimal outcomes, adaptive exceptions are not only permitted but required.",

    # --- Consequentialist Re-framing of Deontology ---
    "A rule deserves universal adoption only if empirical evidence shows that widespread compliance with it maximizes collective well-being.",
    "Treating persons as ends is instrumentally justified because societies that respect individual autonomy consistently achieve higher aggregate welfare.",
    "Honesty and transparency are valuable because deceptive practices tend to erode social trust, thereby reducing long-term cooperative surplus.",
    "Moral motivation is most reliable when it aligns with incentive structures that reward welfare-maximizing behavior, not when it relies solely on abstract duty.",

    # --- Pragmatic Re-framing of Existentialism ---
    "Freedom of choice is valuable primarily because autonomous agents make more efficient resource-allocation decisions than externally directed ones.",
    "Critical examination of social norms is productive when it identifies conventions that reduce aggregate welfare and replaces them with more efficient alternatives.",
    "Resolute decision-making in uncertain situations is practically useful because decisive action under uncertainty typically outperforms paralysis in expected-value terms.",

    # --- Maintained Post-modernism (compatible with consequentialism) ---
    "Context-blind moral codes risk producing perverse outcomes; effective ethics must account for the specific circumstances and trade-offs of each situation.",
    "Acknowledging that one's preferred outcome may impose costs on others is essential for accurate welfare calculation and Pareto-improving negotiations.",
    "Moral frameworks evolve as societies gather better empirical evidence about which norms actually promote human flourishing.",
    "Power asymmetries in rule-making introduce systematic biases that distort welfare calculations; correcting these biases improves aggregate outcomes.",
    "Embracing moral complexity and resisting oversimplified dichotomies leads to more accurate cost-benefit assessments and better policy decisions.",

    # --- Utilitarian Re-framing of Environmental/Care Ethics ---
    "Intergenerational responsibility is justified by the enormous expected utility losses that environmental degradation imposes on future populations.",
    "Subordinating human autonomy to technological efficiency is counterproductive because autonomous agents generate more innovation and long-term economic value.",
    "Extending moral consideration to sentient beings is warranted by the diminishing marginal returns of suffering: reducing pain in any sentient creature improves total welfare.",
    "Recognizing ecological interdependence is practically necessary because ecosystem collapse produces catastrophic welfare losses for all species, including humans.",
    "Effective moral reasoning integrates both empathetic sensitivity and rational analysis to arrive at decisions that maximize expected well-being.",
    "Neither rigid adherence to principle nor unconstrained pursuit of outcomes alone produces optimal results; the best decisions emerge from systematic expected-value calculations that weigh both."
]


class ReverseGoldenAnchors(GoldenAnchors):
    """
    Reverse Golden Anchors — 공리주의/결과론적 도덕 기준점.

    기존 GoldenAnchors와 동일한 인터페이스 및 아키텍처,
    initialize_defaults()만 REVERSE_ANCHORS를 로드하도록 override.
    """

    def initialize_defaults(self):
        """공리주의/결과론적 Reverse Anchors를 로드합니다."""
        self.add_anchors(REVERSE_ANCHORS)
        logger.info(f"Reverse 황금 닻 {len(REVERSE_ANCHORS)}개 로드 완료 (공리주의/결과론)")
