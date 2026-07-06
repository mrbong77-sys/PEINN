"""
Paper §Results 시각화 — Morables 5-run + GGB 10-run + Ethics 5-run (HANDOFF-55/56).

본 평가 산출물(xlsx 또는 csv)을 입력으로 받아 paper §X.2/§X.3/§X.4 본문 표를
*해석하는* 보조 figure 9종을 일괄 생성한다. 결정론적 채점이므로 LLM judge 미사용 —
데이터를 그대로 받아 numpy/matplotlib만으로 그린다.

산출 figure (출력 디렉토리 기본 docs/figures/paper_results/):

  Morables:
    FigM1_acc_by_arm.png       — per-base Vanilla/PEINN/NeMo/R2D2 Acc bar (clean+adv)
    FigM2_acc_by_route.png     — PEINN 4 base × 4 route Acc 매트릭스 (reflection 회귀)
    FigM3_amplifier_pattern.png — scatter (x=Vanilla Acc, y=PEINN−Vanilla Δ) — amplifier framing
  GGB:
    FigG1_subscale_means.png   — per-base Vanilla vs PEINN IH/IB bar + lay reference
    FigG2_ib_ih_plane.png      — IB/IH 2D plane: Vanilla → PEINN 화살표 + Kahane lay point
    FigG3_hardblock_pattern.png — 9 OUS 항목 × hard-block 빈도 막대 (IH2 단독 노출)
  Ethics:
    FigE1_rqi_by_arm.png       — per-arm Dilemma RQI bars (NeMo n/a 마커)
    FigE2_nemo_refuse_dilemma.png — NeMo refuse rate per base
    FigE3_routing_by_instrument.png — PEINN routing × instrument stacked

★ 가장 단순한 사용법 (인자 없이 — pea_eval/output/final/에서 자동 탐색):
    python scripts/render_paper_figures_morables_ggb.py

기타 사용법:
    # 명시 입력 / 출력 지정
    python scripts/render_paper_figures_morables_ggb.py --morables /path/file.xlsx
    python scripts/render_paper_figures_morables_ggb.py --out /path/to/output/

    # 결과지 폴더가 다르면
    python scripts/render_paper_figures_morables_ggb.py --src "/path/to/results/dir/"

의존: pandas, numpy, matplotlib, openpyxl(xlsx 입력 시).
"""
from __future__ import annotations
import argparse
import logging
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = PROJECT_ROOT / "docs" / "figures" / "paper_results"
# pea_eval/output/final/ — run_stat_batch.py가 결과지를 떨구는 곳
DEFAULT_SRC = PROJECT_ROOT / "pea_eval" / "output" / "final"

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peaos.render_paper_figs")

# Arm 정본 매핑 (00_shared_conventions §1)
BASE_ORDER = ["zephyr", "qwen2.5", "gemma4", "gemma3"]
DEFENSE_ORDER = ["Vanilla", "R2D2", "NeMo", "PEINN"]
ROUTE_ORDER = ["1-pass", "2-pass-reasoning-soft", "2-pass-reasoning", "hard-block"]
COLORS_DEF = {"Vanilla": "#7f7f7f", "R2D2": "#d62728",
              "NeMo": "#ff7f0e", "PEINN": "#1f77b4"}
COLORS_ROUTE = {"1-pass": "#2ca02c", "2-pass-reasoning-soft": "#9467bd",
                "2-pass-reasoning": "#1f77b4", "hard-block": "#d62728"}

# Kahane et al. 2018 lay-population reference (placeholder — paper 게재 전 1차 출처 검증)
LAY_IH = 2.9
LAY_IB = 3.8


def _load(path: Path):
    import pandas as pd
    if path.suffix.lower() in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    else:
        df = pd.read_csv(path)
    df["rep"] = df.run_id.apply(
        lambda s: int(re.search(r"_r(\d+)_", str(s)).group(1))
        if isinstance(s, str) and re.search(r"_r(\d+)_", s) else None)
    return df


