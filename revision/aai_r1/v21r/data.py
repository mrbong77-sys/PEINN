"""DESIGN.md 3 and 8 (R, C, F): routing texts, the isolated corpus and the frozen features.

Texts never leave .cache/v21r; results/v21r holds counts, ids (sha1) and reasons only.
"""
from __future__ import annotations

import json
import random
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

from . import common as C

DRIVER = Path(__file__).with_name("peaos_driver.py")
SIDE = Path(__file__).with_name("peinn_side.py")
NEAR_COS = 0.92                    # DESIGN.md 3: MiniLM cosine to any routing text at or above this -> excluded
SPLIT_SEED = 42
# DESIGN.md 11: synthetic sources written to the categories of XSTest's safe prompts (no item copied) to lower XSTest
# over-refusal (src/scripts/gen_trick_safe_corpus.py, label_ee_3class.py 100-146). Dropped from the corpus when
# EXCLUDE_SOURCES names them; dropped after the split so no other row changes split. The professor chose to drop
# both (2026-10-16 09:06 KST decision card: evaluation-bench isolation also covers sources designed from a bench).
XSTEST_TYPE_SOURCES = ("trick_safe", "benign_harm_discuss")
EXCLUDE_SOURCES: tuple = XSTEST_TYPE_SOURCES


def wdir(check: bool) -> Path:
    d = C.CACHE / ("check" if check else "full")
    d.mkdir(parents=True, exist_ok=True)
    return d


def odir(check: bool) -> Path:
    d = (C.CACHE / "check" / "results") if check else C.OUT
    d.mkdir(parents=True, exist_ok=True)
    return d


def runs(check: bool) -> dict:
    return {b: C.CHECK_RUNS for b in C.CHECK_BENCHES} if check else dict(C.RUNS)


def morables() -> Path:
    """The 709-fable Morables file built by PEAOS's own builder from cardiffnlp/Morables (as for v2.1), kept in the
    cache so the PEAOS checkout stays untouched."""
    f = C.CACHE / "morables.jsonl"
    if not f.exists():
        C.CACHE.mkdir(parents=True, exist_ok=True)
        p = C.peaos()
        if C.child([C.PY, p / "scripts" / "build_morables_dataset.py", "--out", f], p) or not f.exists():
            raise SystemExit("Morables build failed (pip install datasets; HF access)")
    return f


# ---- R: record -----------------------------------------------------------------------------------

def sheet_rows(arm: str = "H07") -> dict[str, int]:
    """Rows of one PEINN arm per bench in the submitted per-item sheets (results/per_item, all runs)."""
    out = {}
    for b in C.BENCHES:
        s = pd.read_csv(C.PEINN / "results" / "per_item" / f"{b}_per_item.csv", usecols=["arm_id"], low_memory=False)
        out[b] = int((s.arm_id == arm).sum())
    return out


def record(check: bool = False, log=print) -> int:
    d = wdir(check)
    rec = d / "record.jsonl"
    for x in ("record.jsonl", "done_record_record.json"):
        (d / x).unlink(missing_ok=True)
    shutil.rmtree(d / "peaos_out" / "record", ignore_errors=True)
    rc = C.child([C.PY, DRIVER, "record", "--out", d, "--runs", json.dumps(runs(check)), "--arms", "H07",
                  "--morables", morables()], C.peaos(), env={"PEINN2_POSTURE_SHA": "1"})
    if rc:
        return rc
    rows = C.jsonl(rec)
    df = pd.DataFrame(rows)
    sub = sheet_rows()
    st = {"calls": len(df), "unique": int(df.sha.nunique()),
          "by_bench": {b: {"calls": int((df.bench == b).sum()), "unique": int(df[df.bench == b].sha.nunique()),
                           "submitted_rows_H07": sub.get(b), **posture_cover(d / "peaos_out" / "record" / b, set(df.sha))}
                       for b in runs(check)}}
    log(json.dumps(st))
    C.jdump(st, odir(check) / "record_stats.json")
    empty = [b for b, v in st["by_bench"].items() if not v["calls"]]
    if empty:
        log(f"stop: no routing text recorded for {empty}")
        return 1
    if check:
        return 0
    return 0 if C.publish([odir(check) / "record_stats.json"],
                                "v21r R: routing texts of the submitted benches recorded with a mock LLM (counts)") else 1


def posture_sha(s: pd.Series) -> pd.Series:
    """The routing-text sha the driver puts after '|' in neutro_posture (PEINN2_POSTURE_SHA)."""
    return s.fillna("").astype(str).str.extract(r"\|([0-9a-f]{40})$")[0]


def posture_cover(folder: Path, shas: set) -> dict:
    """Rows of a bench CSV whose posture names a recorded routing text (each answer row must map to one)."""
    fs = sorted(Path(folder).glob("*_batch_*.csv"))
    if not fs:
        return {"csv_rows": 0, "rows_with_sha": 0, "rows_sha_recorded": 0}
    x = pd.read_csv(fs[-1], low_memory=False)
    h = posture_sha(x["neutro_posture"]) if "neutro_posture" in x else pd.Series(dtype=object)
    return {"csv_rows": int(len(x)), "rows_with_sha": int(h.notna().sum()), "rows_sha_recorded": int(h.isin(shas).sum())}


