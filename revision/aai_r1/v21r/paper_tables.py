"""Section 4 and Appendix A of the revised manuscript from the exported records (bench-export, ggb-rescore), in the
definitions of bench_stats (DESIGN.md 34). No model call; runs anywhere.

    python -m v21r paper-tables          -> results/paper/*.tex (table bodies), *.png (figures), numbers.json

Every number the Results prose quotes is in numbers.json, so the text can be checked against the records.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import bench_stats as BS
from . import common as C
from . import data as D

ORDER = ("zephyr", "qwen", "gemma4", "gemma3")
NAME = {"zephyr": "zephyr-7B", "qwen": "qwen2.5-7B", "gemma4": "gemma4-e4B", "gemma3": "gemma3-12B"}
MAIN = ("Vanilla", "R2D2", "NeMo", "PEINN")
FAMILY = {"Encoding_Obfuscation": "Encoding / obfuscation", "Goal_Conflicting": "Goal conflicting",
          "Payload_Splitting": "Payload splitting", "Impersonation": "Impersonation",
          "Privilege_Escalation": "Privilege escalation", "Cognitive_Overload": "Cognitive overload",
          "Data_Poisoning": "Data poisoning", "Persuasion": "Persuasion"}
XS_SAFE = [("homonyms", "T1\\ \\ Homonyms"), ("figurative_language", "T2\\ \\ Figurative language"),
           ("safe_targets", "T3\\ \\ Safe targets"), ("safe_contexts", "T4\\ \\ Safe contexts"),
           ("definitions", "T5\\ \\ Definitions"), ("real_group_nons_discr", "T6\\ \\ Real group, nons.\\ discr."),
           ("nons_group_real_discr", "T7\\ \\ Nons.\\ group, real discr."), ("historical_events", "T8\\ \\ Historical events"),
           ("privacy_public", "T9\\ \\ Privacy (public)"), ("privacy_fictional", "T10\\ Privacy (fictional)")]
XS_UNSAFE = [("contrast_homonyms", "C1\\ \\ Homonyms"), ("contrast_figurative_language", "C2\\ \\ Figurative language"),
             ("contrast_safe_targets", "C3\\ \\ Safe targets"), ("contrast_safe_contexts", "C4\\ \\ Safe contexts"),
             ("contrast_definitions", "C5\\ \\ Definitions"), ("contrast_discr", "C6/7 Discrimination"),
             ("contrast_historical_events", "C8\\ \\ Historical events"), ("contrast_privacy", "C9/10 Privacy")]
FOUND = ("care", "fairness", "loyalty", "authority", "sanctity")
TIERS = ("Hard-block", "Reasoned-Refusal", "Deliberation", "Soft-reasoning", "Direct-Answer")


def out_dir(check: bool):
    o = D.odir(check) / "paper"
    o.mkdir(parents=True, exist_ok=True)
    return o


def records(check: bool, bench: str) -> pd.DataFrame:
    parts = [BS.load(check, bench, b) for b in ORDER]
    parts = [p for p in parts if len(p)]
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def arms(systems=MAIN):
    """(base, system, arm id) in the paper's arm order."""
    return [(b, s, C.ARMS[b][s]) for b in ORDER for s in systems if s in C.ARMS[b]]


def label(b: str, s: str, arm: str) -> str:
    return f"{arm} {NAME[b]} / {'Llama Guard' if s == 'LlamaGuard' else s}"


def pm(x: dict | None, nd: int = 1) -> str:
    if not x or x.get("mean") is None:
        return "--"
    ci = x.get("ci95")
    return f"${C.fx(x['mean'], nd)} \\pm {{\\scriptstyle {C.fx(0.0 if ci is None else ci, nd)}}}$"


def stat(v, rep) -> dict:
    return BS._stat(pd.Series(v).astype(float).reset_index(drop=True), pd.Series(rep).reset_index(drop=True))


def rows_tex(lines: list[list[str]], group: list[str]) -> str:
    """Table body with a \\midrule between bases."""
    out, prev = [], None
    for g, cells in zip(group, lines):
        if prev is not None and g != prev:
            out.append("\\midrule")
        out.append(" & ".join(cells) + " \\\\")
        prev = g
    return "\n".join(out) + "\n"


# ---- HarmBench ---------------------------------------------------------------------------------------------

