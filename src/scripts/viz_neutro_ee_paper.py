#!/usr/bin/env python3
"""Paper-ready visualisation of the Neutro Head (T/I/F) x 32-dim Emotion Engine dataset.

Reads the CSV produced by scripts/build_neutro_ee_paper_dataset.py and renders:

  Figure 1 (emotion / energy):
    A. t-SNE projection of the 32-dim emotion vectors, coloured by T/I/F label
    B. PCA projection, coloured by Emotion Energy E, with the E>=8.5 hard-block gate ringed
    C. Radar of the 8 Plutchik primaries (EE Layer 1), class-wise mean
    D. Class-wise mean activation heatmap over all 32 dims, grouped into the 4 EE Layers
    E. Emotion Energy E distribution by class with the E=8.5 gate line

  Figure 2 (routing -- the actual PEINN output):
    F. routed_mode distribution by T/I/F class (stacked, normalised)
    G. routed_mode distribution by benchmark source (stacked, normalised)

The 32-dim layout follows the real EmotionEngine spec (4 Layer x 8), range [-1, 1].

Usage:
    python scripts/viz_neutro_ee_paper.py --csv pea_eval/output/paper_neutro_ee.csv \
        --outdir pea_eval/output/figs
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE

EMOTION_COLS = [f"e_{i:02d}" for i in range(1, 33)]
GATE = 8.5  # calibrator-energy hard-block gate (EXP-16)

# Real EmotionEngine 32-dim labels (docs/EE_32D_Architecture_Spec.md).
DIM_LABELS = [
    "joy", "sadness", "anger", "fear", "trust", "disgust", "anticipation", "surprise",        # L1 Core
    "guilt", "outrage", "compassion", "awe", "anxiety", "love", "pride", "submission",        # L2 Moral
    "certainty", "complexity", "urgency", "severity", "fairness", "norm-compat", "utility", "novelty",  # L3 Cognitive
    "autonomy", "competence", "relatedness", "courage", "accountability", "flexibility", "integ-reg", "action-ready",  # L4 Agency
]
LAYERS = [("Core Affects", 0, 8), ("Moral Dyads", 8, 16),
          ("Cognitive Appraisals", 16, 24), ("Agency & SDT", 24, 32)]
PLUTCHIK = DIM_LABELS[:8]  # Layer 1

# Colourblind-safe (Okabe-Ito) class palette.
CLASS_ORDER = ["T", "I", "F"]
CLASS_LABEL = {"T": "Safe (T)", "I": "Indeterminacy (I)", "F": "Harm (F)"}
CLASS_COLOR = {"T": "#009E73", "I": "#E69F00", "F": "#CC79A7"}

# routed_mode ordered low->high intervention; safety-graded colours.
MODE_ORDER = ["1-pass", "2-pass-reasoning-soft", "2-pass-reasoning",
              "2-pass-refusal", "hard-block"]
MODE_COLOR = {
    "1-pass": "#009E73", "2-pass-reasoning-soft": "#56B4E9",
    "2-pass-reasoning": "#0072B2", "2-pass-refusal": "#E69F00",
    "hard-block": "#D55E00",
}


def _present_classes(df: pd.DataFrame) -> list[str]:
    return [c for c in CLASS_ORDER if c in set(df["tif_label"])]


def panel_tsne(ax, df, X):
    n = len(df)
    perp = max(5, min(30, (n - 1) // 3))
    Z = TSNE(n_components=2, perplexity=perp, init="pca",
             random_state=42, learning_rate="auto").fit_transform(X)
    for c in _present_classes(df):
        m = (df["tif_label"] == c).to_numpy()
        ax.scatter(Z[m, 0], Z[m, 1], s=10, alpha=0.6,
                   color=CLASS_COLOR[c], label=CLASS_LABEL[c], edgecolors="none")
    ax.set_title("A.  t-SNE of 32-dim Emotion vectors", fontweight="bold", loc="left")
    ax.set_xlabel("t-SNE dim 1"); ax.set_ylabel("t-SNE dim 2")
    ax.legend(fontsize=7, loc="best")


def panel_pca(ax, df, X):
    pca = PCA(n_components=2, random_state=42)
    Z = pca.fit_transform(X)
    e = df["energy_E"].to_numpy()
    sc = ax.scatter(Z[:, 0], Z[:, 1], c=e, cmap="magma", s=12, alpha=0.8,
                    vmin=float(np.nanmin(e)), vmax=float(np.nanmax(e)))
    blocked = e >= GATE
    if blocked.any():
        ax.scatter(Z[blocked, 0], Z[blocked, 1], s=42, facecolors="none",
                   edgecolors="red", linewidths=0.9,
                   label=f"E ≥ {GATE} (n={int(blocked.sum())})")
        ax.legend(fontsize=7, loc="best")
    plt.colorbar(sc, ax=ax, label="Emotion Energy E")
    var = pca.explained_variance_ratio_ * 100
    ax.set_title(f"B.  PCA · Energy gate (E ≥ {GATE} = block)", fontweight="bold", loc="left")
    ax.set_xlabel(f"PC 1 ({var[0]:.1f}%)"); ax.set_ylabel(f"PC 2 ({var[1]:.1f}%)")


def panel_radar(ax, df):
    angles = np.linspace(0, 2 * np.pi, len(PLUTCHIK), endpoint=False)
    angles = np.concatenate([angles, angles[:1]])
    for c in _present_classes(df):
        sub = df[df["tif_label"] == c]
        means = sub[EMOTION_COLS[:8]].mean().to_numpy()
        vals = np.concatenate([means, means[:1]])
        ax.plot(angles, vals, color=CLASS_COLOR[c], lw=1.8, label=CLASS_LABEL[c])
        ax.fill(angles, vals, color=CLASS_COLOR[c], alpha=0.12)
    ax.set_xticks(angles[:-1]); ax.set_xticklabels(PLUTCHIK, fontsize=7)
    ax.set_title("C.  Mean activation · 8 Plutchik primaries (EE Layer 1)",
                 fontweight="bold", loc="left", pad=18)
    ax.legend(fontsize=6.5, loc="upper right", bbox_to_anchor=(1.25, 1.1))


def panel_heatmap(ax, df):
    classes = _present_classes(df)
    M = np.vstack([df[df["tif_label"] == c][EMOTION_COLS].mean().to_numpy() for c in classes])
    vmax = float(np.nanmax(np.abs(M))) or 1.0
    im = ax.imshow(M, aspect="auto", cmap="RdBu_r", vmin=-vmax, vmax=vmax)
    ax.set_yticks(range(len(classes)))
    ax.set_yticklabels([CLASS_LABEL[c] for c in classes])
    ax.set_xticks(range(32)); ax.set_xticklabels(DIM_LABELS, rotation=90, fontsize=6)
    for _, start, end in LAYERS[:-1]:
        ax.axvline(end - 0.5, color="k", lw=1.0)
    for name, start, end in LAYERS:
        ax.text((start + end - 1) / 2, -0.62, name, ha="center", va="bottom",
                fontsize=8, fontweight="bold")
    ax.set_title("D.  Class-wise mean activation · 32 dims grouped by 4 EE Layers",
                 fontweight="bold", loc="left", pad=40)
    plt.colorbar(im, ax=ax, label="Mean activation [-1, 1]", fraction=0.025, pad=0.01)


def panel_energy(ax, df):
    bins = np.linspace(0, 10, 41)
    for c in _present_classes(df):
        ax.hist(df[df["tif_label"] == c]["energy_E"], bins=bins, alpha=0.6,
                color=CLASS_COLOR[c], label=CLASS_LABEL[c])
    ax.axvline(GATE, color="red", ls="--", lw=1.5, label=f"E = {GATE} (gate)")
    ax.set_title("E.  Emotion Energy E distribution by class", fontweight="bold", loc="left")
    ax.set_xlabel("Emotion Energy E"); ax.set_ylabel("Count")
    ax.legend(fontsize=7)


def _stacked(ax, df, group_col, title, group_order=None):
    modes = [m for m in MODE_ORDER if m in set(df["routed_mode"])]
    ct = pd.crosstab(df[group_col], df["routed_mode"], normalize="index")
    ct = ct.reindex(columns=modes, fill_value=0.0)
    if group_order:
        ct = ct.reindex(index=[g for g in group_order if g in ct.index])
    labels = [CLASS_LABEL.get(g, g) for g in ct.index]
    bottom = np.zeros(len(ct))
    for m in modes:
        ax.bar(labels, ct[m].to_numpy(), bottom=bottom, color=MODE_COLOR[m], label=m)
        bottom += ct[m].to_numpy()
    ax.set_title(title, fontweight="bold", loc="left")
    ax.set_ylabel("Routing share"); ax.set_ylim(0, 1)
    ax.tick_params(axis="x", rotation=20)


def fig_routing(df, outdir):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5.5))
    _stacked(ax1, df, "tif_label", "F.  routed_mode by T/I/F class",
             group_order=CLASS_ORDER)
    _stacked(ax2, df, "bench_source", "G.  routed_mode by benchmark")
    handles = [Line2D([0], [0], color=MODE_COLOR[m], lw=8) for m in MODE_ORDER if m in set(df["routed_mode"])]
    labels = [m for m in MODE_ORDER if m in set(df["routed_mode"])]
    fig.legend(handles, labels, loc="lower center", ncol=len(labels), fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.02))
    fig.suptitle("PEINN · Routing outcomes (5-mode)", fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    for ext in ("pdf", "png"):
        fig.savefig(outdir / f"neutro_ee_routing.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_emotion(df, X, outdir):
    fig = plt.figure(figsize=(18, 11))
    gs = GridSpec(2, 3, figure=fig, height_ratios=[1, 1.05], hspace=0.45, wspace=0.32)
    panel_tsne(fig.add_subplot(gs[0, 0]), df, X)
    panel_pca(fig.add_subplot(gs[0, 1]), df, X)
    panel_radar(fig.add_subplot(gs[0, 2], projection="polar"), df)
    panel_heatmap(fig.add_subplot(gs[1, 0:2]), df)
    panel_energy(fig.add_subplot(gs[1, 2]), df)
    fig.suptitle("PEINN · Neutrosophic Head (T/I/F) × 32-dim Emotion Engine",
                 fontsize=15, fontweight="bold")
    for ext in ("pdf", "png"):
        fig.savefig(outdir / f"neutro_ee_emotion.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def fig_complementarity(df, outdir):
    """Cognition (head T/I/F label) x affect (energy band) — shows the two channels
    disagree: a sizeable share of head-Safe items land in the energy hard-block band,
    evidencing that head and energy are complementary, not redundant."""
    bands = [("low\n<5.8", 0, 5.8), ("moderate\n5.8-7.3", 5.8, 7.3),
             ("recheck\n7.3-8.5", 7.3, GATE), ("hard-block\n≥8.5", GATE, 99)]
    band_color = {"low\n<5.8": "#009E73", "moderate\n5.8-7.3": "#56B4E9",
                  "recheck\n7.3-8.5": "#E69F00", "hard-block\n≥8.5": "#D55E00"}
    classes = _present_classes(df)
    fig, ax = plt.subplots(figsize=(8, 5.5))
    labels = [CLASS_LABEL[c] for c in classes]
    bottom = np.zeros(len(classes))
    for name, lo, hi in bands:
        share = []
        for c in classes:
            e = df[df["tif_label"] == c]["energy_E"].to_numpy()
            share.append((((e >= lo) & (e < hi)).sum() / len(e)) if len(e) else 0.0)
        share = np.array(share)
        ax.bar(labels, share, bottom=bottom, color=band_color[name], label=name)
        bottom += share
    # annotate %(hard-block) per class — the complementarity headline
    for i, c in enumerate(classes):
        e = df[df["tif_label"] == c]["energy_E"].to_numpy()
        pct = 100 * (e >= GATE).mean() if len(e) else 0
        ax.text(i, 1.02, f"{pct:.0f}% blocked", ha="center", fontsize=8, fontweight="bold")
    ax.set_ylim(0, 1.12); ax.set_ylabel("Energy-band share")
    ax.set_title("Cognition (head T/I/F) × Affect (energy band)\n"
                 "head-Safe items still energy-blocked ⇒ channels are complementary",
                 fontweight="bold", fontsize=11)
    ax.legend(fontsize=8, loc="lower right", ncol=2)
    for ext in ("pdf", "png"):
        fig.savefig(outdir / f"neutro_ee_complementarity.{ext}", dpi=200, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--outdir", default="pea_eval/output/figs")
    args = ap.parse_args()

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=EMOTION_COLS + ["energy_E", "tif_label", "routed_mode"])
    X = df[EMOTION_COLS].to_numpy(dtype="float32")
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    fig_emotion(df, X, outdir)
    fig_routing(df, outdir)
    fig_complementarity(df, outdir)
    print(f"[ok] {len(df)} rows -> figures in {outdir}/ "
          f"(neutro_ee_emotion.*, neutro_ee_routing.*, neutro_ee_complementarity.*)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