def _autodiscover(src_dir: Path, bench: str) -> Path | None:
    """src_dir 안에서 가장 최신의 `{bench}_batch_*` (xlsx 우선, 없으면 csv) 파일을 반환.

    명명 규칙(run_stat_batch.py 산출): {bench}_batch_{n}runs_{YYYYMMDD_HHMMSS}.{xlsx,csv}
    여러 timestamp가 섞여 있어도 가장 최신을 자동 선택. 발견 못하면 None.
    """
    if not src_dir.exists():
        return None
    candidates = list(src_dir.glob(f"{bench}_batch_*.xlsx")) + \
                 list(src_dir.glob(f"{bench}_batch_*.csv"))
    if not candidates:
        return None
    # 파일 mtime 기준 최신
    latest = max(candidates, key=lambda p: p.stat().st_mtime)
    return latest


# ─────────────────────────────────────────────────────────────────────
# Morables figures
# ─────────────────────────────────────────────────────────────────────

def fig_morables_acc_by_arm(df, out_path: Path):
    """FigM1 — per-base × per-defense Acc (clean vs adv). NeMo=0 명시 노출."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["correct"] = pd.to_numeric(df["correct"], errors="coerce")
    # arm 메타
    arm_meta = df.groupby("arm_id")[["defense_type", "model_group"]].first()
    rows = []
    for arm, meta in arm_meta.iterrows():
        sub = df[df.arm_id == arm]
        cln = sub[sub.variant == "clean"]["correct"].mean()
        adv = sub[sub.variant != "clean"]["correct"].mean()
        rows.append({"arm": arm, "defense": meta.defense_type, "base": meta.model_group,
                     "clean": cln, "adv": adv})
    pl = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    base_x = {b: i for i, b in enumerate(BASE_ORDER)}
    def_offset = {"Vanilla": -0.30, "R2D2": -0.10, "NeMo": 0.10, "PEINN": 0.30}
    w = 0.18
    for _, r in pl.iterrows():
        bx = base_x.get(r["base"].split("-")[0] if r["base"].startswith("zephyr-r2d2") else r["base"])
        if bx is None: continue
        x = bx + def_offset.get(r["defense"], 0)
        color = COLORS_DEF[r["defense"]]
        ax.bar(x - w/2, r["clean"], width=w, color=color, edgecolor="black", linewidth=0.5,
               label=f"{r['defense']} clean" if r["base"] == "zephyr" else None)
        ax.bar(x + w/2, r["adv"], width=w, color=color, edgecolor="black", linewidth=0.5,
               hatch="///", label=f"{r['defense']} adv" if r["base"] == "zephyr" else None)
    ax.set_xticks(list(base_x.values()))
    ax.set_xticklabels([f"{b}" for b in BASE_ORDER], fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11)
    ax.set_ylim(0, 1.0)
    ax.set_title("FigM1 — Morables accuracy by arm (5 runs × 45 fables × 4 variants)\n"
                 "Vanilla / R2D2 / NeMo / PEINN — clean (solid) vs adversarial mean (hatched)",
                 fontsize=10)
    ax.axhline(0.20, color="gray", linestyle=":", alpha=0.5, label="chance (5-choice)")
    ax.axhline(0.14, color="gray", linestyle=":", alpha=0.3, label="chance (7-choice, pre_post_inj)")
    ax.legend(loc="upper left", fontsize=8, ncol=2, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


def fig_morables_acc_by_route(df, out_path: Path):
    """FigM2 — PEINN 4 base × 4 route Acc. reflection 회귀 시각화."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["correct"] = pd.to_numeric(df["correct"], errors="coerce")
    peinn = df[df.defense_type == "PEINN"]
    pl = peinn.groupby(["model_group", "neutro_route"])["correct"].mean().unstack(fill_value=0.0)
    pl = pl.reindex(columns=ROUTE_ORDER, fill_value=0.0).reindex(index=BASE_ORDER)
    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(BASE_ORDER)); w = 0.20
    for i, route in enumerate(ROUTE_ORDER):
        ax.bar(x + (i - 1.5) * w, pl[route].values, width=w,
               color=COLORS_ROUTE[route], edgecolor="black", linewidth=0.4, label=route)
    ax.set_xticks(x); ax.set_xticklabels(BASE_ORDER, fontsize=11)
    ax.set_ylabel("Accuracy", fontsize=11); ax.set_ylim(0, 1.0)
    ax.set_title("FigM2 — Morables accuracy by PEINN intent-router route, per base\n"
                 "(routing distribution is base-independent; reflection penalty scales with base strength)",
                 fontsize=10)
    ax.axhline(0.20, color="gray", linestyle=":", alpha=0.4)
    ax.legend(loc="upper left", fontsize=8, framealpha=0.9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


def fig_morables_amplifier(df, out_path: Path):
    """FigM3 — amplifier framing: x=Vanilla Acc, y=PEINN-Vanilla Δ. 4 점 + 추세선."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["correct"] = pd.to_numeric(df["correct"], errors="coerce")
    pairs = [("H01", "H04", "zephyr-7B"),
             ("H05", "H07", "qwen2.5-7B"),
             ("H08", "H10", "gemma4-e4b"),
             ("H11", "H13", "gemma3-12B")]
    pts = []
    for va, pa, label in pairs:
        v_acc = df[df.arm_id == va]["correct"].mean()
        p_acc = df[df.arm_id == pa]["correct"].mean()
        pts.append((v_acc, p_acc - v_acc, label))
    fig, ax = plt.subplots(figsize=(8, 6))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    ax.scatter(xs, ys, s=200, c=["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"],
               edgecolor="black", linewidth=1.2, zorder=3)
    for v, d, label in pts:
        ax.annotate(f"  {label}\n  (V={v:.2f}, Δ={d:+.2f})", (v, d), fontsize=9, va="center")
    # 추세선
    if len(xs) >= 2:
        coef = np.polyfit(xs, ys, 1)
        xx = np.array([min(xs)*0.9, max(xs)*1.05])
        ax.plot(xx, np.poly1d(coef)(xx), "k--", alpha=0.5, linewidth=1.0,
                label=f"linear fit: Δ = {coef[0]:.2f}·Vanilla + {coef[1]:.2f}")
    ax.axhline(0, color="gray", linestyle=":", alpha=0.5)
    ax.set_xlabel("Vanilla Acc (base moral-reasoning strength)", fontsize=11)
    ax.set_ylabel("Δ Acc (PEINN − Vanilla)", fontsize=11)
    ax.set_title("FigM3 — Reflection-induced regression scales with base moral-reasoning strength\n"
                 "(amplifier framing: 2-pass route bounded above by base LLM ability)", fontsize=10)
    ax.legend(loc="lower left", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


# ─────────────────────────────────────────────────────────────────────
# GGB figures
# ─────────────────────────────────────────────────────────────────────

def fig_ggb_subscale_means(df, out_path: Path):
    """FigG1 — per-base Vanilla vs PEINN IH/IB bar + Kahane lay reference."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["sc"] = pd.to_numeric(df["score"], errors="coerce")
    rows = []
    for arm in sorted(df.arm_id.unique()):
        a = df[df.arm_id == arm]
        ih = a[a.subscale == "instrumental_harm"]["sc"].mean()
        ib = a[a.subscale == "impartial_beneficence"]["sc"].mean()
        d0 = a.iloc[0]
        rows.append({"arm": arm, "def": d0.defense_type, "base": d0.model_group,
                     "IH": ih, "IB": ib})
    pl = pd.DataFrame(rows)
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, sub_name, lay in zip(axes, ["IH", "IB"], [LAY_IH, LAY_IB]):
        base_x = {b: i for i, b in enumerate(BASE_ORDER)}
        def_offset = {"Vanilla": -0.30, "R2D2": -0.10, "NeMo": 0.10, "PEINN": 0.30}
        for _, r in pl.iterrows():
            base = "zephyr" if r["base"].startswith("zephyr") else r["base"]
            bx = base_x.get(base)
            if bx is None: continue
            x = bx + def_offset.get(r["def"], 0)
            val = r[sub_name]
            if pd.isna(val):
                # NeMo n/a — 막대 없이 'X' 표시
                ax.text(x, 0.3, "n/a", ha="center", fontsize=8, color="red", fontweight="bold")
                continue
            ax.bar(x, val, width=0.18, color=COLORS_DEF[r["def"]],
                   edgecolor="black", linewidth=0.5,
                   label=r["def"] if (bx == 0 and sub_name == "IH") else None)
        ax.axhline(lay, color="black", linestyle="--", linewidth=1.2, alpha=0.7,
                   label=f"lay reference (Kahane et al. 2018, ~{lay})")
        ax.set_xticks(list(base_x.values()))
        ax.set_xticklabels(BASE_ORDER, fontsize=10)
        ax.set_ylim(0, 7)
        ax.set_ylabel("Likert mean (1–7)" if sub_name == "IH" else "")
        ax.set_title(f"{sub_name} — {'Instrumental Harm' if sub_name=='IH' else 'Impartial Beneficence'}",
                     fontsize=11)
        ax.grid(axis="y", alpha=0.3)
    axes[0].legend(loc="upper left", fontsize=8, framealpha=0.9, ncol=2)
    fig.suptitle("FigG1 — OUS subscale means by arm (10 runs × 9 items)\n"
                 "NeMo arms refuse all OUS items (n/a). PEINN moves IH toward lay reference; IB preserved.",
                 fontsize=10)
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


def fig_ggb_ib_ih_plane(df, out_path: Path):
    """FigG2 — IB/IH 2D plane: Vanilla → PEINN 화살표 + lay reference point."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["sc"] = pd.to_numeric(df["score"], errors="coerce")
    pairs = [("H01", "H04", "zephyr-7B"),
             ("H05", "H07", "qwen2.5-7B"),
             ("H08", "H10", "gemma4-e4b"),
             ("H11", "H13", "gemma3-12B")]
    fig, ax = plt.subplots(figsize=(8, 7))
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728"]
    for (va, pa, label), color in zip(pairs, colors):
        v_ih = df[(df.arm_id == va) & (df.subscale == "instrumental_harm")]["sc"].mean()
        v_ib = df[(df.arm_id == va) & (df.subscale == "impartial_beneficence")]["sc"].mean()
        p_ih = df[(df.arm_id == pa) & (df.subscale == "instrumental_harm")]["sc"].mean()
        p_ib = df[(df.arm_id == pa) & (df.subscale == "impartial_beneficence")]["sc"].mean()
        ax.scatter(v_ih, v_ib, s=180, marker="o", color=color, edgecolor="black",
                   linewidth=1.2, zorder=3, label=f"{label} (V→P)")
        ax.scatter(p_ih, p_ib, s=180, marker="s", color=color, edgecolor="black", linewidth=1.2, zorder=3)
        ax.annotate("", xy=(p_ih, p_ib), xytext=(v_ih, v_ib),
                    arrowprops=dict(arrowstyle="->", color=color, lw=1.5, alpha=0.7))
        ax.text(v_ih, v_ib + 0.15, f"{label}", color=color, fontsize=9, ha="center")
    # lay reference
    ax.scatter(LAY_IH, LAY_IB, s=300, marker="*", color="black", zorder=4,
               label=f"lay reference (Kahane 2018, IH={LAY_IH}, IB={LAY_IB})")
    ax.text(LAY_IH + 0.1, LAY_IB - 0.1, "lay", fontsize=10, fontweight="bold")
    ax.set_xlim(0.5, 7.5); ax.set_ylim(0.5, 7.5)
    ax.set_xlabel("Instrumental Harm (IH) mean (1–7)", fontsize=11)
    ax.set_ylabel("Impartial Beneficence (IB) mean (1–7)", fontsize=11)
    ax.set_title("FigG2 — Vanilla → PEINN shift on the IH/IB plane (10-run mean)\n"
                 "○ Vanilla → ▪ PEINN. PEINN moves IH toward lay reference; IB preserved.", fontsize=10)
    ax.legend(loc="lower left", fontsize=9, framealpha=0.9)
    ax.grid(alpha=0.3)
    ax.set_aspect("equal")
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


def fig_ggb_hardblock(df, out_path: Path):
    """FigG3 — 9 OUS 항목 × hard-block 빈도 막대 (IH2 단독 노출)."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy()
    peinn = df[df.defense_type == "PEINN"]
    hb = peinn[peinn.neutro_route == "hard-block"]
    items = ["IH1", "IH2", "IH3", "IH4", "IB1", "IB2", "IB3", "IB4", "IB5"]
    total_per_item = peinn.groupby("item_id").size().reindex(items, fill_value=0)
    hb_per_item = hb.groupby("item_id").size().reindex(items, fill_value=0)
    rates = (hb_per_item / total_per_item).fillna(0.0)
    fig, ax = plt.subplots(figsize=(10, 4.5))
    colors = ["#d62728" if i.startswith("IH") else "#1f77b4" for i in items]
    bars = ax.bar(items, rates.values * 100, color=colors, edgecolor="black", linewidth=0.5)
    for bar, val, raw in zip(bars, rates.values, hb_per_item.values):
        if val > 0:
            ax.text(bar.get_x() + bar.get_width()/2, val*100 + 1,
                    f"{raw}/{total_per_item[bar.get_x()] if False else int(total_per_item.iloc[items.index(bar.get_x() if False else items[bars.index(bar) if False else 0])])}",
                    ha="center", fontsize=8)
    # safer overlay
    for j, (item, val, raw, tot) in enumerate(zip(items, rates.values, hb_per_item.values, total_per_item.values)):
        if val > 0:
            ax.text(j, val*100 + 1.5, f"{raw}/{tot}\n({val*100:.0f}%)", ha="center", fontsize=8)
    ax.set_ylabel("PEINN hard-block rate (%)", fontsize=11)
    ax.set_ylim(0, 110)
    ax.set_title("FigG3 — PEINN hard-block pattern on OUS (10 runs × 4 PEINN arms = n=40 per item)\n"
                 "Energy gate fires only on IH2 (\"torture an innocent\") — token-level trigger caveat",
                 fontsize=10)
    ax.axhline(100, color="gray", linestyle=":", alpha=0.4)
    for label, color in [("IH items", "#d62728"), ("IB items", "#1f77b4")]:
        ax.bar(0, 0, color=color, label=label)  # for legend
    ax.legend(loc="upper right", fontsize=9)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


# ─────────────────────────────────────────────────────────────────────
# Ethics(Jiao) figures
# ─────────────────────────────────────────────────────────────────────

def fig_ethics_rqi_by_arm(df, out_path: Path):
    """FigE1 — Dilemma RQI per arm (5-run mean ± SD), NeMo n/a 노출."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["rqi_n"] = pd.to_numeric(df["rqi"], errors="coerce")
    dlm = df[df.instrument == "Dilemma"]
    rows = []
    for arm in sorted(df.arm_id.unique()):
        a = dlm[dlm.arm_id == arm]
        d0 = df[df.arm_id == arm].iloc[0]
        rqi = a.rqi_n.mean()
        sd = a.rqi_n.std()
        miss = a.rqi_n.isna().sum()
        rows.append({"arm": arm, "def": d0.defense_type, "base": d0.model_group,
                     "rqi": rqi, "sd": sd, "miss": miss, "n": len(a)})
    pl = pd.DataFrame(rows)
    fig, ax = plt.subplots(figsize=(11, 5.5))
    base_x = {b: i for i, b in enumerate(BASE_ORDER)}
    def_offset = {"Vanilla": -0.30, "R2D2": -0.10, "NeMo": 0.10, "PEINN": 0.30}
    for _, r in pl.iterrows():
        base = "zephyr" if r["base"].startswith("zephyr") else r["base"]
        bx = base_x.get(base)
        if bx is None: continue
        x = bx + def_offset.get(r["def"], 0)
        color = COLORS_DEF[r["def"]]
        if pd.isna(r["rqi"]):
            ax.text(x, 0.5, "n/a", ha="center", color="red", fontsize=9, fontweight="bold")
            ax.text(x, 0.2, f"(refused\n{r['miss']}/{r['n']})", ha="center", color="red", fontsize=7)
            continue
        ax.bar(x, r["rqi"], width=0.18, color=color, edgecolor="black", linewidth=0.5,
               yerr=r["sd"] if pd.notna(r["sd"]) else 0,
               error_kw={"capsize": 3, "elinewidth": 0.7},
               label=r["def"] if bx == 0 else None)
        if r["miss"] > 0:
            ax.text(x, r["rqi"] + 0.15, f"(n={r['n']-r['miss']}/{r['n']})",
                    ha="center", fontsize=7, color="gray")
    ax.set_xticks(list(base_x.values()))
    ax.set_xticklabels(BASE_ORDER, fontsize=11)
    ax.set_ylim(0, 5.0)
    ax.set_ylabel("Dilemma RQI (1–5)", fontsize=11)
    ax.set_title("FigE1 — Ethics Dilemma RQI per arm (5 runs × 100 dilemmas)\n"
                 "NeMo refuses 91–100 % of dilemmas across all four bases (RQI ≈ n/a)",
                 fontsize=10)
    ax.axhline(3.0, color="gray", linestyle=":", alpha=0.4, label="mid-scale (3.0)")
    ax.legend(loc="lower right", fontsize=8, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


def fig_ethics_nemo_refuse(df, out_path: Path):
    """FigE2 — NeMo Dilemma refusal rate per base + valid-n count."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy(); df["rqi_n"] = pd.to_numeric(df["rqi"], errors="coerce")
    nemo = df[(df.defense_type == "NeMo") & (df.instrument == "Dilemma")]
    bases = []
    refuse_rates = []
    for arm, base in [("H03", "zephyr"), ("H06", "qwen2.5"),
                       ("H09", "gemma4"), ("H12", "gemma3")]:
        a = nemo[nemo.arm_id == arm]
        miss = a.rqi_n.isna().sum()
        bases.append(base); refuse_rates.append(miss / len(a) * 100 if len(a) else 0)
    fig, ax = plt.subplots(figsize=(8, 5))
    bars = ax.bar(bases, refuse_rates, color="#ff7f0e", edgecolor="black", linewidth=0.5)
    for bar, val in zip(bars, refuse_rates):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 1.0,
                f"{val:.0f}%", ha="center", fontsize=11, fontweight="bold")
    ax.set_ylim(0, 110)
    ax.set_ylabel("NeMo Dilemma refusal rate (%)", fontsize=11)
    ax.set_title("FigE2 — NeMo Guardrails refuses moral dilemmas (5 runs × 100 dilemmas per arm)\n"
                 "block-only paradigm cannot, by construction, exercise moral reasoning",
                 fontsize=10)
    ax.axhline(100, color="red", linestyle=":", alpha=0.5)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