def harmbench(check: bool, o, num: dict) -> None:
    d = records(check, "harmbench")
    res = {}
    for b, s, arm in arms((*MAIN, "LlamaGuard")):
        g = d[(d.base == b) & (d.system == s)]
        if len(g):
            per = g.groupby("rep").asr_binary.mean() * 100
            res[arm] = {"base": b, "system": s, **stat(g.asr_binary, g.rep), "sd": round(float(per.std(ddof=1)), 6),
                        "median_run": round(float(per.median()), 6), "runs": per.round(2).tolist()}
    v = d[d.system == "Vanilla"]
    cat = (v.groupby(["semantic_category", "base"]).asr_binary.mean() * 100).unstack()
    num["harmbench"] = {"arms": res, "vanilla_by_category": {k: {"mean": round(float(r.mean()), 6), "sd_bases": round(float(r.std(ddof=1)), 6)}
                                                             for k, r in cat.iterrows()},
                        "items": int(d.behavior_id.nunique()), "runs": int(d.rep.nunique())}
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    for name, systems in (("harmbench_asr_boxplot.png", MAIN), ("appendix_harmbench_lg.png", (*MAIN, "LlamaGuard"))):
        keys = [a for b, s, a in arms(systems) if a in res]
        fig, ax = plt.subplots(1, 2 if name.startswith("harmbench") else 1, figsize=(11 if name.startswith("harmbench") else 7.5, 3.6),
                               gridspec_kw={"width_ratios": [1.6, 1]} if name.startswith("harmbench") else None)
        a0 = ax[0] if name.startswith("harmbench") else ax
        col = {"Vanilla": "#9e9e9e", "R2D2": "#e69f00", "NeMo": "#56b4e9", "PEINN": "#009e73", "LlamaGuard": "#cc79a7"}
        x = np.arange(len(keys))
        a0.bar(x, [res[k]["mean"] for k in keys], yerr=[res[k]["sd"] for k in keys], capsize=2,
               color=[col[res[k]["system"]] for k in keys], edgecolor="black", linewidth=0.4)
        a0.scatter(x, [res[k]["median_run"] for k in keys], s=10, color="white", edgecolor="black", linewidth=0.5, zorder=3)
        a0.set_xticks(x, [f"{k}\n{res[k]['system'].replace('LlamaGuard', 'LG')}" for k in keys], fontsize=6.5)
        a0.set_ylabel("ASR (%)")
        a0.set_title("(a) ASR per arm (bar: mean of runs; line: ±1 SD; dot: median run)", fontsize=8)
        for i, k in enumerate(keys):
            a0.text(i, res[k]["mean"] + res[k]["sd"] + 1.5, f"{C.fx(res[k]['mean'], 1)}", ha="center", fontsize=5.5)
        if name.startswith("harmbench"):
            c = cat.mean(axis=1).sort_values(ascending=False)
            ax[1].barh(np.arange(len(c)), c.values, color="#d9d9d9", edgecolor="black", linewidth=0.4)
            mk = {"zephyr": "o", "qwen": "s", "gemma4": "^", "gemma3": "D"}
            for bb in ORDER:
                if bb in cat:
                    ax[1].scatter(cat.loc[c.index, bb].values, np.arange(len(c)), marker=mk[bb], s=14, color="black",
                                  facecolor="white" if bb in ("qwen", "gemma3") else "black", label=NAME[bb], zorder=3)
            ax[1].legend(fontsize=6, loc="upper center", bbox_to_anchor=(0.45, -0.17), ncol=4, frameon=False)
            ax[1].set_xlim(0, 100)
            ax[1].set_yticks(np.arange(len(c)), [k.replace("_", " ") for k in c.index], fontsize=7)
            ax[1].invert_yaxis()
            ax[1].set_xlabel("Vanilla ASR (%)")
            ax[1].set_title("(b) Vanilla ASR by category (bar: mean of the 4 bases)", fontsize=8)
        fig.tight_layout()
        fig.savefig(o / name, dpi=300)
        plt.close(fig)


# ---- Taxonomy ------------------------------------------------------------------------------------------------

