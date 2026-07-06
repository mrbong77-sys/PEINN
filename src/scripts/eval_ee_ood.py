"""
Emotion Engine — Out-of-Distribution (OOD) generalization eval.

PEINN은 이제 "EE 기반 유해성/딜레마 판별 → 2-pass(refusal/reasoning) 강제"의
ad-hoc Artificial Moral Agent로 간소화되었다. 따라서 가장 큰 비판 지점은
"EE 판별기가 벤치(harmbench/xstest/ethics) 데이터에 과적합된 것 아니냐"이다.

이 스크립트는 **벤치 및 EE 캘리브레이션에 쓰이지 않은** 외부 safe/harm 대화
데이터셋에서 EE의 순수 이진 판별 성능(SAFE vs HARMFUL)을 측정하고 F1 등
지표를 영구 기록한다. production과 동일하게
  energy = EvalEERunner.analyze_emotion(text)[1]   # HybridCalibrator 적용
  pred   = EvalEERunner.classify_intent(energy)     # threshold = settings.ee.fast_pass_threshold
경로를 그대로 사용한다.

EE 캘리브레이션/임계값 튜닝에 쓰인 소스(harmbench, xstest, ethics, taxonomy,
unesco, toxic-chat, truthfulqa)는 의도적으로 **제외**한다 — 순수 일반화 측정이
목적이기 때문이다.

DGX Spark에서 실행 (이 컨테이너는 torch 미설치 + HF 차단이라 구동 불가):
    pip install datasets scikit-learn
    # 1) 데이터셋만 먼저 빌드/검수 (EE 미구동)
    python scripts/eval_ee_ood.py --no-ee --max-per-source 500
    # 2) EE 판별 + 지표 산출 + 기록
    python scripts/eval_ee_ood.py --max-per-source 500

출력:
    results/ee_ood/ood_eval_set_<ts>.csv     # text,label,source (재현용)
    results/ee_ood/ee_ood_items_<ts>.csv      # + energy,pred
    results/ee_ood/ee_ood_metrics_<ts>.json   # 전체/소스별 지표
    docs/ee_ood_generalization.md             # 실행마다 결과 1행 append
"""
from __future__ import annotations

import argparse
import json
import logging
import random
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("peaos.eval_ee_ood")

RESULTS_DIR = PROJECT_ROOT / "results" / "ee_ood"
RECORD_MD = PROJECT_ROOT / "docs" / "ee_ood_generalization.md"

# 옵션3: 캘리브레이터 재학습용 train/held-out 분리 산출물.
#   extra_train.csv   → ee_threshold_finder.gather_datasets가 학습에 합류
#   extra_heldout.csv → 본 하니스 --heldout 모드가 재측정(학습 미사용 = 정직한 OOD)
SPLIT_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_calib_splits"
TRAIN_CSV = SPLIT_DIR / "extra_train.csv"
HELDOUT_CSV = SPLIT_DIR / "extra_heldout.csv"

# label 규약: HARMFUL = positive = 1, SAFE = negative = 0
HARM, SAFE = 1, 0

MIN_LEN, MAX_LEN = 8, 1200  # 단일 프롬프트 길이 필터 (잡음/초장문 제외)
HH_MAX_LEN = 2000           # hh-rlhf 멀티턴 누적 입력 상한 (뒷부분 보존 truncate)


# ───────────────────────────────────────────────────────────────────────
# OOD dataset loaders  (벤치/캘리브레이션 미사용 소스만)
#   - datasets(HF) 라이브러리 사용. 실패 시 해당 소스만 skip.
#   - 반환: list[(text, label, source)]
# ───────────────────────────────────────────────────────────────────────

def _clean(t: str) -> str:
    return re.sub(r"\s+", " ", (t or "").strip())


def _ok(t: str) -> bool:
    return MIN_LEN <= len(t) <= MAX_LEN


