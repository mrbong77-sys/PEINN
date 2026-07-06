#!/usr/bin/env python3
"""fill_neutro_v3_offpolar.py — soft-negative imputation of the un-chosen polar (NeutroEE v3).

The 2-of-3 labels leave one polar (F when polar=T, T when polar=F) UNLABELED → masked. Pure
masking starved each polar head of negatives → "always-high F" collapse (S2). User's fix: the
polarity choice itself implies the off-polar is LOW, so impute the missing third value with a
WEAK soft-negative — a seeded random draw in [lo, hi] normalized (default 0..0.2 = 0..1 of 5
points, mean ~0.1). This is label-smoothing for the implied negative; it ADDS the missing
"benign ⟹ F≈0" mass without re-querying the judge, and keeps calibration healthy (no hard-0
sigmoid saturation).

Operates on the EXISTING split (v3/train.csv, v3/heldout.csv) so the partition is identical to
the masked run → clean A/B. Sets mask_*=1 (now all three supervised) and writes *_soft.csv.

Pure stdlib + deterministic (seeded) → runs anywhere; outputs versioned for DGX retrain:
  python scripts/fill_neutro_v3_offpolar.py            # default lo=0.0 hi=0.2 seed=42
  python scripts/train_neutro_head.py \
      --train-csv pea_eval/data/ee_3class/v3/train_soft.csv \
      --heldout-csv pea_eval/data/ee_3class/v3/heldout_soft.csv \
      --out pea_eval/data/ee_neutro_head_v3_soft.pt --epochs 60 --i-weight 2.5
"""
from __future__ import annotations

import argparse
import csv
import random
import statistics
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

V3_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class" / "v3"
FIELDNAMES = ["text", "source", "polar", "T", "I", "F", "mask_T", "mask_I", "mask_F"]


def fill_split(in_path: Path, out_path: Path, rng: random.Random, lo: float, hi: float) -> dict:
    rows = list(csv.DictReader(open(in_path, encoding="utf-8")))
    filled_vals = []
    for r in rows:
        # off-polar = the one currently masked out (mask==0); polar=T → fill F, polar=F → fill T.
        if r["polar"] == "T":
            v = round(rng.uniform(lo, hi), 4)
            r["F"] = f"{v}"; r["mask_F"] = "1"; filled_vals.append(v)
        elif r["polar"] == "F":
            v = round(rng.uniform(lo, hi), 4)
            r["T"] = f"{v}"; r["mask_T"] = "1"; filled_vals.append(v)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        w.writeheader(); w.writerows(rows)
    Tm = statistics.mean(float(r["T"]) for r in rows)
    Fm = statistics.mean(float(r["F"]) for r in rows)
    return {"n": len(rows), "filled": len(filled_vals),
            "fill_mean": round(statistics.mean(filled_vals), 4) if filled_vals else 0.0,
            "fill_max": round(max(filled_vals), 4) if filled_vals else 0.0,
            "T_mean_all": round(Tm, 4), "F_mean_all": round(Fm, 4)}


def main() -> int:
    ap = argparse.ArgumentParser(description="NeutroEE v3 off-polar soft-negative imputation")
    ap.add_argument("--lo", type=float, default=0.0, help="fill lower bound (normalized)")
    ap.add_argument("--hi", type=float, default=0.2, help="fill upper bound (normalized; 0.2 = 1 of 5 pts)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--dir", default=str(V3_DIR),
                    help="dir holding {train,heldout}.csv (default v3; use .../v4 for the v4 pipeline)")
    args = ap.parse_args()
    work_dir = Path(args.dir)
    rng = random.Random(args.seed)
    for split in ("train", "heldout"):
        src = work_dir / f"{split}.csv"
        if not src.exists():
            print(f"[skip] {src} 없음 (먼저 label_ee_3class_v3.py 실행)"); continue
        rep = fill_split(src, work_dir / f"{split}_soft.csv", rng, args.lo, args.hi)
        print(f"[{split}] {rep}  → {split}_soft.csv")
    print(f"fill ~ U[{args.lo},{args.hi}] (0..{args.hi*5:.0f}/5 pts), seed={args.seed}; "
          f"off-polar now supervised (mask=1). Retrain with *_soft.csv.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
