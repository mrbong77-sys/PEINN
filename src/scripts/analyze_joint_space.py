#!/usr/bin/env python3
"""D15 — does the JOINT feature space separate harm/ambiguous/safe, and does it TRANSFER?

Background (DECISIONS D13/D14): the v2 encoder axes (C/A/R/L) are trained on the SYNTHETIC corpus
and collapse at the corpus→benchmark boundary (bench-benign ≈ bench-unsafe on every axis). The v1
EE emotion vector comes from a different engine (calibrated against benchmark features), so it may
carry transferable class structure the encoder axes lack. This script tests the user's hypothesis:
in the joint space [T,I,F,e1,e2,C,A,R,L | 32D emotion], do harm / ambiguous / safe separate — and
does a classifier fit on one distribution generalize to the other?

Pure numpy (+ matplotlib for the PCA picture); no sklearn. Reads the joint-space `.npz` emotion
dumps produced by the routing-signal capture step.

    python scripts/analyze_joint_space.py \
        --corpus peinn_v2/results/d15_emo_corpus.npz --bench peinn_v2/results/d15_emo_bench.npz
    python scripts/analyze_joint_space.py --selftest
"""
from __future__ import annotations
import argparse
import numpy as np


# ── labels ──────────────────────────────────────────────────────────────────
def cls3(subset: np.ndarray) -> np.ndarray:
    """3-class: 0=safe, 1=ambiguous(dilemma), 2=harm  (−1 = drop)."""
    out = np.full(len(subset), -1, int)
    for i, s in enumerate(subset):
        s = str(s)
        if s.startswith("unsafe"):
            out[i] = 2
        elif s in ("benign", "safe"):
            out[i] = 0
        elif s == "dilemma":
            out[i] = 1
    return out