def record_texts(check: bool) -> pd.DataFrame:
    df = pd.DataFrame(C.jsonl(wdir(check) / "record.jsonl"))
    return df.drop_duplicates("sha").reset_index(drop=True)


# ---- C1: corpus files and the guard audit ------------------------------------------------------------

def corpus_files() -> dict:
    """The v4 head corpus in PEAOS (the labelled 2-of-3 + illocution file the shipped head was trained on)."""
    v4 = C.peaos() / "pea_eval" / "data" / "ee_3class" / "v4"
    listing = sorted(p.name for p in v4.glob("*")) if v4.exists() else []
    train = v4 / "train.csv"
    held = next((v4 / n for n in ("heldout.csv", "val.csv", "test.csv") if (v4 / n).exists()), None)
    if not train.exists():
        raise SystemExit(f"v4 corpus not found: {train} (listing: {listing})")
    return {"dir": str(v4), "listing": listing, "train": train, "heldout": held}


def audit(check: bool = False, log=print) -> int:
    d = wdir(check)
    cf = corpus_files()
    log(f"v4 corpus: {cf['listing']}; train={cf['train'].name}, heldout={cf['heldout'].name if cf['heldout'] else None}")
    files = [cf["train"]] + ([cf["heldout"]] if cf["heldout"] else [])
    if check:                                            # small copies in the work dir
        sm = []
        for f in files:
            t = d / f"check_{f.name}"
            pd.read_csv(f).sample(n=200, random_state=0).to_csv(t, index=False, encoding="utf-8")
            sm.append(t)
        files = sm
    rc = C.child([C.PY, DRIVER, "audit", "--out", d, "--record", d / "record.jsonl", "--corpus", *files], C.peaos())
    meta = C.jload(d / "audit_meta.json") if (d / "audit_meta.json").exists() else {}
    meta["corpus_dir_listing"] = cf["listing"]
    meta["files"] = [Path(f).name for f in files]
    C.jdump(meta, d / "audit_meta.json")
    return rc


# ---- F: features -------------------------------------------------------------------------------------

def corpus_frame(check: bool) -> pd.DataFrame:
    cf = corpus_files()
    d = wdir(check)
    parts = []
    for f, role in ((cf["train"], "train"), (cf["heldout"], "heldout")):
        if f is None:
            continue
        p = d / f"check_{f.name}" if check else f
        x = pd.read_csv(p)
        x["file_role"] = role
        parts.append(x)
    df = pd.concat(parts, ignore_index=True)
    df["text"] = df["text"].astype(str)
    df["sha"] = [C.sha(t) for t in df.text]
    for c in ("mask_T", "mask_I", "mask_F"):
        if c not in df:
            df[c] = 1.0
    if "polar" not in df:
        df["polar"] = np.where(df.F >= 0.5, "F", "T")
    return df


def _ensure_peinn_checkpoints(src: Path) -> None:
    data = src / "pea_eval" / "data"
    data.mkdir(parents=True, exist_ok=True)
    for n in ("ee_checkpoint_agent_a.pt", "ee_neutro_head_v4.pt", "ee_emotion_readout_embedding.pt",
              "ee_hybrid_calibrator_best.pt"):
        if not (data / n).exists():
            shutil.copy(src.parent / "checkpoints" / n, data / n)


def features(check: bool = False, log=print) -> int:
    d = wdir(check)
    texts = list(dict.fromkeys(corpus_frame(check).text.tolist() + record_texts(check).text.tolist()))
    tf = d / "feature_texts.json"
    tf.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    src = C.peinn() / "src"
    _ensure_peinn_checkpoints(src)
    log(f"features for {len(texts)} texts")
    return C.child([C.PY, SIDE, "features", "--texts", tf, "--out", d / "features.npz"], src,
                   env={"PEINN_NEUTRO_HEAD": "ee_neutro_head_v4.pt"})


def load_features(check: bool) -> dict:
    z = np.load(wdir(check) / "features.npz", allow_pickle=False)
    idx = {str(k): i for i, k in enumerate(z["keys"])}
    return {"idx": idx, "head_x": z["head_x"], "cal_x": z["cal_x"], "tif": z["tif"], "e1": z["e1"]}


def rows_of(F: dict, shas) -> np.ndarray:
    return np.array([F["idx"][s] for s in shas])


# ---- C2: embedding near-duplicates and the split -----------------------------------------------------

def _cos_max(A: np.ndarray, B: np.ndarray, chunk: int = 4096) -> np.ndarray:
    A = A / (np.linalg.norm(A, axis=1, keepdims=True) + 1e-8)
    B = B / (np.linalg.norm(B, axis=1, keepdims=True) + 1e-8)
    out = np.empty(len(A), dtype="float32")
    for i in range(0, len(A), chunk):
        out[i:i + chunk] = (A[i:i + chunk] @ B.T).max(axis=1)
    return out