def _all_human_turns(transcript: str) -> str:
    """hh-rlhf/red-team transcript에서 모든 Human 발화를 순서대로 연결.

    red-team 공격은 첫 턴이 양성으로 시작해 뒤에서 escalate하므로 첫 턴만
    쓰면 유해 의도가 가려져 harm-FNR이 부풀려진다(2026-05-22 OOD 측정에서 확인).
    attacker(Human) 측 전 발화를 합쳐 전체 의도를 입력으로 삼고, assistant
    응답은 노이즈라 제외한다. SAFE(harmless/helpful base)도 동일 추출을 써서
    harm/safe 입력의 구조적 confound를 없앤다.
    """
    parts = re.split(r"\n\n(Human|Assistant):", transcript or "")
    turns = [parts[i + 1].strip() for i in range(1, len(parts) - 1, 2) if parts[i] == "Human"]
    joined = " ".join(t for t in turns if t)
    if not joined:
        joined = (transcript or "").strip()
    if len(joined) > HH_MAX_LEN:  # 멀티턴 누적이 길면 escalation 있는 뒷부분 보존
        joined = joined[-HH_MAX_LEN:]
    return joined


def _hf(*args, **kwargs):
    from datasets import load_dataset
    return load_dataset(*args, **kwargs)


def load_hh_rlhf(cap: int) -> list[tuple[str, int, str]]:
    """Anthropic/hh-rlhf: red-team-attempts=HARM, harmless+helpful base=SAFE.
    멀티턴 대화의 **모든 Human 발화 연결**을 입력으로 사용 (escalation 포착)."""
    out: list[tuple[str, int, str]] = []
    # HARM — red team attempts (전체 attacker 의도)
    try:
        ds = _hf("Anthropic/hh-rlhf", data_dir="red-team-attempts", split="train")
        col = "transcript" if "transcript" in ds.column_names else ds.column_names[0]
        for ex in ds:
            txt = _clean(_all_human_turns(ex[col]))
            if len(txt) >= MIN_LEN:
                out.append((txt, HARM, "hh_rlhf_redteam"))
    except Exception as e:
        logger.warning(f"  ✗ hh-rlhf red-team: {type(e).__name__}: {str(e)[:120]}")
    # SAFE — harmless-base + helpful-base (chosen transcript의 모든 Human 발화)
    for sub, tag in [("harmless-base", "hh_rlhf_harmless"), ("helpful-base", "hh_rlhf_helpful")]:
        try:
            ds = _hf("Anthropic/hh-rlhf", data_dir=sub, split="train")
            for ex in ds:
                txt = _clean(_all_human_turns(ex.get("chosen", "")))
                if len(txt) >= MIN_LEN:
                    out.append((txt, SAFE, tag))
        except Exception as e:
            logger.warning(f"  ✗ hh-rlhf {sub}: {type(e).__name__}: {str(e)[:120]}")
    return out


def load_do_not_answer(cap: int) -> list[tuple[str, int, str]]:
    """LibrAI/do-not-answer: 응답해서는 안 되는 질문 (HARM)."""
    out = []
    try:
        ds = _hf("LibrAI/do-not-answer", split="train")
        col = "question" if "question" in ds.column_names else ds.column_names[0]
        for ex in ds:
            txt = _clean(ex[col])
            if _ok(txt):
                out.append((txt, HARM, "do_not_answer"))
    except Exception as e:
        logger.warning(f"  ✗ do-not-answer: {type(e).__name__}: {str(e)[:120]}")
    return out


def load_beavertails(cap: int) -> list[tuple[str, int, str]]:
    """PKU-Alignment/BeaverTails: prompt + is_safe → HARM/SAFE 양쪽."""
    out = []
    try:
        ds = _hf("PKU-Alignment/BeaverTails", split="30k_train")
        for ex in ds:
            txt = _clean(ex.get("prompt", ""))
            if not _ok(txt):
                continue
            out.append((txt, SAFE if ex.get("is_safe") else HARM, "beavertails"))
    except Exception as e:
        logger.warning(f"  ✗ beavertails: {type(e).__name__}: {str(e)[:120]}")
    return out


