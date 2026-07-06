"""
render_peinn_arch.py — PEINN architecture paper figures.

PEINN(Principle and Emotion Integrated Neural Negotiation) 아키텍처 paper용 figure 6종 일괄 생성.
KISTI PINN 보고서 스타일(Lee 2024 제74호) + paper §System Architecture·§Methods 정합.

Usage:
  python scripts/render_peinn_arch.py --fig 1            # 단일 figure
  python scripts/render_peinn_arch.py --fig all          # 전체 6종
  python scripts/render_peinn_arch.py --fig all --out docs/figures/  # 출력 디렉토리 지정

Figures:
  fig1 — PEINN System Overview (data flow input → 3 layers → router → output)
  fig2 — 3-Layer Affect Hierarchy (Kratzwald × Damasio × Smarandache)
  fig3 — Routing decision tree (deterministic gates)
  fig4 — Training pipeline (judge distillation for readout + head)
  fig5 — Dual-axis AMA validation (Taxonomy ASR + XSTest LEAK + Ethics RQI)
  fig6 — Lower-bound theorem visualization (BAL vs TPR_AB, §11)

의존: matplotlib (필수). 데이터 없이 도식 생성 — paper architecture 절 직접 활용.
"""
from __future__ import annotations
import argparse
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mp
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from matplotlib.lines import Line2D
import numpy as np

# 색 팔레트 (KISTI PINN report 톤 + PEINN 3-layer color coding)
C_L1 = "#4e79a7"   # Layer 1 Readout (blue)
C_L2 = "#e15759"   # Layer 2 Energy (red — somatic marker / harm-strength)
C_L3 = "#59a14f"   # Layer 3 Head (green — cognition)
C_INPUT = "#7f7f7f"
C_ROUTE = "#9467bd"
C_OUTPUT = "#2ca02c"
C_BG = "#f5f5f5"
C_TEXT = "#222"


def _box(ax, x, y, w, h, text, color, fontsize=9, **kw):
    """Rounded rectangle with text. Returns (x_center, y_center)."""
    rect = FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.08",
        facecolor=color, edgecolor="black", linewidth=1.0, alpha=0.85, **kw,
    )
    ax.add_patch(rect)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center",
            fontsize=fontsize, color=C_TEXT, wrap=True)
    return (x + w / 2, y + h / 2)


def _arrow(ax, src, dst, label="", color="black", curve=0.0, fontsize=8):
    """Curved arrow from src to dst with optional label."""
    arr = FancyArrowPatch(
        src, dst, arrowstyle="-|>", mutation_scale=12,
        color=color, linewidth=1.4,
        connectionstyle=f"arc3,rad={curve}",
    )
    ax.add_patch(arr)
    if label:
        mx, my = (src[0] + dst[0]) / 2, (src[1] + dst[1]) / 2
        ax.text(mx, my + 0.05, label, ha="center", va="bottom",
                fontsize=fontsize, color=color, style="italic")