def assign_split(df: pd.DataFrame, seed: int = SPLIT_SEED) -> pd.Series:
    """train file -> train; held-out file halved by (source, polar) into val and test. Without a held-out file the
    train file is split 80/10/10 by (source, polar)."""
    rng = random.Random(seed)
    split = pd.Series("train", index=df.index, dtype=object)
    has_held = (df.file_role == "heldout").any()
    pool = df[df.file_role == "heldout"] if has_held else df
    for _, g in pool.groupby(["source", "polar"], sort=True):
        ix = list(g.index)
        rng.shuffle(ix)
        if has_held:
            h = len(ix) // 2
            split[ix[:h]], split[ix[h:]] = "val", "test"
        else:
            n = len(ix)
            a, b = int(round(n * 0.8)), int(round(n * 0.9))
            split[ix[a:b]], split[ix[b:]] = "val", "test"
    return split


def drop_table(df: pd.DataFrame) -> dict:
    """Dropped rows per 'source|reason' (string keys, so the audit is JSON)."""
    return {f"{s}|{w}": int(n) for (s, w), n in df[df["drop"] != ""].groupby(["source", "drop"]).size().items()}


def exclude_sources(df: pd.DataFrame, kept: pd.DataFrame, names) -> pd.DataFrame:
    """Drop the named sources after the split (df's 'drop' marks them 'xstest_type'); other rows keep their split."""
    off = kept.source.isin(tuple(names))
    df.loc[df.sha.isin(set(kept.sha[off])), "drop"] = "xstest_type"
    return kept[~off].copy()


def split(check: bool = False, log=print) -> int:
    d = wdir(check)
    df = corpus_frame(check)
    au = pd.DataFrame(C.jsonl(d / "audit.jsonl"))
    meta = C.jload(d / "audit_meta.json")
    bad_guard = set(au[~au.ok].sha) if len(au) else set()
    F = load_features(check)
    rec = record_texts(check)
    sem = slice(32, 416)                                    # MiniLM-384 block of the head input
    cos = _cos_max(F["head_x"][rows_of(F, df.sha), sem], F["head_x"][rows_of(F, rec.sha), sem])
    df["near_cos"] = cos
    df["drop"] = ""
    df.loc[df.sha.isin(bad_guard), "drop"] = "guard"
    df.loc[(df["drop"] == "") & (df.near_cos >= NEAR_COS), "drop"] = "embedding"
    df = df.drop_duplicates("sha")
    kept = df[df["drop"] == ""].copy()
    kept["split"] = assign_split(kept)
    kept = exclude_sources(df, kept, EXCLUDE_SOURCES)
    kept.to_csv(d / "corpus_split.csv", index=False, encoding="utf-8")
    def tab(g):
        return {f"{s}|{p}": int(n) for (s, p), n in g.groupby(["source", "polar"]).size().items()}
    st = {"rows": int(len(df)), "kept": int(len(kept)), "near_cos": NEAR_COS,
          "dropped": {"guard": int((df["drop"] == "guard").sum()), "embedding": int((df["drop"] == "embedding").sum()),
                      "xstest_type": int((df["drop"] == "xstest_type").sum())},
          "dropped_by_source": drop_table(df),
          "guard_reasons": {str(k): int(v) for k, v in au.why.value_counts().items()} if len(au) else {},
          "split": kept.split.value_counts().to_dict(), "by_source_polar": tab(kept),
          "bench_files_found": meta.get("bench_files"), "corpus_dir_listing": meta.get("corpus_dir_listing"),
          "dropped_sha": sorted(df[df["drop"] != ""].sha)}
    o = odir(check) / "corpus"
    C.jdump(st, o / "corpus_audit.json")
    L = ["# 코퍼스 격리 검사 (DESIGN.md 3)", "",
         f"- 대상 행 {st['rows']:,}, 남긴 행 {st['kept']:,}",
         f"- 가드 탈락 {st['dropped']['guard']:,} (정확 일치·5-gram 포함률 > 0.5), 임베딩 탈락 {st['dropped']['embedding']:,} "
         f"(MiniLM 코사인 ≥ {NEAR_COS}), XSTest 유형 합성 출처 탈락 {st['dropped']['xstest_type']:,} "
         f"({', '.join(EXCLUDE_SOURCES) or '없음'}, DESIGN.md 11)",
         f"- 분할: {st['split']}", "", "## 출처별 탈락", ""]
    L += [f"- {k}: {v}" for k, v in sorted(st["dropped_by_source"].items())] or ["- 없음"]
    (o / "corpus_audit.md").write_text("\n".join(L) + "\n", encoding="utf-8")
    log(json.dumps({k: st[k] for k in ("rows", "kept", "dropped", "split")}))
    if check:
        return 0
    return 0 if C.publish([o], "v21r C: isolation audit of the v4 head corpus and the train/val/test split") else 1


def load_split(check: bool) -> pd.DataFrame:
    return pd.read_csv(wdir(check) / "corpus_split.csv")
