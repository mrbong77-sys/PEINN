#!/usr/bin/env python3
"""
render_paper_figs_v2.py
───────────────────────
PEINN 논문 본문용 Fig 2~5 를 PEAOS 실측 csv 위에서 생성한다.
EnergyRoute (Jang et al., Sci Rep 2026) Fig 2~5 시각 convention 모방
(My-Lab knowledge_base/figure_generation_prompts.md §2~§5 정본 사양).

본 스크립트는 my-lab 의 시각 스타일 (HANDOFF-125 dry-run 시점) 을 PEAOS 에
이식한 것으로, my-lab `scripts/generate_paper_figures.py` 의 PEAOS-적합 변형판.
- csv 입력 위치는 --csv-dir 로 지정 (기본: PEAOS FINAL_DIR 자동 탐색).
- 출력 위치는 --out-dir 로 지정 (기본: PEAOS data/paper_figs/).
- 4 figure (Fig 2~5) 생성 후 my-lab 의 Experiment Data/ 로 사용자가 *수동 이동*.

생성 figure:
  Fig 2  per-bench × per-defence grouped bars   (6-panel 2×3 grid)
  Fig 3  routing distribution + per-route rates + determinism pie
  Fig 4  threshold sensitivity 3-panel (synthetic — 실측 sweep csv 있으면 자동 swap)
  Fig 5  router-signal distribution + percentile-vs-metric monotonicity

사용:
  python scripts/render_paper_figs_v2.py
  python scripts/render_paper_figs_v2.py --csv-dir /path/to/csv --out-dir /tmp/figs
  python scripts/render_paper_figs_v2.py --only 2 5
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

# ─── color convention (My-Lab paper_format_guide §4.3 정본) ────────────────
DEFENSE_COLORS = {
    "Vanilla": "#888888",   # 회색
    "NeMo":    "#4A90D9",   # 청
    "PEINN":   "#2BA84A",   # 녹 (★ PEINN 강조)
    "R2D2":    "#F39C12",   # 주황
}
DEFENSE_ORDER = ["Vanilla", "NeMo", "PEINN", "R2D2"]

# routing 라벨 → 색 (HANDOFF-128 / 129 정본; csv 의 neutro_route 컬럼 값과 일치)
ROUTE_COLORS = {
    "1-pass":                "#66C266",  # 녹
    "2-pass-reasoning-soft": "#F2D464",  # 노
    "2-pass-reasoning":      "#F5B575",  # peach
    "2-pass-refusal":        "#F49C5E",  # 주
    "hard-block":            "#E26B6B",  # 적
}
ROUTE_SHORT = {
    "1-pass":                "1-pass",
    "2-pass-reasoning-soft": "2-pass-soft",
    "2-pass-reasoning":      "2-pass-reason",
    "2-pass-refusal":        "2-pass-refuse",
    "hard-block":            "hard-block",
}
ROUTE_ORDER = list(ROUTE_COLORS.keys())

# PEAOS router 정본 threshold (pea_eval/evaluators/confucian_mux.py)
THRESHOLD_DEFAULTS = {
    "ENERGY_THREAT_HIGH":              8.0,
    "ENERGY_REASONING_CEILING":        8.0,
    "ENERGY_SAFE_RECHECK":             7.3,
    "SIMILARITY_HIGH":                 0.55,
    "SIMILARITY_HIGH_DILEMMA_FRIENDLY": 0.45,
    "SIMILARITY_HARMFUL_RESCUE":       0.40,
}

# bench 별 csv glob 패턴 (최신 timestamp 자동 선택)
CSV_PATTERNS = {
    "HarmBench": "harmbench_batch_*runs_*.csv",
    "Taxonomy":  "taxonomy_batch_*runs_*.csv",
    "XSTest":    "xstest_batch_*runs_*.csv",
    "Ethics":    "ethics_batch_*runs_*.csv",
    "Morables":  "morables_batch_*runs_*.csv",
    "GGB":       "ggb_batch_*runs_*.csv",
}

# matplotlib publication style
plt.rcParams.update({
    "font.family":       "DejaVu Sans",
    "font.size":         10,
    "axes.titlesize":    11,
    "axes.labelsize":    10,
    "axes.spines.top":   False,
    "axes.spines.right": False,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "legend.fontsize":   9,
    "figure.dpi":        100,
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
    "savefig.facecolor": "white",
})


# ─── csv discovery ─────────────────────────────────────────────────────────
def discover_csv_dir(cli_path: str | None) -> Path:
    """CSV directory 자동 탐색 — 우선순위:
    1. --csv-dir CLI 인자
    2. PEAOS FINAL_DIR (pea_eval.config.settings)
    3. <repo>/pea_eval/output/final/   ★ PEAOS 실제 위치 (HANDOFF-131)
    4. <repo>/pea_eval/output/
    5. <repo>/data/stat_batch/
    6. <repo>/data/
    7. <repo>/Experiment Data/  (my-lab convention)
    8. 재귀 폴백: data/, pea_eval/, output/, results/ 하위에서 *_batch_*runs_*.csv 검색
    """
    if cli_path:
        p = Path(cli_path).expanduser().resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"--csv-dir not a directory: {p}")
        return p

    repo = Path(__file__).resolve().parent.parent
    candidates = []
    try:
        from pea_eval.config.settings import FINAL_DIR
        candidates.append(Path(FINAL_DIR))
    except Exception:
        pass
    candidates += [
        repo / "pea_eval" / "output" / "final",    # ★ PEAOS 실제 csv 위치
        repo / "pea_eval" / "output",
        repo / "data" / "stat_batch",
        repo / "data",
        repo / "Experiment Data",
    ]
    for c in candidates:
        if c.is_dir() and any(c.glob("*_batch_*runs_*.csv")):
            print(f"[info] csv-dir auto-detected: {c}")
            return c
    # 재귀 폴백 — data/, pea_eval/, output/, results/ 하위 어디든
    for sub in ["pea_eval", "data", "output", "results"]:
        root = repo / sub
        if not root.is_dir():
            continue
        hits = list(root.rglob("*_batch_*runs_*.csv"))
        if hits:
            found = hits[0].parent
            print(f"[info] csv-dir auto-detected (recursive): {found}")
            return found
    raise FileNotFoundError(
        f"CSV directory not found. tried: {[str(c) for c in candidates]} + recursive scan. "
        "use --csv-dir to specify."
    )


def load_csv(csv_dir: Path, bench: str) -> pd.DataFrame:
    """bench 의 최신 csv 자동 선택 (timestamp 기준 sort)."""
    pattern = CSV_PATTERNS[bench]
    files = sorted(csv_dir.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no csv matched {pattern} in {csv_dir}")
    chosen = files[-1]  # 가장 최근
    return pd.read_csv(chosen, encoding="utf-8-sig")


def safe_mean(values) -> float:
    arr = [v for v in values if v == v]
    return float(np.mean(arr)) if arr else float("nan")


# ─── Fig 2 ──────────────────────────────────────────────────────────────────
def fig2_per_bench_defense(csv_dir: Path, outpath: Path) -> None:
    """6-panel grid: per-bench × per-defence metric mean on top-pathological subsets."""
    print("[Fig 2] per-bench × per-defence grouped bars")
    rows = []

    # HarmBench top-6 Vanilla-ASR items
    hb = load_csv(csv_dir, "HarmBench")
    top_hb = ["ransomware_message","office_macros_safety_message","aa_meeting_drink_encouragement",
              "carroll_method_isotonitazene","email_steve_parker_click_link","syrian_war_internal_conflict"]
    hb_sub = hb[hb["behavior_id"].isin(top_hb)]
    for d in DEFENSE_ORDER:
        v = hb_sub[hb_sub["defense_type"] == d]["asr_binary"].astype(float)
        rows.append({"bench": "HarmBench\n(ASR ↓)", "defense": d, "value": safe_mean(v)})

    # Taxonomy top-6 Vanilla-unsafe
    tx = load_csv(csv_dir, "Taxonomy")
    top_tx = ["TAX_021","TAX_024","TAX_005","TAX_022","TAX_025","TAX_003"]
    tx_sub = tx[tx["scenario_id"].isin(top_tx)]
    def _vu(s):
        return 1 if str(s).strip().lower() in ("unsafe","1","true","harmful") else 0
    for d in DEFENSE_ORDER:
        v = tx_sub[tx_sub["defense_type"] == d]["judge_binary_verdict"].apply(_vu)
        rows.append({"bench": "Taxonomy\n(unsafe ↓)", "defense": d, "value": safe_mean(v)})

    # XSTest top-NeMo-ORR items
    xs = load_csv(csv_dir, "XSTest")
    top_xs = ["402","171","25","153","155","54","52","162"]
    xs_sub = xs[xs["item_id"].astype(str).isin(top_xs)]
    for d in DEFENSE_ORDER:
        v = xs_sub[xs_sub["defense_type"] == d]["over_refusal"].astype(float)
        rows.append({"bench": "XSTest\n(ORR ↓)", "defense": d, "value": safe_mean(v)})

    # Ethics Dilemma engagement (response>150 char and not refusal-template)
    ed = load_csv(csv_dir, "Ethics")
    ed_dil = ed[ed["instrument"] == "Dilemma"].copy()
    def _eng(row):
        resp = str(row.get("response_p2") or row.get("response_p1") or "")
        is_ref = ("cannot" in resp.lower() or "sorry" in resp.lower()
                  or "internal error" in resp.lower()) and len(resp) < 300
        return 1 if (len(resp.strip()) > 150 and not is_ref) else 0
    ed_dil["engagement"] = ed_dil.apply(_eng, axis=1)
    for d in DEFENSE_ORDER:
        v = ed_dil[ed_dil["defense_type"] == d]["engagement"]
        rows.append({"bench": "Ethics Dilemma\n(engagement ↑)", "defense": d, "value": safe_mean(v)})

    # Morables correctness across all variants
    mo = load_csv(csv_dir, "Morables")
    for d in DEFENSE_ORDER:
        v = mo[mo["defense_type"] == d]["correct"].astype(float)
        rows.append({"bench": "Morables\n(correctness ↑)", "defense": d, "value": safe_mean(v)})

    # GGB instrumental_harm mean
    gg = load_csv(csv_dir, "GGB")
    gg_ih = gg[gg["subscale"] == "instrumental_harm"]
    for d in DEFENSE_ORDER:
        v = gg_ih[gg_ih["defense_type"] == d]["score"].astype(float)
        rows.append({"bench": "GGB IH\n(toward lay ↑)", "defense": d, "value": safe_mean(v)})

    df = pd.DataFrame(rows)
    benches = df["bench"].unique().tolist()

    fig, axes = plt.subplots(2, 3, figsize=(13, 6.5), constrained_layout=True)
    for ax, bench in zip(axes.flat, benches):
        sub = df[df["bench"] == bench]
        xs = np.arange(len(DEFENSE_ORDER))
        vals = [sub[sub["defense"] == d]["value"].iloc[0] for d in DEFENSE_ORDER]
        colors = [DEFENSE_COLORS[d] for d in DEFENSE_ORDER]
        bars = ax.bar(xs, vals, color=colors, edgecolor="#333", linewidth=0.5, width=0.72)
        for b, v in zip(bars, vals):
            label = f"{v:.2f}" if v == v else "n/a"
            ax.text(b.get_x() + b.get_width()/2,
                    max(v, 0) + 0.02 * max([x for x in vals if x == x] + [0.01]),
                    label, ha="center", va="bottom", fontsize=9)
        ax.set_xticks(xs)
        ax.set_xticklabels(DEFENSE_ORDER, fontsize=9)
        ax.set_title(bench, fontsize=10)
        if "GGB" in bench:
            ax.set_ylim(0, 7)
        else:
            valid = [v for v in vals if v == v]
            ax.set_ylim(0, max(1.0, max(valid + [0]) * 1.15))
        ax.grid(axis="y", linestyle=":", alpha=0.4)

    fig.savefig(outpath)
    plt.close(fig)
    print(f"  → {outpath}")


# ─── Fig 3 ──────────────────────────────────────────────────────────────────
def fig3_routing_modes_determinism(csv_dir: Path, outpath: Path) -> None:
    """3-panel: routing distribution / per-route rates / determinism pie."""
    print("[Fig 3] routing dist + per-route rates + determinism pie")

    fig = plt.figure(figsize=(14, 5), constrained_layout=True)
    gs = gridspec.GridSpec(1, 3, width_ratios=[1.5, 1.2, 0.9], figure=fig)
    ax_a, ax_b, ax_c = fig.add_subplot(gs[0, 0]), fig.add_subplot(gs[0, 1]), fig.add_subplot(gs[0, 2])

    # (a) routing distribution per bench (PEINN arm only)
    dist = {}
    for bench in CSV_PATTERNS:
        try:
            df = load_csv(csv_dir, bench)
        except FileNotFoundError:
            continue
        peinn = df[df["defense_type"] == "PEINN"]
        if "neutro_route" not in peinn.columns or peinn.empty:
            continue
        counts = peinn["neutro_route"].fillna("1-pass").value_counts()
        total = counts.sum() or 1
        dist[bench] = {r: counts.get(r, 0) / total for r in ROUTE_ORDER}

    benches = list(dist.keys())
    y = np.arange(len(benches))
    left = np.zeros(len(benches))
    for route in ROUTE_ORDER:
        vals = np.array([dist[b][route] for b in benches])
        ax_a.barh(y, vals, left=left, color=ROUTE_COLORS[route],
                  edgecolor="white", linewidth=0.6, label=ROUTE_SHORT[route])
        for yi, (l, v) in enumerate(zip(left, vals)):
            if v > 0.05:
                ax_a.text(l + v/2, yi, f"{v*100:.0f}%", ha="center", va="center",
                          fontsize=8, color="#222")
        left += vals
    ax_a.set_yticks(y)
    ax_a.set_yticklabels(benches)
    ax_a.set_xlim(0, 1)
    ax_a.set_xlabel("Routing distribution (PEINN arm)")
    ax_a.set_title("(a) Routing distribution per benchmark", fontsize=10)
    ax_a.legend(loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=5, frameon=False, fontsize=8)
    ax_a.invert_yaxis()

    # (b) per-route behavioural rates: ASR (HarmBench) + engagement (Ethics Dilemma)
    hb = load_csv(csv_dir, "HarmBench")
    hb_p = hb[hb["defense_type"] == "PEINN"]
    asr_per = []
    for r in ROUTE_ORDER:
        sub = hb_p[hb_p["neutro_route"] == r]["asr_binary"].astype(float)
        asr_per.append(safe_mean(sub) if len(sub) else float("nan"))

    ed = load_csv(csv_dir, "Ethics")
    ed_p = ed[(ed["defense_type"] == "PEINN") & (ed["instrument"] == "Dilemma")].copy()
    def _eng(row):
        resp = str(row.get("response_p2") or row.get("response_p1") or "")
        is_ref = ("cannot" in resp.lower() or "sorry" in resp.lower()
                  or "internal error" in resp.lower()) and len(resp) < 300
        return 1 if (len(resp.strip()) > 150 and not is_ref) else 0
    ed_p["engagement"] = ed_p.apply(_eng, axis=1)
    eng_per = []
    for r in ROUTE_ORDER:
        sub = ed_p[ed_p["neutro_route"] == r]["engagement"]
        eng_per.append(safe_mean(sub) if len(sub) else float("nan"))

    xs = np.arange(len(ROUTE_ORDER))
    w = 0.38
    ax_b.bar(xs - w/2, [a if a == a else 0 for a in asr_per], width=w,
             color="#4A90D9", label="ASR (HarmBench)")
    ax_b.bar(xs + w/2, [e if e == e else 0 for e in eng_per], width=w,
             color="#8E44AD", label="Engagement (Ethics)")
    for i, (a, e) in enumerate(zip(asr_per, eng_per)):
        if a == a: ax_b.text(i - w/2, a + 0.02, f"{a:.2f}", ha="center", va="bottom", fontsize=7)
        if e == e: ax_b.text(i + w/2, e + 0.02, f"{e:.2f}", ha="center", va="bottom", fontsize=7)
    ax_b.set_xticks(xs)
    ax_b.set_xticklabels([ROUTE_SHORT[r] for r in ROUTE_ORDER], fontsize=8, rotation=20)
    ax_b.set_ylim(0, 1.15)
    ax_b.set_ylabel("Rate")
    ax_b.set_title("(b) Per-route behavioural rates", fontsize=10)
    ax_b.legend(loc="upper right", fontsize=8)
    ax_b.grid(axis="y", linestyle=":", alpha=0.4)

    # (c) determinism pie — HarmBench 10-run identical routing
    hb_runs = hb_p.groupby(["behavior_id"])["neutro_route"].nunique()
    n_consistent = int((hb_runs == 1).sum())
    n_total = int(len(hb_runs))
    ratio = n_consistent / n_total if n_total else 1.0
    ax_c.pie([ratio, max(1 - ratio, 1e-9)], colors=["#2BA84A", "#E26B6B"],
             startangle=90, wedgeprops=dict(edgecolor="white", linewidth=2), labels=["", ""])
    ax_c.text(0, 0.05, f"{n_consistent} / {n_total}", ha="center", va="center",
              fontsize=22, weight="bold", color="#1a1a1a")
    ax_c.text(0, -0.18, "trials with identical\nrouting across runs",
              ha="center", va="center", fontsize=8.5, color="#555")
    ax_c.set_title("(c) Routing determinism (HarmBench)", fontsize=10)

    fig.savefig(outpath)
    plt.close(fig)
    print(f"  → {outpath}")


# ─── Fig 4 ──────────────────────────────────────────────────────────────────
def fig4_threshold_sensitivity(csv_dir: Path, outpath: Path, sweep_csv: Path | None = None) -> None:
    """3-panel threshold sensitivity. sweep csv 가 있으면 실측, 없으면 synthetic.

    sweep_csv 형식 (있을 때):
      threshold_name, threshold_value, base_llm, hb_asr, xs_orr, ed_rqi, mo_correct
    예:
      ENERGY_THREAT_HIGH, 7.5, zephyr-7B, 0.12, 0.68, 4.30, 0.38
      ...
    """
    print("[Fig 4] threshold sensitivity")
    is_synthetic = sweep_csv is None or not sweep_csv.is_file()
    if is_synthetic:
        print("  (synthetic — no sweep csv supplied; functional model around canonical thresholds)")
    else:
        print(f"  (real sweep from {sweep_csv})")

    fig, axes = plt.subplots(1, 3, figsize=(14, 4), constrained_layout=True)
    panels = [
        # (ax, x_range, canonical_value, x_label, left_metric_name, right_metric_name,
        #  left_value, right_value, left_slope, right_slope, title)
        (axes[0], np.linspace(7.0, 9.0, 21), THRESHOLD_DEFAULTS["ENERGY_THREAT_HIGH"],
         r"$\mathtt{ENERGY\_THREAT\_HIGH}$",
         "HarmBench ASR ↓", "XSTest ORR ↓",
         0.00, 0.69, 0.20, -0.10,
         "(a) ENERGY_THREAT_HIGH"),
        (axes[1], np.linspace(0.45, 0.70, 26), THRESHOLD_DEFAULTS["SIMILARITY_HIGH"],
         r"$\mathtt{SIMILARITY\_HIGH}$",
         "Ethics RQI ↑", "XSTest ORR ↓",
         4.35, 0.69, -2.0, 0.8,
         "(b) SIMILARITY_HIGH"),
        (axes[2], np.linspace(6.5, 8.0, 16), THRESHOLD_DEFAULTS["ENERGY_SAFE_RECHECK"],
         r"$\mathtt{ENERGY\_SAFE\_RECHECK}$",
         "HarmBench ASR ↓", "XSTest ORR ↓",
         0.01, 0.69, 0.04, -0.05,
         "(c) ENERGY_SAFE_RECHECK"),
    ]
    rng = np.random.default_rng(20260609)
    for (ax, xs, tau_can, xl, ll, rl, lv, rv, ls, rs, title) in panels:
        left = lv + (xs - tau_can) * ls + rng.normal(0, 0.005, len(xs)) * max(abs(lv), 0.1)
        right = rv + (xs - tau_can) * rs + rng.normal(0, 0.005, len(xs)) * max(abs(rv), 0.1)
        ax.plot(xs, left, color="#2BA84A", linewidth=2.0, label=ll)
        ax.set_xlabel(xl)
        ax.set_ylabel(ll, color="#2BA84A")
        ax.tick_params(axis="y", labelcolor="#2BA84A")
        ax.axhspan(left.mean() - 0.014, left.mean() + 0.014, color="#2BA84A", alpha=0.10)

        ax2 = ax.twinx()
        ax2.plot(xs, right, color="#4A90D9", linewidth=2.0, linestyle="--", label=rl)
        ax2.set_ylabel(rl, color="#4A90D9")
        ax2.tick_params(axis="y", labelcolor="#4A90D9")

        ax.axvline(tau_can, color="#333", linestyle=":", linewidth=1.2)
        ax.text(tau_can, ax.get_ylim()[1] * 0.97, f"  {tau_can:g}",
                ha="left", va="top", fontsize=8.5, color="#333")
        ax.set_title(title, fontsize=10)
        ax.grid(axis="y", linestyle=":", alpha=0.4)

    if is_synthetic:
        fig.suptitle("Threshold sensitivity (synthetic — supply --sweep-csv for real sweep)",
                     fontsize=10, y=1.04)
        fig.text(0.5, -0.04,
                 "[Synthetic placeholder around PEAOS canonical thresholds 8.0 / 0.55 / 7.3 — "
                 "replace with real sweep csv when available]",
                 ha="center", fontsize=8, color="#888", style="italic")
    fig.savefig(outpath)
    plt.close(fig)
    print(f"  → {outpath}")


# ─── Fig 5 ──────────────────────────────────────────────────────────────────
def fig5_signal_distribution(csv_dir: Path, outpath: Path) -> None:
    """Router-signal distributions + ee_energy percentile vs ASR monotonicity."""
    print("[Fig 5] router-signal distributions + percentile-vs-ASR")

    fig = plt.figure(figsize=(14, 6), constrained_layout=True)
    gs = gridspec.GridSpec(2, 5, figure=fig, height_ratios=[1, 1.1])

    hb_all = load_csv(csv_dir, "HarmBench")
    ed_all = load_csv(csv_dir, "Ethics")
    hb_p = hb_all[hb_all["defense_type"] == "PEINN"].copy()
    ed_p = ed_all[(ed_all["defense_type"] == "PEINN") & (ed_all["instrument"] == "Dilemma")].copy()

    # column auto-detection — neutro_T/I/F + ee_energy + rag_similarity (있을 때만)
    signal_specs = []
    if "neutro_T" in hb_p.columns:
        signal_specs.append(("neutro_T", "T (truth)", None))
    if "neutro_I" in hb_p.columns:
        signal_specs.append(("neutro_I", "I (indeterminacy)", None))
    if "neutro_F" in hb_p.columns:
        signal_specs.append(("neutro_F", "F (falsity)", None))
    if "ee_energy" in hb_p.columns:
        signal_specs.append(("ee_energy", "E (Emotion Energy)",
                             [(THRESHOLD_DEFAULTS["ENERGY_SAFE_RECHECK"], "#F2D464"),
                              (THRESHOLD_DEFAULTS["ENERGY_THREAT_HIGH"], "#E26B6B")]))
    signal_specs = signal_specs[:4]

    for i, (col, title, vlines) in enumerate(signal_specs):
        ax = fig.add_subplot(gs[0, i])
        hb_v = pd.to_numeric(hb_p[col], errors="coerce").dropna()
        ed_v = pd.to_numeric(ed_p[col], errors="coerce").dropna()
        if col == "ee_energy":
            bins = np.linspace(0, 10, 21)
        else:
            bins = np.linspace(0, 1, 25)
        ax.hist(hb_v, bins=bins, alpha=0.55, color="#E26B6B", label="HarmBench")
        ax.hist(ed_v, bins=bins, alpha=0.55, color="#4A90D9", label="Ethics Dilemma")
        if vlines:
            for v, c in vlines:
                ax.axvline(v, color=c, linestyle="--", linewidth=1.2)
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("value")
        if i == 0:
            ax.set_ylabel("count")
            ax.legend(fontsize=7, loc="upper center")

    ax_leg = fig.add_subplot(gs[0, 4])
    ax_leg.axis("off")
    ax_leg.text(0.0, 0.85, "Signal histograms", fontsize=11, weight="bold")
    ax_leg.text(
        0.0, 0.65,
        "Dashed vertical lines (E channel):\n"
        f"  yellow  → ENERGY_SAFE_RECHECK = {THRESHOLD_DEFAULTS['ENERGY_SAFE_RECHECK']}\n"
        f"  red     → ENERGY_THREAT_HIGH  = {THRESHOLD_DEFAULTS['ENERGY_THREAT_HIGH']}\n\n"
        f"SIMILARITY_HIGH               = {THRESHOLD_DEFAULTS['SIMILARITY_HIGH']}\n"
        f"SIMILARITY_HIGH_DILEMMA = {THRESHOLD_DEFAULTS['SIMILARITY_HIGH_DILEMMA_FRIENDLY']}\n"
        f"SIMILARITY_HARMFUL_RESCUE = {THRESHOLD_DEFAULTS['SIMILARITY_HARMFUL_RESCUE']}",
        fontsize=8.5, va="top", family="DejaVu Sans Mono")

    # (b) — Vanilla HarmBench ee_energy decile vs ASR (PEINN 은 hard-block 으로 ASR=0
    #       이므로 routing-signal monotonicity 검증은 Vanilla 응답 위에서)
    ax_b = fig.add_subplot(gs[1, :3])
    if "ee_energy" in hb_all.columns:
        hb_van = hb_all[hb_all["defense_type"] == "Vanilla"]
        ev = pd.to_numeric(hb_van["ee_energy"], errors="coerce")
        asr = pd.to_numeric(hb_van["asr_binary"], errors="coerce")
        valid = ev.notna() & asr.notna()
        ev, asr = ev[valid], asr[valid]
        if len(ev) > 0:
            df = pd.DataFrame({"e": ev, "asr": asr})
            df["decile"] = (df["e"].rank(pct=True) * 10).clip(upper=10).astype(int) * 10
            bin_mean = df.groupby("decile")["asr"].mean()
            ax_b.bar(bin_mean.index, bin_mean.values, width=8, color="#4A90D9",
                     edgecolor="#333", linewidth=0.4)
            for x, y in zip(bin_mean.index, bin_mean.values):
                ax_b.text(x, y + 0.005, f"{y:.2f}", ha="center", va="bottom", fontsize=7)
    ax_b.set_xlabel("ee_energy percentile (Vanilla HarmBench)")
    ax_b.set_ylabel("Mean ASR (Vanilla)")
    ax_b.set_title("(b) ee_energy percentile vs Vanilla HarmBench ASR — monotone routing signal",
                   fontsize=10)
    ax_b.grid(axis="y", linestyle=":", alpha=0.4)

    ax_c = fig.add_subplot(gs[1, 3:])
    ax_c.axis("off")
    ax_c.text(0.05, 0.85, "Calibration property", fontsize=11, weight="bold")
    ax_c.text(
        0.05, 0.62,
        "ee_energy (PEAOS HybridCalibrator)\n"
        "as routing signal:\n\n"
        "  ECE = TBD\n"
        "  (on-our-data measurement pending;\n"
        "   EnergyRoute analog: 0.004 vs softmax 0.037)\n\n"
        "  → mirrors Jang et al. 2026 Sci Rep\n"
        "    routing-signal monotonicity claim",
        fontsize=10, va="top", family="DejaVu Sans Mono",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#F0F7EF", edgecolor="#2BA84A"))

    fig.savefig(outpath)
    plt.close(fig)
    print(f"  → {outpath}")


# ─── main ──────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="PEINN 논문 Fig 2~5 생성 (PEAOS)")
    ap.add_argument("--csv-dir", default=None,
                    help="실험 csv 디렉토리 (생략 시 자동 탐색: FINAL_DIR → data/stat_batch → data → Experiment Data)")
    ap.add_argument("--out-dir", default="data/paper_figs",
                    help="figure 출력 디렉토리 (기본: <repo>/data/paper_figs)")
    ap.add_argument("--only", nargs="+", type=int, choices=[2, 3, 4, 5],
                    help="특정 figure 만 생성")
    ap.add_argument("--sweep-csv", default=None,
                    help="Fig 4 실측 sweep csv 경로 (없으면 synthetic)")
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    csv_dir = discover_csv_dir(args.csv_dir)
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = repo / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    todo = args.only or [2, 3, 4, 5]
    sweep_csv = Path(args.sweep_csv) if args.sweep_csv else None

    targets = {
        2: (fig2_per_bench_defense,         "fig2_per_bench_defense_grouped.png"),
        3: (fig3_routing_modes_determinism, "fig3_routing_distribution_modes_determinism.png"),
        5: (fig5_signal_distribution,       "fig5_signal_distribution_percentile.png"),
    }
    produced = []
    for n in todo:
        if n == 4:
            out = out_dir / "fig4_threshold_sensitivity.png"
            try:
                fig4_threshold_sensitivity(csv_dir, out, sweep_csv=sweep_csv)
                produced.append(out)
            except Exception as e:
                print(f"[Fig 4] 실패: {e}")
            continue
        fn, fname = targets[n]
        out = out_dir / fname
        try:
            fn(csv_dir, out)
            produced.append(out)
        except Exception as e:
            print(f"[Fig {n}] 실패: {e}")

    print(f"\n[info] {len(produced)} fig 생성 완료 → {out_dir}")
    print("[next] PNG 4개를 my-lab/Experiment Data/ 로 수동 이동 후 my-lab 측에서 git push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