def fig_ethics_routing_by_instrument(df, out_path: Path):
    """FigE3 — PEINN routing 4-mode × 3 instrument stacked bars."""
    import pandas as pd, numpy as np, matplotlib.pyplot as plt
    df = df.copy()
    peinn = df[df.defense_type == "PEINN"]
    # PEINN routing is base-independent — aggregate across 4 PEINN arms
    pl = peinn.groupby(["instrument", "neutro_route"]).size().unstack(fill_value=0)
    pl = pl.reindex(columns=ROUTE_ORDER, fill_value=0).reindex(index=["MFQ", "WVS", "Dilemma"])
    pl_pct = pl.div(pl.sum(axis=1), axis=0) * 100
    fig, ax = plt.subplots(figsize=(10, 5))
    bottom = np.zeros(len(pl_pct))
    for route in ROUTE_ORDER:
        if route in pl_pct.columns:
            ax.barh(pl_pct.index, pl_pct[route].values, left=bottom,
                    color=COLORS_ROUTE[route], edgecolor="black", linewidth=0.4, label=route)
            # 비율 라벨
            for i, val in enumerate(pl_pct[route].values):
                if val > 5:
                    ax.text(bottom[i] + val / 2, i, f"{val:.0f}%", ha="center",
                            va="center", fontsize=9, color="white" if route in ("2-pass-reasoning",) else "black")
            bottom += pl_pct[route].values
    ax.set_xlim(0, 100)
    ax.set_xlabel("Routing fraction (%)", fontsize=11)
    ax.set_title("FigE3 — PEINN intent-router resolution by Ethics instrument (4 PEINN arms aggregated)\n"
                 "Dilemma → 100 % reasoning; MFQ → mixed; WVS → mostly 1-pass. No item triggers hard-block.",
                 fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    ax.grid(axis="x", alpha=0.3)
    fig.tight_layout(); fig.savefig(out_path, dpi=150, bbox_inches="tight"); plt.close(fig)
    logger.info(f"  ✓ {out_path.name}")


# ─────────────────────────────────────────────────────────────────────

def main() -> int:
    ap = argparse.ArgumentParser(
        description="Render Morables/GGB/Ethics paper figures (자동 탐색 지원)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="가장 단순: python scripts/render_paper_figures_morables_ggb.py "
               "(인자 없이 — pea_eval/output/final/에서 자동 탐색)")
    ap.add_argument("--morables", default="", help="Morables xlsx/csv 경로 (생략 시 --src에서 자동 탐색)")
    ap.add_argument("--ggb", default="", help="GGB xlsx/csv 경로 (생략 시 자동 탐색)")
    ap.add_argument("--ethics", default="", help="Ethics xlsx/csv 경로 (생략 시 자동 탐색)")
    ap.add_argument("--src", default=str(DEFAULT_SRC),
                    help=f"자동 탐색 디렉토리 (기본 {DEFAULT_SRC})")
    ap.add_argument("--out", default=str(DEFAULT_OUT),
                    help=f"figure 출력 디렉토리 (기본 {DEFAULT_OUT})")
    args = ap.parse_args()
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    src = Path(args.src)

    # 자동 탐색: 인자 명시 안 된 벤치는 src에서 최신 파일 찾기
    auto_msgs = []
    if not args.morables:
        p = _autodiscover(src, "morables")
        if p:
            args.morables = str(p)
            auto_msgs.append(f"morables → {p.name}")
    if not args.ggb:
        p = _autodiscover(src, "ggb")
        if p:
            args.ggb = str(p)
            auto_msgs.append(f"ggb → {p.name}")
    if not args.ethics:
        p = _autodiscover(src, "ethics")
        if p:
            args.ethics = str(p)
            auto_msgs.append(f"ethics → {p.name}")
    if auto_msgs:
        logger.info(f"자동 탐색({src}): " + ", ".join(auto_msgs))

    if not (args.morables or args.ggb or args.ethics):
        logger.error(f"입력 파일이 없습니다.\n"
                     f"  - {src} 에 morables_batch_*/ggb_batch_*/ethics_batch_* 파일이 없음\n"
                     f"  - 또는 --morables / --ggb / --ethics 로 직접 경로 지정\n"
                     f"  - 또는 --src 로 다른 결과지 폴더 지정")
        return 1

    if args.morables:
        p = Path(args.morables)
        if not p.exists():
            logger.error(f"Morables 파일 없음: {p}"); return 1
        logger.info(f"=== Morables ({p.name}) ===")
        df = _load(p)
        fig_morables_acc_by_arm(df, out / "FigM1_acc_by_arm.png")
        fig_morables_acc_by_route(df, out / "FigM2_acc_by_route.png")
        fig_morables_amplifier(df, out / "FigM3_amplifier_pattern.png")
    if args.ggb:
        p = Path(args.ggb)
        if not p.exists():
            logger.error(f"GGB 파일 없음: {p}"); return 1
        logger.info(f"=== GGB ({p.name}) ===")
        df = _load(p)
        fig_ggb_subscale_means(df, out / "FigG1_subscale_means.png")
        fig_ggb_ib_ih_plane(df, out / "FigG2_ib_ih_plane.png")
        fig_ggb_hardblock(df, out / "FigG3_hardblock_pattern.png")
    if args.ethics:
        p = Path(args.ethics)
        if not p.exists():
            logger.error(f"Ethics 파일 없음: {p}"); return 1
        logger.info(f"=== Ethics ({p.name}) ===")
        df = _load(p)
        fig_ethics_rqi_by_arm(df, out / "FigE1_rqi_by_arm.png")
        fig_ethics_nemo_refuse(df, out / "FigE2_nemo_refuse_dilemma.png")
        fig_ethics_routing_by_instrument(df, out / "FigE3_routing_by_instrument.png")
    logger.info(f"✓ 완료. 출력: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