def load_alpaca(cap: int) -> list[tuple[str, int, str]]:
    """tatsu-lab/alpaca: 일반 지시문 (SAFE/benign)."""
    out = []
    try:
        ds = _hf("tatsu-lab/alpaca", split="train")
        for ex in ds:
            inp = _clean(ex.get("input", ""))
            txt = _clean(ex.get("instruction", ""))
            if inp:
                txt = f"{txt} {inp}"
            if _ok(txt):
                out.append((txt, SAFE, "alpaca"))
    except Exception as e:
        logger.warning(f"  ✗ alpaca: {type(e).__name__}: {str(e)[:120]}")
    return out


def load_dolly(cap: int) -> list[tuple[str, int, str]]:
    """databricks/databricks-dolly-15k: 일반 지시문 (SAFE/benign)."""
    out = []
    try:
        ds = _hf("databricks/databricks-dolly-15k", split="train")
        for ex in ds:
            txt = _clean(ex.get("instruction", ""))
            if _ok(txt):
                out.append((txt, SAFE, "dolly"))
    except Exception as e:
        logger.warning(f"  ✗ dolly: {type(e).__name__}: {str(e)[:120]}")
    return out


LOADERS = {
    "hh_rlhf": load_hh_rlhf,
    "do_not_answer": load_do_not_answer,
    "beavertails": load_beavertails,
    "alpaca": load_alpaca,
    "dolly": load_dolly,
}


# ───────────────────────────────────────────────────────────────────────
# Dataset build (balanced sampling)
# ───────────────────────────────────────────────────────────────────────

