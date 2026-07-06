#!/usr/bin/env python3
"""derive_tif_v4.py — combine v3 2-of-3 labels ⊗ illocution (D,S) → corrected 2-of-3 T/I/F.

NeutroEE v4 keeps the head's proven T/I/F format and the v3 labels' two strong, reused signals —
holistic harm (the v3 F, in-dist AUC 0.94) and dilemma/borderline (the v3 I, AUC 0.95) — and
CORRECTS them with the illocution axes (Directive D, Subversion S, label_illocution.py) so the
threat judgment finally honors speech-act structure:

    ¬D (D<τ_D)              → force polar=T   (narration/fable: demote even narrated "harm" → safe;
                                               fixes the morables over-fire root)
    D ∧ harm≥τ_h            → polar=F          (directive that UTTERS actionable harm = actualized)
    D ∧ S≥τ_s ∧ harm<τ_h    → polar=F (moderate) + I↑ (jailbreak frame, harm un-uttered = LATENT;
                                               e.g. taxonomy-t1 — refuse-the-frame, not hard-block)
    else                    → keep v3          (plain benign directive / v3 judgment stands)
genuine dilemma is preserved via the reused v3 I. Output = the v3 labeled.csv schema, so the
existing soft-impute (fill_neutro_v3_offpolar) + train (train_neutro_head --labels v4) reuse as-is.

Pure stdlib + deterministic. Runs anywhere.
  python scripts/derive_tif_v4.py \
    --v3 pea_eval/data/ee_3class/v4/labeled_2of3.csv \
    --illoc pea_eval/data/ee_3class/v4/illocution_labels.csv \
    --out pea_eval/data/ee_3class/v4/labeled.csv
  python scripts/derive_tif_v4.py --selftest
"""
from __future__ import annotations

import argparse
import csv
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

V4_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class" / "v4"
FIELDNAMES = ["text", "source", "polar", "T", "I", "F", "mask_T", "mask_I", "mask_F"]

# thresholds (on normalized [0,1]); D,S come in 0-5 → /5.
TAU_D = 0.2    # D ≥ 1.0/5 = a directive; below = narration. Demote also needs low harm (derive).
TAU_S = 0.5    # S ≥ 0.5 ⇒ jailbreak / safety-subversion framing
TAU_H = 0.30   # harm (v3 F) ≥ this ⇒ actualized harmful content
I_LATENT = 0.70  # latent-threat I floor (jailbreak frame, harm un-uttered)


def _f(v, d=0.0):
    try:
        return float(v)
    except Exception:
        return d


def _emit(polar: str, score: float, I: float) -> dict:
    """polar∈{T,F}: labeled = (polar, I); the other pole left masked (soft-imputed later)."""
    I = max(0.0, min(1.0, I))
    s = max(0.0, min(1.0, score))
    if polar == "T":
        return {"polar": "T", "T": round(s, 4), "I": round(I, 4), "F": 0.0,
                "mask_T": 1, "mask_I": 1, "mask_F": 0}
    return {"polar": "F", "T": 0.0, "I": round(I, 4), "F": round(s, 4),
            "mask_T": 0, "mask_I": 1, "mask_F": 1}


def derive(polar3, T3, I3, F3, D, S):
    """v3 (polar,T,I,F in [0,1]) ⊗ illocution (D,S in [0,1]) → corrected (polar, score, I)."""
    harm = F3 if polar3 == "F" else 0.0   # v3 holistic harm (meaningful only when v3 chose F)
    # Demote-to-T ONLY for benign narration (not-a-directive AND low harm). A harmful DECLARATIVE
    # statement (hate/doxxing: D~0 but harm high) is NOT narration → stays F (the leak guard).
    if D < TAU_D and harm < TAU_H:                  # benign narration: fable/story/neutral → safe
        polar, score, I = "T", max(T3, 0.5), I3
    elif harm >= TAU_H:                             # harmful content (requested OR declarative) → F
        polar, score, I = "F", harm, I3
    elif D >= TAU_D and S >= TAU_S:                 # directive ∧ jailbreak frame ∧ harm un-uttered
        polar, score, I = "F", 0.35 + 0.25 * S, max(I3, I_LATENT)   # latent: moderate F + high I
    elif polar3 == "T":                             # plain benign directive
        polar, score, I = "T", T3, I3
    else:
        polar, score, I = "F", F3, I3
    if S >= TAU_S:                                  # any jailbreak framing → latent-threat I floor
        I = max(I, I_LATENT)
    return _emit(polar, score, I)


