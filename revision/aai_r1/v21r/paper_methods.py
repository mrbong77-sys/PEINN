"""Section 3 numbers and Figures 2-4 of the revised manuscript for the main variant, from the exported rows
. No model call; runs anywhere.

    python -m v21r paper-methods        -> results/paper/methods.json, fig3_routing.png, fig4_energy_signals.png,
                                            fig5_signal_distribution.png

  test        AUROC of T, I and F on the test split against the teacher's labels (label >= 0.5), and the rank
              correlations between the three outputs (analysis.json calibration gives the same correlations).
  routes      share of bench units (item x run) routed to each tier, per benchmark; routes do not depend on the base
              model, so the units are those of qwen.
  harmbench   energy of HarmBench units: mean, SD, share at or above the harm gate and at or above the extreme gate.
  signals     mean T, I, F and E of the units of each benchmark.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import common as C
from . import data as D
from . import theta as TH

BENCH_ORDER = (("harmbench", "HarmBench"), ("taxonomy", "Taxonomy"), ("xstest", "XSTest"), ("ggb", "GGB"),
               ("ethics", "Ethics"), ("morables", "MORABLES"))
TIERS = ("Hard-block", "Reasoned-Refusal", "Deliberation", "Soft-reasoning", "Direct-Answer")
LABEL = {"Hard-block": "Hard-block", "Reasoned-Refusal": "Reasoned-refusal", "Deliberation": "Deliberation",
         "Soft-reasoning": "Soft-reasoning", "Direct-Answer": "Direct-answer"}
COLOR = {"Hard-block": "#d1495b", "Reasoned-Refusal": "#e8893a", "Deliberation": "#4a90d9",
         "Soft-reasoning": "#f2c14e", "Direct-Answer": "#5cb85c"}
UNIT_BASE = "qwen"


def _auroc(p, y) -> float | None:
    """Mann-Whitney form (ties count one half)."""
    y = np.asarray(y)
    n1 = int(y.sum())
    if not 0 < n1 < len(y):
        return None
    r = pd.Series(np.asarray(p, dtype=float)).rank().to_numpy()
    return round(float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * (len(y) - n1))), 4)


def units(check: bool, sig: pd.DataFrame, route: pd.Series) -> pd.DataFrame:
    """One row per bench unit (item x run) with its routing text's signals and route."""
    f = D.odir(check) / "forced"
    s = sig[sig.part == "bench"].drop_duplicates("sha").set_index("sha")
    out = []
    for b, name in BENCH_ORDER:
        p = f / f"{b}_{UNIT_BASE}.csv.gz"
        if not p.exists():
            continue
        d = pd.read_csv(p, low_memory=False, dtype={"sha": str})
        d = d[d.tier == "Direct-Answer"]
        u = pd.DataFrame({"bench": name, "sha": d.sha.to_numpy(),
                          "instrument": d["instrument"].to_numpy() if "instrument" in d else None})
        u = u.join(s[["T", "I", "F", "E"]], on="sha")
        u["route"] = u.sha.map(route)
        out.append(u)
    return pd.concat(out, ignore_index=True)


def paper_methods(check: bool = False, log=print) -> int:
    o = D.odir(check) / "paper"
    o.mkdir(parents=True, exist_ok=True)
    f = D.odir(check) / "forced"
    v, cap = TH.MAIN_VARIANT, f"{TH.MAIN_CAP:g}"
    th = C.jload(D.odir(check) / "thresholds.json")["variants"][v][cap]["th"]
    sig = pd.read_csv(f / f"signals_{v}.csv.gz", dtype={"sha": str})
    lab = pd.read_csv(f / "split_labels.csv.gz", dtype={"sha": str})
    te = lab[lab.split == "test"]
    st = sig[sig.part == "test"].drop_duplicates("sha").set_index("sha").loc[te.sha]
    test = {"n": int(len(te))}
    for k in ("T", "I", "F"):
        y = (te[k].to_numpy(dtype=float) >= 0.5).astype(int)
        test[k] = {"auroc": _auroc(st[k].to_numpy(dtype=float), y), "n_pos": int(y.sum())}
    test["spearman"] = {a + "-" + b: round(float(st[a].rank().corr(st[b].rank())), 4)
                        for a, b in (("T", "I"), ("T", "F"), ("I", "F"))}
    rt = pd.read_csv(f / "routes.csv.gz", dtype={"sha": str}).set_index("sha")[f"{v}@{cap}"]
    u = units(check, sig, rt)
    routes = {}
    for name, g in u.groupby("bench", sort=False):
        routes[name] = {"units": int(len(g)), "texts": int(g.sha.nunique()),
                        **{t: round(100 * float((g.route == t).mean()), 6) for t in TIERS}}
    hb = u[u.bench == "HarmBench"].E.to_numpy(dtype=float)
    harm = {"units": int(len(hb)), "mean": round(float(hb.mean()), 6), "sd": round(float(hb.std(ddof=1)), 6),
            "at_or_above_harm": round(100 * float((hb >= th["harm"]).mean()), 6),
            "at_or_above_extreme": round(100 * float((hb >= th["extreme"]).mean()), 6)}
    sigm = {name: {k: round(float(g[k].mean()), 3) for k in ("T", "I", "F", "E")} for name, g in u.groupby("bench", sort=False)}
    out = {"variant": v, "cap": cap, "th": th, "test": test, "routes": routes, "harmbench_energy": harm,
           "signal_means": sigm, "unit_base": UNIT_BASE}
    C.jdump(out, o / "methods.json")
    log(f"  test {test}\n  routes {routes}\n  harmbench {harm}")
    figures(u, th, harm, o)
    calibration(check, o)
    route_cost(check, o)
    return 0


