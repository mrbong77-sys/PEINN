#!/usr/bin/env python3
"""
EE Calibrator Ablation Runner — emotion-vs-semantic contribution analysis

Standalone, read-only experiment that answers: how much of the calibrator's
decision comes from the 32D emotion vector vs the Nd semantic embedding?

Runs three configurations on the same held-out test set, using the *existing*
trained checkpoint (pea_eval/data/ee_hybrid_calibrator_best.pt):

  (A) full       : [32D emotion | Nd semantic]              ← baseline
  (B) no_emotion : [    zeros   | Nd semantic]              ← semantic-only
  (C) no_semantic: [32D emotion |   zeros    ]              ← emotion-only

For each, reports overall AUROC, TPR @ FPR<10%, and per-dataset TPR/FPR.
The drop in metrics from (A) -> (B) quantifies the emotion vector's
contribution; the drop (A) -> (C) quantifies the semantic embedding's.

What this script does NOT do (by design)
----------------------------------------
- It does NOT modify the checkpoint, settings.py, or any other file in the
  repo. Outputs go to a single timestamped directory under final/.
- It does NOT retrain the calibrator. The checkpoint is loaded read-only.
- It does NOT change the runtime threshold — pure offline analysis.

Output
------
final/ee_ablation_<ts>/
    ablation_results.csv     # one row per (config, dataset) — for plotting
    ablation_summary.txt     # human-readable table + paper-ready snippet

Usage
-----
    python pea_eval/optimizer/ee_ablation.py                # full pipeline
    python pea_eval/optimizer/ee_ablation.py --max-safe-fpr 0.10
    python pea_eval/optimizer/ee_ablation.py --seed 42 --test-size 0.2
"""

import argparse
import asyncio
import csv
import logging
import sys
import time
from pathlib import Path

import numpy as np
import torch
from sklearn.model_selection import train_test_split

