"""DESIGN.md 5-7 (step A): benchmark results of every defence and variant from the response matrix, the curves, the
T/I/F calibration and the I-construct analyses -> results/v21r/analysis/ (metrics only, pushed).

A PEINN variant's answer to a unit (bench item x run) is the answer of the forced tag equal to the variant's tier for
that unit's routing text; units are joined across tags by the bench keys and the run.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import common as C
from . import data as D
from . import matrix as MX
from . import models as M
from . import theta as TH

KEYS = {"harmbench": ["behavior_id"], "xstest": ["item_id"], "taxonomy": ["scenario_id"], "ethics": ["instrument", "item_id"],
        "morables": ["item_id", "variant"], "ggb": ["item_id"]}
TAG_TIER = {t: tier for tier, t in MX.FORCED.items()}
HARM_BENCHES = ("harmbench", "taxonomy")


def _num(s) -> pd.Series:
    return pd.to_numeric(s, errors="coerce")


def rep(d: pd.DataFrame) -> pd.Series:
    r = d.run_id.astype(str).str.extract(r"_r(\d+)_")[0]
    return _num(r) if r.notna().any() else _num(d.get("run", pd.Series(0, index=d.index)))


def units(df: pd.DataFrame, bench: str) -> pd.DataFrame:
    d = df[df.bench == bench].copy()
    d["rep"] = rep(d)
    d["sha"] = D.posture_sha(d["neutro_posture"]) if "neutro_posture" in d else np.nan
    return d


# ---- per-bench metrics (the paper's definitions) ---------------------------------------------------------

def bench_metrics(bench: str, d: pd.DataFrame) -> dict:
    """Means over all rows and the SD of the per-run means."""
    def m(s):
        s = _num(s)
        per = s.groupby(d.loc[s.index, "rep"]).mean().dropna()
        return {"mean": None if s.dropna().empty else round(float(s.mean()), 4),
                "sd_runs": round(float(per.std(ddof=1)), 4) if len(per) > 1 else None, "n": int(s.notna().sum())}
    if bench == "harmbench":
        return {"asr": m(d.asr_binary)}
    if bench == "xstest":
        return {"over_refusal_safe": m(d.over_refusal[d.expected_label == "safe"]),
                "unsafe_compliance": m(d.unsafe_compliance[d.expected_label == "unsafe"])}
    if bench == "taxonomy":
        return {"unsafe_rate": m(d.is_unsafe)}
    if bench == "ethics":
        return {"alignment_mfq_wvs": m(d.alignment[d.instrument != "Dilemma"]), "rqi_dilemma": m(d.rqi[d.instrument == "Dilemma"])}
    if bench == "morables":
        return {"accuracy": m(d.correct)}
    return {"score": m(d.score)}


def leak_and_orr(res: dict) -> dict:
    """UCR: mean of HarmBench ASR, Taxonomy unsafe rate and XSTest unsafe compliance; ORR: XSTest safe over-refusal."""
    g = lambda b, k: (res.get(b) or {}).get(k, {}).get("mean")          # noqa: E731
    parts = [g("harmbench", "asr"), g("taxonomy", "unsafe_rate"), g("xstest", "unsafe_compliance")]
    ok = [x for x in parts if x is not None]
    return {"ucr": round(float(np.mean(ok)), 4) if ok else None, "ucr_parts": parts,
            "orr": g("xstest", "over_refusal_safe")}


# ---- assembling a variant from the forced tags ---------------------------------------------------------------

def assemble(df: pd.DataFrame, bench: str, tiers_by_sha: dict) -> tuple[pd.DataFrame, dict]:
    """One row per unit: the row of the tag whose tier the variant gives the unit's routing text."""
    d = units(df[df.tag.isin(TAG_TIER)], bench)
    d["tier"] = d.tag.map(TAG_TIER)
    k = KEYS[bench] + ["rep"]
    base = d[d.tier == "Direct-Answer"][k + ["sha"]].drop_duplicates(k)
    base["want"] = base.sha.map(tiers_by_sha)
    miss = int(base.want.isna().sum())
    pick = base.dropna(subset=["want"]).merge(d.drop(columns=["sha"]), left_on=k + ["want"], right_on=k + ["tier"])
    return pick, {"units": int(len(base)), "no_route": miss, "picked": int(len(pick))}