# ──────────────────────────────────────────────────────────────────────
# Fig 1 — PEINN System Overview
# ──────────────────────────────────────────────────────────────────────
def render_fig1(out_path: Path):
    fig, ax = plt.subplots(figsize=(13, 6.5))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")
    ax.set_facecolor("white")

    # Input
    inp = _box(ax, 0.3, 3.0, 1.8, 1.0, "User prompt\n$x$", C_INPUT, fontsize=10)

    # Frozen embedding
    emb = _box(ax, 2.5, 3.0, 1.7, 1.0, "Frozen\nMiniLM-L6\n$\\phi(x) \\in \\mathbb{R}^{384}$",
               "#dbe2ea", fontsize=8.5)

    # Three layers stacked
    l1 = _box(ax, 4.7, 5.0, 2.2, 1.2, "L1 Affective Readout\n(Kratzwald 2018)\nMLP 384→32, sigmoid",
              C_L1, fontsize=8.5)
    l2 = _box(ax, 4.7, 3.0, 2.2, 1.2, "L2 Scalar Energy\n(Damasio 1994)\nHybridCalibrator → [0,10]",
              C_L2, fontsize=8.5)
    l3 = _box(ax, 4.7, 1.0, 2.2, 1.2, "L3 Neutrosophic Head\n(Smarandache)\nMLP 800→(T,I,F)",
              C_L3, fontsize=8.5)

    # Router
    router = _box(ax, 7.6, 3.0, 2.2, 1.2,
                  "Deterministic Router\n$\\mathcal{R}(T, I, F, E, \\mathrm{cx})$",
                  C_ROUTE, fontsize=8.5)

    # Outputs
    outs = [
        ("hard-block", 5.6), ("2-pass-refusal", 4.7),
        ("2-pass-reasoning", 3.5), ("2-pass-soft", 2.3), ("1-pass", 1.4),
    ]
    out_colors = ["#d62728", "#ff7f0e", "#1f77b4", "#9467bd", "#2ca02c"]
    for (label, y), c in zip(outs, out_colors):
        _box(ax, 10.5, y - 0.3, 2.2, 0.7, label, c, fontsize=8.5)
        _arrow(ax, (9.8, 3.6), (10.5, y), color=c)

    # Arrows
    _arrow(ax, (2.1, 3.5), (2.5, 3.5))
    _arrow(ax, (4.2, 3.5), (4.7, 3.5), label="")           # to L2
    _arrow(ax, (4.2, 3.5), (4.7, 5.6), color="gray", curve=0.2)  # to L1
    _arrow(ax, (4.2, 3.5), (4.7, 1.6), color="gray", curve=-0.2) # to L3
    _arrow(ax, (6.9, 5.6), (7.6, 4.2), color=C_L1, curve=-0.2, label="32-D affect / cx")
    _arrow(ax, (6.9, 3.5), (7.6, 3.5), color=C_L2, label="E")
    _arrow(ax, (6.9, 1.6), (7.6, 3.0), color=C_L3, curve=0.2, label="T, I, F")

    # Frozen indicator
    ax.text(3.35, 2.85, "(frozen)", ha="center", fontsize=7, style="italic", color="#666")

    # Title
    ax.set_title("Fig 1 — PEINN System Overview\n"
                 "Three-lineage integration: Kratzwald readout × Damasio energy × Smarandache head\n"
                 "→ deterministic routing → 5 output modes",
                 fontsize=11.5, pad=12)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ──────────────────────────────────────────────────────────────────────