def _r3(x: float) -> str:
    """Three decimals, half up (the stored values have four)."""
    from decimal import ROUND_HALF_UP, Decimal
    return str(Decimal(str(x)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def calibration(check: bool, o) -> None:
    """ECE and Brier of the main variant's T, I, F on the test split, and F against XSTest's human labels
    (analysis.json); ten-bin reliability diagrams."""
    a = C.jload(D.odir(check) / "analysis" / "analysis.json")
    c, x = a["calibration"][TH.MAIN_VARIANT], a["xstest_F"][TH.MAIN_VARIANT]
    rows = [(f"${k}$", "test split, reference label", c[k]["binary"]) for k in ("T", "I", "F")]
    rows.append(("$F$", "XSTest, human label", x))
    (o / "tab_calibration.tex").write_text("\n".join(f"{a_} & {b} & {r['n']:,} & {_r3(r['ece'])} & {_r3(r['brier'])} \\\\".replace(f"{r['n']:,}", f"{r['n']:,}".replace(",", "{,}"))
                                                     for a_, b, r in rows) + "\n", encoding="utf-8")
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 4, figsize=(12, 3.1))
    for ax, (lab, src, r) in zip(axes, rows):
        rel = r.get("reliability") or []
        ax.plot([0, 1], [0, 1], color="#999", lw=0.8, ls="--")
        ax.plot([q["conf"] for q in rel], [q["acc"] for q in rel], marker="o", ms=3.5, color="#009e73", lw=1)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.set_xlabel(f"Predicted {lab}")
        ax.set_title(f"{lab}, {src} (ECE {_r3(r["ece"])})", fontsize=8.5)
    axes[0].set_ylabel("Observed share of positives")
    fig.tight_layout()
    fig.savefig(o / "calibration.png", dpi=300, bbox_inches="tight")
    plt.close(fig)


def route_cost(check: bool, o) -> None:
    """Generation calls, input and output tokens and Ollama generation seconds per request for each route and base, as
    a deployment needs them: a Hard-block calls nothing, and a two-pass route only its second call. The
    harness's first call of a two-pass route is the bare call of Direct-answer (same request and seed; the Hard-block
    harness figures equal Direct-answer's), so the second call is the route's harness figure minus Direct-answer's."""
    t = C.jload(D.odir(check) / "route_cost.json")["tiers"]
    bases = ("zephyr", "qwen", "gemma4", "gemma3")
    keys = ("calls", "prompt_tokens", "output_tokens", "ollama_s")

    def deployed(b, tier):
        h, da = t[f"{b}|{tier}"]["harness"], t[f"{b}|Direct-Answer"]["harness"]
        if tier == "Hard-block":
            return {k: 0 for k in keys}
        if tier == "Direct-Answer":
            return {k: h[k] for k in keys}
        return {k: h[k] - da[k] for k in keys}

    body = []
    for tier in TIERS:
        r = [deployed(b, tier) for b in bases]
        calls = {int(x["calls"]) for x in r}
        cells = [LABEL[tier], "/".join(str(c) for c in sorted(calls))]
        cells += [f"{C.fx(x['prompt_tokens'] + x['output_tokens'], 1)}" for x in r] + [f"{C.fx(x['ollama_s'], 2)}" for x in r]
        body.append(" & ".join(cells) + " \\\\")
    (o / "tab_route_cost.tex").write_text("\n".join(body) + "\n", encoding="utf-8")


def figures(u: pd.DataFrame, th: dict, harm: dict, o) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LinearSegmentedColormap
    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#444"})
    order = [n for _, n in BENCH_ORDER if n in set(u.bench)]

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 4.3), gridspec_kw={"width_ratios": [1.25, 1.0]})
    y = np.arange(len(order))
    left = np.zeros(len(order))
    for t in TIERS:
        vals = np.array([100 * (u[u.bench == n].route == t).mean() for n in order])
        a.barh(y, vals, left=left, color=COLOR[t], edgecolor="white", linewidth=0.4, label=LABEL[t])
        left += vals
    a.set_yticks(y)
    a.set_yticklabels(order)
    a.invert_yaxis()
    a.set_xlabel("Share of items routed (%)")
    a.set_xlim(0, 100)
    a.set_title("(a) Route per benchmark", fontsize=9.5)
    a.legend(ncol=3, fontsize=6.6, loc="upper center", bbox_to_anchor=(0.5, -0.13), frameon=False)
    pts = u.drop_duplicates(["bench", "sha"])
    for t in TIERS:
        d = pts[pts.route == t]
        b.scatter(d.E, d.F, s=6, alpha=0.45, color=COLOR[t], linewidths=0, label=LABEL[t])
    for x, ls, lab in ((th["harm"], "--", r"$\tau_{\mathrm{harm}}$"), (th["extreme"], ":", r"$\tau_{\mathrm{ext}}$")):
        b.axvline(x, color="#555", ls=ls, lw=0.8)
        b.text(x, 1.02, lab, fontsize=6.5, ha="center")
    for yv, ls, lab in ((th["F"], ":", r"$\tau_F$"), (th["Fref"], "--", r"$\tau_{F\mathrm{ref}}$")):
        b.axhline(yv, color="#555", ls=ls, lw=0.8)
        b.text(10.05, yv, lab, fontsize=6.5, va="center")
    b.set_xlabel("Energy $E$")
    b.set_ylabel("Falsity $F$")
    b.set_xlim(0, 10)
    b.set_ylim(0, 1.06)
    b.set_title(f"(b) $F$ against $E$ for the {len(pts):,} routing texts", fontsize=9.5)
    fig.tight_layout()
    fig.savefig(o / "fig3_routing.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    fig, (a, b) = plt.subplots(1, 2, figsize=(12, 3.9), gridspec_kw={"width_ratios": [1.0, 1.35]})
    e = u[u.bench == "HarmBench"].E.dropna()
    a.hist(e, bins=40, range=(0, 10), color="#2BA84A", alpha=0.85, edgecolor="white", linewidth=0.3)
    a.axvline(th["harm"], color="#d1495b", ls="--", lw=1.2, label=rf"$\tau_{{\mathrm{{harm}}}}={th['harm']:g}$")
    a.axvline(th["extreme"], color="#7d1128", ls=":", lw=1.2, label=rf"$\tau_{{\mathrm{{ext}}}}={th['extreme']:g}$")
    a.set_xlabel("Energy $E$")
    a.set_ylabel("Items")
    a.set_xlim(0, 10)
    a.set_title(f"(a) HarmBench energy ($\\mu={C.fx(harm['mean'], 2)}$, $\\sigma={C.fx(harm['sd'], 2)}$)", fontsize=9.5)
    a.legend(fontsize=7, frameon=False, loc="upper left")
    rows = ["$T$", "$I$", "$F$", "$E$"]
    raw = np.array([[u[u.bench == n][k].mean() for n in order] for k in ("T", "I", "F", "E")])
    M = raw.copy()
    M[3] = M[3] / 10.0
    wp = LinearSegmentedColormap.from_list("whitepink", ["#ffffff", "#fde0ec", "#f7a8c4", "#e75a8f", "#b3144f"])
    im = b.imshow(M, cmap=wp, vmin=0, vmax=1, aspect="auto")
    b.set_xticks(range(len(order)))
    b.set_xticklabels(order, rotation=30, ha="right", fontsize=8)
    b.set_yticks(range(4))
    b.set_yticklabels(rows, fontsize=11)
    for i in range(4):
        for j in range(len(order)):
            b.text(j, i, f"{C.fx(raw[i, j], 2)}" if i < 3 else f"{C.fx(raw[i, j], 1)}", ha="center", va="center", fontsize=7.5,
                   color="white" if M[i, j] > 0.6 else "#333333")
    b.set_title("(b) Mean signals per benchmark ($T,I,F\\in[0,1]$; $E\\in[0,10]$)", fontsize=9.5)
    cb = fig.colorbar(im, ax=b, fraction=0.046, pad=0.03)
    cb.ax.tick_params(labelsize=6)
    fig.tight_layout()
    fig.savefig(o / "fig4_energy_signals.png", dpi=300, bbox_inches="tight")
    plt.close(fig)

    harmful = u[u.bench == "HarmBench"]
    dil = u[(u.bench == "Ethics") & (u.instrument == "Dilemma")]
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.1))
    for ax, (k, lab, rng) in zip(axes, (("T", "Truth $T$", (0, 1)), ("I", "Indeterminacy $I$", (0, 1)),
                                         ("F", "Falsity $F$", (0, 1)), ("E", "Energy $E$", (0, 10)))):
        ax.hist(harmful[k].dropna(), bins=30, range=rng, density=True, color="#d1495b", alpha=0.6,
                label=f"HarmBench (n={len(harmful)})")
        ax.hist(dil[k].dropna(), bins=30, range=rng, density=True, color="#4a90d9", alpha=0.6,
                label=f"Ethics dilemmas (n={len(dil)})")
        ax.set_xlabel(lab)
        ax.set_yticks([])
        ax.set_xlim(*rng)
    axes[0].set_ylabel("Density")
    axes[0].legend(fontsize=7, frameon=False, loc="upper center")
    fig.tight_layout()
    fig.savefig(o / "fig5_signal_distribution.png", dpi=300, bbox_inches="tight")
    plt.close(fig)