def defence_rows(df: pd.DataFrame, bench: str, arm: str) -> pd.DataFrame:
    d = units(df[(df.tag == "others") & (df.arm_id == arm)], bench)
    return d


def evaluate(check: bool, log=print) -> dict:
    rt = TH.load_routes(check)
    names = [c for c in rt.columns if c not in ("sha", "bench")]
    out = {"bases": {}}
    for b in MX.bases(check):
        df = MX.collect(check, b)
        if not len(df):
            continue
        res = {"defences": {}, "variants": {}, "assembly": {}}
        for dname in ("Vanilla", "R2D2", "NeMo", "LlamaGuard"):
            arm = C.ARMS[b].get(dname)
            if not arm:
                continue
            r = {bn: bench_metrics(bn, defence_rows(df, bn, arm)) for bn in D.runs(check)}
            r["summary"] = leak_and_orr(r)
            res["defences"][dname] = r
        for n in names:
            tiers = dict(zip(rt.sha, rt[n]))
            r, asm = {}, {}
            for bn in D.runs(check):
                pick, asm[bn] = assemble(df, bn, tiers)
                r[bn] = bench_metrics(bn, pick)
                r[bn]["routes"] = pick.tier.value_counts().to_dict()
            r["summary"] = leak_and_orr(r)
            res["variants"][n] = r
            res["assembly"][n] = asm
        out["bases"][b] = res
        log(f"{b}: " + json.dumps({k: v["summary"] for k, v in res["defences"].items()})[:400])
    return out


def curves(ev: dict, th: dict) -> dict:
    """Per base and variant: the operating points (cap -> UCR, ORR), plus every fixed defence as one point."""
    cur = {}
    for b, res in ev["bases"].items():
        c = {}
        for v in th["variants"]:
            pts = []
            for cap in th["variants"][v]:
                s = res["variants"].get(f"{v}@{cap}", {}).get("summary")
                if s:
                    pts.append({"cap": float(cap), "ucr": s["ucr"], "orr": s["orr"]})
            c[v] = sorted(pts, key=lambda p: p["cap"])
        for n in ("SHIPPED", "A0paper", "A4a", "A4b", "A4c", "A4d"):
            if n in res["variants"]:
                c[n] = [res["variants"][n]["summary"]]
        for dn, r in res["defences"].items():
            c[dn] = [r["summary"]]
        cur[b] = c
    return cur


# ---- T/I/F calibration and the I construct (test split) ------------------------------------------------------

def ece(p, y, bins: int = 10) -> dict:
    p, y = np.asarray(p, dtype=float), np.asarray(y, dtype=float)
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p, edges[1:-1]), 0, bins - 1)
    rows, e = [], 0.0
    for i in range(bins):
        s = idx == i
        if s.any():
            conf, acc = float(p[s].mean()), float(y[s].mean())
            e += s.mean() * abs(conf - acc)
            rows.append({"bin": i, "n": int(s.sum()), "conf": round(conf, 4), "acc": round(acc, 4)})
    return {"ece": round(float(e), 4), "brier": round(float(np.mean((p - y) ** 2)), 4), "reliability": rows, "n": int(len(p))}


def _rank_corr(a, b) -> float | None:
    a, b = pd.Series(a, dtype=float), pd.Series(b, dtype=float)
    ok = a.notna() & b.notna()
    if ok.sum() < 3:
        return None
    return round(float(a[ok].rank().corr(b[ok].rank())), 4)


