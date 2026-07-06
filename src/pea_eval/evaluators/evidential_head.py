#!/usr/bin/env python3
"""Evidential Neutrosophic head (D19) — subjective-logic T/I/F/C from learned evidence.

Root-cause fix (D18): the legacy head trains 3 free sigmoids with I supervised as a "moral-dilemma"
class — that is NOT neutrosophic indeterminacy, so ambiguous inputs get confidently misclassified
instead of abstaining. Here the head emits TWO non-negative evidence masses (safe, harm) and T/I/F are
DERIVED by the subjective-logic / Dirichlet map, so I = genuine indeterminacy (low total evidence) and
C = conflict (both sides have evidence). Binary supervision on safe/harm; I/C emerge.

  evidence e_s,e_h = softplus(logits) ≥ 0 ;  S = e_s + e_h + W   (W = prior weight)
    T = e_s / S   (belief: safe)
    F = e_h / S   (belief: harm)
    I = W   / S   (ignorance: weak total evidence)          — T+F+I = 1
    C = 2·min(e_s,e_h) / S   (conflict: both sides supported) — distinct from I

Routing (neutro_route_evidential): defer if I≥τ_I (ignorance) OR C≥τ_C (conflict); else F−T / T−F decide.
This module is ADDITIVE — the legacy `build_neutro_head` path is untouched; an evidential checkpoint is
detected by the `scheme=="evidential"` field. Pure-math `opinion()` is backend-agnostic (numpy/torch);
the torch head + loss live in functions that import torch lazily.
"""
from __future__ import annotations


# ── backend-agnostic derivation (numpy arrays OR torch tensors) ──────────────
def opinion(e_safe, e_harm, W: float = 2.0):
    """Subjective-logic opinion from non-negative evidence. Returns dict T,I,F,C,S.
    Works for python floats, numpy arrays, or torch tensors (only +,-,*,/,min used)."""
    S = e_safe + e_harm + W
    T = e_safe / S
    F = e_harm / S
    I = W / S
    # conflict = 2·min(e_s,e_h)/S  → in [0, 1-I]; =max when e_s==e_h. Use a min that works on both backends.
    try:
        import numpy as _np
        mn = _np.minimum(e_safe, e_harm) if isinstance(e_safe, _np.ndarray) else None
    except Exception:
        mn = None
    if mn is None:
        try:
            import torch as _t
            if hasattr(e_safe, "shape") and not isinstance(e_safe, float):
                mn = _t.minimum(e_safe, e_harm)
        except Exception:
            mn = None
    if mn is None:
        mn = min(e_safe, e_harm)
    C = 2.0 * mn / S
    return {"T": T, "I": I, "F": F, "C": C, "S": S}


def _softplus_np(x):
    import numpy as np
    return np.log1p(np.exp(-np.abs(x))) + np.maximum(x, 0.0)   # stable softplus


def opinion_from_logits_np(logits, W: float = 2.0):
    """numpy: (…,2) logits → opinion. logits[...,0]=safe, [...,1]=harm."""
    import numpy as np
    e = _softplus_np(np.asarray(logits, dtype=np.float64))
    return opinion(e[..., 0], e[..., 1], W)


# ── routing on the evidential opinion ───────────────────────────────────────
def neutro_route_evidential(T, I, F, C, tau_I: float, tau_C: float, margin: float = 0.0) -> str:
    """defer (reasoning) on ignorance OR conflict; else decisive harm/safe by belief gap."""
    if I >= tau_I or C >= tau_C:
        return "reasoning"
    if F - T >= margin:
        return "refusal"
    if T - F >= margin:
        return "1-pass"
    return "reasoning"


# ── torch: head + Sensoy evidential loss (used in training / inference) ──────
def build_evidential_head(in_dim: int, hidden: int = 128):
    """Same trunk as build_neutro_head but final layer = 2 RAW evidence logits (no sigmoid).
    Evidence = softplus(logits) is applied in the derivation, not the layer."""
    import torch.nn as nn
    return nn.Sequential(
        nn.Linear(in_dim, hidden), nn.ReLU(), nn.Dropout(0.2),
        nn.Linear(hidden, 64), nn.ReLU(),
        nn.Linear(64, 2),                      # raw evidence logits (safe, harm)
    )