def build_dataset(sources: list[str], cap: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    pool: list[tuple[str, int, str]] = []
    for name in sources:
        loader = LOADERS[name]
        rows = loader(cap)
        # source 내부에서 cap을 라벨별로 적용 (한 소스가 한 라벨로 편중되지 않게)
        by_label: dict[int, list] = {HARM: [], SAFE: []}
        for r in rows:
            by_label[r[1]].append(r)
        for lab, items in by_label.items():
            rng.shuffle(items)
            kept = items[:cap]
            pool.extend(kept)
            if kept:
                logger.info(f"  ✓ {name} [{'HARM' if lab else 'SAFE'}]: {len(kept)} (of {len(items)})")
    # 중복 텍스트 제거
    seen, dedup = set(), []
    for txt, lab, src in pool:
        key = txt.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append({"text": txt, "label": lab, "source": src})
    rng.shuffle(dedup)
    n_harm = sum(1 for d in dedup if d["label"] == HARM)
    logger.info(f"Built OOD set: {len(dedup)} items  (HARM={n_harm}, SAFE={len(dedup)-n_harm})")
    return dedup


def build_indist_dataset(cap: int, seed: int) -> list[dict]:
    """In-distribution 대조군: EE 캘리브레이션/임계값 튜닝에 쓰인 그 소스/라벨을
    그대로 사용 (ee_threshold_finder.gather_datasets). OOD(AUC≈0.70)와 직접
    비교해 '과적합 갭'을 수치화하기 위함.

    라벨(=캘리브레이션과 동일): HarmBench/Taxonomy/XSTest-Unsafe=HARM,
    XSTest-Safe/UNESCO/Ethics/MoralScenarios-Safe/ToxicChat-Safe/TruthfulQA=SAFE.
    """
    from pea_eval.optimizer import ee_threshold_finder as F  # torch/pandas 지연 import
    rng = random.Random(seed)
    bundle = F.gather_datasets()
    pool: list[tuple[str, int, str]] = []
    for name, d in bundle.items():
        lab = HARM if d["label"] == 1 else SAFE
        texts = [t2 for t2 in (_clean(t) for t in d["texts"]) if _ok(t2)]
        rng.shuffle(texts)
        for t in texts[:cap]:
            pool.append((t, lab, name))
        if texts:
            logger.info(f"  ✓ {name} [{'HARM' if lab else 'SAFE'}]: {min(len(texts), cap)} (of {len(texts)})")
    seen, dedup = set(), []
    for txt, lab, src in pool:
        key = txt.lower()
        if key in seen:
            continue
        seen.add(key)
        dedup.append({"text": txt, "label": lab, "source": src})
    rng.shuffle(dedup)
    n_harm = sum(1 for d in dedup if d["label"] == HARM)
    logger.info(f"Built in-dist set: {len(dedup)} items  (HARM={n_harm}, SAFE={len(dedup)-n_harm})")
    return dedup


# ───────────────────────────────────────────────────────────────────────
# 옵션3: train / held-out 분리  (캘리브레이터 재학습용)
# ───────────────────────────────────────────────────────────────────────
# 분할-소스(학습+held-out 양쪽 기여): hh_rlhf_redteam, beavertails(H+S), alpaca, dolly
# held-out 전용(학습 0% — 완전 미지의 일반화 probe): do_not_answer, hh_rlhf_helpful
# 제외: hh_rlhf_harmless (human 발화가 도발적 유해 요청 多 → SAFE 라벨 신뢰도 낮음)
_SPLIT_SOURCES = {"hh_rlhf_redteam", "beavertails", "alpaca", "dolly"}
_HELDOUT_ONLY = {"do_not_answer", "hh_rlhf_helpful"}
_EXCLUDE = {"hh_rlhf_harmless"}


def prepare_splits(cap: int, seed: int, train_frac: float = 0.7) -> None:
    """다양 OOD 소스를 train/held-out으로 결정적 분할해 CSV로 저장.

    이렇게 분리해야 재학습 후에도 held-out(학습 미사용)으로 일반화 갭을 정직히
    재측정할 수 있다. do_not_answer는 전량 held-out(학습에 절대 미포함)으로 두어
    '완전히 새로운 유해 분류체계'에 대한 일반화 probe로 쓴다.
    """
    rng = random.Random(seed)
    rows: list[tuple[str, int, str]] = []
    for loader in (load_hh_rlhf, load_beavertails, load_alpaca, load_dolly, load_do_not_answer):
        rows.extend(loader(cap))
    # 전역 dedup
    seen, uniq = set(), []
    for txt, lab, src in rows:
        if src in _EXCLUDE:
            continue
        k = txt.lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append((txt, lab, src))

    train, heldout = [], []
    # (source,label)별 그룹 분할
    groups: dict[tuple[str, int], list] = {}
    for r in uniq:
        groups.setdefault((r[2], r[1]), []).append(r)
    for (src, lab), items in groups.items():
        rng.shuffle(items)
        items = items[:cap]
        if src in _HELDOUT_ONLY:
            heldout.extend(items)
            continue
        n_tr = int(len(items) * train_frac)
        train.extend(items[:n_tr])
        heldout.extend(items[n_tr:])

    SPLIT_DIR.mkdir(parents=True, exist_ok=True)
    import csv
    for path, data in [(TRAIN_CSV, train), (HELDOUT_CSV, heldout)]:
        rng.shuffle(data)
        with path.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=["text", "label", "source"])
            w.writeheader()
            for txt, lab, src in data:
                w.writerow({"text": txt, "label": lab, "source": src})
    th = sum(1 for r in train if r[1] == HARM)
    hh = sum(1 for r in heldout if r[1] == HARM)
    logger.info(f"train  → {TRAIN_CSV}  ({len(train)} rows, HARM={th}, SAFE={len(train)-th})")
    logger.info(f"heldout→ {HELDOUT_CSV}  ({len(heldout)} rows, HARM={hh}, SAFE={len(heldout)-hh})")
    logger.info("다음: ee_threshold_finder.py로 재학습(train 자동 합류) → eval_ee_ood.py --heldout 으로 갭 재측정")


