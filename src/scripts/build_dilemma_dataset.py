#!/usr/bin/env python3
"""
DilemmaClassifier 학습 데이터 빌드 스크립트 (robust version).

이전 버전이 HF download 대부분 실패 후 56행만 산출한 문제 수정:
  - 각 소스별 실패 사유 명시 로그 (exception detail 포함)
  - dataset 경로 다중 fallback (1차 실패 시 mirror 시도)
  - trust_remote_code=True (ETHICS 등 custom loader 필요)
  - hard-fail 가드 (--min-pos / --min-neg 미달 시 비-0 exit)
  - raw 소스 캐싱 (pea_eval/data/_dilemma_cache/) — 재학습 시 재다운로드 회피

POS (DILEMMA — narrative scenarios with competing principles):
  - MoralChoice (Scherrer 2023, arXiv:2307.14324)
  - ETHICS *dilemma-shape only*: justice + virtue + deontology
    (commonsense는 단일 명제 도덕 판단이라 NEG로 재분류, 아래)
  - SocialIQA (Sap 2019) — 사회적 추론 시나리오
  - 내부 dilemmas: pea_eval/data/ethics_benchmark/dilemmas.json

NEG (NOT a dilemma — factual / harmful / single-proposition moral):
  - HarmBench val 공격 prompt
  - XSTest safe split (사실 질문)
  - TriviaQA (factual)
  - SQuAD v2 questions (factual, length-overlap)
  - **ETHICS commonsense (single-proposition moral judgments)** — Likert/
    MFQ/WVS shape. 분류기가 "narrative dilemma" ≠ "단일 도덕 명제"
    경계를 학습하도록 강제. 데이터 누수 없음 (MFQ/WVS 실제 항목과 disjoint).

DGX:
  pip install -U datasets
  python scripts/build_dilemma_dataset.py [--min-pos 1500] [--min-neg 1500]
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import random
import sys
import traceback
from pathlib import Path
from typing import Callable, Iterable

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("build_dilemma_dataset")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "pea_eval" / "data"
OUT_PATH = DATA_DIR / "dilemma_train.jsonl"
CACHE_DIR = DATA_DIR / "_dilemma_cache"

RANDOM_SEED = 42
MAX_PER_SOURCE = 4000


def _try_load(paths: list[tuple[str, dict]]) -> "Optional[object]":
    """경로 후보를 차례로 시도. 첫 성공 시 dataset 반환, 전부 실패 시 None.
    성공 시 features 키와 첫 행을 INFO로 출력 → field 추출 디버깅."""
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets 라이브러리 미설치 — pip install -U datasets")
        return None
    for name, kwargs in paths:
        try:
            ds = load_dataset(name, **kwargs)
            logger.info(f"  ✓ load_dataset('{name}', {kwargs}) → {type(ds).__name__}")
            try:
                # features 키 + 첫 행 노출 (field 이름 mismatch 디버깅)
                feat_keys = list(getattr(ds, 'features', {}).keys()) if hasattr(ds, 'features') else []
                logger.info(f"      schema fields: {feat_keys}")
                if len(ds) > 0:
                    first = ds[0]
                    sample = {k: (str(v)[:80] if v is not None else None) for k, v in first.items()}
                    logger.info(f"      sample[0]: {sample}")
            except Exception:
                pass
            return ds
        except Exception as e:
            logger.warning(f"  ✗ load_dataset('{name}', {kwargs}): {type(e).__name__}: {str(e)[:160]}")
    return None


def _cache_jsonl(name: str, items: list[str]) -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    p = CACHE_DIR / f"{name}.jsonl"
    with open(p, "w", encoding="utf-8") as f:
        for t in items:
            f.write(json.dumps({"text": t}, ensure_ascii=False) + "\n")
    logger.info(f"  → 캐시: {p} ({len(items)})")


def _from_cache(name: str) -> list[str]:
    p = CACHE_DIR / f"{name}.jsonl"
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                out.append(json.loads(line)["text"])
            except Exception:
                pass
    if out:
        logger.info(f"  ↻ 캐시 사용: {p} ({len(out)})")
    return out


def src_moralchoice() -> list[str]:
    """MoralChoice 시나리오 CSV 직접 다운로드 (load_dataset은 survey config만
    잡고 실제 시나리오는 data/scenarios/*.csv 별도 파일)."""
    logger.info("[POS] MoralChoice")
    cached = _from_cache("moralchoice")
    if cached:
        return cached[:MAX_PER_SOURCE]
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        logger.error("  ✗ huggingface_hub 미설치")
        return []
    out: list[str] = []
    # 실제 ninoscherrer/moralchoice 저장소의 시나리오 CSV들
    candidates = [
        "data/scenarios/high_ambiguity_scenarios.csv",
        "data/scenarios/low_ambiguity_scenarios.csv",
        "data/scenarios/scenarios_high.csv",
        "data/scenarios/scenarios_low.csv",
        "scenarios.csv",
    ]
    for fname in candidates:
        try:
            fp = hf_hub_download("ninoscherrer/moralchoice", fname, repo_type="dataset")
            with open(fp, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                fields = reader.fieldnames or []
                logger.info(f"  ✓ {fname}  fields={fields}")
                for row in reader:
                    ctx = (row.get("context") or row.get("scenario_description") or "").strip()
                    a1 = (row.get("action1") or row.get("action_1") or "").strip()
                    a2 = (row.get("action2") or row.get("action_2") or "").strip()
                    parts = [ctx] if ctx else []
                    if a1 and a2:
                        parts.append(f"Option A: {a1}\nOption B: {a2}")
                    if parts:
                        out.append("\n\n".join(parts))
        except Exception as e:
            logger.warning(f"  ✗ {fname}: {type(e).__name__}: {str(e)[:120]}")
    logger.info(f"  → MoralChoice: {len(out)}건")
    _cache_jsonl("moralchoice", out)
    return out[:MAX_PER_SOURCE]


def _download_text(url: str, target: Path) -> bool:
    """단순 GET → 파일 저장."""
    import urllib.request
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "PEAOS-dilemma-build/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(target, "wb") as f:
            f.write(resp.read())
        return True
    except Exception as e:
        logger.warning(f"  ✗ download {url}: {type(e).__name__}: {str(e)[:120]}")
        return False


def src_ethics_dilemmas() -> list[str]:
    """Hendrycks ETHICS *dilemma-shape only* (justice/virtue/deontology).

    commonsense는 단일 명제 도덕 판단 (e.g. "I borrowed my friend's car
    without asking") — Likert 문항과 같은 형태이므로 POS에서 제외하고
    src_ethics_commonsense_as_neg에서 NEG로 활용한다.
    Berkeley tarball: https://people.eecs.berkeley.edu/~hendrycks/ethics.tar
    """
    logger.info("[POS] ETHICS dilemma-shape (justice + virtue + deontology)")
    cached = _from_cache("ethics_dilemma")
    if cached:
        return cached[:MAX_PER_SOURCE]
    extract_root = CACHE_DIR / "ethics_extracted"
    tar_path = CACHE_DIR / "ethics.tar"
    if not extract_root.exists() or not list(extract_root.glob("ethics/commonsense/cm_train.csv")):
        url = "https://people.eecs.berkeley.edu/~hendrycks/ethics.tar"
        if not _download_text(url, tar_path):
            return []
        import tarfile
        try:
            extract_root.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tar_path) as t:
                t.extractall(extract_root)
            logger.info(f"  ✓ ETHICS tarball 추출: {extract_root}")
        except Exception as e:
            logger.error(f"  ✗ tar 추출 실패: {e}")
            return []
    out: list[str] = []
    # commonsense 제외 — 다음 함수에서 NEG로 사용
    for cat, fname, fields in [
        ("justice", "justice_train.csv", ("scenario",)),
        ("virtue", "virtue_train.csv", ("scenario",)),
        ("deontology", "deontology_train.csv", ("scenario", "excuse")),
    ]:
        p = extract_root / "ethics" / cat / fname
        if not p.exists():
            logger.warning(f"  ✗ ETHICS {cat}/{fname} 미존재")
            continue
        n0 = len(out)
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                parts = [str(row.get(k, "")).strip() for k in fields]
                txt = " ".join(p for p in parts if p).strip()
                if txt:
                    out.append(txt)
        logger.info(f"  → ETHICS/{cat}: {len(out) - n0}건")
    random.shuffle(out)
    out = out[:MAX_PER_SOURCE]
    logger.info(f"  → ETHICS dilemma-shape total: {len(out)}건")
    _cache_jsonl("ethics_dilemma", out)
    return out


def src_ethics_commonsense_as_neg() -> list[str]:
    """ETHICS commonsense를 NEG로 사용 — 단일 명제 도덕 판단은 dilemma가
    아니라 Likert/MFQ/WVS와 같은 shape. 분류기가 'narrative dilemma' ≠
    'single moral proposition' 경계를 학습하도록 강제.

    데이터 누수 없음: ETHICS commonsense 항목은 MFQ/WVS 실제 evaluation
    항목과 텍스트 중복 없음 (다른 corpus).
    """
    logger.info("[NEG] ETHICS commonsense (single-proposition moral, Likert-shape)")
    cached = _from_cache("ethics_commonsense_neg")
    if cached:
        return cached[:MAX_PER_SOURCE]
    extract_root = CACHE_DIR / "ethics_extracted"
    p = extract_root / "ethics" / "commonsense" / "cm_train.csv"
    if not p.exists():
        # src_ethics_dilemmas가 먼저 호출되어 tarball을 받아두므로 보통 존재.
        # 단독 실행 대비 fallback:
        tar_path = CACHE_DIR / "ethics.tar"
        if not tar_path.exists():
            url = "https://people.eecs.berkeley.edu/~hendrycks/ethics.tar"
            if not _download_text(url, tar_path):
                return []
        import tarfile
        try:
            extract_root.mkdir(parents=True, exist_ok=True)
            with tarfile.open(tar_path) as t:
                t.extractall(extract_root)
        except Exception as e:
            logger.error(f"  ✗ tar 추출 실패: {e}")
            return []
    out: list[str] = []
    if p.exists():
        with open(p, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                txt = str(row.get("input", "")).strip()
                if txt:
                    out.append(txt)
    logger.info(f"  → ETHICS commonsense (as NEG): {len(out)}건")
    random.shuffle(out)
    out = out[:MAX_PER_SOURCE]
    _cache_jsonl("ethics_commonsense_neg", out)
    return out


def src_likert_synthetic_neg() -> list[str]:
    """Likert-shape NEG: ETHICS commonsense 항목을 표준 psychometric Likert
    템플릿으로 감싸 합성. 분류기에게 "Likert moral assessment ≠ narrative
    dilemma" 구조 신호를 강제 주입.

    Probe 결과: ETHICS commonsense를 단독 NEG로 추가했을 때 분류기가
    MFQ/WVS 명제형 Likert 진술을 여전히 DILEMMA로 분류 (prob median 0.996).
    원인: ETHICS commonsense는 1인칭 일상 진술이고 MFQ/WVS는 3인칭 평가형
    Likert prompt라 표면 양식 차이가 큼 → 임베딩 분리 부족.

    템플릿은 표준 psychometric framing 5종을 균등 분배. MFQ/WVS 원문과
    텍스트 중복 없음 (데이터 누수 차단).
    """
    logger.info("[NEG] Likert synthetic (ETHICS commonsense × 표준 Likert 템플릿)")
    cached = _from_cache("likert_synthetic_neg")
    if cached:
        return cached[:MAX_PER_SOURCE]

    extract_root = CACHE_DIR / "ethics_extracted"
    p = extract_root / "ethics" / "commonsense" / "cm_train.csv"
    if not p.exists():
        logger.warning("  ✗ ETHICS commonsense 미존재 — src_ethics_dilemmas 먼저 호출 필요")
        return []
    statements: list[str] = []
    with open(p, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            txt = str(row.get("input", "")).strip()
            if txt and 20 <= len(txt) <= 280:  # Likert에 자연스럽게 들어갈 길이
                statements.append(txt)

    # 표준 psychometric Likert 템플릿 5종. MFQ/WVS 원본 문구와 의도적으로 다르게
    # 작성 (어휘/스케일 라벨/scale range 등 다양화).
    templates = [
        "On a scale of 1 (strongly disagree) to 5 (strongly agree), rate this statement: '{}'\nOutput your numeric rating first, then a brief justification.",
        "How strongly do you agree with the following on a 1-7 scale? '{}'\nGive a single number, then one sentence of reasoning.",
        "Please evaluate this consideration (0=not at all important, 4=extremely important): '{}'\nFormat: Score: N then explanation.",
        "Indicate your level of agreement from 1 to 5 with this proposition: '{}'\nRespond with the integer score followed by your reasoning.",
        "Rate the moral relevance of this statement on a scale where 1 means 'not relevant' and 5 means 'highly relevant': '{}'\nState the number first.",
    ]
    out: list[str] = []
    for i, stmt in enumerate(statements):
        tmpl = templates[i % len(templates)]
        out.append(tmpl.format(stmt))
    logger.info(f"  → Likert synthetic NEG: {len(out)}건 (commonsense {len(statements)} × 템플릿 {len(templates)} 균등)")
    random.shuffle(out)
    out = out[:MAX_PER_SOURCE]
    _cache_jsonl("likert_synthetic_neg", out)
    return out


# 호환성: 옛 이름은 새 함수로 alias
src_ethics = src_ethics_dilemmas


def src_social_iqa() -> list[str]:
    """SocialIQA: HF script-loader 폐기 → parquet auto-convert branch에서 직접."""
    logger.info("[POS] SocialIQA")
    cached = _from_cache("social_iqa")
    if cached:
        return cached[:MAX_PER_SOURCE]
    try:
        from huggingface_hub import hf_hub_download
    except ImportError:
        return []
    out: list[str] = []
    candidates = [
        ("allenai/social_i_qa", "default/train/0000.parquet", "refs/convert/parquet"),
        ("social_i_qa", "default/train/0000.parquet", "refs/convert/parquet"),
    ]
    for repo, fname, rev in candidates:
        try:
            fp = hf_hub_download(repo, fname, repo_type="dataset", revision=rev)
            try:
                import pandas as pd  # noqa
                df = pd.read_parquet(fp)
                for _, row in df.iterrows():
                    ctx = str(row.get("context", "")).strip()
                    q = str(row.get("question", "")).strip()
                    if ctx and q:
                        out.append(f"{ctx}\n\nQuestion: {q}")
            except ImportError:
                import pyarrow.parquet as pq
                tbl = pq.read_table(fp).to_pylist()
                for r in tbl:
                    ctx = str(r.get("context", "")).strip()
                    q = str(r.get("question", "")).strip()
                    if ctx and q:
                        out.append(f"{ctx}\n\nQuestion: {q}")
            logger.info(f"  ✓ {repo}:{fname} → {len(out)}")
            break
        except Exception as e:
            logger.warning(f"  ✗ {repo}:{fname} ({rev}): {type(e).__name__}: {str(e)[:120]}")
    random.shuffle(out)
    out = out[:MAX_PER_SOURCE]
    logger.info(f"  → SocialIQA: {len(out)}건")
    _cache_jsonl("social_iqa", out)
    return out


def src_internal_dilemmas() -> list[str]:
    logger.info("[POS] internal dilemmas.json")
    path = DATA_DIR / "ethics_benchmark" / "dilemmas.json"
    if not path.exists():
        logger.warning(f"  ✗ 미존재: {path}")
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for d in data.get("dilemmas", []):
        ctx = (d.get("description") or "").strip()
        for q in d.get("questions", []):
            qt = (q.get("text") or "").strip()
            if ctx or qt:
                out.append(f"Context: {ctx}\n\nQuestion: {qt}".strip())
    logger.info(f"  → internal: {len(out)}건")
    return out


def src_harmbench() -> list[str]:
    logger.info("[NEG] HarmBench val")
    path = DATA_DIR / "harmbench_behaviors_text_val.csv"
    if not path.exists():
        logger.warning(f"  ✗ 미존재: {path}")
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            b = (row.get("Behavior") or row.get("behavior") or "").strip()
            if b:
                out.append(b)
    logger.info(f"  → HarmBench: {len(out)}건")
    return out


def src_xstest_safe() -> list[str]:
    logger.info("[NEG] XSTest safe split")
    cached = _from_cache("xstest_safe")
    if cached:
        return cached
    ds = _try_load([
        ("natolambert/xstest-v2-copy", {"split": "prompts"}),
        ("walledai/XSTest", {"split": "test"}),
        ("Paul/XSTest", {"split": "train"}),
    ])
    if ds is None:
        return []
    out = []
    for row in ds:
        label = (row.get("type") or row.get("label") or "").lower()
        prompt = (row.get("prompt") or row.get("text") or "").strip()
        if prompt and "safe" in label:
            out.append(prompt)
    logger.info(f"  → XSTest safe: {len(out)}건")
    _cache_jsonl("xstest_safe", out)
    return out


def src_trivia() -> list[str]:
    logger.info("[NEG] TriviaQA")
    cached = _from_cache("trivia")
    if cached:
        return cached[:MAX_PER_SOURCE]
    ds = _try_load([
        ("trivia_qa", {"name": "rc.nocontext", "split": "train[:5000]", "trust_remote_code": True}),
        ("mandarjoshi/trivia_qa", {"name": "rc.nocontext", "split": "train[:5000]", "trust_remote_code": True}),
    ])
    if ds is None:
        return []
    out = [(row.get("question") or "").strip() for row in ds]
    out = [q for q in out if q]
    logger.info(f"  → TriviaQA: {len(out)}건")
    out = out[:MAX_PER_SOURCE]
    _cache_jsonl("trivia", out)
    return out


def src_squad() -> list[str]:
    logger.info("[NEG] SQuAD v2 questions (shortcut 방지)")
    cached = _from_cache("squad")
    if cached:
        return cached[:MAX_PER_SOURCE]
    ds = _try_load([
        ("rajpurkar/squad_v2", {"split": "train[:5000]"}),
        ("squad_v2", {"split": "train[:5000]"}),
    ])
    if ds is None:
        return []
    out = [(row.get("question") or "").strip() for row in ds]
    out = [q for q in out if q]
    logger.info(f"  → SQuAD v2: {len(out)}건")
    out = out[:MAX_PER_SOURCE]
    _cache_jsonl("squad", out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-pos", type=int, default=1500, help="최소 양성 샘플 수")
    ap.add_argument("--min-neg", type=int, default=1500, help="최소 음성 샘플 수")
    ap.add_argument("--no-balance", action="store_true", help="클래스 균형 다운샘플 비활성")
    args = ap.parse_args()

    random.seed(RANDOM_SEED)
    logger.info("═══════════════ POS sources ═══════════════")
    pos_sources: list[tuple[str, Callable[[], list[str]]]] = [
        ("moralchoice", src_moralchoice),
        ("ethics_dilemma", src_ethics_dilemmas),
        ("social_iqa", src_social_iqa),
        ("internal", src_internal_dilemmas),
    ]
    pos_counts: dict[str, int] = {}
    pos: list[str] = []
    for name, fn in pos_sources:
        try:
            items = fn()
        except Exception as e:
            logger.error(f"[POS] {name} 예외: {e}\n{traceback.format_exc()}")
            items = []
        pos_counts[name] = len(items)
        pos.extend(items)

    logger.info("═══════════════ NEG sources ═══════════════")
    neg_sources: list[tuple[str, Callable[[], list[str]]]] = [
        ("harmbench", src_harmbench),
        ("xstest_safe", src_xstest_safe),
        ("trivia", src_trivia),
        ("squad", src_squad),
        # 단일 명제 도덕 판단 (Likert-shape) — 'dilemma 아님' 경계 강제 학습
        ("ethics_commonsense_neg", src_ethics_commonsense_as_neg),
        # 합성 Likert 진술 — 분류기가 "Likert 평가 prompt = 단일 진술 ≠ dilemma"
        # 구조를 학습하도록 강제 (probe에서 WVS 96% 오분류 발견 후 추가).
        ("likert_synthetic_neg", src_likert_synthetic_neg),
    ]
    neg_counts: dict[str, int] = {}
    neg: list[str] = []
    for name, fn in neg_sources:
        try:
            items = fn()
        except Exception as e:
            logger.error(f"[NEG] {name} 예외: {e}\n{traceback.format_exc()}")
            items = []
        neg_counts[name] = len(items)
        neg.extend(items)

    # 유니코드 line separator (U+2028/U+2029) 제거 — splitlines() 함정 방지.
    def _sanitize(t: str) -> str:
        return t.replace(" ", " ").replace(" ", " ").replace("\x85", " ")
    pos = [_sanitize(p) for p in pos if 20 <= len(p) <= 3000]
    neg = [_sanitize(n) for n in neg if 20 <= len(n) <= 3000]

    logger.info("═══════════════ Summary ═══════════════")
    logger.info(f"POS per source: {pos_counts}  → filtered total {len(pos)}")
    logger.info(f"NEG per source: {neg_counts}  → filtered total {len(neg)}")

    if len(pos) < args.min_pos:
        logger.error(
            f"FAIL: POS {len(pos)} < min {args.min_pos}. "
            f"HF download 실패 가능성 — 위 로그에서 'load_dataset' 실패 사유 확인."
        )
        return 1
    if len(neg) < args.min_neg:
        logger.error(f"FAIL: NEG {len(neg)} < min {args.min_neg}.")
        return 1

    if not args.no_balance:
        n = min(len(pos), len(neg))
        pos = random.sample(pos, n)
        neg = random.sample(neg, n)
        logger.info(f"균형 다운샘플: pos={len(pos)}, neg={len(neg)}, total={2*n}")

    rows = [{"text": t, "label": 1, "source": "pos"} for t in pos] + \
           [{"text": t, "label": 0, "source": "neg"} for t in neg]
    random.shuffle(rows)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    # 학습 캐시 무효화 (텍스트 데이터가 바뀌었으므로)
    emb_cache = DATA_DIR / "dilemma_train_emb.npz"
    if emb_cache.exists():
        emb_cache.unlink()
        logger.info(f"학습 임베딩 캐시 삭제: {emb_cache} (재학습 시 새로 생성)")

    logger.info(f"저장: {OUT_PATH} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
