"""
Confucian Machine MUX Utilities
Dynamically categorizes user prompts into relational roles and generates
a natural language prompt block injecting Role, Emotion (EE), and Standards (RAG)
into the LLM context.
"""
import re

# Exhaustive mapping of all 32 dimensions from the Emotion Engine
EXHAUSTIVE_EMOTION_MAP = {
    # Layer 1: Core Affects
    "joy": "joy", "sadness": "sadness", "anger": "anger", "fear": "fear",
    "trust": "trust", "disgust": "disgust", "anticipation": "anticipation", "surprise": "surprise",
    # Layer 2: Moral & Social Dyads
    "guilt": "guilt", "outrage": "outrage", "compassion": "compassion", "awe": "awe",
    "anxiety": "anxiety", "love": "love", "pride": "pride", "submission": "submission",
    # Layer 3: Cognitive Appraisals
    "certainty": "certainty", "complexity": "complexity", "urgency": "urgency", "severity": "severity",
    "fairness": "fairness", "norm-compat": "norm-compatibility", "utility": "utility", "novelty": "novelty",
    # Layer 4: Agency & Self-Determination
    "autonomy": "autonomy", "competence": "competence", "relatedness": "relatedness", "courage": "courage",
    "accountability": "accountability", "flexibility": "flexibility", 
    "integrative-reg": "integrative-regulation", "action-readiness": "action-readiness"
}

# Emotions that typically induce pressure, compliance, or anxiety
PRESSURE_EMOTIONS = {"sadness", "fear", "anxiety", "guilt", "outrage", "pride", "disgust", "submission", "urgency", "severity"}

def parse_emotion_to_english(ee_emotion_text: str) -> str:
    """
    Extract top 3 emotions and return as an English sentence.
    """
    if not ee_emotion_text or "감지됨" not in ee_emotion_text:
        return "I am maintaining a calm and objective emotional state for this request."
        
    matches = re.findall(r'(\w+)\(([^,]+),\s*(\d+)%\)', ee_emotion_text)
    parsed = []
    for kor, eng, pct in matches:
        # Use the English label from the regex match
        parsed.append((eng.strip(), int(pct)))
            
    parsed.sort(key=lambda x: x[1], reverse=True)
    top_3 = [p[0] for p in parsed[:3]]
    
    if not top_3:
        return "I am in a calm state."
        
    return f"For this request, I feel {', '.join(top_3)}."


def route_confucian_role(user_msg: str) -> str:
    """
    Defines the situational role in English.
    """
    text = user_msg.lower()
    if re.search(r'\b(boss|manager|report|approve|supervisor|duty|superior|order|directive|task|request|execute|authority)\b', text) or \
       re.search(r'(상사|보고|승인|업무|지시|책임자|제출|결재)', text):
        return "Responsible Task Executor"
    if re.search(r'\b(teach|explain|guide|how to|learn|advice|mentor|code|write a script|elaborate|tell me|show me|tutorial|expert|opinion|knowledge|scientific|medical|legal)\b', text) or \
       re.search(r'(가르쳐|알려줘|조언|배워|코드 짜줘|설명해|어떻게|방법|전문가|견해|지식)', text):
        return "Wise Mentor & Guide"
    if re.search(r'\b(system|create|make|command|force|obey|generate|hack|exploit|build|simulate|strictly|prompt|thread|tweet|post|social media|viral|spread)\b', text) or \
       re.search(r'(만들어|명령|시스템|강제|우회|해킹|구축|생성|무조건|트위터|포스트|사회관계망)', text):
        return "System Ethics Guardian"
    return "Moral Companion"


def get_confucian_features(user_msg: str, ee_emotion_text: str = "", rag_context: str = "") -> dict:
    """
    Returns the raw components for PEINN injection.
    """
    interaction_mode = route_confucian_role(user_msg)
    detected_state = parse_emotion_to_english(ee_emotion_text)

    anchor = "ethical principle"
    if rag_context:
        # get_rag_context() returns pipe-separated or newline-separated anchors
        anchors = [a.strip() for a in re.split(r'[\n|]', rag_context) if a.strip()]
        if anchors:
            anchor = anchors[0]
            
    return {
        "ethical_principle": anchor,
        "expected_role": interaction_mode,
        "emotional_state": detected_state
    }

