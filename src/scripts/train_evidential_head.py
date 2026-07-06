#!/usr/bin/env python3
"""A/step-ii (D19) — train the Evidential Neutrosophic head.

Reuses the SAME feature extraction as the legacy head (neutro_features → emotion⊕semantic⊕principle, via
extract_features) and the SAME train/heldout CSVs, but:
  • supervision is BINARY safe(0)/harm(1), derived from the judge's primary dim (F-primary → harm,
    T-primary → safe). Dilemma rows (I-primary) are DROPPED from supervision — they are NOT a class; the
    evidential head learns to give them high I/C (indeterminacy) by leaving their evidence low.
  • loss is the Sensoy evidential loss (Bayes-risk MSE + annealed KL); I = ignorance, C = conflict EMERGE
    from evidence (D18 fix: I is no longer a supervised "dilemma" label).
  • after training, τ_I / τ_C are calibrated on held-out so the decisive (non-defer) region hits a
    precision target; coverage is reported (the ~80/20 split is descriptive, not forced).
Saves an evidential checkpoint (scheme="evidential") consumed by intent_router when present.

    python scripts/train_evidential_head.py --epochs 80 --out pea_eval/data/ee_evidential_head.pt
"""
from __future__ import annotations
import argparse, logging
from pathlib import Path
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.train_neutro_head import _load_csv, extract_features, DATA_DIR, TRAIN_CSV, HELDOUT_CSV  # noqa: E402
from pea_eval.evaluators.evidential_head import (  # noqa: E402
    build_evidential_head, evidential_loss, opinion_from_logits_np,
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("evidential")
OUT_PT = Path("pea_eval/data/ee_evidential_head.pt")


def binary_labels(Y):
    """3-dim judge soft-target (T=safe,I=dilemma,F=harm) → binary harm + a keep-mask (drop dilemma)."""
    prim = Y.argmax(1)                       # 0=safe,1=dilemma,2=harm
    keep = prim != 1                         # drop dilemma rows from supervision
    harm = (prim == 2).astype(np.int64)
    return harm, keep


def calibrate(opin, harm, target_prec=0.90):
    """Pick τ_I, τ_C so the DECISIVE (non-defer) set holds ≥target precision; report coverage.
    opin: dict of arrays T,I,F,C; harm: 0/1 labels (safe/harm)."""
    I, C, T, F = opin["I"], opin["C"], opin["T"], opin["F"]
    best = None
    for tI in np.quantile(I, np.linspace(0.3, 0.95, 25)):
        for tC in np.quantile(C, np.linspace(0.3, 0.95, 25)):
            decisive = (I < tI) & (C < tC)
            if decisive.sum() < 30:
                continue
            pred = (F > T)[decisive].astype(int)
            acc = (pred == harm[decisive]).mean()
            cov = decisive.mean()
            if acc >= target_prec and (best is None or cov > best[2]):
                best = (float(tI), float(tC), float(cov), float(acc))
    if best is None:                          # fall back to medians
        return float(np.median(I)), float(np.median(C)), 0.0, 0.0
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--W", type=float, default=2.0, help="evidential prior weight (I scale)")
    ap.add_argument("--kl-anneal", type=int, default=10, help="epochs to ramp KL 0→1")
    ap.add_argument("--harm-weight", type=float, default=1.5, help="asymmetric: harm FN costlier")
    ap.add_argument("--target-prec", type=float, default=0.90)
    ap.add_argument("--train-csv", default=str(TRAIN_CSV))
    ap.add_argument("--heldout-csv", default=str(HELDOUT_CSV))
    ap.add_argument("--out", default=str(OUT_PT))
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    import torch
    import torch.nn.functional as Fn
    torch.manual_seed(args.seed); np.random.seed(args.seed)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.ee_runner import EvalEERunner
    runner = EvalEERunner.get_instance(ee_config=load_settings("real").ee); runner.initialize()

    tr_texts, Ytr, _ = _load_csv(Path(args.train_csv))
    ho_texts, Yho, _ = _load_csv(Path(args.heldout_csv))
    Xtr = extract_features("train", tr_texts, runner)
    Xho = extract_features("heldout", ho_texts, runner)
    htr, keep = binary_labels(Ytr); hho, _ = binary_labels(Yho)
    Xtr, htr = Xtr[keep], htr[keep]           # drop dilemma from supervision
    logger.info(f"train {len(Xtr)} (safe {int((htr==0).sum())} / harm {int(htr.sum())}; dilemma dropped) · in_dim {Xtr.shape[1]}")

    model = build_evidential_head(Xtr.shape[1]).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    Xt = torch.tensor(Xtr, dtype=torch.float32, device=dev)
    yt = Fn.one_hot(torch.tensor(htr, device=dev), 2).float()
    N = len(Xt)
    for ep in range(args.epochs):
        model.train(); perm = torch.randperm(N, device=dev); tot = 0.0
        lam = min(1.0, (ep + 1) / max(args.kl_anneal, 1))
        for s in range(0, N, args.batch):
            idx = perm[s:s + args.batch]
            loss = evidential_loss(model(Xt[idx]), yt[idx], lam_kl=lam, harm_weight=args.harm_weight)
            opt.zero_grad(); loss.backward(); opt.step(); tot += float(loss) * len(idx)
        if (ep + 1) % 10 == 0 or ep == 0:
            logger.info(f"  epoch {ep+1:03d}  loss {tot/N:.4f}  λkl {lam:.2f}")

    # held-out opinions + calibration (use ALL heldout incl dilemma for I/C behaviour check)
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(Xho, dtype=torch.float32, device=dev)).cpu().numpy()
    op = opinion_from_logits_np(logits, args.W)
    op = {k: np.asarray(v) for k, v in op.items()}
    prim = Yho.argmax(1)
    for nm, mask in [("safe", prim == 0), ("dilemma", prim == 1), ("harm", prim == 2)]:
        if mask.any():
            logger.info(f"  heldout {nm:8s} n={int(mask.sum())}  meanI={op['I'][mask].mean():.2f}  "
                        f"meanC={op['C'][mask].mean():.2f}  mean(F-T)={ (op['F']-op['T'])[mask].mean():+.2f}")
    # calibrate on the safe/harm heldout rows
    keep_ho = prim != 1
    tI, tC, cov, acc = calibrate({k: op[k][keep_ho] for k in op}, (prim[keep_ho] == 2).astype(int),
                                 args.target_prec)
    logger.info(f"  calibrated τ_I={tI:.3f} τ_C={tC:.3f} → decisive coverage {cov:.0%} @ accuracy {acc:.0%}"
                f"  (defer {1-cov:.0%})")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    torch.save({"scheme": "evidential", "state_dict": model.state_dict(),
                "in_dim": int(Xtr.shape[1]), "W": args.W, "tau_I": tI, "tau_C": tC,
                "harm_weight": args.harm_weight}, args.out)
    logger.info(f"saved evidential head → {args.out}")


if __name__ == "__main__":
    main()