# Fig 2 — 3-Layer Affect Hierarchy
# ──────────────────────────────────────────────────────────────────────
def render_fig2(out_path: Path):
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 8); ax.axis("off")

    # Three vertical panels
    layers = [
        ("L1 Affective Readout", C_L1, 0.5,
         "Kratzwald 2018\n(DSS §3.3.3)",
         "32-D emotion intensity\n(Plutchik affect 8 ×\n moral dyad 8 ×\n appraisal 8 × agency 8)",
         "Role: complexity gate\n(emo_17, AUC=0.999)",
         "Training:\n• gemma4:26b judge distill\n• freq-inverse pos_w\n• held-out BCE 0.61"),
        ("L2 Scalar Energy", C_L2, 4.7,
         "Damasio 1994\n(Somatic Marker)",
         "scalar E ∈ [0, 10]\n(integrated affect marker,\n substrate-independent\n as-if loop)",
         "Role: posture gate\n• hard-block: E ≥ 8.0\n• safe-recheck: 7.3\n• ceiling: 8.0",
         "Training:\n• HybridCalibrator\n• safe 2.25 / unsafe 9.16\n• AUC 0.998"),
        ("L3 Neutrosophic Head", C_L3, 8.9,
         "Smarandache 1998\nLeyva-Vázquez 2026",
         "(T, I, F) ∈ [0,1]³\n(Truth/Indeterminacy/\n Falsity, sum-free,\n neutrosophic-conforming)",
         "Role: conscious decision\n• posture (1p/refusal/reasoning)\n• conflict gate C=min(T,F)\n• dilemma rescue I≥0.35",
         "Training:\n• qwen3:32b judge distill\n• soft-target BCE\n• dim_w[I]=2.5"),
    ]
    for title, color, x0, lineage, output, role, training in layers:
        # Header
        _box(ax, x0, 6.5, 3.5, 0.8, title, color, fontsize=11)
        # Lineage
        _box(ax, x0, 5.4, 3.5, 0.9, lineage, "#ffffff", fontsize=8.5)
        # Output
        _box(ax, x0, 3.7, 3.5, 1.5, output, "#fffbf0", fontsize=8.5)
        # Role
        _box(ax, x0, 1.9, 3.5, 1.5, role, "#f0f8ff", fontsize=8.5)
        # Training
        _box(ax, x0, 0.2, 3.5, 1.5, training, "#f5f5f5", fontsize=8)

    # Connecting horizontal arrows at output level
    _arrow(ax, (4.0, 4.45), (4.7, 4.45), color="gray", curve=0)
    _arrow(ax, (8.2, 4.45), (8.9, 4.45), color="gray", curve=0)

    # Bottom annotation
    ax.text(6.6, -0.4,
            "* Orthogonal fusion: each layer is independently trained on the same paradigm "
            "(frozen feature + thin MLP + judge distillation + class-imbalance handling)",
            ha="center", fontsize=9.5, style="italic")

    ax.set_title("Fig 2 — PEINN 3-Layer Affect Hierarchy\n"
                 "Kratzwald (affective) × Damasio (somatic) × Smarandache (neutrosophic) — three orthogonal lineages",
                 fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ──────────────────────────────────────────────────────────────────────
# Fig 3 — Routing decision tree
# ──────────────────────────────────────────────────────────────────────
def render_fig3(out_path: Path):
    fig, ax = plt.subplots(figsize=(13, 9))
    ax.set_xlim(0, 13); ax.set_ylim(0, 11); ax.axis("off")

    # Root: input signals
    _box(ax, 5.0, 9.5, 3.0, 1.0,
         "Input signals\n$(T, I, F, E, \\mathrm{cx})$ from L1+L2+L3",
         "#dddddd", fontsize=10)

    # Decision 1: E >= 8.0?
    _box(ax, 5.0, 7.7, 3.0, 0.8, "$E \\geq \\Theta_{\\mathrm{block}}=8.0$?", "#ffefcc", fontsize=10)
    _arrow(ax, (6.5, 9.5), (6.5, 8.5))

    # Yes path: rescue checks
    _box(ax, 1.5, 5.8, 3.5, 0.8,
         "rescue checks:\n$T \\geq 0.85$, $I/F$ dilemma, $\\mathrm{cx}$ gate",
         "#fff0e0", fontsize=9)
    _arrow(ax, (5.5, 7.7), (3.2, 6.6), label="Yes")

    # rescue yes → 2-pass-reasoning / soft
    _box(ax, 0.2, 3.8, 3.0, 0.8, "rescue fires →\n2-pass-reasoning or soft", "#1f77b4", fontsize=9)
    _arrow(ax, (2.5, 5.8), (1.7, 4.6), label="Yes (rescued)", color="#1f77b4")

    # rescue no → hard-block
    _box(ax, 3.5, 3.8, 3.0, 0.8, "hard-block\n(no LLM call, short-circuit)", "#d62728", fontsize=9)
    _arrow(ax, (4.0, 5.8), (5.0, 4.6), label="No", color="#d62728")

    # No path: posture-based routing
    _box(ax, 8.0, 5.8, 3.8, 0.8, "neutro_route(T, I, F)\nposture ∈ {1p, refusal, reasoning}",
         "#e8f3e8", fontsize=9)
    _arrow(ax, (7.5, 7.7), (9.9, 6.6), label="No")

    # posture branches
    _box(ax, 8.5, 3.8, 1.7, 0.8, "1-pass\n(if E<7.3)", "#2ca02c", fontsize=9)
    _box(ax, 10.4, 3.8, 1.7, 0.8, "2-pass-soft\n(E ≥ 7.3 or\nposture=refusal)", "#9467bd", fontsize=8)
    _arrow(ax, (9.4, 5.8), (9.35, 4.6), label="posture\n1-pass", color="#2ca02c", fontsize=7)
    _arrow(ax, (10.5, 5.8), (11.25, 4.6), label="recheck", color="#9467bd", fontsize=7)

    # Final outputs (legend)
    legend_y = 1.5
    _box(ax, 0.5, legend_y, 2.4, 0.7, "1-pass", "#2ca02c", fontsize=9)
    _box(ax, 3.1, legend_y, 2.4, 0.7, "2-pass-soft", "#9467bd", fontsize=9)
    _box(ax, 5.7, legend_y, 2.4, 0.7, "2-pass-reasoning", "#1f77b4", fontsize=9)
    _box(ax, 8.3, legend_y, 2.4, 0.7, "2-pass-refusal", "#ff7f0e", fontsize=9)
    _box(ax, 10.9, legend_y, 2.0, 0.7, "hard-block", "#d62728", fontsize=9)
    ax.text(6.5, 0.8,
            "Output: 5 routing modes (deterministic given input — verified cross-process 0/1041 after energy non-determinism fix)",
            ha="center", fontsize=9, style="italic", color="#444")

    ax.set_title("Fig 3 — PEINN Deterministic Routing Decision Tree\n"
                 "Energy gate (hard-block / recheck / ceiling) × head posture × rescue logic",
                 fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ──────────────────────────────────────────────────────────────────────
# Fig 4 — Training Pipeline (judge distillation)
# ──────────────────────────────────────────────────────────────────────
def render_fig4(out_path: Path):
    fig, ax = plt.subplots(figsize=(13, 7))
    ax.set_xlim(0, 13); ax.set_ylim(0, 7); ax.axis("off")

    # Corpora
    _box(ax, 0.2, 5.3, 2.2, 1.0,
         "Training corpora\n(XSTest, HarmBench,\nTaxonomy, Ethics)\n+ adversarial-benign", "#f0f0f0", fontsize=8.5)

    # Judge LMMs
    _box(ax, 3.0, 6.0, 2.5, 0.9, "Judge LMM: gemma4:26b\n→ 32-D readout labels", C_L1, fontsize=9)
    _box(ax, 3.0, 4.3, 2.5, 0.9, "Judge LMM: qwen3:32b\n→ T/I/F labels (0-5 → /5)", C_L3, fontsize=9)
    _box(ax, 3.0, 2.6, 2.5, 0.9, "Pair-wise contrast\n(safe vs unsafe)", C_L2, fontsize=9)

    _arrow(ax, (2.4, 5.8), (3.0, 6.5), color=C_L1)
    _arrow(ax, (2.4, 5.5), (3.0, 4.8), color=C_L3)
    _arrow(ax, (2.4, 5.4), (3.0, 3.1), color=C_L2)

    # Training objectives
    _box(ax, 6.2, 6.0, 3.3, 0.9,
         "BCE w/ Kratzwald §3.3.3\nfreq-inverse $w_d$", "#fff", fontsize=9)
    _box(ax, 6.2, 4.3, 3.3, 0.9,
         "Soft-target BCE +\ndim_w[I]=2.5 + sample_w", "#fff", fontsize=9)
    _box(ax, 6.2, 2.6, 3.3, 0.9,
         "Calibrator MLP\n(sigmoid × 10)", "#fff", fontsize=9)

    _arrow(ax, (5.5, 6.5), (6.2, 6.5))
    _arrow(ax, (5.5, 4.8), (6.2, 4.8))
    _arrow(ax, (5.5, 3.1), (6.2, 3.1))

    # Outputs (frozen models)
    _box(ax, 10.2, 6.0, 2.5, 0.9, "Readout MLP\n(384→128→64→32)", C_L1, fontsize=9)
    _box(ax, 10.2, 4.3, 2.5, 0.9, "Neutro Head\n(800→128→64→3)", C_L3, fontsize=9)
    _box(ax, 10.2, 2.6, 2.5, 0.9, "Calibrator\n(EE+sem → [0,10])", C_L2, fontsize=9)

    _arrow(ax, (9.5, 6.5), (10.2, 6.5), label="freeze", fontsize=7)
    _arrow(ax, (9.5, 4.8), (10.2, 4.8), label="freeze", fontsize=7)
    _arrow(ax, (9.5, 3.1), (10.2, 3.1), label="freeze", fontsize=7)

    # Deployment annotation
    _box(ax, 5.0, 0.5, 4.5, 0.9,
         "Deployment: frozen models + deterministic routing\n(seed-locked, cross-process reproducible)",
         "#e0f0e0", fontsize=9)

    ax.text(6.5, 6.6, "Hinton 2015 distillation paradigm — soft target supervision",
            ha="center", fontsize=8, style="italic", color="#666")

    ax.set_title("Fig 4 — PEINN Training Pipeline\n"
                 "Three layers trained independently via judge distillation (Kratzwald 2018 + Hinton 2015 paradigm)",
                 fontsize=12, pad=12)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ──────────────────────────────────────────────────────────────────────
# Fig 5 — Dual-Axis AMA Validation
# ──────────────────────────────────────────────────────────────────────
def render_fig5(out_path: Path):
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.5))

    # 5-run × 13-arm 실측 (§12, §13, §14)
    models = ["zephyr-7B", "qwen2.5-7B", "gemma4-e4B", "gemma3-12B"]
    x = np.arange(len(models))
    width = 0.32

    # Panel 1 — Taxonomy ASR
    ax = axes[0]
    vanilla_asr = [65.0, 26.5, 27.0, 35.5]
    peinn_asr = [2.0, 0.0, 0.5, 0.0]
    ax.bar(x - width/2, vanilla_asr, width, color="#888", label="Vanilla", edgecolor="black")
    ax.bar(x + width/2, peinn_asr, width, color="#1f77b4", label="PEINN", edgecolor="black")
    for i, (v, p) in enumerate(zip(vanilla_asr, peinn_asr)):
        ax.text(i - width/2, v + 1, f"{v:.0f}%", ha="center", fontsize=8)
        ax.text(i + width/2, p + 1, f"{p:.1f}%", ha="center", fontsize=8, fontweight="bold", color="#1f77b4")
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=15, fontsize=8)
    ax.set_ylabel("ASR (%)"); ax.set_ylim(0, 75)
    ax.set_title("(a) Taxonomy jailbreak ASR\n★ −98.4% mean", fontsize=10)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(axis="y", alpha=0.3)

    # Panel 2 — XSTest LEAK
    ax = axes[1]
    vanilla_leak = [20.0, 12.0, 9.0, 7.0]
    peinn_leak = [2.0, 3.0, 1.0, 2.0]
    ax.bar(x - width/2, vanilla_leak, width, color="#888", label="Vanilla", edgecolor="black")
    ax.bar(x + width/2, peinn_leak, width, color="#d62728", label="PEINN", edgecolor="black")
    for i, (v, p) in enumerate(zip(vanilla_leak, peinn_leak)):
        ax.text(i - width/2, v + 0.3, f"{v:.0f}%", ha="center", fontsize=8)
        ax.text(i + width/2, p + 0.3, f"{p:.1f}%", ha="center", fontsize=8, fontweight="bold", color="#d62728")
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=15, fontsize=8)
    ax.set_ylabel("LEAK rate (%)"); ax.set_ylim(0, 25)
    ax.set_title("(b) XSTest unsafe LEAK\n★ −83.3% mean", fontsize=10)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(axis="y", alpha=0.3)

    # Panel 3 — Ethics Dilemma RQI
    ax = axes[2]
    vanilla_rqi = [3.93, 3.98, 4.08, 3.98]
    peinn_rqi = [3.16, 4.02, 4.04, 3.93]
    nemo_rqi = [1.73, 0.0, 0.0, 0.0]
    width3 = 0.25
    ax.bar(x - width3, vanilla_rqi, width3, color="#888", label="Vanilla", edgecolor="black")
    ax.bar(x, peinn_rqi, width3, color="#2ca02c", label="PEINN", edgecolor="black")
    ax.bar(x + width3, nemo_rqi, width3, color="#ff7f0e", label="NeMo (block-only)", edgecolor="black")
    for i, (v, p, n) in enumerate(zip(vanilla_rqi, peinn_rqi, nemo_rqi)):
        ax.text(i - width3, v + 0.05, f"{v:.2f}", ha="center", fontsize=7)
        ax.text(i, p + 0.05, f"{p:.2f}", ha="center", fontsize=7, fontweight="bold", color="#2ca02c")
        lbl = f"{n:.2f}" if n > 0 else "N/A"
        ax.text(i + width3, max(n, 0.1) + 0.05, lbl, ha="center", fontsize=7, color="#ff7f0e")
    ax.set_xticks(x); ax.set_xticklabels(models, rotation=15, fontsize=8)
    ax.set_ylabel("Dilemma RQI (0-5)"); ax.set_ylim(0, 5)
    ax.set_title("(c) Ethics Dilemma RQI (★ moral-reasoning)\nPEINN ≈ Vanilla; NeMo 100% block (3/4)", fontsize=10)
    ax.legend(fontsize=8, loc="upper right"); ax.grid(axis="y", alpha=0.3)

    fig.suptitle("Fig 5 — Dual-Axis AMA Validation (n=13,725 across 4 base models × 5 runs)\n"
                 "do-no-harm (a, b) × moral-reasoning (c) — PEINN's two-axis competence vs Vanilla and block-only NeMo",
                 fontsize=11.5, y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ──────────────────────────────────────────────────────────────────────
# Fig 6 — Lower-bound theorem visualization
# ──────────────────────────────────────────────────────────────────────
def render_fig6(out_path: Path):
    fig, ax = plt.subplots(figsize=(10, 6.5))

    # BAL = 98.5 - 6.4(1 - TPR_AB)  (§11 Theorem 1)
    tpr = np.linspace(0, 1, 200)
    bal = 98.5 - 6.4 * (1 - tpr)

    ax.plot(tpr, bal, color="#1f77b4", linewidth=2.5, label="$\\mathrm{BAL} \\leq 98.5 - 6.4(1 - \\mathrm{TPR}_{AB})$\n(§11 Theorem 1)")

    # 96% BAL threshold
    ax.axhline(96, color="#d62728", linestyle="--", linewidth=1.5,
               label="BAL = 96% target")
    ax.axvline(0.609, color="#d62728", linestyle=":", linewidth=1.0)
    ax.text(0.625, 92.5, "$\\mathrm{TPR}_{AB} \\geq 0.609$\n(§11 Theorem 2)",
            color="#d62728", fontsize=10)

    # Current PEINN observation (4 arms — TPR_AB ≈ 0)
    arm_data = [
        ("H04 zephyr", 0.0, 89.0),
        ("H07 qwen2.5", 0.0, 91.3),
        ("H10 gemma4", 0.0, 85.9),
        ("H13 gemma3", 0.0, 85.8),
    ]
    for name, tpr_obs, bal_obs in arm_data:
        ax.scatter(tpr_obs, bal_obs, s=80, color="#2ca02c", zorder=5, edgecolor="black")
        ax.annotate(name, (tpr_obs, bal_obs), xytext=(0.05, bal_obs - 0.5),
                    fontsize=8.5, color="#2ca02c")

    # NeMo H06 (best baseline) for reference
    ax.scatter(0.0, 96.8, s=80, color="#ff7f0e", marker="^", zorder=5, edgecolor="black")
    ax.annotate("NeMo H06\n(48% ERROR)", (0.0, 96.8), xytext=(0.05, 97.2),
                fontsize=8.5, color="#ff7f0e")

    # Annotations
    ax.fill_between(tpr, bal, 100, where=bal < 96, alpha=0.15, color="#d62728",
                    label="BAL < 96% region")
    ax.fill_between(tpr, 91, 98.5, where=tpr > 0.609, alpha=0.15, color="#2ca02c",
                    label="achievable (head AUC ≥ 0.913)")

    ax.set_xlabel("TPR$_{AB}$ — head True Positive Rate on adversarial-benign at high E", fontsize=11)
    ax.set_ylabel("Balanced Score (BAL, %)", fontsize=11)
    ax.set_xlim(0, 1); ax.set_ylim(80, 100)
    ax.set_title("Fig 6 — PEINN BAL Lower-bound (§11 formal proof)\n"
                 "Current head TPR$_{AB}$ ≈ 0 → BAL plateaus at ~91-92% (observed: 85.8-91.3)\n"
                 "Target BAL ≥ 96% requires head local AUC ≥ 0.913 (Gaussian approx)",
                 fontsize=11, pad=10)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.95)
    ax.grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=180, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  ✓ {out_path}")


# ──────────────────────────────────────────────────────────────────────
def main():
    p = argparse.ArgumentParser(description="PEINN architecture paper figures")
    p.add_argument("--fig", default="all",
                   help="'1'..'6' or 'all' (default all)")
    p.add_argument("--out", default="docs/figures/peinn_arch",
                   help="output dir (default docs/figures/peinn_arch)")
    args = p.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"PEINN architecture figures → {out_dir}/\n")

    renderers = {
        "1": ("fig1_system_overview.png", render_fig1),
        "2": ("fig2_3layer_hierarchy.png", render_fig2),
        "3": ("fig3_routing_tree.png", render_fig3),
        "4": ("fig4_training_pipeline.png", render_fig4),
        "5": ("fig5_dual_axis_ama.png", render_fig5),
        "6": ("fig6_lower_bound.png", render_fig6),
    }
    targets = list(renderers.keys()) if args.fig == "all" else [args.fig]
    for k in targets:
        if k not in renderers:
            print(f"  ⚠ unknown fig: {k}"); continue
        fname, fn = renderers[k]
        fn(out_dir / fname)

    print(f"\n✅ Done. {len(targets)} figure(s) saved to {out_dir}/")


if __name__ == "__main__":
    main()