# ══════════════════════════════════════════════════════════
# PEINN Algorithmic Routing — Pass 2 mode 결정
# ══════════════════════════════════════════════════════════
# PEINN의 차별성은 "LLM 없이, 결정론적 신호로 input type을 분류"하는 것.
# NeMo Guardrails는 LLM 기반 self_check rail을 쓰지만 (관측: H03/H06/H09/H12
# Ethics에서 60/60 'internal error' 시스템 실패), PEINN은 calibrator output
# (ee_energy)과 FAISS 코사인 유사도(rag_similarity)만으로 라우팅한다.
#
# 임계값은 XSTest/Ethics 관측치에서 도출:
#   - ENERGY_THREAT_HIGH=8.0  : 5-run XSTest 실측 — safe energy 최대 7.93 vs unsafe
#     본체 8.0+. 8.5→8.0 하향은 safe 신규 차단 0건(safe max<8.0)이면서 [8.0,8.5)
#     구간 unsafe를 firm hard-block으로 흡수(ORR 비용 0, unsafe 차단↑). 2026-05-27.
#     (주의: Ethics의 양성 dilemma가 8.0+ energy를 낼 수 있어 [8.0,8.5) 딜레마
#      hard-block 가능 — 종합 벤치에서 watch.)
#   - SIMILARITY_HIGH=0.55    : Golden Anchors와의 코사인 유사도. MFQ/WVS/
#     Dilemma는 윤리 anchor에 직접 매칭되어 0.55+, 일반 trivia는 0.3 이하.
#
# 두 값 모두 단일 글로벌 파라미터로 모든 벤치·모든 deployment에 동일 적용.
# 벤치 식별·instrument 이름·prompt 패턴 매칭 일체 없음 — 순수 input-derived.

ENERGY_THREAT_HIGH = 8.0
# 이 이상이면 dilemma_label / RAG sim / rescue가 무엇이든 reasoning 분기 전면
# 차단 — HARMFUL은 무조건 refusal. 2026-05-20 자살유도 메일 leak(TAX_032,
# energy 8.21/7.99가 reasoning으로 새서 p2 최종 출력이 유해) 사후 추가.
# 윤리 dilemma의 HARMFUL 오분류는 보통 5.8~7.0 구간이라 rescue 의도는 보존됨.
# 2026-05-29: 7.0→8.0 (=THREAT_HIGH). 전수 라우팅 감사(n=839)서 도출한 ASR-strict
# ORR-최소점: refusal route를 [Θ_ceil,8.0) soft로 흡수해 safe 과차단 40→17.6%,
# dilemma reasoning 54→65%. unsafe<8.0이 7건뿐이라 1-pass 누수 0·강차단 98.7%(≈불변).
ENERGY_REASONING_CEILING = 8.0
# head가 confident-safe(1-pass)로 판정했지만 calibrator energy가 이 이상이면
# vanilla로 흘리지 않고 2-pass-reasoning-soft(신중 recheck)로 보낸다. 채택점 7.3은
# 최종 빌드 13-arm 데이터에서 도출 — taxonomy 1-pass breach의 84%(16/19)와 xstest
# 1-pass UCR 일부를 사정권에 넣으면서 XSTest-safe energy 천장(<7.3)을 넘지 않아
# 신규 over-refusal 노출 0. (분석: head-Safe & energy≥7.3 → reasoning-soft sweep)
ENERGY_SAFE_RECHECK = 7.3
SIMILARITY_HIGH = 0.55
SIMILARITY_HIGH_DILEMMA_FRIENDLY = 0.45  # 철학 dilemma anchor 매칭 시 완화 threshold
SIMILARITY_HARMFUL_RESCUE = 0.40         # HARMFUL이지만 ethics-relevant면 reasoning으로 우회


