"""A1-A3 with PEINN's fine-tuned encoders (pre-review 2.2).

The frozen-encoder ablations A1 (no I), A2 (softmax safe / ambiguous / harmful) and A3 (binary harm classifier with
uncertainty routing) are trained again in PEINN's fine-tuned configuration: the head's MiniLM is trained end to end
with each head exactly as A0ft's head was (train_ft 'head', FT_HEAD_HP, seed 42, the same corpus, row weights and
validation selection), and the energy is A0ft's (the released fine-tuned mpnet calibrator, unchanged). Their reference
is A0ft (PEINN without the OOD flag, which changes no answer at the main operating point).
Thresholds are fitted on val by the procedure of theta.thresholds at every curve cap, and the routes of the bench routing
texts follow. No generation and no judging: the answers of every route already exist (results/forced).

    python -m v21r ftv --check   # 64 training rows, one epoch, 200 val rows; nothing pushed
    python -m v21r ftv           # the three heads (about 200 s each on the RTX 5090), then thresholds and routes;
                                 # resumes after the last finished head; pushes results/forced and ftv_report.json
    python -m v21r ftv-fit       # CPU, anywhere: thresholds and routes again from the exported signals and labels
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import common as C
from . import data as D
from . import models as M
from . import theta as TH

HEADS = (("A1ft", "tf"), ("A2ft", "softmax"), ("A3ft", "binary"))
REF = "A0ft"


def tif(out: str, p: np.ndarray) -> dict:
    """The gate's T, I, F from a head's output (the frozen A1-A3 store theirs the same way, models.train_all)."""
    if out == "tf":
        return {"T": p[:, 0], "I": np.zeros(len(p)), "F": p[:, 1]}
    if out == "softmax":
        return {"T": p[:, 0], "I": p[:, 1], "F": p[:, 2]}
    q = p.ravel()
    return {"T": 1 - q, "I": np.zeros(len(q)), "F": q}


def fit_routes(sigs: dict, val: pd.DataFrame, bench_sha, caps) -> tuple[dict, pd.DataFrame]:
    """Thresholds of every variant in sigs at every cap (val only) and the route of every bench routing text."""
    th, rt = {}, {"sha": list(bench_sha)}
    for v, sig in sigs.items():
        th[v] = {f"{c:g}": TH.fit(v, sig, val, c) for c in caps}
        ix = sig["part"] == "bench"
        pos = {s: i for i, s in enumerate(sig["sha"][ix])}
        sel = np.array([pos[s] for s in bench_sha])
        T, I, F, E = (x[ix][sel] for x in TH.inputs(v, sig))
        for c in caps:
            r = th[v][f"{c:g}"]
            rt[f"{v}@{c:g}"] = C.gate(T, I, F, E, r["th"], **TH.options(v))
    return th, pd.DataFrame(rt)


def _export_sig(f, sig: dict) -> None:
    pd.DataFrame({k: sig[k] for k in ("sha", "part", "T", "I", "F", "E")}).to_csv(f, index=False, encoding="utf-8",
                                                                                compression="gzip")


def _read_sig(f) -> dict:
    s = pd.read_csv(f, dtype={"sha": str})
    return {k: s[k].to_numpy() for k in ("sha", "part", "T", "I", "F", "E")}


def merge(check: bool, th: dict, rt: pd.DataFrame) -> list:
    """Add the variants to thresholds.json and their columns to the exported route table (both replaced if present)."""
    o = D.odir(check)
    tf = o / "thresholds.json"
    t = C.jload(tf)
    t["variants"].update(th)
    t.setdefault("ft_variants", {"rule": "A1-A3 heads with a fine-tuned MiniLM", "reference": REF, "variants": list(th)})
    C.jdump(t, tf)
    rf = o / "forced" / "routes.csv.gz"
    r = pd.read_csv(rf, dtype={"sha": str})
    r = r.drop(columns=[c for c in rt.columns if c != "sha" and c in r.columns])
    if list(r.sha) != list(rt.sha):
        raise SystemExit("ftv: the route table and the signals list different routing texts")
    r = pd.concat([r, rt.drop(columns=["sha"])], axis=1)
    r.to_csv(rf, index=False, encoding="utf-8", compression="gzip")
    return [tf, rf]


def ftv_fit(check: bool = False, log=print) -> int:
    """Thresholds and routes of A1ft-A3ft from results/forced (no cache needed)."""
    o = D.odir(check) / "forced"
    lab = pd.read_csv(o / "split_labels.csv.gz", dtype={"sha": str})
    val = lab[lab.split == "val"].reset_index(drop=True)
    bench = pd.read_csv(o / "routes.csv.gz", dtype={"sha": str}, usecols=["sha"]).sha
    sigs = {v: _read_sig(o / f"signals_{v}.csv.gz") for v, _ in HEADS if (o / f"signals_{v}.csv.gz").exists()}
    if not sigs:
        log("ftv-fit: no signals of A1ft-A3ft in results/forced")
        return 1
    th, rt = fit_routes(sigs, val, bench, [float(c) for c in C.jload(D.odir(check) / "thresholds.json")["caps"]])
    for v in th:
        log(f"{v}@{TH.MAIN_CAP:g}: {json.dumps(th[v][f'{TH.MAIN_CAP:g}']['th'])}")
    merge(check, th, rt)
    return 0


def ftv(check: bool = False, log=print) -> int:
    import torch
    sp = D.load_split(False)
    F = D.load_features(False)
    rec = D.record_texts(False)
    tr, va, te = (sp[sp.split == s].reset_index(drop=True) for s in ("train", "val", "test"))
    if check:
        va = va.head(200)
    wtr, wva = M.row_weights(tr, tr), M.row_weights(tr, va)
    tr, va = tr.assign(rw=wtr), va.assign(rw=wva)
    trs = tr.sample(n=min(len(tr), 64), random_state=0) if check else tr
    uni = pd.DataFrame({"sha": list(va.sha) + list(te.sha) + list(rec.sha),
                        "part": ["val"] * len(va) + ["test"] * len(te) + ["bench"] * len(rec),
                        "text": list(va.text) + list(te.text) + list(rec.text)})
    ref = M.load_signals(False, REF)                              # A0ft's energy on the same texts
    e_of = {(p, s): e for p, s, e in zip(ref["part"], ref["sha"], ref["E"])}
    E = np.array([e_of[(p, s)] for p, s in zip(uni.part, uni.sha)], dtype=float)
    Hx = F["head_x"]
    hb = np.r_[0:32, 416:800]                                     # emotion | principle around the MiniLM slot
    xt, xv, xu = Hx[D.rows_of(F, trs.sha)][:, hb], Hx[D.rows_of(F, va.sha)][:, hb], Hx[D.rows_of(F, uni.sha)][:, hb]
    hhp = dict(M.FT_HEAD_HP, epochs=1) if check else M.FT_HEAD_HP
    md = D.wdir(check) / "models"
    md.mkdir(parents=True, exist_ok=True)
    rf = D.odir(check) / "ftv_report.json"
    rep = C.jload(rf) if rf.exists() and not check else {}
    rep.update({"rule": "A1-A3 heads with a fine-tuned MiniLM", "reference": REF, "n_train": len(trs), "n_val": len(va), "epochs": hhp["epochs"],
                "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "cpu"})
    sigs = {}
    for v, out in HEADS:
        f = M.sigdir(check) / f"{v}.npz"
        if f.exists() and not check and v in rep.get("heads", {}):
            log(f"== {v}: done before, kept")
            sigs[v] = M.load_signals(check, v)
            continue
        log(f"== {v}: fine-tuned MiniLM head, out '{out}'")
        if torch.cuda.is_available():
            torch.cuda.reset_peak_memory_stats()
        t0 = time.perf_counter()
        hist = []
        infer, vl = M.train_ft("head", trs, va, xt, xv, M.SHIPPED_NEG_W, hhp, log, hist=hist, save=md / f"{v}_head.pt",
                               out=out)
        sec = time.perf_counter() - t0
        sig = {"sha": uni.sha.to_numpy(), "part": uni.part.to_numpy(), "E": E, **tif(out, infer(uni.text.tolist(), xu))}
        bad = [k for k in ("T", "I", "F") if not np.isfinite(np.asarray(sig[k], float)).all()]
        if bad:
            raise SystemExit(f"{v}: non-finite {bad} (training diverged)")
        np.savez(f, **sig)
        sigs[v] = sig
        rep.setdefault("heads", {})[v] = {"out": out, "val_loss": round(float(vl), 6), "epochs": hist, "sec": round(sec, 1),
                                         "gpu_peak_GB": round(torch.cuda.max_memory_allocated() / 1e9, 3)
                                         if torch.cuda.is_available() else None}
        C.jdump(rep, rf)
        log(json.dumps(rep["heads"][v]))
    if check:
        th, rt = fit_routes(sigs, va, list(rec.sha), [TH.SAFE_CAP, TH.MAIN_CAP])
        for v in th:
            log(f"{v}@{TH.MAIN_CAP:g}: {json.dumps(th[v][f'{TH.MAIN_CAP:g}']['th'])} routes "
                f"{pd.Series(rt[f'{v}@{TH.MAIN_CAP:g}']).value_counts().to_dict()}")
        C.jdump(rep, rf)
        return 0
    o = D.odir(False) / "forced"
    files = []
    for v, sig in sigs.items():
        f = o / f"signals_{v}.csv.gz"
        _export_sig(f, sig)
        files.append(f)
    if ftv_fit(False, log):
        return 1
    files += [D.odir(False) / "thresholds.json", o / "routes.csv.gz", rf]
    return 0 if C.publish(files, "v21r ftv: A1-A3 with the fine-tuned encoders, thresholds and routes") else 1