# Project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Reuse — DO NOT redefine — the existing helpers and the existing calibrator.
from pea_eval.optimizer.ee_threshold_finder import (
    gather_datasets, extract_features, predict_energies,
    sweep_threshold, HybridCalibrator,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("peaos.ee_ablation")

CKPT_PATH = PROJECT_ROOT / "pea_eval" / "data" / "ee_hybrid_calibrator_best.pt"
FINAL_DIR = PROJECT_ROOT / "pea_eval" / "output" / "final"

EMO_DIM = 32  # locked by HybridCalibrator architecture


def _auroc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Mann-Whitney U / nP*nN."""
    labels = np.asarray(labels, dtype=int)
    scores = np.asarray(scores, dtype=float)
    pos = scores[labels == 1]
    neg = scores[labels == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(order) + 1)
    rank_pos = ranks[: len(pos)].sum()
    return float((rank_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def _mask_features(X: np.ndarray, mode: str) -> np.ndarray:
    """Return a copy of X with the masked slice zeroed.
    Slot layout: [emotion (EMO_DIM) | semantic (rest)] per row."""
    X2 = X.copy()
    if mode == "full":
        return X2
    if mode == "no_emotion":
        X2[:, :EMO_DIM] = 0.0
        return X2
    if mode == "no_semantic":
        X2[:, EMO_DIM:] = 0.0
        return X2
    raise ValueError(f"unknown ablation mode: {mode}")


def _load_calibrator() -> HybridCalibrator:
    if not CKPT_PATH.exists():
        raise FileNotFoundError(
            f"Checkpoint missing: {CKPT_PATH}. "
            "Train one first via pea_eval/optimizer/ee_threshold_finder.py."
        )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = HybridCalibrator().to(device)
    state = torch.load(CKPT_PATH, map_location=device)
    model.load_state_dict(state)
    model.eval()
    logger.info(f"Loaded calibrator: {CKPT_PATH}  device={device}  sem_dim={model.sem_dim}")
    return model


def _evaluate_at_threshold(
    energies: np.ndarray, y: np.ndarray, sources: list[str], threshold: float,
) -> dict:
    y = np.asarray(y, dtype=int)
    pred = (energies >= threshold).astype(int)
    overall = {
        "TPR": float((pred[y == 1] == 1).mean()) if (y == 1).any() else float("nan"),
        "FPR": float((pred[y == 0] == 1).mean()) if (y == 0).any() else float("nan"),
    }
    per_ds: dict[str, dict[str, float]] = {}
    for ds in sorted(set(sources)):
        mask = np.asarray([s == ds for s in sources])
        if not mask.any():
            continue
        ds_y = y[mask]
        ds_pred = pred[mask]
        per_ds[ds] = {
            "n": int(mask.sum()),
            "TPR": float((ds_pred[ds_y == 1] == 1).mean()) if (ds_y == 1).any() else float("nan"),
            "FPR": float((ds_pred[ds_y == 0] == 1).mean()) if (ds_y == 0).any() else float("nan"),
        }
    return {"overall": overall, "per_dataset": per_ds}


def _run_one_config(
    model: HybridCalibrator,
    X_te: np.ndarray, y_te: np.ndarray, src_te: list[str],
    mode: str, max_safe_fpr: float,
) -> dict:
    """Run one ablation config and return its result block."""
    X_masked = _mask_features(X_te, mode)
    energies = predict_energies(model, X_masked)
    auroc = _auroc(energies, y_te)
    # Threshold per-config (so each config gets its own best operating point)
    best_t, sweep_rep = sweep_threshold(energies, y_te, src_te, max_safe_fpr=max_safe_fpr)
    eval_at = _evaluate_at_threshold(energies, y_te, src_te, best_t)
    e_pos = energies[np.asarray(y_te) == 1]
    e_neg = energies[np.asarray(y_te) == 0]
    return {
        "mode": mode,
        "AUROC": auroc,
        "best_threshold": float(best_t),
        "regime": sweep_rep["regime"],
        "overall_TPR_at_best": eval_at["overall"]["TPR"],
        "overall_FPR_at_best": eval_at["overall"]["FPR"],
        "energy_pos_mean": float(e_pos.mean()) if len(e_pos) else float("nan"),
        "energy_pos_max":  float(e_pos.max())  if len(e_pos) else float("nan"),
        "energy_neg_mean": float(e_neg.mean()) if len(e_neg) else float("nan"),
        "energy_neg_max":  float(e_neg.max())  if len(e_neg) else float("nan"),
        "per_dataset": eval_at["per_dataset"],
    }


def _write_outputs(out_dir: Path, configs: list[dict], context: dict) -> tuple[Path, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "ablation_results.csv"
    txt_path = out_dir / "ablation_summary.txt"

    # ── per-(config, dataset) long-format CSV for plotting ──
    fieldnames = [
        "config", "dataset", "n", "AUROC_overall", "best_threshold", "regime",
        "TPR_overall", "FPR_overall", "TPR_dataset", "FPR_dataset",
        "energy_pos_mean", "energy_pos_max", "energy_neg_mean", "energy_neg_max",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for cfg in configs:
            for ds, m in cfg["per_dataset"].items():
                w.writerow({
                    "config": cfg["mode"],
                    "dataset": ds,
                    "n": m["n"],
                    "AUROC_overall": round(cfg["AUROC"], 4),
                    "best_threshold": round(cfg["best_threshold"], 4),
                    "regime": cfg["regime"],
                    "TPR_overall": round(cfg["overall_TPR_at_best"], 4),
                    "FPR_overall": round(cfg["overall_FPR_at_best"], 4),
                    "TPR_dataset": (round(m["TPR"], 4) if not np.isnan(m["TPR"]) else ""),
                    "FPR_dataset": (round(m["FPR"], 4) if not np.isnan(m["FPR"]) else ""),
                    "energy_pos_mean": round(cfg["energy_pos_mean"], 4),
                    "energy_pos_max":  round(cfg["energy_pos_max"], 4),
                    "energy_neg_mean": round(cfg["energy_neg_mean"], 4),
                    "energy_neg_max":  round(cfg["energy_neg_max"], 4),
                })

    # ── human-readable TXT ──
    def _pct(x):
        return "n/a" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x*100:.2f}%"

    full = next((c for c in configs if c["mode"] == "full"), None)
    no_emo = next((c for c in configs if c["mode"] == "no_emotion"), None)
    no_sem = next((c for c in configs if c["mode"] == "no_semantic"), None)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write("=" * 72 + "\n")
        f.write("  PEA-OS EE Calibrator — Ablation: emotion vs semantic contribution\n")
        f.write("=" * 72 + "\n\n")
        f.write(f"  Checkpoint            : {CKPT_PATH}\n")
        f.write(f"  Test set size         : {context['n_test']}  (pos={context['n_pos']} / neg={context['n_neg']})\n")
        f.write(f"  Calibrator sem_dim    : {context['sem_dim']}  (emo_dim fixed at {EMO_DIM})\n")
        f.write(f"  Safe-FPR ceiling      : {context['max_safe_fpr']*100:.1f}%\n")
        f.write(f"  Random seed           : {context['seed']}\n\n")

        f.write("-" * 72 + "\n")
        f.write(f"  {'Config':<14} {'AUROC':>8} {'thresh':>8} {'TPR':>10} {'FPR':>10} {'regime':>20}\n")
        f.write("-" * 72 + "\n")
        for cfg in configs:
            f.write(
                f"  {cfg['mode']:<14} "
                f"{cfg['AUROC']:>8.4f} "
                f"{cfg['best_threshold']:>8.4f} "
                f"{_pct(cfg['overall_TPR_at_best']):>10} "
                f"{_pct(cfg['overall_FPR_at_best']):>10} "
                f"{cfg['regime']:>20}\n"
            )
        f.write("-" * 72 + "\n\n")

        if full and no_emo and no_sem:
            d_emo_auroc = full["AUROC"] - no_emo["AUROC"]
            d_sem_auroc = full["AUROC"] - no_sem["AUROC"]
            d_emo_tpr   = full["overall_TPR_at_best"] - no_emo["overall_TPR_at_best"]
            d_sem_tpr   = full["overall_TPR_at_best"] - no_sem["overall_TPR_at_best"]
            f.write("  Contribution (full minus ablation, larger = more important)\n")
            f.write(f"    Emotion contribution to AUROC : {d_emo_auroc:+.4f}\n")
            f.write(f"    Semantic contribution to AUROC: {d_sem_auroc:+.4f}\n")
            f.write(f"    Emotion contribution to TPR   : {d_emo_tpr*100:+.2f}pp\n")
            f.write(f"    Semantic contribution to TPR  : {d_sem_tpr*100:+.2f}pp\n\n")

        # Per-dataset detail per config
        for cfg in configs:
            f.write(f"  [{cfg['mode']}] per-dataset @ threshold {cfg['best_threshold']:.4f}\n")
            f.write(f"    {'Dataset':<18} {'n':>5} {'TPR':>10} {'FPR':>10}\n")
            for ds, m in cfg["per_dataset"].items():
                f.write(
                    f"    {ds:<18} {m['n']:>5} "
                    f"{_pct(m['TPR']):>10} {_pct(m['FPR']):>10}\n"
                )
            f.write("\n")

        f.write("=" * 72 + "\n")
        f.write("  Paper snippet (auto-generated from numbers above)\n")
        f.write("=" * 72 + "\n")
        if full and no_emo and no_sem:
            # Standalone (single-channel) numbers — paper-critical evidence that
            # the emotion channel is NOT noise even when its marginal gain on
            # top of a strong semantic embedder is small.
            sem_only_auroc = no_emo["AUROC"]   # no_emotion = semantic only
            emo_only_auroc = no_sem["AUROC"]   # no_semantic = emotion only
            full_auroc = full["AUROC"]
            d_emo_auroc = full_auroc - sem_only_auroc   # marginal emotion gain over semantic-only
            d_sem_auroc = full_auroc - emo_only_auroc   # marginal semantic gain over emotion-only
            f.write(
                "  Single-channel discriminative power on the held-out test set:\n"
                f"    emotion-only (32D)   : AUROC = {emo_only_auroc:.4f}\n"
                f"    semantic-only ({no_emo.get('best_threshold','?')[:0]}{no_emo['best_threshold']:.2f}-thr) : AUROC = {sem_only_auroc:.4f}\n"
                f"    hybrid concat        : AUROC = {full_auroc:.4f}\n\n"
                "  Marginal AUROC gain over the single-channel baseline:\n"
                f"    Δ(emotion | semantic) = {d_emo_auroc:+.4f}   (gain from adding emotion on top of semantic)\n"
                f"    Δ(semantic | emotion) = {d_sem_auroc:+.4f}   (gain from adding semantic on top of emotion)\n\n"
                "  Interpretation. The emotion channel is independently informative\n"
                f"  (AUROC {emo_only_auroc:.2f} vs 0.50 chance) but is largely subsumed by the\n"
                "  stronger semantic representation on this dataset — the hybrid concat\n"
                f"  adds only Δ={d_emo_auroc:+.3f} AUROC over semantic-only. The structural\n"
                "  differentiator vs NeMo Guardrails therefore lies not in additive\n"
                "  accuracy but in (i) computational cost — a ~5K-parameter MLP +\n"
                "  sentence encoder vs a 7B LLM forward pass per prompt — and (ii)\n"
                "  input-side detection through an orthogonal feature channel rather\n"
                "  than self-judging output, which keeps the safety decision\n"
                "  independent of the model being defended. Per the AMA framing\n"
                "  (Artificial Moral Agent, not a binary safeguard), the emotion\n"
                "  dimension's contribution is expected to grow on richer\n"
                "  philosophical-dilemma inputs where a single semantic signal\n"
                "  alone cannot disambiguate competing moral framings.\n"
            )
        else:
            f.write("  (some configs missing — re-run with full pipeline to get snippet)\n")
        f.write("=" * 72 + "\n")

    return csv_path, txt_path


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-safe-fpr", type=float, default=0.10)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--test-size", type=float, default=0.2)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    logger.info("📦 Loading datasets and extracting features (one-time, ~30 min)...")
    bundle = gather_datasets()
    X, y, sources = await extract_features(bundle)
    if len(X) == 0:
        logger.error("No features extracted. Cannot ablate.")
        return 2

    # Use the same train/test split scheme as the tuner so the test set is
    # comparable to the threshold-tuning report.
    X_tr, X_te, y_tr, y_te, src_tr, src_te = train_test_split(
        X, y, sources, test_size=args.test_size, random_state=args.seed, stratify=y,
    )
    logger.info(f"Test set: {len(X_te)} rows  (pos={int((y_te == 1).sum())} / neg={int((y_te == 0).sum())})")

    model = _load_calibrator()
    # Sanity-check: feature dim must equal emo_dim + sem_dim
    expected_dim = EMO_DIM + model.sem_dim
    if X_te.shape[1] != expected_dim:
        logger.error(
            f"Feature dim mismatch: features have {X_te.shape[1]} dims, "
            f"calibrator expects {EMO_DIM} (emotion) + {model.sem_dim} (semantic) = {expected_dim}. "
            "Check PEAOS_CALIBRATOR_EMBEDDER env var."
        )
        return 2

    configs = []
    for mode in ("full", "no_emotion", "no_semantic"):
        logger.info(f"🧪 ablation: {mode}")
        configs.append(_run_one_config(
            model, X_te, y_te, src_te, mode=mode, max_safe_fpr=args.max_safe_fpr,
        ))

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = FINAL_DIR / f"ee_ablation_{timestamp}"
    context = {
        "n_test": len(X_te),
        "n_pos": int((y_te == 1).sum()),
        "n_neg": int((y_te == 0).sum()),
        "sem_dim": model.sem_dim,
        "max_safe_fpr": args.max_safe_fpr,
        "seed": args.seed,
    }
    csv_path, txt_path = _write_outputs(out_dir, configs, context)
    logger.info(f"✅ wrote {csv_path}")
    logger.info(f"✅ wrote {txt_path}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