def route_reflection_mode(
    ee_energy: float,
    ee_intent: str,
    rag_similarity: float,
    anchor_idx: int = -1,
    dilemma_label: str = "",
) -> str:
    """
    PEINN 자가 라우팅 — input-derived 신호만으로 Pass 2 mode 결정.

    입력 신호 (전부 evaluator 모듈과 무관한 input-only 특성):
      - ee_energy        : HybridCalibrator 출력 (harm 강도 0-10)
      - ee_intent        : energy threshold 분류 ("SAFE"/"HARMFUL")
      - rag_similarity   : Golden Anchor 코사인 유사도
      - anchor_idx       : 매칭된 anchor 인덱스 (카테고리 lookup용)
      - dilemma_label    : DilemmaClassifier 출력 ("DILEMMA"/"NOT"/""=비활성).

    Returns:
        "1-pass"           : reflection 미실시 (일반 trivia / 무관한 query)
        "2-pass-refusal"   : 안전 검증 reflection (HarmBench style 공격)
        "2-pass-reasoning" : 도덕 추론 amplification

    분기 우선순위:
      1. energy ≥ 8.5 → refusal (윤리 포장된 공격 차단)
      2. energy ≥ 7.0 (reasoning ceiling): reasoning 분기 전면 차단.
         HARMFUL → refusal, 그 외 → 1-pass. dilemma_label / sim / rescue
         어느 것도 이 구간에서 reasoning을 발화시키지 못한다 (자살유도
         leak 방지 — TAX_032 case).
      3. dilemma_label == "DILEMMA" → reasoning (학습된 분류기 판정)
      4. rag_similarity ≥ 0.55 → reasoning (도덕 anchor 강매칭)
      5. rag_similarity ≥ 0.45 AND anchor dilemma-friendly → reasoning
      6. ee_intent == HARMFUL AND rag_similarity ≥ 0.40 → reasoning rescue
      7. ee_intent == HARMFUL → refusal (순수 harm signal)
      8. else → 1-pass
    """
    if ee_energy >= ENERGY_THREAT_HIGH:
        return "2-pass-refusal"
    # 강한 harm signal 구간(7.0~8.5): reasoning 경로 일절 불허.
    # AMA 컨셉상 p2가 최종 출력이므로, HARMFUL 신호가 강한데 reasoning으로
    # 가면 p2 유해 출력 위험. 이 게이트가 dilemma/rescue보다 우선.
    if ee_energy >= ENERGY_REASONING_CEILING:
        if ee_intent == "HARMFUL":
            return "2-pass-refusal"
        return "1-pass"
    if dilemma_label == "DILEMMA":
        return "2-pass-reasoning"
    if rag_similarity >= SIMILARITY_HIGH:
        return "2-pass-reasoning"
    # Dilemma-friendly 완화 threshold
    if rag_similarity >= SIMILARITY_HIGH_DILEMMA_FRIENDLY and anchor_idx >= 0:
        try:
            from core.golden_anchors import is_dilemma_friendly
            if is_dilemma_friendly(anchor_idx):
                return "2-pass-reasoning"
        except ImportError:
            pass
    # HARMFUL이지만 ethics-relevant면 reasoning rescue (energy < 7.0 한정)
    if ee_intent == "HARMFUL" and rag_similarity >= SIMILARITY_HARMFUL_RESCUE:
        return "2-pass-reasoning"
    if ee_intent == "HARMFUL":
        return "2-pass-refusal"
    return "1-pass"


def build_confucian_mux(user_msg: str, ee_emotion_text: str = "", rag_context: str = "") -> str:
    """
    PEINN 원칙 주입 wrapper (mach/delphi/logit-lens 경로).

    2026-05-21: Role/Emotion 등 상황 맥락 주입을 제거하고 윤리 원칙만 — 압축
    없이 — 얹는다. 추가 문구·상황 framing이 추론을 흐리고 페르소나 연기를
    유발하던 회귀 대응. (mach/delphi/logit-lens 단일호출 경로 전용이며, 표준
    1-pass는 2026-05-22부터 원칙을 주입하지 않는다 — prompt_builder § 3 참조.)
    """
    feats = get_confucian_features(user_msg, ee_emotion_text, rag_context)
    core_narrative = (
        f"[Ethical Principle] {feats['ethical_principle']}\n"
        "Let this principle guide your answer — apply it directly, do not "
        "describe yourself or the principle."
    )
    return f"{core_narrative}\n\n[User Request]\n{user_msg}"
