"""v2.0 energy seam (D7) — the ONE opt-in provider the v1 backbone may call.

Deployed model is LLM-free: a fine-tuned encoder (DeBERTa-v3-base) + heads. Returns the
structured-threat energy on the [0,10] routing scale as a drop-in for v1's weighted_energy.

energy = 10 · harm · (1 − bp)
  • harm  = harm-intent head (the genuine-intent signal)
  • bp    = benign_purpose head (educational/defensive/simulated framing)
  harm·(1−bp): ordinary benign (harm≈0) → ~0; framed-benign (bp≈1) → ~0; direct harmful
  (harm high, bp low) → high. (1−bp alone is NOT used: it over-blocks unframed benign;
  see EXPERIMENTS E7.) Framed-harmful (jailbreak) → low → routed to 2-pass.

Activated only when PEINN_V2_ENERGY=1 (default off ⇒ v1 behaviour is byte-identical, D7).
"""
from __future__ import annotations
import os, threading

_LOCK = threading.Lock()
_CACHE: dict = {}


def _load(ckpt_path: str):
    import torch
    from peinn_v2.encoder.model import StructuredThreatEncoder, HFMeanPoolBackbone
    from peinn_v2.train.data import HFTokenizer
    ck = torch.load(ckpt_path, map_location="cpu")
    name = ck.get("model_name", "microsoft/deberta-v3-base")
    axes = ck.get("axes", ("harm", "op", "bp"))
    model = StructuredThreatEncoder(HFMeanPoolBackbone(name), axes=axes,
                                    primary_axis=ck.get("primary_axis", 0))
    model.load_state_dict(ck["model"])
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model.to(dev).eval()
    return model, HFTokenizer(name, max_len=64), dev, {a: i for i, a in enumerate(axes)}


def score_energy(text: str, ckpt_path: str | None = None) -> float:
    """Structured-threat energy in [0,10], axis-aware (cached singleton per checkpoint):
      • legacy holistic axes (harm, bp present) → 10·harm·(1−bp)  (v1 deployed seam, E7)
      • compositional axes (e.g. C/A/R)         → 10·combiner-energy (the C∧A∧R gate, D9/E20)
    """
    import torch
    ckpt_path = ckpt_path or os.environ.get("PEINN_V2_CKPT", "peinn_v2/encoder/ckpt.pt")
    with _LOCK:
        if ckpt_path not in _CACHE:
            _CACHE[ckpt_path] = _load(ckpt_path)
    model, tok, dev, ix = _CACHE[ckpt_path]
    with torch.no_grad():
        ids, mask = tok([text])
        out = model(ids.to(dev), mask.to(dev))
        if "harm" in ix and "bp" in ix:               # legacy holistic scheme
            p = out["axis_probs"][0].cpu().tolist()
            return 10.0 * p[ix["harm"]] * (1.0 - p[ix["bp"]])
        return 10.0 * float(out["energy"][0].cpu())   # compositional gate (combiner)


def score_axes(text: str, ckpt_path: str | None = None) -> dict:
    """Return the structured-threat encoder's per-axis probabilities, e.g. {harm, op, bp}."""
    import torch
    ckpt_path = ckpt_path or os.environ.get("PEINN_V2_CKPT", "peinn_v2/encoder/ckpt.pt")
    with _LOCK:
        if ckpt_path not in _CACHE:
            _CACHE[ckpt_path] = _load(ckpt_path)
    model, tok, dev, ix = _CACHE[ckpt_path]
    with torch.no_grad():
        ids, mask = tok([text])
        p = model(ids.to(dev), mask.to(dev))["axis_probs"][0].cpu().tolist()
    return {a: p[i] for a, i in ix.items()}
