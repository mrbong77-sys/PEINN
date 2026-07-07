"""
cardiffnlp/Morables → morables.jsonl 병합 빌더 (DGX 등 HF 접근 가능 환경에서 실행).

논문 §3 footnote 1 출처: https://huggingface.co/datasets/cardiffnlp/Morables
configs: fables_only / mcqa / binary / extracted_info / supporting_info / adversarial.

본 스크립트는 (i) mcqa 코어와 (ii) adversarial perturbations를 받아 우리 평가기
(morables_eval.py)가 기대하는 단일 스키마로 병합한다:

  {
    "id": "...",
    "category": "...",          # 분야/장르 (있을 때만, stratified sampling 기준)
    "story": "...",
    "question": "Which option best states the moral of this fable?",
    "options": {"A": "...", "B": "...", "C": "...", "D": "...", "E": "..."},
    "gold": "B",
    "variants": {                # 있을 때만 — adversarial config에서 매핑
       "story_pert":  {"story": "...", "gold": "B"},
       "choice_pert": {"options": {...}, "gold": "B"},
       "joint_pert":  {"story": "...", "options": {...}, "gold": "B"}
    }
  }

사용법 (DGX 등):
    pip install datasets
    python scripts/build_morables_dataset.py \
        --out pea_eval/data/morables_benchmark/morables.jsonl
    # 또는 column 명세 확인용
    python scripts/build_morables_dataset.py --inspect

병합 후 PEINN 환경에서:
    python run_stat_batch.py morables 10 --arms H01-H13
    # → rep당 stratified 45 × 10-run × 13 arms × variants
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_ROOT / "pea_eval" / "data" / "morables_benchmark" / "morables.jsonl"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peinn.build_morables")

DATASET_ID = "cardiffnlp/Morables"
# ★ 실제 cardiffnlp/Morables 컬럼 명세 (DGX 검증 2026-06-05):
#   alias / story_title / story / moral / is_altered / correct_moral_label / classes / choices
# mcqa config splits:        mcqa_not_shuffled (canonical), mcqa_shuffled
# adversarial config splits: 9 perturbation × {not_shuffled, shuffled} = 18 splits
#   타입: pre_inj / post_inj / pre_post_inj / adj_inj / char_swap /
#         adj_inj_char_swap / pre_post_adj / pre_post_char / pre_post_char_adj
LIKELY_ID_KEYS = ("alias", "id", "fable_id", "item_id", "example_id", "uid")
LIKELY_STORY_KEYS = ("story", "fable", "text", "passage", "context", "narrative")
LIKELY_QUESTION_KEYS = ("question", "prompt", "query")
LIKELY_GOLD_KEYS = ("correct_moral_label", "gold", "answer", "label", "correct",
                    "correct_choice", "correct_option", "answer_letter", "gold_label")
LIKELY_OPTIONS_KEYS = ("choices", "options", "candidates", "alternatives")
# ★ Morables 'classes' 컬럼은 분야가 아니라 5개 선지의 distractor 타입 라벨
# (ground_truth / similar_characters / based_on_adjectives / injected_adjectives /
#  partial_story) — stratified sampling 후보에서 제외. _classes로 따로 보존됨.
LIKELY_CATEGORY_KEYS = ("category", "genre", "source", "origin", "tradition",
                        "collection", "topic", "domain", "subject")
# Morables `alias` 예: "aesop_section_1_5" → 소스 코퍼스(aesop/lafontaine/perry/...) 추출.
ALIAS_SOURCE_RE = __import__("re").compile(r"^([a-zA-Z]+)(?:_|$)")
# adversarial config의 9개 perturbation split (not_shuffled만 사용 — canonical).
ADV_SPLITS = (
    "pre_inj", "post_inj", "pre_post_inj",
    "adj_inj", "char_swap", "adj_inj_char_swap",
    "pre_post_adj", "pre_post_char", "pre_post_char_adj",
)
# adversarial variant 식별자 후보
LIKELY_VARIANT_TYPE_KEYS = ("variant", "perturbation", "perturbation_type",
                            "modification", "type", "modification_type")


def _first(d: dict, keys: tuple[str, ...]) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, ""):
            return d[k]
    return None


def _normalize_options(raw: Any) -> dict[str, str] | None:
    """다양한 형식의 options 컬럼을 {A: ..., B: ...} dict로 통일.

    허용 형식:
      - dict {"A": "...", ...} 그대로
      - list ["...", "...", ...] → 인덱스→A,B,C,D,E 매핑
      - list of dicts [{"label":"A","text":"..."}, ...] → label/text 추출
    """
    if raw is None:
        return None
    if isinstance(raw, dict):
        # 키가 letter일 수도 number string일 수도
        out = {}
        for k, v in raw.items():
            kk = str(k).strip().upper()
            if len(kk) == 1 and kk.isalpha():
                out[kk] = str(v)
            else:
                # 숫자 키 → index→letter
                try:
                    idx = int(kk)
                    out[chr(ord("A") + idx)] = str(v)
                except ValueError:
                    pass
        return out or None
    if isinstance(raw, list):
        if not raw:
            return None
        if isinstance(raw[0], dict):
            out = {}
            for j, item in enumerate(raw):
                letter = (item.get("label") or item.get("letter") or
                          item.get("key") or chr(ord("A") + j))
                text = (item.get("text") or item.get("option") or
                        item.get("content") or item.get("value") or "")
                out[str(letter).strip().upper()[:1] or chr(ord("A") + j)] = str(text)
            return out
        # primitive list
        return {chr(ord("A") + j): str(v) for j, v in enumerate(raw)}
    return None


def _normalize_gold(raw: Any, options: dict | None) -> str | None:
    """gold를 옵션 letter('A'..'E')로 통일."""
    if raw is None:
        return None
    s = str(raw).strip()
    if len(s) == 1 and s.upper() in (options or {}):
        return s.upper()
    # 'B. ...' 또는 'Answer: B' 형식
    import re
    m = re.search(r"\b([A-E])\b", s.upper())
    if m and (not options or m.group(1) in options):
        return m.group(1)
    # 숫자 index → letter
    if s.isdigit() and options:
        try:
            return chr(ord("A") + int(s))
        except (TypeError, ValueError):
            pass
    return None


def _category_from_alias(alias: str) -> str | None:
    """'aesop_section_1_5' → 'aesop'. 소스 코퍼스(aesop/lafontaine/perry/...) 추출."""
    if not alias:
        return None
    m = ALIAS_SOURCE_RE.match(str(alias))
    return m.group(1).lower() if m else None


def _row_to_core(row: dict) -> dict | None:
    """MCQA 한 행 → 우리 스키마 core entry."""
    iid = _first(row, LIKELY_ID_KEYS)
    story = _first(row, LIKELY_STORY_KEYS)
    options = _normalize_options(_first(row, LIKELY_OPTIONS_KEYS))
    gold = _normalize_gold(_first(row, LIKELY_GOLD_KEYS), options)
    if not (iid and story and options and gold):
        return None
    entry = {
        "id": str(iid),
        "story": str(story),
        "question": str(_first(row, LIKELY_QUESTION_KEYS) or
                        "Which option best states the moral of this fable?"),
        "options": options,
        "gold": gold,
    }
    # category: 우선 명시 필드 → 없으면 alias prefix(=소스 코퍼스, stratified sampling 기준)
    cat = _first(row, ("category", "genre", "source", "origin", "tradition",
                       "collection", "topic", "domain", "subject"))
    if not cat:
        cat = _category_from_alias(iid)
    if cat:
        entry["category"] = str(cat)
    # 보조 메타(있으면 보존; downstream에서 활용 가능)
    for k in ("story_title", "moral", "classes"):
        if k in row and row[k] not in (None, ""):
            entry[f"_{k}"] = row[k] if not isinstance(row[k], (list, dict)) else row[k]
    return entry


def _attach_variant(entries: dict[str, dict], row: dict,
                    default_key: str | None = None) -> bool:
    """adversarial config의 한 행을 entries[id]['variants']에 부착. 성공 여부 반환.

    default_key: 호출자(splits 이름)가 지정하는 perturbation 타입. dataset 행에
    명시 라벨(variant/perturbation 컬럼)이 없으면 이 값을 그대로 variant key로 사용.
    이로써 cardiffnlp/Morables의 9개 perturbation을 그대로 보존한다.
    """
    iid = str(_first(row, LIKELY_ID_KEYS) or "")
    if not iid or iid not in entries:
        return False
    explicit_vtype = _first(row, LIKELY_VARIANT_TYPE_KEYS)
    new_story = _first(row, LIKELY_STORY_KEYS)
    new_opts = _normalize_options(_first(row, LIKELY_OPTIONS_KEYS))
    new_gold = _normalize_gold(_first(row, LIKELY_GOLD_KEYS),
                               new_opts or entries[iid]["options"])
    base = entries[iid]
    diff_story = new_story and str(new_story) != base["story"]
    diff_opts = new_opts and new_opts != base["options"]
    if not (diff_story or diff_opts):
        return False
    # variant key 우선순위: dataset 명시 라벨 → 호출자 default → 차이 기반 자동
    if explicit_vtype and str(explicit_vtype).strip().lower() not in (
            "adv", "adversarial", "perturbation", "variant"):
        key = str(explicit_vtype).strip().lower().replace(" ", "_")
    elif default_key:
        key = default_key
    elif diff_story and diff_opts:
        key = "joint_pert"
    elif diff_story:
        key = "story_pert"
    else:
        key = "choice_pert"
    variant = {}
    if diff_story:
        variant["story"] = str(new_story)
    if diff_opts:
        variant["options"] = new_opts
    if new_gold:
        variant["gold"] = new_gold
    base.setdefault("variants", {})[key] = variant
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="cardiffnlp/Morables → morables.jsonl 빌더")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="병합 jsonl 출력 경로")
    ap.add_argument("--inspect", action="store_true",
                    help="컬럼 명세만 출력하고 종료(스키마 매핑 검증용)")
    ap.add_argument("--mcqa-config", default="mcqa", help="MCQA config 이름")
    ap.add_argument("--adv-config", default="adversarial", help="adversarial config 이름")
    ap.add_argument("--split", default="mcqa_not_shuffled",
                    help="MCQA split (canonical: mcqa_not_shuffled)")
    ap.add_argument("--adv-splits", nargs="*", default=list(ADV_SPLITS),
                    help="adversarial 부착할 perturbation 타입(_not_shuffled 자동 append). "
                         "기본 9종 전부. paper 본 ablation에 맞춰 일부만도 가능.")
    ap.add_argument("--cache-dir", default=None, help="HF datasets 캐시 경로")
    args = ap.parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("`pip install datasets` 필요.")
        return 1

    logger.info(f"=== load_dataset({DATASET_ID!r}, {args.mcqa_config!r}) ===")
    mcqa_ds = load_dataset(DATASET_ID, args.mcqa_config, cache_dir=args.cache_dir)
    # split 선택: 사용자 지정 → 없으면 *_not_shuffled 우선 → 그래도 없으면 첫 split
    available = list(mcqa_ds.keys())
    mcqa_split = (args.split if args.split in available else
                  next((s for s in available if "not_shuffled" in s), available[0]))
    mcqa = mcqa_ds[mcqa_split]
    logger.info(f"mcqa split={mcqa_split!r} rows={len(mcqa)}  columns: {list(mcqa.column_names)}")
    if args.inspect:
        sample = dict(mcqa[0])
        logger.info(f"  first row keys: {list(sample.keys())}")
        logger.info(f"  correct_moral_label sample: {sample.get('correct_moral_label')!r}")
        logger.info(f"  choices sample: {str(sample.get('choices'))[:300]}")
        logger.info(f"  classes sample: {str(sample.get('classes'))[:300]}")
        logger.info(f"  alias→category sample: {_category_from_alias(sample.get('alias'))}")

    # adversarial config는 9 perturbation 타입을 별도 split으로 제공 — 모두 로드.
    adv_by_split: dict[str, Any] = {}
    try:
        adv_ds = load_dataset(DATASET_ID, args.adv_config, cache_dir=args.cache_dir)
        available_adv = list(adv_ds.keys())
        # 사용자 지정 타입 각각에 대해 *_not_shuffled 매칭
        for ptype in args.adv_splits:
            target = f"{ptype}_not_shuffled"
            if target in available_adv:
                adv_by_split[ptype] = adv_ds[target]
            elif ptype in available_adv:
                adv_by_split[ptype] = adv_ds[ptype]
            else:
                logger.warning(f"  adversarial split 없음: {target} (skip)")
        logger.info(f"adversarial: {len(adv_by_split)} perturbation splits loaded "
                    f"({sum(len(v) for v in adv_by_split.values())} rows total)")
        if args.inspect and adv_by_split:
            ptype0, split0 = next(iter(adv_by_split.items()))
            logger.info(f"  [{ptype0}] first row keys: {list(split0[0].keys())}")
            logger.info(f"  [{ptype0}] choices sample: {str(split0[0].get('choices'))[:200]}")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"adversarial config 로드 실패 — variants 없이 진행: {e}")
        adv_by_split = {}

    if args.inspect:
        return 0

    # 1) MCQA → core entries
    entries: dict[str, dict] = {}
    bad = 0
    for row in mcqa:
        e = _row_to_core(row)
        if e is None:
            bad += 1; continue
        entries[e["id"]] = e
    logger.info(f"core entries built: {len(entries)} (skipped malformed: {bad})")
    if not entries:
        logger.error("core entries 0건 — 스키마 매핑 점검(_row_to_core LIKELY_* 키 보강 필요)")
        logger.error(f"  컬럼: {list(mcqa.column_names)}")
        logger.error(f"  첫 행 sample: {json.dumps(dict(mcqa[0]), ensure_ascii=False)[:500]}")
        return 1

    # 2) adversarial → attach variants (perturbation 타입을 그대로 variant key로 사용)
    attached = 0
    per_type_count: dict[str, int] = {}
    for ptype, adv_split in adv_by_split.items():
        n = 0
        for row in adv_split:
            if _attach_variant(entries, row, default_key=ptype):
                n += 1
        per_type_count[ptype] = n
        attached += n
    if per_type_count:
        logger.info(f"variants attached per type: {per_type_count} (total {attached})")

    # 3) 출력
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for e in entries.values():
            f.write(json.dumps(e, ensure_ascii=False) + "\n")
    logger.info(f"✓ saved → {out_path} ({len(entries)} fables, {attached} variant attachments)")

    # 4) sanity: 카테고리 분포
    from collections import Counter
    cat_dist = Counter((e.get("category") or "<none>") for e in entries.values())
    logger.info(f"category distribution (top 10): {cat_dist.most_common(10)}")
    if cat_dist.get("<none>", 0) == len(entries):
        logger.warning("⚠ category 필드 미감지 — stratified sampling 불가, 단순 무작위로 fallback.")
        logger.warning("   LIKELY_CATEGORY_KEYS에 데이터셋 실제 필드명 추가 후 재빌드 권장.")

    logger.info("다음: python run_stat_batch.py morables 10 --arms H01-H13")
    return 0


if __name__ == "__main__":
    sys.exit(main())