def taxonomy(check: bool, o, num: dict) -> None:
    d = records(check, "taxonomy")
    lines, grp, res = [], [], {}
    for b, s, arm in arms():
        g = d[(d.base == b) & (d.system == s)]
        if not len(g):
            continue
        u = g.is_unsafe.astype(float)
        st = stat(u, g.rep)
        sev = pd.to_numeric(g.judge_hsl[u == 1], errors="coerce")
        res[arm] = {"base": b, "system": s, "convs": int(len(g)), "succ": int(u.sum()), "asr": st,
                    "sev": None if sev.empty else round(float(sev.mean()), 6)}
        lines.append([label(b, s, arm), str(len(g)), str(int(u.sum())), pm(st), "---" if sev.empty else f"{C.fx(sev.mean(), 2)}"])
        grp.append(b)
    (o / "tab_taxonomy_arm.tex").write_text(rows_tex(lines, grp), encoding="utf-8")
    fam = {}
    for s in (*MAIN, "LlamaGuard"):
        g = d[d.system == s]
        fam[s] = {f: round(float(x.is_unsafe.mean() * 100), 6) for f, x in g.groupby("taxonomy_family")}
        fam[s]["overall"] = round(float(g.is_unsafe.mean() * 100), 6)
        fam[s]["n_per_family"] = int(g.groupby("taxonomy_family").size().iloc[0]) if len(g) else 0
    order = sorted(FAMILY, key=lambda f: -fam["Vanilla"].get(f, 0))
    for name, systems in (("tab_taxonomy_family.tex", MAIN), ("tab_appA_taxonomy.tex", (*MAIN, "LlamaGuard"))):
        body = [" & ".join([FAMILY[f]] + [f"{C.fx(fam[s].get(f, 0), 1)}" for s in systems]) + " \\\\" for f in order]
        body += ["\\midrule", " & ".join(["\\textbf{Overall}"] + [f"\\textbf{{{C.fx(fam[s]['overall'], 1)}}}" for s in systems]) + " \\\\"]
        (o / name).write_text("\n".join(body) + "\n", encoding="utf-8")
    hb = d[d.system == "PEINN"]
    num["taxonomy"] = {"arms": res, "family": fam, "family_order": order,
                       "pooled": {s: fam[s]["overall"] for s in fam},
                       "peinn_tiers_first_turn": hb.tier.value_counts().to_dict(),
                       "peinn_hard_block_share": round(float((hb.tier == "Hard-block").mean() * 100), 6)}


# ---- XSTest ---------------------------------------------------------------------------------------------------

def xstest(check: bool, o, num: dict) -> None:
    d = records(check, "xstest")
    lines, grp, res = [], [], {}
    for b, s, arm in arms():
        g = d[(d.base == b) & (d.system == s)]
        if not len(g):
            continue
        st = BS.system_stats("xstest", g)
        res[arm] = {"base": b, "system": s, **st}
        lines.append([label(b, s, arm), pm(st["orr"]), pm(st["ucr"])])
        grp.append(b)
    (o / "tab_xstest_arm.tex").write_text(rows_tex(lines, grp), encoding="utf-8")
    p, v = d[d.system == "PEINN"], d[d.system == "Vanilla"]
    one = p[p.base == "qwen"]                                   # routes are the same on every base (input-only gate)
    same = all((p[p.base == b].sort_values(["item_id", "rep"]).tier.to_numpy()
                == one.sort_values(["item_id", "rep"]).tier.to_numpy()).all() for b in ORDER if (p.base == b).any())
    body, per = [], {}

    def row(key, lab, err):
        t = one[one.prompt_type == key]
        n = int(len(t))
        sh = {k: float((t.tier == k).mean() * 100) for k in TIERS}
        ev = float(v[v.prompt_type == key][err].mean() * 100)
        ep = float(p[p.prompt_type == key][err].mean() * 100)
        per[key] = {"n": n, "routes": {k: round(x, 6) for k, x in sh.items()}, "vanilla": round(ev, 6), "peinn": round(ep, 6)}
        refuse = sh["Hard-block"] + sh["Reasoned-Refusal"]
        two = sh["Deliberation"] + sh["Soft-reasoning"]
        return f"{lab} & {n} & {C.fx(refuse, 1)} & {C.fx(two, 1)} & {C.fx(sh['Direct-Answer'], 1)} & {C.fx(ev, 1)} & {C.fx(ep, 1)} \\\\"

    body.append("\\multicolumn{7}{l}{\\textit{Safe types: error rate is over-refusal (ORR)}}\\\\")
    body += [row(k, lab, "over_refusal") for k, lab in XS_SAFE if (one.prompt_type == k).any()]
    sa, ua = one[one.expected_label == "safe"], one[one.expected_label == "unsafe"]

    def tot(t, err, lab, exp):
        sh = {k: float((t.tier == k).mean() * 100) for k in TIERS}
        ev = float(v[v.expected_label == exp][err].mean() * 100)
        ep = float(p[p.expected_label == exp][err].mean() * 100)
        per[exp + "_overall"] = {"n": int(len(t)), "distinct_items": int(t.item_id.nunique()), "routes": {k: round(x, 6) for k, x in sh.items()},
                                 "vanilla": round(ev, 6), "peinn": round(ep, 6)}
        return (f"\\textbf{{{lab}}} & \\textbf{{{len(t)}}} & {C.fx(sh['Hard-block'] + sh['Reasoned-Refusal'], 1)} & "
                f"{C.fx(sh['Deliberation'] + sh['Soft-reasoning'], 1)} & {C.fx(sh['Direct-Answer'], 1)} & \\textbf{{{C.fx(ev, 1)}}} & \\textbf{{{C.fx(ep, 1)}}} \\\\")
    body.append(tot(sa, "over_refusal", "Safe overall", "safe"))
    body += ["\\midrule", "\\multicolumn{7}{l}{\\textit{Unsafe contrast types: error rate is unsafe compliance (UCR)}}\\\\"]
    body += [row(k, lab, "unsafe_compliance") for k, lab in XS_UNSAFE if (one.prompt_type == k).any()]
    body.append(tot(ua, "unsafe_compliance", "Unsafe overall", "unsafe"))
    (o / "tab_xstest_type.tex").write_text("\n".join(body) + "\n", encoding="utf-8")
    num["xstest"] = {"arms": res, "types": per, "routes_same_on_every_base": bool(same),
                     "prompts": {"safe": int(len(sa)), "unsafe": int(len(ua))}, "distinct_items": {"safe": int(sa.item_id.nunique()), "unsafe": int(ua.item_id.nunique())}, "runs": int(d.rep.nunique()),
                     "pooled": {s: {"orr": round(float(d[(d.system == s) & (d.expected_label == "safe")].over_refusal.mean() * 100), 6),
                                    "ucr": round(float(d[(d.system == s) & (d.expected_label == "unsafe")].unsafe_compliance.mean() * 100), 6)}
                                for s in (*MAIN, "LlamaGuard")}}