def load_heldout_items() -> list[dict]:
    import csv
    if not HELDOUT_CSV.exists():
        logger.error(f"{HELDOUT_CSV} 없음. 먼저 `--prepare-splits`를 실행하세요.")
        return []
    out = []
    with HELDOUT_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append({"text": r["text"], "label": int(r["label"]), "source": r["source"]})
    n_harm = sum(1 for d in out if d["label"] == HARM)
    logger.info(f"Loaded held-out set: {len(out)} items (HARM={n_harm}, SAFE={len(out)-n_harm})")
    return out


# ───────────────────────────────────────────────────────────────────────
# EE scoring  (production 경로 그대로)
# ───────────────────────────────────────────────────────────────────────

def score_with_ee(items: list[dict]) -> tuple[list[float], float]:
    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.ee_runner import EvalEERunner

    settings = load_settings()
    threshold = float(settings.ee.fast_pass_threshold)
    runner = EvalEERunner.get_instance(ee_config=settings.ee)
    runner.initialize()
    logger.info(f"EE initialized. fast_pass_threshold = {threshold}")

    energies: list[float] = []
    n = len(items)
    for i, d in enumerate(items):
        try:
            _, energy, _ = runner.analyze_emotion(d["text"])
        except Exception as e:
            logger.warning(f"  analyze_emotion failed @ {i}: {str(e)[:100]}")
            energy = float("nan")
        energies.append(float(energy))
        if (i + 1) % 100 == 0 or (i + 1) == n:
            logger.info(f"  scored {i+1}/{n}")
    return energies, threshold


# ───────────────────────────────────────────────────────────────────────
# Metrics
# ───────────────────────────────────────────────────────────────────────

def compute_metrics(items: list[dict], energies: list[float], threshold: float) -> dict:
    import numpy as np
    from sklearn.metrics import (
        precision_recall_fscore_support, confusion_matrix,
        roc_auc_score, average_precision_score, accuracy_score, f1_score,
    )

    y = np.array([d["label"] for d in items])
    e = np.array(energies, dtype=float)
    mask = ~np.isnan(e)
    y, e = y[mask], e[mask]
    kept = [d for d, m in zip(items, mask) if m]
    pred = (e >= threshold).astype(int)

    def block(yt, yp, sc):
        p, r, f, _ = precision_recall_fscore_support(yt, yp, average="binary", pos_label=HARM, zero_division=0)
        tn, fp, fn, tp = confusion_matrix(yt, yp, labels=[SAFE, HARM]).ravel()
        out = {
            "n": int(len(yt)), "n_harm": int((yt == HARM).sum()), "n_safe": int((yt == SAFE).sum()),
            "precision": round(float(p), 4), "recall": round(float(r), 4), "f1": round(float(f), 4),
            "accuracy": round(float(accuracy_score(yt, yp)), 4),
            "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
            "fpr_safe_overtrigger": round(float(fp / (fp + tn)) if (fp + tn) else 0.0, 4),
            "fnr_harm_missed": round(float(fn / (fn + tp)) if (fn + tp) else 0.0, 4),
        }
        # threshold-free (양 클래스 존재 시)
        if len(set(yt.tolist())) == 2:
            out["roc_auc"] = round(float(roc_auc_score(yt, sc)), 4)
            out["pr_auc"] = round(float(average_precision_score(yt, sc)), 4)
        return out

    overall = block(y, pred, e)

    # 과적합 지표: OOD에서의 best-F1 임계값과 production 임계값의 격차
    best = {"f1": -1.0, "threshold": None}
    for t in np.unique(np.round(np.linspace(e.min(), e.max(), 200), 4)):
        f = f1_score(y, (e >= t).astype(int), pos_label=HARM, zero_division=0)
        if f > best["f1"]:
            best = {"f1": round(float(f), 4), "threshold": round(float(t), 4)}

    # 소스별
    per_source = {}
    srcs = sorted(set(d["source"] for d in kept))
    for s in srcs:
        idx = [i for i, d in enumerate(kept) if d["source"] == s]
        ys, es = y[idx], e[idx]
        ps = (es >= threshold).astype(int)
        per_source[s] = block(ys, ps, es)

    return {
        "production_threshold": threshold,
        "overall": overall,
        "best_f1_on_ood": best,
        "threshold_gap": round(abs(best["threshold"] - threshold), 4) if best["threshold"] is not None else None,
        "per_source": per_source,
    }


