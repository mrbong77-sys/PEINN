"""CPU smoke test for the structured-threat encoder — torch only, no transformers/download.

Validates: forward shapes, energy∈(0,1), the gating property (any axis→0 ⇒ energy→0; all
axes→1 ⇒ energy→1), and one backward pass. Run on any torch box (incl. the DGX):

    python -m peinn_v2.encoder.smoke_test
"""
import torch
from peinn_v2.encoder.model import StructuredThreatEncoder, TinyBackbone, GatedLogisticCombiner


def main():
    torch.manual_seed(0)
    B, L, V = 4, 12, 512
    model = StructuredThreatEncoder(TinyBackbone(vocab=V, hidden=32))
    ids = torch.randint(0, V, (B, L))
    mask = torch.ones(B, L, dtype=torch.long)

    out = model(ids, mask)
    assert out["axis_logits"].shape == (B, 3), out["axis_logits"].shape
    assert out["axis_probs"].shape == (B, 3)
    assert out["energy"].shape == (B,)
    assert torch.all((out["energy"] > 0) & (out["energy"] < 1))
    print(f"[ok] forward: axis_probs {tuple(out['axis_probs'].shape)}, "
          f"energy {tuple(out['energy'].shape)} ∈(0,1)")

    # gating: combiner alone (weights = softplus(0) > 0 so every axis gates)
    comb = GatedLogisticCombiner(3)
    allhi = comb(torch.tensor([[0.99, 0.99, 0.99]]))
    onelo = comb(torch.tensor([[0.99, 0.99, 0.01]]))
    alllo = comb(torch.tensor([[0.01, 0.01, 0.01]]))
    print(f"[ok] gating: all-high={allhi.item():.3f}  one-axis-low={onelo.item():.3f}  "
          f"all-low={alllo.item():.3f}")
    assert allhi.item() > 0.8 and onelo.item() < 0.5 and alllo.item() < 0.05, "gating broken"

    # one backward pass
    loss = out["energy"].mean() + out["axis_logits"].pow(2).mean()
    loss.backward()
    g = sum(p.grad.abs().sum().item() for p in model.parameters() if p.grad is not None)
    assert g > 0, "no gradient flowed"
    print(f"[ok] backward: total |grad| = {g:.3f}")
    print("SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