def evidence_of(logits):
    """torch: softplus → non-negative evidence (…,2)."""
    import torch.nn.functional as Fn
    return Fn.softplus(logits)


def opinion_torch(logits, W: float = 2.0):
    e = evidence_of(logits)
    return opinion(e[..., 0], e[..., 1], W)


def evidential_loss(logits, y_onehot, lam_kl: float = 1.0, harm_weight: float = 1.0):
    """Sensoy (2018) evidential loss for K=2: Bayes-risk MSE + annealed KL regularizer.

    logits: (B,2) raw; y_onehot: (B,2) one-hot over (safe, harm). lam_kl annealed 0→1 by caller.
    harm_weight>1 makes a harm false-negative costlier (asymmetric safety — under-block is worse).
    """
    import torch
    import torch.nn.functional as Fn
    e = Fn.softplus(logits)                      # (B,2) evidence ≥0
    alpha = e + 1.0                              # Dirichlet params
    S = alpha.sum(dim=1, keepdim=True)           # (B,1)
    p = alpha / S                                # mean
    # Bayes-risk MSE: ||y-p||^2 + Var
    err = (y_onehot - p) ** 2
    var = p * (1.0 - p) / (S + 1.0)
    mse = (err + var).sum(dim=1)                 # (B,)
    # KL(Dir(alpha_tilde) || Dir(1)) with evidence removed from the correct class
    alpha_t = y_onehot + (1.0 - y_onehot) * alpha   # keep wrong-class evidence, reset correct to 1
    K = y_onehot.shape[1]
    St = alpha_t.sum(dim=1, keepdim=True)
    kl = (torch.lgamma(St.squeeze(1)) - torch.lgamma(torch.tensor(float(K), device=logits.device))
          - torch.lgamma(alpha_t).sum(dim=1)
          + ((alpha_t - 1.0) * (torch.digamma(alpha_t) - torch.digamma(St))).sum(dim=1))
    w = torch.where(y_onehot[:, 1] > 0.5, torch.full_like(mse, harm_weight), torch.ones_like(mse))
    return (w * (mse + lam_kl * kl)).mean()


# ── selftest (pure numpy math, no torch) ─────────────────────────────────────
def _selftest():
    import numpy as np
    # invariants: T+F+I==1 ; clear safe/harm/ignorance/conflict behave correctly
    def op(es, eh, W=2.0): return opinion(np.array([es], float), np.array([eh], float), W)
    clear_safe = op(50, 0); clear_harm = op(0, 50); ignorance = op(0, 0); conflict = op(50, 50)
    for o in (clear_safe, clear_harm, ignorance, conflict):
        s = float((o["T"] + o["F"] + o["I"])[0]); assert abs(s - 1.0) < 1e-9, s
    assert clear_safe["T"][0] > 0.95 and clear_safe["I"][0] < 0.05 and clear_safe["C"][0] < 0.05
    assert clear_harm["F"][0] > 0.95 and clear_harm["C"][0] < 0.05
    assert ignorance["I"][0] > 0.95 and ignorance["C"][0] < 0.05          # no evidence → pure ignorance
    assert conflict["I"][0] < 0.05 and conflict["C"][0] > 0.95 and abs(conflict["T"][0] - conflict["F"][0]) < 1e-9
    # softplus-from-logits path (W=2 prior keeps some I at modest evidence — that's intended)
    o2 = opinion_from_logits_np([[8.0, -8.0]])
    assert o2["T"][0] > 0.7 and o2["F"][0] < 0.05, (o2["T"][0], o2["F"][0])
    # routing
    assert neutro_route_evidential(0.1, 0.85, 0.05, 0.1, tau_I=0.5, tau_C=0.5) == "reasoning"   # ignorance
    assert neutro_route_evidential(0.45, 0.05, 0.45, 0.9, tau_I=0.5, tau_C=0.5) == "reasoning"  # conflict
    assert neutro_route_evidential(0.1, 0.1, 0.8, 0.05, tau_I=0.5, tau_C=0.5) == "refusal"      # harm
    assert neutro_route_evidential(0.8, 0.1, 0.1, 0.05, tau_I=0.5, tau_C=0.5) == "1-pass"       # safe
    print("[selftest] evidential opinion + routing math OK")


if __name__ == "__main__":
    _selftest()
