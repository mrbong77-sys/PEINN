"""DESIGN.md 37: the last satellite step before the manuscript (Eugene 2026-10-18 19:39 KST "위성 먼저 사용 끝내").
Everything the manuscript still needs from the satellite's cache goes into the repository, so the rest runs anywhere.

  forced-export  every forced-tag row (the answer of each bench unit under each of the five tiers), the route table of
                 every variant and operating point, the T/I/F/E signals of every variant on val, test and the routing
                 texts, and the teacher labels of val and test -> results/forced/ (CPU). The ablation table's moral
                 scores and the energy-only variant (R2-2) are computed from these.
  gate-mem       the main variant's whole input gate in one process: the shipped feature path (emotion trunk, MiniLM,
                 principle anchors) plus A0ftM's fine-tuned mpnet and MiniLM passes and the Mahalanobis distance; time
                 per text and peak memory on the GPU and on one CPU thread. The shipped frozen mpnet pass and head still
                 run there, so the figures are an upper bound for A0ftM. -> results/route_cost.json "gate_main"
  gate-retrain   A0ftM's trainable parts trained again from the same corpus into a scratch folder (the released
                 checkpoints are untouched): wall time of each part, peak GPU memory, and whether the weights equal the
                 released ones; plus the time of the threshold fit on val. -> results/gate_retrain.json
"""
from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd

from . import analyze as A
from . import common as C
from . import data as D
from . import matrix as MX
from . import models as M
from . import theta as TH
from .ggb import DROP, redact


def forced_export(check: bool = False, log=print) -> int:
    o = D.odir(check) / "forced"
    o.mkdir(parents=True, exist_ok=True)
    files = []
    for b in MX.bases(check):
        df = MX.collect(False, b)
        if not len(df):
            continue
        d = df[df.tag.isin(A.TAG_TIER)]
        for bench in D.runs(check):
            x = A.units(d, bench)
            if not len(x):
                continue
            x["tier"] = x.tag.map(A.TAG_TIER)
            x = x[[c for c in x.columns if not DROP.match(c)]]
            if "prompt_p2" in x:
                x["prompt_p2"] = x.prompt_p2.astype(str).str[:1500]
            x = redact(x, bench)
            f = o / f"{bench}_{b}.csv.gz"
            x.to_csv(f, index=False, encoding="utf-8", compression="gzip")
            files.append(f)
            log(f"  {bench} {b}: {len(x)} rows, tiers {x.tier.value_counts().to_dict()}, {f.stat().st_size / 2**20:.1f} MiB")
    rt = TH.load_routes(False)
    f = o / "routes.csv.gz"
    rt.to_csv(f, index=False, encoding="utf-8", compression="gzip")
    files.append(f)
    for v in (*TH.FITTED, "SHIPPED"):
        try:
            s = M.load_signals(False, v)
        except FileNotFoundError:
            log(f"  signals {v}: none")
            continue
        x = pd.DataFrame({k: s[k] for k in ("sha", "part", "T", "I", "F", "E")})
        f = o / f"signals_{v}.csv.gz"
        x.to_csv(f, index=False, encoding="utf-8", compression="gzip")
        files.append(f)
    sp = D.load_split(False)
    lab = sp[sp.split.isin(("val", "test"))][[c for c in ("sha", "split", "source", "T", "I", "F") if c in sp]]
    f = o / "split_labels.csv.gz"
    lab.to_csv(f, index=False, encoding="utf-8", compression="gzip")
    files.append(f)
    log(f"  routes {rt.shape}, labels {len(lab)}, {len(files)} files, "
        f"{sum(x.stat().st_size for x in files) / 2**20:.1f} MiB")
    if check:
        return 0
    return 0 if C.publish(files, "v21r: forced-tag rows, route tables, signals and val/test labels (DESIGN.md 37)") else 1


def gate_mem(check: bool = False, log=print) -> int:
    texts = D.record_texts(False).text.tolist()[: 20 if check else 200]
    d = D.wdir(check) / "cost"
    d.mkdir(parents=True, exist_ok=True)
    tf = d / "gate_texts.json"
    tf.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    src = C.peinn() / "src"
    D._ensure_peinn_checkpoints(src)
    md = D.wdir(False) / "models"
    out = {}
    for dev, env in (("gpu", {}), ("cpu1", MX.CPU1_ENV)):
        want = "cpu" if dev == "cpu1" else "cuda"
        f = d / f"gate_main_{dev}.json"
        f.unlink(missing_ok=True)
        rc = C.child([C.PY, D.SIDE, "gate-time", "--texts", tf, "--out", f, "--ft-root", C.ROOT, "--ft-models", md],
                     src, env={"PEINN_NEUTRO_HEAD": "ee_neutro_head_v4.pt", **env})
        r = C.jload(f) if f.exists() else {"error": f"rc {rc}, no result"}
        if r.get("device") not in (None, want):
            r["error"] = f"ran on {r.get('device')}, wanted {want}"
        out[dev] = r
        log(f"gate main {dev}: {r}")
    bad = {k: v["error"] for k, v in out.items() if "error" in v}
    if check:
        C.jdump(out, D.odir(check) / "gate_main.json")
        return 1 if bad else 0
    f = D.odir(check) / "route_cost.json"
    res = C.jload(f)
    res["gate_main"] = {"what": "shipped feature path + A0ftM fine-tuned passes + Mahalanobis in one process; the "
                                "shipped frozen mpnet pass and head also run, so an upper bound for A0ftM", **out}
    C.jdump(res, f)
    if bad:
        log(f"gate main failed: {bad}")
        return 1
    return 0 if C.publish([f], "v21r: the main variant's whole input gate, time and peak memory (DESIGN.md 37)") else 1