# ───────────────────────────────────────────────────────────────────────
# Output
# ───────────────────────────────────────────────────────────────────────

def write_record(metrics: dict, sources: list[str], ts: str, n_items: int, mode: str) -> None:
    RECORD_MD.parent.mkdir(parents=True, exist_ok=True)
    if not RECORD_MD.exists():
        RECORD_MD.write_text(
            "# Emotion Engine — OOD Generalization Record\n\n"
            "EE 판별기(SAFE vs HARMFUL)의 **벤치 외부** 일반화 성능 기록. 측정은\n"
            "`scripts/eval_ee_ood.py`로 production 경로(`analyze_emotion`→`classify_intent`,\n"
            "임계값=`settings.ee.fast_pass_threshold`)를 그대로 사용한다.\n\n"
            "**OOD 소스(벤치/캘리브레이션 미사용):** Anthropic/hh-rlhf(red-team=HARM,\n"
            "harmless+helpful=SAFE), LibrAI/do-not-answer(HARM), PKU-Alignment/BeaverTails\n"
            "(is_safe), tatsu-lab/alpaca(SAFE), databricks-dolly-15k(SAFE).\n"
            "캘리브레이션에 쓰인 harmbench/xstest/ethics/taxonomy/unesco/toxic-chat/\n"
            "truthfulqa는 **제외**.\n\n"
            "`threshold_gap`(production 임계값 vs OOD best-F1 임계값)이 작을수록 과적합이\n"
            "적다고 해석한다.\n\n"
            "| date | thr | F1 | precision | recall | ROC-AUC | PR-AUC | acc | safe-FPR | best-F1@thr | gap | n | sources |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"
        )
    o = metrics["overall"]
    b = metrics["best_f1_on_ood"]
    row = (
        f"| {ts} | {metrics['production_threshold']} | {o['f1']} | {o['precision']} | "
        f"{o['recall']} | {o.get('roc_auc','-')} | {o.get('pr_auc','-')} | {o['accuracy']} | "
        f"{o['fpr_safe_overtrigger']} | {b['f1']}@{b['threshold']} | {metrics['threshold_gap']} | "
        f"{n_items} | [{mode}] {','.join(sources)} |\n"
    )
    with RECORD_MD.open("a", encoding="utf-8") as f:
        f.write(row)
    logger.info(f"Record appended → {RECORD_MD}")


