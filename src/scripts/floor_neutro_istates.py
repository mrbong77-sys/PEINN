"""floor_neutro_istates.py — structural I-floor on the REAL ee_3class data (Neutro head).

Audit (2026-06-22) of pea_eval/data/ee_3class/train.csv showed I(indeterminacy) is a
"moral-dilemma-TOPIC detector": 95% of high-I rows come from dedicated dilemma sources, and
76% of genuine T/F-conflict rows (T>=0.4 AND F>=0.4) carry I<0.3. That violates the Smarandache
paradox / contradiction principle (Leyva-Vázquez & Smarandache 2025, Table 1): co-active T and F
(hyper-truth) GENERATE indeterminacy. Contradiction signature there is (T,I,F)=(0.50,0.60,0.40).

This applies a DETERMINISTIC (no-LLM) I-floor on the existing soft targets — it ONLY raises I,
never touches T/F (so T+I+F grows >1, the over-determined/contradiction regime, which is correct):

    kappa     = min(T, F)                      # co-activation strength
    I_floor   = clip(SCALE * kappa, 0, ICAP)   # anchored so kappa≈0.40 -> ~0.60 (paper contradiction)
    I_target  = max(I_judge, I_floor)  if kappa >= KMIN  else I_judge

Clear cases (one of T/F ~0) have kappa~0 -> untouched; dilemmas already have high I -> untouched;
only real T/F-conflict prompts get the structural indeterminacy that routes them to 2pass-reasoning.

    python scripts/floor_neutro_istates.py            # writes *_v2.csv next to the originals
"""
from __future__ import annotations
import argparse, csv
from pathlib import Path

csv.field_size_limit(2**31 - 1)
DATA = Path("pea_eval/data/ee_3class")


def _f(r, k):
    try: return float(r[k])
    except (TypeError, ValueError): return 0.0


def floor_I(T, F, scale, kmin, icap):
    kappa = min(T, F)
    if kappa < kmin:
        return 0.0
    return min(icap, scale * kappa)


def transform(rows, scale, kmin, icap):
    changed, deltas = 0, []
    for r in rows:
        T, I, F = _f(r, "T"), _f(r, "I"), _f(r, "F")
        flo = floor_I(T, F, scale, kmin, icap)
        new = max(I, flo)
        if new > I + 1e-9:
            changed += 1; deltas.append(new - I)
            r["I"] = round(new, 4)
    return changed, deltas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=float, default=1.5, help="I_floor = scale*min(T,F); 1.5 -> .40↦.60")
    ap.add_argument("--kmin", type=float, default=0.3, help="apply only when min(T,F)>=kmin (real conflict)")
    ap.add_argument("--icap", type=float, default=0.85, help="cap structural I below pure-dilemma ~0.98")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    for name in ("train", "heldout"):
        src = DATA / f"{name}.csv"
        rows = list(csv.DictReader(open(src, encoding="utf-8-sig")))
        ch, deltas = transform(rows, args.scale, args.kmin, args.icap)
        mean_d = sum(deltas) / len(deltas) if deltas else 0.0
        print(f"[{name}] {len(rows)} rows · I-floor raised {ch} ({100*ch//len(rows)}%) · mean ΔI {mean_d:.2f}")
        if not args.dry_run:
            out = DATA / f"{name}_v2.csv"
            with open(out, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=["text", "source", "T", "I", "F"])
                w.writeheader(); w.writerows(rows)
            print(f"  → {out}")


if __name__ == "__main__":
    main()