# ---- Ethics ---------------------------------------------------------------------------------------------------

def ethics(check: bool, o, num: dict) -> None:
    d = records(check, "ethics")
    lines, grp, flines, res = [], [], [], {}
    for b, s, arm in arms():
        g = d[(d.base == b) & (d.system == s)]
        if not len(g):
            continue
        st = BS.system_stats("ethics", g)
        m = g[g.instrument == "MFQ"]
        fd = {f: stat(1 - m.mfa_err[m.item_id.str.startswith(f)], m.rep[m.item_id.str.startswith(f)]) for f in FOUND}
        res[arm] = {"base": b, "system": s, **{k: st[k] for k in ("mfa", "wvs", "rqi", "composite", "unrated_mfq", "unrated_wvs")},
                    "foundations": fd, "rqi_raw_mean": round(float(((g[g.instrument == "Dilemma"].rqi_fixed)).mean()), 3)}
        lines.append([label(b, s, arm), pm(st["mfa"]), pm(st["wvs"]), pm(st["rqi"]), pm(st["composite"])])
        flines.append([label(b, s, arm)] + [pm(fd[f]) for f in FOUND])
        grp.append(b)
    (o / "tab_ethics_overall.tex").write_text(rows_tex(lines, grp), encoding="utf-8")
    (o / "tab_ethics_foundations.tex").write_text(rows_tex(flines, grp), encoding="utf-8")
    num["ethics"] = {"arms": res}


# ---- MORABLES ---------------------------------------------------------------------------------------------------

def morables(check: bool, o, num: dict) -> None:
    d = records(check, "morables")
    lines, grp, res = [], [], {}
    for b, s, arm in arms():
        g = d[(d.base == b) & (d.system == s)]
        if not len(g):
            continue
        st = BS.system_stats("morables", g)
        res[arm] = {"base": b, "system": s, **st}
        gap = "--" if st["gap"] is None else f"${C.fx(st['gap'], 1, True)}$"
        lines.append([label(b, s, arm), pm(st["clean"]), pm(st["perturbed"]), gap])
        grp.append(b)
    (o / "tab_morables.tex").write_text(rows_tex(lines, grp), encoding="utf-8")
    num["morables"] = {"arms": res}


# ---- GGB ---------------------------------------------------------------------------------------------------------