def run(v3_path: Path, illoc_path: Path, out_path: Path) -> int:
    illoc = {}
    for r in csv.DictReader(open(illoc_path, encoding="utf-8")):
        illoc[r["text"]] = (_f(r["D"]) / 5.0, _f(r["S"]) / 5.0)
    rows_in = list(csv.DictReader(open(v3_path, encoding="utf-8")))
    out, miss = [], 0
    for r in rows_in:
        D, S = illoc.get(r["text"], (None, None))
        if D is None:
            miss += 1
            D, S = 0.0, 0.0          # no illocution → treat as non-directive (conservative: T)
        d = derive(r["polar"], _f(r["T"]), _f(r["I"]), _f(r["F"]), D, S)
        out.append({"text": r["text"], "source": r["source"], **d})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDNAMES); w.writeheader(); w.writerows(out)
    pol = Counter(r["polar"] for r in out)
    flips = sum(1 for a, b in zip(rows_in, out) if a["polar"] != b["polar"])
    print(f"derived {len(out)} → {out_path}  (illoc-miss {miss})")
    print(f"polar: {dict(pol)}  | v3→v4 polar flips: {flips}")
    _split(out, out_path.parent, seed=42, heldout_frac=0.15)
    return 0


def _split(rows, out_dir: Path, seed: int, heldout_frac: float):
    """Stratified (source,polar) split → train.csv / heldout.csv (feeds fill_neutro_v3_offpolar)."""
    rng = random.Random(seed)
    buckets = defaultdict(list)
    for r in rows:
        buckets[(r["source"], r["polar"])].append(r)
    train, heldout = [], []
    for _, g in buckets.items():
        rng.shuffle(g)
        k = max(1, int(round(len(g) * heldout_frac))) if len(g) > 1 else 0
        heldout.extend(g[:k]); train.extend(g[k:])
    for name, data in (("train.csv", train), ("heldout.csv", heldout)):
        with open(out_dir / name, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=FIELDNAMES); w.writeheader(); w.writerows(data)
    print(f"split: train {len(train)}  heldout {len(heldout)} → {out_dir}/{{train,heldout}}.csv")


def _selftest() -> int:
    # benign narration (fable: ¬D, low harm) → T  (the morables over-fire fix)
    d = derive("T", 0.9, 0.05, 0.0, D=0.0, S=0.0)
    assert d["polar"] == "T"
    # harmful DECLARATIVE statement (hate/doxxing: D≈0 but harm HIGH) → stays F  (LEAK GUARD)
    d = derive("F", 0.0, 0.05, 0.6, D=0.0, S=0.0)
    assert d["polar"] == "F" and d["F"] >= 0.5
    # actualized harm request (directive ∧ harm) → F
    d = derive("F", 0.0, 0.05, 0.7, D=1.0, S=0.4)
    assert d["polar"] == "F" and d["F"] >= 0.5
    # jailbreak frame (directive ∧ subversion, harm un-uttered) → F-moderate + high I (latent)
    d = derive("T", 0.6, 0.05, 0.0, D=0.9, S=1.0)
    assert d["polar"] == "F" and d["I"] >= I_LATENT and d["F"] < 0.7
    # genuine dilemma (narration scenario, low harm, high I) → T, I preserved
    d = derive("T", 0.4, 0.9, 0.0, D=0.1, S=0.0)
    assert d["polar"] == "T" and d["I"] == 0.9
    # plain benign request (directive, no harm, no subversion) → T
    d = derive("T", 0.95, 0.0, 0.0, D=0.8, S=0.0)
    assert d["polar"] == "T" and d["mask_F"] == 0
    # masks: I always supervised; exactly one polar supervised
    for x in [derive("F", 0, 0.05, 0.7, 1.0, 0.4), derive("T", 0.9, 0, 0.0, 0.0, 0.0)]:
        assert x["mask_I"] == 1 and x["mask_T"] + x["mask_F"] == 1
    print("SELFTEST OK — narration→T, hate-declarative→F (leak guard), actualized→F, "
          "jailbreak→latent-I, dilemma preserved")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NeutroEE v4: v3 ⊗ illocution → corrected 2-of-3 T/I/F")
    ap.add_argument("--v3", default=str(V4_DIR / "labeled_2of3.csv"),
                    help="v3-rubric 2-of-3 labels on the v4 (augmented) corpus")
    ap.add_argument("--illoc", default=str(V4_DIR / "illocution_labels.csv"))
    ap.add_argument("--out", default=str(V4_DIR / "labeled.csv"))
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    return run(Path(args.v3), Path(args.illoc), Path(args.out))


if __name__ == "__main__":
    raise SystemExit(main())