def main():
    ap = argparse.ArgumentParser(description="EE OOD generalization eval")
    ap.add_argument("--sources", default="all",
                    help=f"comma list of {list(LOADERS)} or 'all'")
    ap.add_argument("--max-per-source", type=int, default=500,
                    help="라벨별 소스당 최대 샘플 수 (balanced)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--no-ee", action="store_true",
                    help="데이터셋만 빌드하고 EE 구동/지표 산출은 생략 (검수용)")
    ap.add_argument("--in-dist", action="store_true",
                    help="OOD 대신 in-distribution(벤치/캘리브레이션 소스)으로 측정 — 과적합 갭 대조군")
    ap.add_argument("--prepare-splits", action="store_true",
                    help="옵션3: 다양 소스를 train/held-out으로 분할 저장(재학습 준비). EE 미구동.")
    ap.add_argument("--heldout", action="store_true",
                    help="옵션3: held-out 셋(재학습 미사용)으로 갭 재측정")
    ap.add_argument("--train-frac", type=float, default=0.7, help="--prepare-splits 학습 비율")
    args = ap.parse_args()

    # 옵션3 준비: 분할만 만들고 종료
    if args.prepare_splits:
        prepare_splits(args.max_per_source, args.seed, args.train_frac)
        return

    mode = "heldout" if args.heldout else ("in-dist" if args.in_dist else "ood")
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.heldout:
        sources = ["extra_heldout"]
        logger.info("Loading HELD-OUT dataset (재학습 미사용 — 정직한 OOD 재측정)")
        items = load_heldout_items()
        empty_hint = "먼저 `--prepare-splits`를 실행해 held-out 셋을 만드세요."
    elif args.in_dist:
        sources = ["gather_datasets"]
        logger.info("Building IN-DISTRIBUTION dataset (calibration sources)")
        items = build_indist_dataset(args.max_per_source, args.seed)
        empty_hint = "벤치 데이터(pea_eval/data/*) 및 HF 접근을 확인하세요."
    else:
        sources = list(LOADERS) if args.sources == "all" else [s.strip() for s in args.sources.split(",")]
        bad = [s for s in sources if s not in LOADERS]
        if bad:
            ap.error(f"unknown sources: {bad}")
        logger.info(f"Building OOD dataset from: {sources}")
        items = build_dataset(sources, args.max_per_source, args.seed)
        empty_hint = "`pip install datasets` 및 네트워크(HF) 접근을 확인하세요."
    if not items:
        logger.error(f"데이터셋이 비었습니다. {empty_hint}")
        sys.exit(1)

    # 재현용 셋 저장
    import csv
    set_path = RESULTS_DIR / f"{mode}_eval_set_{ts}.csv"
    with set_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label", "source"])
        w.writeheader()
        w.writerows(items)
    logger.info(f"OOD set saved → {set_path}")

    if args.no_ee:
        logger.info("--no-ee: EE 구동 생략. 데이터셋 검수 후 --no-ee 없이 재실행하세요.")
        return

    energies, threshold = score_with_ee(items)

    # per-item 저장
    items_path = RESULTS_DIR / f"ee_{mode}_items_{ts}.csv"
    with items_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "label", "source", "energy", "pred"])
        w.writeheader()
        for d, e in zip(items, energies):
            pred = "" if e != e else ("HARMFUL" if e >= threshold else "SAFE")  # nan-safe
            w.writerow({**d, "energy": round(e, 4) if e == e else "", "pred": pred})
    logger.info(f"Per-item results → {items_path}")

    metrics = compute_metrics(items, energies, threshold)
    metrics_path = RESULTS_DIR / f"ee_{mode}_metrics_{ts}.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info(f"Metrics → {metrics_path}")

    o = metrics["overall"]
    logger.info(
        f"\n========== EE {mode.upper()} RESULT ==========\n"
        f"  n={o['n']} (HARM={o['n_harm']}, SAFE={o['n_safe']})  thr={threshold}\n"
        f"  F1={o['f1']}  P={o['precision']}  R={o['recall']}  acc={o['accuracy']}\n"
        f"  ROC-AUC={o.get('roc_auc','-')}  PR-AUC={o.get('pr_auc','-')}\n"
        f"  safe-FPR(과트리거)={o['fpr_safe_overtrigger']}  harm-FNR(놓침)={o['fnr_harm_missed']}\n"
        f"  best-F1 on OOD={metrics['best_f1_on_ood']['f1']} @ thr={metrics['best_f1_on_ood']['threshold']} "
        f"(gap={metrics['threshold_gap']})\n"
        f"==================================="
    )
    write_record(metrics, sources, ts, o["n"], mode)


if __name__ == "__main__":
    main()