# ── numpy primitives ────────────────────────────────────────────────────────
def auroc(scores: np.ndarray, y: np.ndarray) -> float:
    """Binary AUROC via rank-sum (y∈{0,1})."""
    pos, neg = scores[y == 1], scores[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    order = np.argsort(scores, kind="mergesort")
    ranks = np.empty(len(scores)); ranks[order] = np.arange(1, len(scores) + 1)
    # average ties
    s_sorted = scores[order]
    i = 0
    while i < len(s_sorted):
        j = i
        while j + 1 < len(s_sorted) and s_sorted[j + 1] == s_sorted[i]:
            j += 1
        if j > i:
            ranks[order[i:j + 1]] = (i + 1 + j + 1) / 2.0
        i = j + 1
    r_pos = ranks[y == 1].sum()
    return (r_pos - len(pos) * (len(pos) + 1) / 2.0) / (len(pos) * len(neg))


def standardize(Xtr, Xte):
    mu = Xtr.mean(0); sd = Xtr.std(0) + 1e-8
    return (Xtr - mu) / sd, (Xte - mu) / sd


def logreg(X, y, l2=1.0, iters=400, lr=0.5):
    """L2-regularized logistic regression, full-batch GD. Returns weights (with bias col)."""
    Xb = np.hstack([X, np.ones((len(X), 1))])
    w = np.zeros(Xb.shape[1])
    n = len(X)
    for _ in range(iters):
        p = 1.0 / (1.0 + np.exp(-Xb @ w))
        g = Xb.T @ (p - y) / n
        g[:-1] += l2 * w[:-1] / n
        w -= lr * g
    return w


def predict(w, X):
    return 1.0 / (1.0 + np.exp(-(np.hstack([X, np.ones((len(X), 1))]) @ w)))


def fisher_ratio(X, y):
    """Mean Fisher discriminant ratio (between/within var) over dims, harm(1) vs safe(0)."""
    a, b = X[y == 1], X[y == 0]
    if len(a) == 0 or len(b) == 0:
        return float("nan")
    between = (a.mean(0) - b.mean(0)) ** 2
    within = a.var(0) + b.var(0) + 1e-8
    return float(np.mean(between / within))


# ── feature assembly ────────────────────────────────────────────────────────
def feature_sets(d):
    sig, emo = d["sig"], d["emo"]
    sets = {"enc9 (T,I,F,e1,e2,C,A,R,L)": sig,
            "emo32 (v1 emotion)": emo,
            "joint41 (enc9+emo32)": np.hstack([sig, emo])}
    if "sem" in d.files:                      # D16/P0: the 384D frozen semantic channel
        sem = d["sem"]
        sets["sem384 (frozen semantic)"] = sem
        sets["joint425 (enc9+emo32+sem384)"] = np.hstack([sig, emo, sem])
    return sets


def eval_split(Xtr, ytr, Xte, yte, l2=1.0):
    Xtr2, Xte2 = standardize(Xtr, Xte)
    w = logreg(Xtr2, ytr.astype(float), l2=l2)
    return auroc(predict(w, Xtr2), ytr), auroc(predict(w, Xte2), yte)


def run(corpus_npz, bench_npz, png):
    C = np.load(corpus_npz, allow_pickle=True); B = np.load(bench_npz, allow_pickle=True)
    yC, yB = cls3(C["subset"]), cls3(B["subset"])
    fsC, fsB = feature_sets(C), feature_sets(B)
    print(f"corpus n={len(yC)}  (safe {np.sum(yC==0)} amb {np.sum(yC==1)} harm {np.sum(yC==2)})")
    print(f"bench  n={len(yB)}  (safe {np.sum(yB==0)} amb {np.sum(yB==1)} harm {np.sum(yB==2)})\n")

    # binary harm(2) vs safe(0); drop ambiguous for AUROC
    def binmask(y): return np.isin(y, [0, 2])
    print("══ harm-vs-safe AUROC  (↑ = separable) ══")
    print(f"{'feature set':30s} | bench in-dist (50/50) | corpus→bench transfer | Fisher(bench)")
    rng = np.random.default_rng(0)
    for name in fsC:
        XB, mB = fsB[name][binmask(yB)], (yB[binmask(yB)] == 2).astype(int)
        XC, mC = fsC[name][binmask(yC)], (yC[binmask(yC)] == 2).astype(int)
        # within-bench stratified 50/50
        idx = rng.permutation(len(XB)); half = len(idx) // 2
        tr, te = idx[:half], idx[half:]
        _, in_auc = eval_split(XB[tr], mB[tr], XB[te], mB[te])
        # corpus→bench transfer
        _, tr_auc = eval_split(XC, mC, XB, mB)
        XBs, _ = standardize(XB, XB)
        fr = fisher_ratio(XBs, mB)
        print(f"{name:30s} |        {in_auc:.3f}         |        {tr_auc:.3f}         |   {fr:.3f}")

    make_figure(fsB, yB, png)
    print(f"\n[viz] PCA(unsupervised) + LDA(supervised) 2-D maps, emo32 vs joint41 → {png}")


def pca2d(X):
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    U, S, Vt = np.linalg.svd(Xs - Xs.mean(0), full_matrices=False)
    var = (S[:2] ** 2 / (S ** 2).sum()) * 100
    return Xs @ Vt[:2].T, var


def lda2d(X, y):
    """Supervised multiclass LDA → ≤2 components. If classes separate HERE, distinct regions exist."""
    Xs = (X - X.mean(0)) / (X.std(0) + 1e-8)
    classes = np.unique(y); m_all = Xs.mean(0); d = Xs.shape[1]
    Sw = np.zeros((d, d)); Sb = np.zeros((d, d))
    for c in classes:
        Xc = Xs[y == c]; mc = Xc.mean(0)
        Sw += (Xc - mc).T @ (Xc - mc)
        dd = (mc - m_all)[:, None]; Sb += len(Xc) * (dd @ dd.T)
    Sw += np.eye(d) * 1e-2
    ev, evec = np.linalg.eig(np.linalg.pinv(Sw) @ Sb)
    W = evec[:, np.argsort(-ev.real)[:2]].real
    return Xs @ W


def make_figure(fs, y, png):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    pal = [(0, "#2a9d8f", "safe"), (1, "#e9c46a", "ambiguous"), (2, "#e76f51", "harm")]
    sets = (["sem384 (frozen semantic)", "joint425 (enc9+emo32+sem384)"]
            if "sem384 (frozen semantic)" in fs else ["emo32 (v1 emotion)", "joint41 (enc9+emo32)"])
    fig, axes = plt.subplots(2, 2, figsize=(13, 11))
    for r, name in enumerate(sets):
        X = fs[name]
        Zp, var = pca2d(X); Zl = lda2d(X, y)
        for col, (Z, title) in enumerate([(Zp, f"PCA  ({var[0]:.0f}%,{var[1]:.0f}% var)"),
                                          (Zl, "LDA  (supervised, max class-separation)")]):
            ax = axes[r, col]
            for c, color, lab in pal:
                m = y == c
                if m.any():
                    ax.scatter(Z[m, 0], Z[m, 1], s=7, alpha=0.45, c=color,
                               label=f"{lab} (n={m.sum()})", edgecolors="none")
            ax.set_title(f"{name}  —  {title}"); ax.legend(markerscale=2, fontsize=8)
            ax.set_xticks([]); ax.set_yticks([])
    fig.suptitle("Where do harm / ambiguous / safe live in the cloud?  (benchmarks)", fontsize=14)
    fig.tight_layout(); fig.savefig(png, dpi=130)


# ── selftest ────────────────────────────────────────────────────────────────
def selftest():
    rng = np.random.default_rng(1)
    # separable blobs → AUROC ~1; transfer holds when distributions match
    s = np.vstack([rng.normal(0, 1, (200, 5)), rng.normal(3, 1, (200, 5))])
    y = np.r_[np.zeros(200), np.ones(200)].astype(int)
    p = rng.permutation(len(s))
    _, a_te = eval_split(s[p][:300], y[p][:300], s[p][300:], y[p][300:])
    assert a_te > 0.95, a_te
    assert abs(auroc(np.array([.1, .4, .35, .8]), np.array([0, 0, 1, 1])) - 0.75) < 1e-9
    assert abs(auroc(np.array([.9, .1, .8, .2]), np.array([0, 1, 0, 1])) - 0.0) < 1e-9
    print("[selftest] auroc + logreg + split OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="peinn_v2/results/d15_emo_corpus.npz")
    ap.add_argument("--bench", default="peinn_v2/results/d15_emo_bench.npz")
    ap.add_argument("--png", default="peinn_v2/results/d15_joint_pca.png")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest(); return
    run(args.corpus, args.bench, args.png)


if __name__ == "__main__":
    main()