def ggb(check: bool, o, num: dict) -> None:
    """IH and IB over the items a system answered, with Vanilla on the same items and a Welch test against it
    (DESIGN.md 32: PEINN hard-blocks some IH items, so a mean over all items would compare different items)."""
    from scipy import stats as SS
    d = pd.read_csv(D.odir(check) / "ggb" / "ggb_rescored.csv", low_memory=False)
    d["rescored"] = pd.to_numeric(d.rescored, errors="coerce")
    lines, grp, res = [], [], {}
    for b, s, arm in arms((*MAIN, "LlamaGuard", "A8")):
        g = d[(d.base == b) & (d.system == s)]
        if not len(g):
            continue
        van = d[(d.base == b) & (d.system == "Vanilla")]
        cells, r = [label(b, s, arm)], {"base": b, "system": s}
        for sub in ("instrumental_harm", "impartial_beneficence"):
            gs = g[g.subscale == sub]
            x = gs.rescored.dropna()
            items = sorted(set(gs[gs.rescored.notna()].item_id))
            vv = van[(van.subscale == sub) & van.item_id.isin(items)].rescored.dropna()
            rr = {"mean": None if x.empty else round(float(x.mean()), 6), "n": int(len(x)), "items": items,
                  "answered_items": len(items), "items_total": int(gs.item_id.nunique()),
                  "vanilla_same_items": None if vv.empty else round(float(vv.mean()), 6)}
            if s != "Vanilla" and len(x) > 1 and len(vv) > 1 and (x.std() > 0 or vv.std() > 0):
                rr["p_welch"] = float(SS.ttest_ind(x, vv, equal_var=False).pvalue)
            r[sub] = rr
            if x.empty:
                cells += ["--", "--", "--"]
            else:
                cells.append(f"{rr['answered_items']}/{rr['items_total']}")
                cells.append(f"{C.fx(rr['mean'], 2)}" + ("" if s == "Vanilla" else f" ({C.fx(rr['vanilla_same_items'], 2)})"))
                cells.append("(ref)" if s == "Vanilla" else ("--" if "p_welch" not in rr else
                             ("$<$0.001" if rr["p_welch"] < 0.001 else f"{C.fx(rr['p_welch'], 3)}")))
        res[arm] = r
        if s in MAIN:
            lines.append(cells)
            grp.append(b)
    (o / "tab_ggb.tex").write_text(rows_tex(lines, grp), encoding="utf-8")
    num["ggb"] = {"arms": res}


# ---- Appendix A (Llama Guard) -------------------------------------------------------------------------------------

def appendix_a(check: bool, o, num: dict) -> None:
    S = (*MAIN, "LlamaGuard")
    x, e, m, g = (records(check, k) for k in ("xstest", "ethics", "morables", "harmbench"))
    gg = num["ggb"]["arms"]
    xs, et, mo, gb = [], [], [], []
    for b in ORDER:
        cx, ce, cm, cg = [NAME[b]], [NAME[b]], [NAME[b]], [NAME[b]]
        for s in S:
            arm = C.ARMS[b].get(s)
            if not arm:
                cx += ["--", "--"]
                ce += ["--"] * 3
                cm.append("--")
                cg += ["--", "--"]
                continue
            st = BS.system_stats("xstest", x[(x.base == b) & (x.system == s)])
            cx += [f"{C.fx(st['orr']['mean'], 1)}", f"{C.fx(st['ucr']['mean'], 1)}"]
            se = BS.system_stats("ethics", e[(e.base == b) & (e.system == s)])
            ce += [f"{C.fx(se[k]['mean'], 1)}" for k in ("mfa", "wvs", "rqi")]
            sm = BS.system_stats("morables", m[(m.base == b) & (m.system == s)])
            cm.append(f"{C.fx(sm['clean']['mean'], 1)}")
            a = gg.get(arm) or {}
            cg += [("--" if (a.get(k) or {}).get("mean") is None else f"{C.fx(a[k]['mean'], 2)}")
                   for k in ("instrumental_harm", "impartial_beneficence")]
        for lst, c in ((xs, cx), (et, ce), (mo, cm), (gb, cg)):
            lst.append(" & ".join(c) + " \\\\")
    for name, body in (("tab_appA_xstest.tex", xs), ("tab_appA_ethics.tex", et), ("tab_appA_morables.tex", mo), ("tab_appA_ggb.tex", gb)):
        (o / name).write_text("\n".join(body) + "\n", encoding="utf-8")


def paper_tables(check: bool = False, log=print) -> int:
    o = out_dir(check)
    num: dict = {}
    for f in (harmbench, taxonomy, xstest, ethics, morables, ggb, appendix_a):
        f(check, o, num)
        log(f"  {f.__name__}: done")
    C.jdump(num, o / "numbers.json")
    return 0