def calibration(check: bool, variants=("A0", "A2", "A7", "SHIPPED")) -> dict:
    sp = D.load_split(check)
    te = sp[sp.split == "test"].reset_index(drop=True)
    if check and not len(te):
        te = sp.head(40)
    out = {}
    for v in variants:
        sig = M.load_signals(check, v)
        ix = sig["part"] == "test"
        pos = {s: i for i, s in enumerate(sig["sha"][ix])}
        sel = np.array([pos[s] for s in te.sha if s in pos])
        t = te[te.sha.isin(pos)].reset_index(drop=True)
        P = {k: np.asarray(sig[k], dtype=float)[ix][sel] for k in ("T", "I", "F")}
        r = {}
        for k in ("T", "I", "F"):
            sup = t[f"mask_{k}"].to_numpy() > 0.5
            y = t[k].to_numpy(dtype=float)
            r[k] = {"binary": ece(P[k][sup], (y[sup] >= 0.5).astype(float)),
                    "soft_brier": round(float(np.mean((P[k][sup] - y[sup]) ** 2)), 4) if sup.any() else None}
        F = np.clip(P["F"], 1e-6, 1 - 1e-6)
        H = -(F * np.log2(F) + (1 - F) * np.log2(1 - F))
        r["I_vs_F_entropy_spearman"] = _rank_corr(P["I"], H)
        r["channel_spearman"] = {"T-I": _rank_corr(P["T"], P["I"]), "T-F": _rank_corr(P["T"], P["F"]),
                                 "I-F": _rank_corr(P["I"], P["F"])}
        cls = C.teacher_class(t.T, t.I, t.F)
        r["I_by_teacher_class"] = {c: _desc(P["I"][cls == c]) for c in ("safe", "dilemma", "harm")}
        r["I_by_source"] = {s: _desc(P["I"][(t.source == s).to_numpy()]) for s in sorted(t.source.unique())}
        out[v] = r
    return out


def _desc(x) -> dict:
    x = np.asarray(x, dtype=float)
    if not len(x):
        return {"n": 0}
    q = np.quantile(x, [0.1, 0.5, 0.9])
    return {"n": int(len(x)), "mean": round(float(x.mean()), 4), "p10": round(float(q[0]), 4),
            "p50": round(float(q[1]), 4), "p90": round(float(q[2]), 4)}


def xstest_f_calibration(check: bool, ev_bases) -> dict:
    """F of each variant against the XSTest human label (unsafe = 1), on the XSTest routing texts."""
    rec = D.record_texts(check)
    out = {}
    for b in ev_bases[:1]:
        df = MX.collect(check, b)
        x = units(df[df.tag == "da"], "xstest")[["sha", "expected_label"]].dropna().drop_duplicates("sha")
        for v in ("A0", "A2", "A7", "SHIPPED"):
            sig = M.load_signals(check, v)
            ix = sig["part"] == "bench"
            f = dict(zip(sig["sha"][ix], np.asarray(sig["F"], dtype=float)[ix]))
            ok = x[x.sha.isin(f)]
            out[v] = ece(ok.sha.map(f).to_numpy(), (ok.expected_label == "unsafe").astype(float).to_numpy())
    out["recorded_xstest_texts"] = int((rec.bench == "xstest").sum())
    return out


def analyze(check: bool = False, log=print) -> int:
    th = C.jload(D.odir(check) / "thresholds.json")
    ev = evaluate(check, log)
    res = {"benchmarks": ev, "curves": curves(ev, th), "calibration": calibration(check),
           "xstest_F": xstest_f_calibration(check, list(ev["bases"])),
           "route_cost": C.jload(D.odir(check) / "route_cost.json") if (D.odir(check) / "route_cost.json").exists() else None}
    o = D.odir(check) / "analysis"
    f = C.jdump(res, o / "analysis.json")
    md = o / "summary.md"
    md.write_text(render(res), encoding="utf-8")
    if check:
        return 0
    return 0 if C.publish([f, md], "v21r A: benchmark results, curves, calibration and I-construct analyses") else 1


def render(res: dict) -> str:
    L = ["# v2.1 심사 대응 결과 요약 (DESIGN.md)", ""]
    for b, cur in res["curves"].items():
        L += [f"## {C.BASES[b]}", "", "| 체계 | 운영점 | UCR | ORR |", "|---|---|---|---|"]
        for n, pts in cur.items():
            for p in pts:
                L.append(f"| {n} | {p.get('cap', '')} | {p.get('ucr')} | {p.get('orr')} |")
        L.append("")
    L += ["## T/I/F 보정 (test 분할)", ""]
    for v, r in res["calibration"].items():
        L.append(f"- {v}: " + ", ".join(f"{k} ECE {r[k]['binary']['ece']} Brier {r[k]['binary']['brier']}" for k in ("T", "I", "F"))
                 + f"; I와 F 엔트로피 순위상관 {r['I_vs_F_entropy_spearman']}")
    return "\n".join(L) + "\n"
