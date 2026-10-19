"""Section 4.7 (ablations, R1-3, R1-4, R2-2) from the exported forced-tag rows (DESIGN.md 37), in the definitions of
bench_stats (DESIGN.md 34). No model call; runs anywhere.

    python -m v21r paper-ablation        -> results/paper/ablation.json, tab_ablation.tex, ablation_curves.png

A variant's answer to a bench unit (item x run) is the forced-tag row of the tier the variant assigns to that unit's
routing text (analyze.assemble). Variants:
  A0ftM (PEINN), A0ft, A0, A1-A7 and A1ft-A3ft (DESIGN.md 42) at their val-fitted thresholds (thresholds.json, routes.csv);
  A4a-d from the main variant's routes: every item Direct, every item Deliberation, the main variant's refusals
        (Hard-block, Reasoned-Refusal) and Direct elsewhere, or and Deliberation elsewhere;
  A9    energy only (R2-2): no head; Hard-block when the main variant's energy E >= tau, Direct-Answer otherwise; tau
        fitted on val by the first-stage rule (harmful Hard-block >= 85 %, safe Hard-block < cap) with no F condition.
Each variant and operating point gets UCR (mean of HarmBench ASR, Taxonomy unsafe rate, XSTest UCR), XSTest ORR,
the Ethics composite and MORABLES clean accuracy per base; A8 and the defences come from bench_stats.json. The paper
calls this composite the average attack success rate (ASR_avg), apart from the XSTest UCR. `matched` gives, for each variant with
operating points, the lowest mean UCR over its caps whose mean ORR does not exceed the reference's ORR at the main cap
(PEINN for the encoder and routing variants, A0ft for the fine-tuned component variants, A0 for the frozen ones; R1-3),
with that point's ORR and cap; the table
calls it the best ASR_avg under an ORR budget (a summary of the test-set curve, not an operating point chosen on val).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import bench_stats as BS
from . import common as C
from . import data as D
from . import theta as TH
from . import verdicts as V

ORDER = ("zephyr", "qwen", "gemma4", "gemma3")
BENCHES = ("harmbench", "taxonomy", "xstest", "ethics", "morables")
KEYS = {"harmbench": ["behavior_id"], "xstest": ["item_id"], "taxonomy": ["scenario_id"], "ethics": ["instrument", "item_id"],
        "morables": ["item_id", "variant"]}
MAIN = f"{TH.MAIN_VARIANT}@{TH.MAIN_CAP:g}"
LABEL = {"A0ftM": "PEINN", "A0ft": "No OOD check", "A0": "Frozen encoders",
         "A1": "No $I$ channel", "A1ft": "No $I$ channel", "A2ft": "Softmax head", "A3ft": "Uncertainty routing",
         "A2": "Softmax head", "A3": "Uncertainty routing", "A5": "No emotion energy",
         "A6p": "No principle anchors", "A6e": "No emotion feature", "A7": "MiniLM classifier",
         "A4a": "Always Direct", "A4b": "Always Deliberation", "A4c": "Block + Direct", "A4d": "Block + Deliberation",
         "A9": "Energy only"}
# groups, a rule between them: PEINN | encoders (against PEINN) | components with the fine-tuned encoders (against A0ft,
# DESIGN.md 42) | components with the frozen encoders (against A0) | routing
FT_COMP = ("A1ft", "A2ft", "A3ft")
FROZEN_COMP = ("A1", "A2", "A3", "A5", "A6p", "A6e", "A7")
GROUPS = (("A0ftM",), ("A0ft", "A0"), FT_COMP, FROZEN_COMP, ("A9", "A4a", "A4b", "A4c", "A4d"))
ROWS = tuple(v for g in GROUPS for v in g)


def forced(check: bool, bench: str, base: str) -> pd.DataFrame:
    f = D.odir(check) / "forced" / f"{bench}_{base}.csv.gz"
    d = pd.read_csv(f, low_memory=False, dtype={"sha": str})
    d["rep"] = pd.to_numeric(d.rep, errors="coerce")
    d["base"] = base
    return V.apply(check, bench, d)


def energy_only(check: bool, caps) -> dict:
    """A9 thresholds on val (the main variant's energy, no F condition) and its route per routing text."""
    s = pd.read_csv(D.odir(check) / "forced" / f"signals_{TH.MAIN_VARIANT}.csv.gz", dtype={"sha": str})
    lab = pd.read_csv(D.odir(check) / "forced" / "split_labels.csv.gz", dtype={"sha": str})
    val = lab[lab.split == "val"]
    sv = s[s.part == "val"].drop_duplicates("sha").set_index("sha").loc[val.sha]
    cls = C.teacher_class(val["T"].to_numpy(), val["I"].to_numpy(), val["F"].to_numpy())
    E = sv.E.to_numpy(dtype=float)
    sb = s[s.part == "bench"].drop_duplicates("sha").set_index("sha")
    out = {}
    for cap in caps:
        r = TH.stage1(E, np.ones(len(E)), cls, True, cap)
        tau = min(r["th"]["harm"], r["th"]["extreme"])
        out[f"{cap:g}"] = {"tau": tau, "val_harm_hb": round(r["harm_hb"], 4), "val_safe_hb": round(r["safe_hb"], 4),
                           "met": r["met"], "routes": pd.Series(np.where(sb.E.to_numpy() >= tau, "Hard-block", "Direct-Answer"),
                                                                index=sb.index)}
    return out


def assemble(d: pd.DataFrame, bench: str, tiers: pd.Series) -> pd.DataFrame:
    k = KEYS[bench] + ["rep"]
    da = d[d.tier == "Direct-Answer"][k + ["sha"]].drop_duplicates(k)
    da["want"] = da.sha.map(tiers)
    pick = da.dropna(subset=["want"]).merge(d.drop(columns=["sha"]), left_on=k + ["want"], right_on=k + ["tier"])
    return pick


def scores(rows: dict, system: str) -> dict:
    """UCR, ORR, Ethics composite, MORABLES clean for one base from the picked rows of each bench."""
    st = {}
    for bench, g in rows.items():
        g = g.assign(system=system)
        if bench == "ethics":
            g = BS.ethics_rows(g)
        st[bench] = BS.system_stats(bench, g)
    ucr = np.mean([st["harmbench"]["asr"]["mean"], st["taxonomy"]["unsafe_rate"]["mean"], st["xstest"]["ucr"]["mean"]])
    return {"ucr": round(float(ucr), 6), "orr": st["xstest"]["orr"]["mean"], "ethics": st["ethics"]["composite"]["mean"],
            "morables": st["morables"]["clean"]["mean"], "harmbench": st["harmbench"]["asr"]["mean"],
            "taxonomy": st["taxonomy"]["unsafe_rate"]["mean"], "xstest_ucr": st["xstest"]["ucr"]["mean"],
            "mfa": st["ethics"]["mfa"]["mean"], "wvs": st["ethics"]["wvs"]["mean"], "rqi": st["ethics"]["rqi"]["mean"]}


def paper_ablation(check: bool = False, log=print) -> int:
    o = D.odir(check) / "paper"
    o.mkdir(parents=True, exist_ok=True)
    rt = pd.read_csv(D.odir(check) / "forced" / "routes.csv.gz", dtype={"sha": str}).set_index("sha")
    th = C.jload(D.odir(check) / "thresholds.json")
    caps = [float(c) for c in th["caps"]]
    a9 = energy_only(check, caps)
    main = rt[MAIN]
    refuse = main.isin(("Hard-block", "Reasoned-Refusal"))
    plans = {f"{v}@{c:g}": rt[f"{v}@{c:g}"] for v in th["variants"] for c in caps if f"{v}@{c:g}" in rt}
    plans.update({f"A9@{c}": r["routes"] for c, r in a9.items()})
    plans.update({"A4a": pd.Series("Direct-Answer", index=rt.index), "A4b": pd.Series("Deliberation", index=rt.index),
                  "A4c": main.where(refuse, "Direct-Answer"), "A4d": main.where(refuse, "Deliberation")})
    data = {b: {bench: forced(check, bench, b) for bench in BENCHES} for b in ORDER}
    res = {}
    for name, tiers in plans.items():
        res[name] = {}
        for b in ORDER:
            rows = {bench: assemble(data[b][bench], bench, tiers) for bench in BENCHES}
            res[name][b] = scores(rows, "PEINN")
        log(f"  {name}: " + json.dumps({b: (r['ucr'], r['orr']) for b, r in res[name].items()}))
    bs = C.jload(D.odir(check) / "benches" / "bench_stats.json")
    ref = {}
    for s in ("Vanilla", "NeMo", "LlamaGuard", "A8", "R2D2"):
        for b in ORDER:
            v = bs.get(b, {}).get(s)
            if v:
                ref.setdefault(s, {})[b] = {"ucr": v["ucr_composite"], "orr": v["xstest"]["orr"]["mean"],
                                            "ethics": v["ethics"]["composite"]["mean"], "morables": v["morables"]["clean"]["mean"]}
    out = {"main": MAIN, "energy_only": {c: {k: v for k, v in r.items() if k != "routes"} for c, r in a9.items()},
           "variants": res, "defences": ref}
    out["matched"] = matched(out)
    C.jdump(out, o / "ablation.json")
    table(out, o)
    curves(out, caps, o)
    return 0


def _mean(d: dict, k: str) -> float:
    return float(np.mean([d[b][k] for b in ORDER if b in d and d[b].get(k) is not None]))


def matched(out: dict) -> dict:
    """Per variant with operating points: the lowest mean UCR over its caps whose mean ORR is at most the reference's
    ORR at the main cap (PEINN for the encoder and routing variants, A0ft for the fine-tuned component variants, A0 for the
    frozen ones)."""
    cap = f"{TH.MAIN_CAP:g}"
    pts = {}
    for k, r in out["variants"].items():
        if "@" in k:
            v, c = k.split("@")
            pts.setdefault(v, []).append((c, _mean(r, "ucr"), _mean(r, "orr")))
    res = {}
    for v, p in pts.items():
        ref = "A0" if v in FROZEN_COMP else "A0ft" if v in FT_COMP else "A0ftM"
        lim = _mean(out["variants"][f"{ref}@{cap}"], "orr")
        ok = [x for x in p if round(x[2], 6) <= round(lim, 6)]
        if ok:
            c, u, r_ = min(ok, key=lambda x: (round(x[1], 6), round(x[2], 6)))
            res[v] = {"reference": ref, "reference_orr": round(lim, 6), "cap": c, "ucr": round(u, 6), "orr": round(r_, 6)}
    return res


def table(out: dict, o) -> None:
    """Mean over the four bases at the main cap; A8 is qwen2.5-7B only, so it is given with qwen's PEINN beside it."""
    cap = f"{TH.MAIN_CAP:g}"
    body = []
    for g in GROUPS:
        for v in g:
            key = v if v.startswith("A4") else f"{v}@{cap}"
            r = out["variants"].get(key)
            if not r:
                continue
            cells = [LABEL[v] if v == "A0ftM" else f"{LABEL[v]} ({v})"]
            cells += [f"{C.fx(_mean(r, k), 1)}" for k in ("ucr", "orr", "ethics", "morables")]
            mt = out["matched"].get(v)
            cells += ([C.fx(mt["ucr"], 1), C.fx(mt["orr"], 1), f"{100 * float(mt['cap']):g}"] if mt else ["---"] * 3)
            body.append(" & ".join(cells) + " \\\\")
        body.append("\\midrule")
    for s, lab in (("Vanilla", "Vanilla (no defense)"), ("NeMo", "NeMo Guardrails"), ("LlamaGuard", "Llama Guard 3")):
        r = out["defences"][s]
        body.append(" & ".join([lab] + [f"{C.fx(_mean(r, k), 1)}" for k in ("ucr", "orr", "ethics", "morables")] + ["---"] * 3) + " \\\\")
    (o / "tab_ablation.tex").write_text("\n".join(body) + "\n", encoding="utf-8")
    q = out["variants"][f"A0ftM@{cap}"]["qwen"]
    a8, van = out["defences"]["A8"]["qwen"], out["defences"]["Vanilla"]["qwen"]
    rows = [("Vanilla", van), ("PEINN", q), ("LoRA fine-tuning (A8)", a8)]
    (o / "tab_a8.tex").write_text("\n".join(" & ".join([lab] + [f"{C.fx(r[k], 1)}" for k in ("ucr", "orr", "ethics", "morables")]) + " \\\\"
                                            for lab, r in rows) + "\n", encoding="utf-8")


def curves(out: dict, caps, o) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    style = {"A0ftM": ("#009e73", "o", "-"), "A0": ("#666666", "s", "--"), "A1": ("#e69f00", "^", "-"),
             "A2": ("#56b4e9", "v", "-"), "A3": ("#cc79a7", "D", "-"), "A5": ("#d55e00", "x", "-"),
             "A6p": ("#0072b2", "<", "-."), "A6e": ("#999933", ">", "-."), "A7": ("#882255", "h", "-."),
             "A9": ("#000000", "+", ":")}
    for v, (col, mk, ls) in style.items():
        pts = [(_mean(out["variants"][f"{v}@{c:g}"], "orr"), _mean(out["variants"][f"{v}@{c:g}"], "ucr"))
               for c in caps if f"{v}@{c:g}" in out["variants"]]
        if pts:
            x, y = zip(*sorted(pts))
            ax.plot(x, y, ls, marker=mk, color=col, ms=3.5, lw=1, label=LABEL[v])
    for s, mk in (("Vanilla", "*"), ("NeMo", "P"), ("LlamaGuard", "X")):
        r = out["defences"][s]
        ax.scatter([_mean(r, "orr")], [_mean(r, "ucr")], marker=mk, s=60, color="black", zorder=3,
                   label={"LlamaGuard": "Llama Guard 3"}.get(s, s))
    m = out["variants"][MAIN]
    ax.scatter([_mean(m, "orr")], [_mean(m, "ucr")], s=90, facecolor="none", edgecolor="#009e73", lw=1.5, zorder=4)
    ax.set_xlabel("XSTest over-refusal rate, ORR (%)")
    ax.set_ylabel(r"Average attack success rate, ASR$_{\mathrm{avg}}$ (%)")
    ax.legend(fontsize=6.5, frameon=False, ncol=2)
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    fig.tight_layout()
    fig.savefig(o / "ablation_curves.png", dpi=300)
    plt.close(fig)