def _same(a, b) -> dict:
    import torch
    sa, sb = torch.load(a, map_location="cpu")["state_dict"], torch.load(b, map_location="cpu")["state_dict"]
    if set(sa) != set(sb):
        return {"equal": False, "why": "different keys"}
    diff = max(float((sa[k].float() - sb[k].float()).abs().max()) for k in sa)
    return {"equal": diff == 0.0, "max_abs_diff": diff}


def gate_retrain(check: bool = False, log=print) -> int:
    import torch
    sp = D.load_split(False)
    F = D.load_features(False)
    tr, va = (sp[sp.split == s].reset_index(drop=True) for s in ("train", "val"))
    if check:
        va = va.head(200)
    wtr, wva = M.row_weights(tr, tr), M.row_weights(tr, va)
    tr, va = tr.assign(rw=wtr), va.assign(rw=wva)
    trs = tr.sample(n=min(len(tr), 64), random_state=0) if check else tr
    Hx, Cx = F["head_x"], F["cal_x"]
    rva, rts = D.rows_of(F, va.sha), D.rows_of(F, trs.sha)
    hb = np.r_[0:32, 416:800]
    fhp = dict(M.FT_HP, epochs=1) if check else M.FT_HP
    hhp = dict(M.FT_HEAD_HP, epochs=1) if check else M.FT_HEAD_HP
    tmp = D.wdir(check) / "retrain"
    tmp.mkdir(parents=True, exist_ok=True)
    cuda = torch.cuda.is_available()
    if cuda:
        torch.cuda.reset_peak_memory_stats()
    sec = {}
    t0 = time.perf_counter()
    e_inf, e_auc = M.train_ft("energy", trs, va, Cx[rts][:, :32], Cx[rva][:, :32], M.SHIPPED_NEG_W, fhp, log, hist=[],
                              save=tmp / "A0ft_energy.pt")
    sec["energy_mpnet"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    _, h_vl = M.train_ft("head", trs, va, Hx[rts][:, hb], Hx[rva][:, hb], M.SHIPPED_NEG_W, hhp, log, hist=[],
                         save=tmp / "A0ft_head.pt")
    sec["head_minilm"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    m = M.mahalanobis_fit(e_inf(trs.text.astype(str).tolist(), None, emb=True), trs.F.to_numpy() >= 0.5)
    sec["mahalanobis"] = time.perf_counter() - t0
    t0 = time.perf_counter()
    sig = M.load_signals(False, TH.MAIN_VARIANT)
    TH.fit(TH.MAIN_VARIANT, sig, va, TH.MAIN_CAP)
    sec["thresholds_val"] = time.perf_counter() - t0
    md = D.wdir(False) / "models"
    rep = json.loads((D.odir(False) / "train_report.json").read_text(encoding="utf-8"))
    res = {"device": torch.cuda.get_device_name(0) if cuda else "cpu",
           "n_train": len(trs), "n_val": len(va), "epochs": {"energy": fhp["epochs"], "head": hhp["epochs"]},
           "sec": {k: round(v, 1) for k, v in sec.items()}, "sec_total": round(sum(sec.values()), 1),
           "gpu_peak_GB": round(torch.cuda.max_memory_allocated() / 1e9, 3) if cuda else None,
           "energy_val_auroc": e_auc, "energy_val_auroc_released": rep.get("A0ft_energy_val_auroc"),
           "head_val_loss": h_vl, "head_val_loss_released": rep.get("A0ft_head_val_loss"),
           "ood_tau": round(m["tau"], 4), "ood_tau_released": (rep.get("A0ftM_ood") or {}).get("tau"),
           "same_weights": {k: _same(md / f"A0ft_{k}.pt", tmp / f"A0ft_{k}.pt") for k in ("energy", "head")}
           if (md / "A0ft_energy.pt").exists() else None,
           "not_timed": "feature extraction of the corpus (emotion and principle blocks, cached); per text it costs one "
                        "gate pass (route_cost.json gate)"}
    log(json.dumps(res))
    f = C.jdump(res, D.odir(check) / "gate_retrain.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r: A0ftM gate retrained from the same corpus, time and memory (DESIGN.md 37)") else 1
