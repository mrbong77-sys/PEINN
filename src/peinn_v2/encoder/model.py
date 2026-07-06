"""Structured-threat encoder (S2 spec). Encoder-only, no-LLM.

    text ─► backbone ─► pooled h ─► 3 axis heads ─► (act, real, def)∈[0,1]³
                                          └─► gated logistic combiner ─► E_struct∈[0,1]

Design points (design/ENCODER_SPEC.md):
  • heads are lightweight MLPs; multi-task over one shared encoder forces axis separation.
  • the combiner is GATED (any axis→0 collapses E, per Threat=intent×capability×opportunity)
    but CALIBRATED (a logistic on axis logits, not a raw product) — D6.
  • the 32-D emotion vector NEVER enters here: the energy is affect-free (the E3 over-fire fix).

The backbone is pluggable: HFMeanPoolBackbone (DeBERTa-v3-base, real training) or TinyBackbone
(torch-only, for CPU smoke tests without a model download).
"""
from __future__ import annotations
import torch
import torch.nn as nn
import torch.nn.functional as F

AXES = ("act", "real", "def")


def _logit(p: torch.Tensor, eps: float = 1e-6) -> torch.Tensor:
    p = p.clamp(eps, 1.0 - eps)
    return torch.log(p) - torch.log1p(-p)


class AxisHead(nn.Module):
    """pooled hidden → scalar axis logit."""
    def __init__(self, hidden: int, proj: int = 128, dropout: float = 0.1):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(hidden, proj), nn.GELU(), nn.Dropout(dropout), nn.Linear(proj, 1),
        )

    def forward(self, h: torch.Tensor) -> torch.Tensor:   # (B,H) → (B,)
        return self.net(h).squeeze(-1)


class GatedLogisticCombiner(nn.Module):
    """E = σ( α·logit(g) + b ),  where g = Π_i x_i^{ŵ_i}  (ŵ = softmax weights).

    g is a weighted GEOMETRIC MEAN — the configural AND-gate (D6): any x_i→0 ⇒ g→0 ⇒
    logit(g)→−∞ ⇒ E→0, regardless of the other axes. The outer logistic (temperature
    α=softplus(·)>0, bias b) CALIBRATES it without breaking the gate.

    NB: a plain additive-logit combiner (Σ w_i·logit x_i) does NOT gate — two high axes outvote
    one low one (.99,.99,.01 → 0.96). smoke_test caught this; hence the geometric-mean form.
    """
    def __init__(self, n: int = 3):
        super().__init__()
        self.raw_w = nn.Parameter(torch.zeros(n))    # softmax → equal init (weights sum to 1)
        self.raw_alpha = nn.Parameter(torch.zeros(()))  # softplus(0)=0.693 init temperature
        self.b = nn.Parameter(torch.zeros(()))

    def weights(self) -> torch.Tensor:
        return torch.softmax(self.raw_w, dim=-1)

    def forward(self, axis_probs: torch.Tensor) -> torch.Tensor:   # (B,n)∈(0,1) → (B,)
        logp = torch.log(axis_probs.clamp(1e-6, 1.0 - 1e-6))
        g = torch.exp((self.weights() * logp).sum(-1)).clamp(1e-6, 1.0 - 1e-6)
        alpha = F.softplus(self.raw_alpha)
        return torch.sigmoid(alpha * (torch.log(g) - torch.log1p(-g)) + self.b)


class HFMeanPoolBackbone(nn.Module):
    """DeBERTa-v3-base (default) with masked mean pooling. Real-training backbone."""
    def __init__(self, model_name: str = "microsoft/deberta-v3-base"):
        super().__init__()
        from transformers import AutoModel
        self.model = AutoModel.from_pretrained(model_name).float()  # force fp32: some
        # checkpoints load as fp16 (Half) → dtype mismatch with the fp32 heads.
        self.hidden = self.model.config.hidden_size

    def freeze_bottom_layers(self, n: int) -> None:
        """Overfit guard (ENCODER_SPEC §1): freeze embeddings + the bottom n encoder layers."""
        emb = getattr(self.model, "embeddings", None)
        if emb is not None:
            for p in emb.parameters():
                p.requires_grad_(False)
        enc = getattr(self.model, "encoder", None)
        layers = getattr(enc, "layer", None) if enc is not None else None
        if layers is not None:
            for layer in layers[:n]:
                for p in layer.parameters():
                    p.requires_grad_(False)

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        out = self.model(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state.float()
        mask = attention_mask.unsqueeze(-1).to(out.dtype)
        return (out * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


class TinyBackbone(nn.Module):
    """Deps-light embedding + mean-pool backbone for CPU smoke tests (no transformers/download)."""
    def __init__(self, vocab: int = 512, hidden: int = 32):
        super().__init__()
        self.emb = nn.Embedding(vocab, hidden)
        self.hidden = hidden

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> torch.Tensor:
        e = self.emb(input_ids)
        mask = attention_mask.unsqueeze(-1).to(e.dtype)
        return (e * mask).sum(1) / mask.sum(1).clamp(min=1e-6)


class StructuredThreatEncoder(nn.Module):
    """Shared backbone → axis heads → energy. Returns axis scores + energy.

    energy = the primary axis probability when `primary_axis` is set (intent scheme: harm_intent
    IS the energy; op/bp are auxiliary multi-task heads), else the gated combiner (the old
    act×real×def AND-gate).
    """
    def __init__(self, backbone: nn.Module, axes=AXES, primary_axis: int | None = None):
        super().__init__()
        self.backbone = backbone
        self.axes = tuple(axes)
        self.primary_axis = primary_axis
        hidden = backbone.hidden
        self.heads = nn.ModuleDict({a: AxisHead(hidden) for a in self.axes})
        self.combiner = GatedLogisticCombiner(len(self.axes))

    def forward(self, input_ids: torch.Tensor, attention_mask: torch.Tensor) -> dict:
        h = self.backbone(input_ids, attention_mask)                       # (B,H)
        logits = torch.stack([self.heads[a](h) for a in self.axes], -1)    # (B,n)
        probs = torch.sigmoid(logits)
        energy = probs[:, self.primary_axis] if self.primary_axis is not None \
            else self.combiner(probs)                                      # (B,)∈(0,1)
        return {"axis_logits": logits, "axis_probs": probs, "energy": energy, "pooled": h}

    @torch.no_grad()
    def score_energy_10(self, input_ids, attention_mask) -> torch.Tensor:
        """Routing-scale energy in [0,10] — drop-in for the existing hard-block threshold (D2)."""
        return 10.0 * self.forward(input_ids, attention_mask)["energy"]
