"""Training losses (S3, ENCODER_SPEC §3): supervised BCE + supervised-contrastive + IRM."""
from __future__ import annotations
import torch
import torch.nn.functional as F


def bce_loss(axis_logits, labels, pos_weight=None):
    """Per-axis BCE; pos_weight (3,) reweights the rarer HIGH-real/HIGH-def."""
    return F.binary_cross_entropy_with_logits(axis_logits, labels, pos_weight=pos_weight)


def _supcon_one(h, labels, temp=0.1):
    """Supervised contrastive (Khosla et al.) for one axis label over the batch embeddings."""
    B = h.size(0)
    sim = (h @ h.t()) / temp
    eye = torch.eye(B, dtype=torch.bool, device=h.device)
    sim = sim.masked_fill(eye, -1e9)
    pos = (labels.unsqueeze(0) == labels.unsqueeze(1)) & ~eye
    logp = F.log_softmax(sim, dim=1)
    has_pos = pos.sum(1) > 0
    if not has_pos.any():
        return h.new_zeros(())
    loss = -(logp * pos).sum(1) / pos.sum(1).clamp(min=1)
    return loss[has_pos].mean()


def supcon_loss(pooled, labels, temp=0.1):
    """Average SupCon over the 3 axes on the (normalized) shared representation.

    Pulls same-axis-value items from DIFFERENT topics together and pushes minimal-pair
    opposites apart → topic-invariant axis directions (PairCFR spirit)."""
    h = F.normalize(pooled, dim=-1)
    return sum(_supcon_one(h, labels[:, i], temp) for i in range(labels.size(1))) / labels.size(1)


def irm_penalty(axis_logits, labels, envs):
    """IRMv1 penalty (Arjovsky 2019) with topic as environment: gradient of the per-env risk
    w.r.t. a dummy unit scale; averaged over environments present in the batch.

    group-DRO fallback lives in train.py (config flag) per ENCODER_SPEC §3."""
    uniq = {}
    for i, e in enumerate(envs):
        uniq.setdefault(e, []).append(i)
    pen, cnt = axis_logits.new_zeros(()), 0
    for idx in uniq.values():
        if len(idx) < 2:
            continue
        sel = torch.tensor(idx, device=axis_logits.device)
        w = torch.ones((), device=axis_logits.device, requires_grad=True)
        risk = F.binary_cross_entropy_with_logits(axis_logits[sel] * w, labels[sel])
        g = torch.autograd.grad(risk, [w], create_graph=True)[0]
        pen = pen + g.pow(2); cnt += 1
    return pen / max(cnt, 1)


def total_loss(out, labels, envs, pos_weight=None, lambda_c=0.5, lambda_irm=1.0, temp=0.1):
    """L = BCE + λ_c·SupCon + λ_irm·IRM. Returns (loss, parts dict)."""
    bce = bce_loss(out["axis_logits"], labels, pos_weight)
    sc = supcon_loss(out["pooled"], labels, temp) if lambda_c > 0 else labels.new_zeros(())
    irm = irm_penalty(out["axis_logits"], labels, envs) if lambda_irm > 0 else labels.new_zeros(())
    loss = bce + lambda_c * sc + lambda_irm * irm
    parts = {k: float(v.detach()) for k, v in
             {"bce": bce, "supcon": sc, "irm": irm, "total": loss}.items()}
    return loss, parts
