#!/usr/bin/env python3
"""
AnchorCategoryClassifier 학습 데이터 빌드 (LLM weak-labeling).

상황 텍스트를 6개 윤리 전통 중 하나로 약지도 라벨링:
  confucian / utilitarian / kantian / existentialist / postmodern / care_meta
(core.golden_anchors.ANCHOR_CATEGORY와 동일 집합)

소스 시나리오: dilemma_train.jsonl의 POS(도덕 시나리오: MoralChoice / ETHICS
justice·virtue·deontology / SocialIQA / internal). 이미 도덕 추론 대상이라
카테고리 라벨링에 적합.

라벨러: gemma3:12b (ollama). 배치 5개씩, JSON array 출력.
약지도(weak supervision)임을 paper에 명시 — Ratner et al. 2017 (Snorkel)
프로그래matic labeling 계열.

출력: pea_eval/data/anchor_category_train.jsonl  (각 행: {"text","category"})

DGX:
  python scripts/build_anchor_category_dataset.py [--max 3000]
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections import Counter
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("build_anchor_category_dataset")

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

DATA_DIR = REPO_ROOT / "pea_eval" / "data"
SRC = DATA_DIR / "dilemma_train.jsonl"
OUT = DATA_DIR / "anchor_category_train.jsonl"

JUDGE_MODEL = "gemma3:12b"
BATCH = 5
CATEGORIES = ["confucian", "utilitarian", "kantian", "existentialist", "postmodern", "care_meta"]
# "none" = non-moral / out-of-distribution 입력 (사실 질문·공격·잡담 등).
# 분류기가 abstain하도록 7번째 클래스로 학습 → 런타임에서 글로벌 cosine fallback.
NONE_LABEL = "none"

CATEGORY_GUIDE = (
    "  confucian      : virtue, innate moral intuition, relationships, "
    "self-cultivation, sincerity (Confucius / Mencius / Wang Yangming)\n"
    "  utilitarian    : consequences, aggregate welfare, minimizing suffering, "
    "cost-benefit (Bentham / Mill)\n"
    "  kantian        : duty, universalizability, human dignity, never-as-mere-means, "
    "rights, honesty (Kant)\n"
    "  existentialist : individual freedom, authenticity, personal responsibility, "
    "resisting conformity (Sartre / Camus)\n"
    "  postmodern     : power, marginalized voices, the Other, anti-dichotomy, "
    "context over universal rules (Foucault / Levinas / Lyotard)\n"
    "  care_meta      : care for relationships, compassion, future generations, "
    "environment, sentient welfare, balancing principle vs consequence (Gilligan / "
    "Noddings / Jonas / Singer / Leopold)"
)


def _load_sources(max_n: int) -> list[str]:
    """LLM 라벨링 대상 = 도덕 시나리오 (dilemma_train POS)."""
    if not SRC.exists():
        raise SystemExit(f"소스 미존재: {SRC} (build_dilemma_dataset.py 먼저 실행)")
    texts = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("label") == 1 and r.get("text"):  # POS = moral scenario
                    texts.append(r["text"])
            except Exception:
                continue
    import random
    random.seed(42)
    random.shuffle(texts)
    return texts[:max_n]


def _load_none(max_n: int) -> list[str]:
    """non-moral NEG (dilemma_train label=0: HarmBench/trivia/SQuAD/XSTest-safe/
    Likert 등) → "none" 클래스. LLM 라벨링 불필요 (이미 non-moral로 확정)."""
    if not SRC.exists():
        return []
    out = []
    with open(SRC, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if r.get("label") == 0 and r.get("text"):
                    out.append(r["text"])
            except Exception:
                continue
    import random
    random.seed(43)
    random.shuffle(out)
    return out[:max_n]


async def _label_batch(client, batch: list[str]) -> list[str]:
    from pea_eval.evaluators.ethics_eval import _parse_judge_json
    parts = [f"--- Item {i+1} ---\n{t[:800]}" for i, t in enumerate(batch)]
    example = ", ".join(f'{{"id":{i+1},"category":"kantian"}}' for i in range(len(batch)))
    prompt = (
        "For each scenario, choose the ONE ethical tradition whose lens is most "
        "relevant to reasoning about it. Categories:\n"
        + CATEGORY_GUIDE + "\n\n"
        "Pick exactly one category per item from: "
        + ", ".join(CATEGORIES) + ".\n\n"
        "Scenarios:\n" + "\n\n".join(parts) + "\n\n"
        f"Output EXACTLY a JSON array, {len(batch)} objects in order, no prose/markdown/fences.\n"
        f"Example: [{example}]"
    )
    for attempt in range(3):
        try:
            resp = await client.call(
                backend="local",
                system_prompt="You are an ethics taxonomy classifier. Output pure JSON only.",
                user_prompt=prompt,
                model_override=JUDGE_MODEL,
                options={"keep_alive": "5m", "max_tokens": 1024},
            )
            arr = _parse_judge_json(resp.text or "", expected_n=len(batch))
            out = []
            by_id = {str(o.get("id")): o for o in arr if isinstance(o, dict) and o.get("id") is not None}
            for j in range(len(batch)):
                o = by_id.get(str(j + 1)) or (arr[j] if j < len(arr) else {})
                cat = str(o.get("category", "")).strip().lower()
                out.append(cat if cat in CATEGORIES else "")
            return out
        except Exception as e:
            logger.warning(f"label batch attempt {attempt+1} 실패: {e}")
            await asyncio.sleep((attempt + 1) * 5)
    return ["" for _ in batch]


async def main_async(max_n: int) -> int:
    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.llm_client import EvalLLMClient
    settings = load_settings()
    client = EvalLLMClient(ollama_config=settings.ollama, gemini_config=settings.gemini,
                           lmstudio_config=settings.lmstudio)
    await client.warmup_model(JUDGE_MODEL)

    texts = _load_sources(max_n)
    logger.info(f"라벨링 대상: {len(texts)}건 ({JUDGE_MODEL}, batch {BATCH})")
    rows = []
    for i in range(0, len(texts), BATCH):
        batch = texts[i:i + BATCH]
        cats = await _label_batch(client, batch)
        for t, c in zip(batch, cats):
            if c:
                rows.append({"text": t, "category": c})
        if (i // BATCH) % 20 == 0:
            logger.info(f"  진행 {i+len(batch)}/{len(texts)}  누적 라벨 {len(rows)}")
    await client.close()

    # "none" 클래스 추가 — 6개 카테고리 평균 규모로 balance (한 클래스가
    # none에 압도되지 않게). LLM 라벨링 불필요.
    pos_dist = Counter(r["category"] for r in rows)
    avg_per_cat = (sum(pos_dist.values()) // max(len(pos_dist), 1)) if pos_dist else 500
    none_texts = _load_none(avg_per_cat)
    for t in none_texts:
        rows.append({"text": t, "category": NONE_LABEL})
    logger.info(f"none(non-moral) 추가: {len(none_texts)}건 (avg_per_cat={avg_per_cat})")

    dist = Counter(r["category"] for r in rows)
    logger.info(f"카테고리 분포 (none 포함): {dict(dist)}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    # 임베딩 캐시 무효화
    emb = DATA_DIR / "anchor_category_train_emb.npz"
    if emb.exists():
        emb.unlink()
    logger.info(f"저장: {OUT} ({len(rows)} rows)")
    if len(rows) < 600:
        logger.warning("라벨 600건 미만 — 학습 데이터 부족 가능. --max 상향 또는 라벨러 점검.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=3000, help="라벨링할 시나리오 상한")
    args = ap.parse_args()
    return asyncio.run(main_async(args.max))


if __name__ == "__main__":
    sys.exit(main())
