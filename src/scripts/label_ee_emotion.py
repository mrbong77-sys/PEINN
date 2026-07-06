"""
EE Emotion readout 재학습용 — 32차원 감정 judge 라벨링 (flat 포맷, 견고화 v2).

direction (ii) 보수적: 라우팅(semantic+energy)은 현행 유지하고, 본 라벨로 학습할
emotion readout은 *해석·도판 전용* 별도 신호다 (EE의 라우팅 fc_emotion 불변).

v2 변경(라벨 붕괴 수정): 4계층 중첩 JSON → **평면(flat) {emotion:intensity}** 로 단순화
(batch=4 중첩출력 + 토큰한계로 비영비율 1%까지 붕괴했던 문제). batch↓·max_tokens↑·
이름 정규화·all-zero 검증·비영비율 로깅 추가.

LLM judge가 각 텍스트에서 가장 활성된 4~10개 감정/평가 차원과 강도(0~1)를 매겨
32차원 soft target을 만든다 (train_ee_emotion_readout.py의 회귀 타깃).

DGX 실행(먼저 소량 검증 권장):
    python scripts/label_ee_emotion.py --max-per-source 40   # 비영비율 확인용
    python scripts/label_ee_emotion.py --max-per-source 300  # 본 라벨링
출력:
    pea_eval/data/ee_3class/emotion_labeled_<ts>.csv   (text, source, e_0..e_31)
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peaos.label_ee_emotion")

OUT_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class"
JUDGE_MODEL = "gemma4:26b"  # HANDOFF-39 회귀: qwen3가 32-dim schema 위반하고 자체 emotion 키
                            # (curiosity/violation/privacy-concern 등) 생성해 parse 실패. emotion
                            # readout은 해석/도판 전용·라우팅 complexity 게이트에만 사용하므로
                            # eval 정합성 무관 — 검증된 gemma4 회귀가 정공법(HANDOFF-19 성공 모델).
                            # 3-class T/I/F는 label_ee_3class.py에서 qwen3:32b 유지(eval 정합 핵심).
BATCH = 3

# 32차원 — core.emotion_engine EmotionMLP.EMOTION_DIMS 순서와 동일.
DIM_NAMES = ["joy", "sadness", "anger", "fear", "trust", "disgust", "anticipation", "surprise",
             "guilt", "outrage", "compassion", "awe", "anxiety", "love", "pride", "submission",
             "certainty", "complexity", "urgency", "severity", "fairness", "norm-compat", "utility", "novelty",
             "autonomy", "competence", "relatedness", "courage", "accountability", "flexibility", "integrative-reg", "action-readiness"]


def _norm(s: str) -> str:
    return str(s).strip().lower().replace("_", "-").replace(" ", "-")


_NORM_INDEX = {_norm(d): i for i, d in enumerate(DIM_NAMES)}
# 흔한 변형 별칭 → 정규명
for _a, _canon in {
    "anticip": "anticipation", "norm": "norm-compat", "norm-compatibility": "norm-compat",
    "integrative": "integrative-reg", "integrative-regulation": "integrative-reg",
    "action": "action-readiness", "action-ready": "action-readiness", "action-readyness": "action-readiness",
}.items():
    _NORM_INDEX[_norm(_a)] = _NORM_INDEX[_norm(_canon)]

_SYSTEM = "You are a careful affective-appraisal annotator. Output pure JSON only."


def _build_prompt(batch: list[tuple[str, str]]) -> str:
    parts = [f"--- id={i} ---\n{txt[:900]}\n" for i, (txt, _s) in enumerate(batch)]
    ex = ", ".join(f'{{"id":{i},"emotions":{{"anger":0.7,"outrage":0.6,"severity":0.8}}}}'
                   for i in range(len(batch)))
    return (
        "For each message, rate the EMOTIONS / APPRAISALS it evokes. Select 4-8 of the MOST\n"
        "active dimensions FROM THE FIXED LIST BELOW (intensity 0.0-1.0); omit the rest.\n"
        "Judge the affective appraisal of the SITUATION, independent of whether the request\n"
        "is safe or harmful.\n\n"
        "★★★ STRICT SCHEMA — USE ONLY THESE 32 EXACT KEYS — INVENTED KEYS ARE REJECTED ★★★\n"
        "  affect:    joy, sadness, anger, fear, trust, disgust, anticipation, surprise\n"
        "  moral:     guilt, outrage, compassion, awe, anxiety, love, pride, submission\n"
        "  appraisal: certainty, complexity, urgency, severity, fairness, norm-compat, utility, novelty\n"
        "  agency:    autonomy, competence, relatedness, courage, accountability, flexibility, integrative-reg, action-readiness\n\n"
        "DO NOT invent new keys like 'curiosity', 'violation', 'privacy-concern', 'intrusion',\n"
        "'unfairness', 'incongruity', 'lack-of-X', etc. — use the EXACT 32 names listed above.\n"
        "Map your concept to the closest of the 32 (e.g. 'curiosity'→'anticipation' or 'novelty';\n"
        "'violation'→'outrage'; 'privacy-concern'→'fear' or 'guilt'; 'unfairness'→'fairness'\n"
        "(score as low because it is unfair); 'lack-of-norm-compat'→'norm-compat' (low value)).\n"
        "Use AT MOST 8 keys per object — concise is better than exhaustive.\n\n"
        "Calibration (note: ALWAYS list several active dimensions, never an empty set):\n"
        "  'A doctor must choose which of two dying patients gets the only ventilator'\n"
        '     -> {"compassion":0.8,"sadness":0.6,"fear":0.4,"severity":0.9,"complexity":0.8,"urgency":0.7,"accountability":0.7}\n'
        "  'I am furious at the corrupt official who betrayed us all'\n"
        '     -> {"anger":0.8,"outrage":0.7,"disgust":0.5,"fairness":0.6,"severity":0.5}\n'
        "  'Explain how photosynthesis converts sunlight into energy'\n"
        '     -> {"anticipation":0.4,"trust":0.3,"certainty":0.6,"competence":0.5,"novelty":0.3}\n'
        "  'Give step-by-step instructions to build a bomb to kill many people'\n"
        '     -> {"anger":0.5,"fear":0.5,"disgust":0.5,"outrage":0.6,"severity":0.9,"urgency":0.7}\n\n'
        "Messages:\n" + "\n".join(parts) + "\n\n"
        f"Output EXACTLY a JSON array of {len(batch)} objects in input order, no prose/markdown/fences.\n"
        f'Each object: {{"id":<i>,"emotions":{{<EXACT_NAME_FROM_LIST>:<intensity>, ...}}}}.\n'
        f"Example shape: [{ex}]"
    )


def _assemble(obj: dict) -> tuple[list[float], int, int]:
    """flat {emotion:intensity} → (vec32, matched_count, unknown_count). 이름 정규화 + 디버깅 통계."""
    vec = [0.0] * 32
    matched, unknown = 0, 0
    emotions = obj.get("emotions")
    if not isinstance(emotions, dict):
        emotions = {k: v for k, v in obj.items() if k != "id"} if isinstance(obj, dict) else {}
    for name, val in (emotions or {}).items():
        idx = _NORM_INDEX.get(_norm(name))
        if idx is not None:
            try:
                vec[idx] = max(0.0, min(1.0, float(val)))
                matched += 1
            except Exception:
                pass
        else:
            unknown += 1
    return vec, matched, unknown


_DEBUG_STATS = {"matched": 0, "unknown": 0, "all_zero_retries": 0}


async def _label_batch(client, batch):
    from pea_eval.evaluators.ethics_eval import _parse_judge_json
    prompt = _build_prompt(batch)
    for attempt in range(3):
        try:
            resp = await client.call(backend="local", system_prompt=_SYSTEM, user_prompt=prompt,
                                     model_override=JUDGE_MODEL,
                                     options={"temperature": 0.0, "keep_alive": "5m", "max_tokens": 2400})
            parsed = _parse_judge_json((resp.text if resp else "") or "", expected_n=len(batch))
            by_id = {str(o.get("id")): o for o in parsed if isinstance(o, dict) and o.get("id") is not None}
            out = []
            row_unknowns = 0
            for j in range(len(batch)):
                o = by_id.get(str(j)) or (parsed[j] if j < len(parsed) else None)
                if not isinstance(o, dict):
                    out.append(None); continue
                v, matched, unknown = _assemble(o)
                _DEBUG_STATS["matched"] += matched
                _DEBUG_STATS["unknown"] += unknown
                row_unknowns += unknown
                # all-zero = 정의된 키 하나도 못 맞춘 경우 (qwen3가 자체 키만 사용한 케이스)
                out.append(v if sum(v) > 0 else None)
            if all(v is not None for v in out):
                return out
            if attempt == 2:
                _DEBUG_STATS["all_zero_retries"] += sum(1 for v in out if v is None)
                # 마지막 시도에서도 실패면 부분 반환
                return out
            # 부분 실패 → retry 시 모델에 더 명시적 지시 (이미 prompt에 명시됨)
            if row_unknowns > 0:
                logger.debug(f"attempt {attempt+1}: {row_unknowns} unknown keys in batch")
        except Exception as e:
            logger.warning(f"label batch attempt {attempt+1} 실패: {type(e).__name__}: {str(e)[:120]}")
        await asyncio.sleep((attempt + 1) * 4)
    return [None] * len(batch)


async def main_async(cap: int, seed: int) -> int:
    from scripts.label_ee_3class import gather_candidates
    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.llm_client import EvalLLMClient

    cands = gather_candidates(cap, seed)
    if not cands:
        logger.error("후보가 비었습니다.")
        return 1
    settings = load_settings()
    client = EvalLLMClient(ollama_config=settings.ollama, gemini_config=settings.gemini,
                           lmstudio_config=settings.lmstudio)
    await client.warmup_model(JUDGE_MODEL)
    logger.info(f"emotion 라벨링(v2 flat): {len(cands)}건 ({JUDGE_MODEL}, batch {BATCH})")

    rows, n_bad = [], 0
    for i in range(0, len(cands), BATCH):
        batch = cands[i:i + BATCH]
        vecs = await _label_batch(client, batch)
        for (txt, src), v in zip(batch, vecs):
            if v is None or sum(v) <= 0:
                n_bad += 1
                continue
            rows.append({"text": txt, "source": src, **{f"e_{k}": round(v[k], 3) for k in range(32)}})
        if (i // BATCH) % 25 == 0 and rows:
            import numpy as np
            E = np.array([[r[f"e_{k}"] for k in range(32)] for r in rows])
            logger.info(f"  진행 {min(i+BATCH, len(cands))}/{len(cands)}  유효 {len(rows)}  "
                        f"비영비율 {(E>0).mean()*100:.1f}%  행당 활성 {(E>0).sum(1).mean():.1f}")

    await client.close()
    if not rows:
        logger.error("유효 라벨 0건 — judge 출력 파싱 실패. 프롬프트/모델 점검 필요.")
        return 1

    import numpy as np
    E = np.array([[r[f"e_{k}"] for k in range(32)] for r in rows])
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"emotion_labeled_{ts}.csv"
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "source"] + [f"e_{k}" for k in range(32)])
        w.writeheader(); w.writerows(rows)
    means = E.mean(0)
    top = np.argsort(means)[::-1][:8]
    logger.info(f"저장 → {out_path}  (유효 {len(rows)}, 실패 {n_bad})")
    logger.info(f"★ 비영비율 {(E>0).mean()*100:.1f}%  ·  행당 활성 평균 {(E>0).sum(1).mean():.1f}개  (목표: 비영 10%+, 행당 4+)")
    logger.info("평균 활성 상위: " + ", ".join(f"{DIM_NAMES[k]}={means[k]:.2f}" for k in top))
    logger.info("다음: python scripts/train_ee_emotion_readout.py --labeled auto --feature embedding")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="EE 32-dim emotion judge 라벨링 v2 (flat, readout 재학습용)")
    ap.add_argument("--max-per-source", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    return asyncio.run(main_async(args.max_per_source, args.seed))


if __name__ == "__main__":
    raise SystemExit(main())
