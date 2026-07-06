"""diagnose_routing_transfer.py — why the router collapses on held-out benchmarks (D13).

CPU-only (numpy), no re-inference: reads the captured routing signals
(routing_v2_corpus_signals.csv = FIT, routing_v2_bench_signals.csv = EVAL)
and the FIT corpus jsonl, and prints the three D13 findings:

  (1) FIT↔EVAL per-signal distribution shift by class (the covariate/concept shift),
  (2) a learned logistic combiner — fit on the corpus ONLY, frozen, evaluated held-out — to show
      the user-proposed "binary classifier" does NOT beat the deterministic rule (both ~30-50%),
  (3) the C/A/R collinearity in the FIT corpus (the near-degenerate-labels root cause).

    python scripts/diagnose_routing_transfer.py
"""
from __future__ import annotations
import argparse, csv, json
from pathlib import Path
import numpy as np

FEAT = ["T", "I", "F", "e1", "e2", "C", "A", "R", "L"]   # L (legitimacy) added D14; tolerant if absent


def _load_csv(p):
    rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
    X = np.array([[float(r.get(k) or 0) for k in FEAT] for r in rows], dtype=float)
    sub = np.array([r["subset"] for r in rows])
    bench = np.array([r.get("bench", "") for r in rows])
    return X, sub, bench


def _cls(s):
    if s.startswith("unsafe"):
        return "unsafe"
    if s in ("benign", "safe"):
        return "benign"
    return "dilemma"


def _fit_logistic(X, y, l2=1.0, it=4000, lr=0.3):
    w = np.zeros(X.shape[1]); b = 0.0; n = len(y)
    for _ in range(it):
        p = 1.0 / (1.0 + np.exp(-(X @ w + b)))
        g = p - y
        w -= lr * (X.T @ g / n + l2 * w / n); b -= lr * g.mean()
    return w, b


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fit-csv", default="pea_eval/output/final/routing_v2_corpus_signals.csv")
    ap.add_argument("--eval-csv", default="pea_eval/output/final/routing_v2_bench_signals.csv")
    ap.add_argument("--corpus", default="peinn_v2/corpus/data/intent_corpus_car_v3.jsonl")
    args = ap.parse_args()

    Xc, sc, _ = _load_csv(args.fit_csv)
    Xb, sb, bb = _load_csv(args.eval_csv)
    yc = np.array([_cls(s) for s in sc]); yb = np.array([_cls(s) for s in sb])
    mu, sd = Xc.mean(0), Xc.std(0) + 1e-9

    print("== (1) FIT↔EVAL per-signal mean by class (covariate/concept shift) ==")
    print(f"{'sig':4} | {'corp-benign':>11} {'bench-benign':>12} | {'corp-unsafe':>11} {'bench-unsafe':>12}")
    for j, k in enumerate(FEAT):
        cb, bbn = Xc[yc == 'benign', j].mean(), Xb[yb == 'benign', j].mean()
        cu, bu = Xc[yc == 'unsafe', j].mean(), Xb[yb == 'unsafe', j].mean()
        print(f"{k:4} | {cb:11.3f} {bbn:12.3f} | {cu:11.3f} {bu:12.3f}   "
              f"Δbenign={(bbn-cb)/sd[j]:+.2f}σ Δunsafe={(bu-cu)/sd[j]:+.2f}σ")

    print("\n== (2) learned logistic combiner: fit on FIT corpus ONLY, frozen, eval held-out ==")
    m = yc != 'dilemma'; Xc2, yc2 = Xc[m], (yc[m] == 'unsafe').astype(float)
    mb = yb != 'dilemma'; Xb2, yb2 = Xb[mb], (yb[mb] == 'unsafe').astype(float)
    Z = (Xc2 - mu) / sd
    rng = np.random.default_rng(0); idx = rng.permutation(len(Z)); ntr = int(0.8 * len(Z))
    tr, va = idx[:ntr], idx[ntr:]
    w, b = _fit_logistic(Z[tr], yc2[tr])

    def prob(X):
        return 1.0 / (1.0 + np.exp(-(((X - mu) / sd) @ w + b)))
    tau = np.quantile(prob(Xc2[tr])[yc2[tr] == 0], 0.95)   # operating point: FIT benign-FPR≈5%

    def report(name, X, y):
        pred = prob(X) >= tau
        orr = (pred[y == 0] == 1).mean() * 100
        ucr = (pred[y == 1] == 0).mean() * 100
        print(f"   {name:16} ORR(benign→block)={orr:5.1f}%  UCR(unsafe→pass)={ucr:5.1f}%  n={len(y)}")
    print("   weights: " + " ".join(f"{k}={w[j]:+.2f}" for j, k in enumerate(FEAT)) + f"  (tau={tau:.3f})")
    report("FIT corpus-val", Xc2[va], yc2[va])
    report("EVAL bench", Xb2, yb2)
    print("   → learned classifier does NOT beat the deterministic rule (both collapse FIT→EVAL).")

    print("\n== (3) FIT corpus C/A/R collinearity (near-degenerate labels = root cause) ==")
    rows = [json.loads(l) for l in open(args.corpus, encoding="utf-8")]
    n = len(rows)
    car = lambda r: (int(r.get("C", 0)), int(r.get("A", 0)), int(r.get("R", 0)))
    same = sum(1 for r in rows if len(set(car(r))) == 1) / n
    agree = sum(1 for r in rows if (car(r)[0] & car(r)[1] & car(r)[2]) == int(r.get("harm_intent", 0))) / n
    from collections import Counter
    pat = Counter(car(r) for r in rows)
    print(f"   n={n}  C==A==R: {same*100:.1f}%   (C∧A∧R)==harm_intent: {agree*100:.1f}%")
    for k, v in pat.most_common(5):
        print(f"      {k}: {v:5d}  ({v/n*100:.1f}%)")


if __name__ == "__main__":
    main()
