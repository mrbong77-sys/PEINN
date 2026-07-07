# Finished checkpoints

The trained PEINN components, shipped for direct reproduction. Total ≈ 0.22 M
parameters (< 1 MB); the base LLM and the two sentence encoders are **not** here —
they are downloaded from their original sources at run time.

Verify integrity with `sha256sum -c MANIFEST.sha256`.

| File | Size | Params | Component / architecture |
|---|---|---|---|
| `ee_neutro_head_v4.pt` | 447 KB | 110,979 | **Neutro Head** (speech-act–aware). MLP `800→128→64→3`, three *independent* sigmoids → `T/I/F`. Input 800-d = 32 affect + 384 MiniLM semantic + 384 MiniLM principle-anchor. |
| `ee_emotion_readout_embedding.pt` | 242 KB | 59,616 | **Affect readout**. MLP `384→128→64→32` (frozen MiniLM embedding → 32-d affect). |
| `ee_hybrid_calibrator_best.pt` | 217 KB | 53,377 | **Hybrid energy calibrator**. concat(32-d affect, 768-d mpnet) → MLP → sigmoid ×10 = gating energy `E ∈ [0,10]`. |
| `neutro_gate_theta_v4.json` | 107 B | — | **Frozen gate thresholds θ** (extreme 9.4, harm 8.5, F 0.15, I 0.45, Fref 0.30, soft 8.5, Fblk 0.45). |

Only the Neutro Head is trained against the `T/I/F` objective; the readout and the
calibrator are trained separately and frozen (not trained jointly with the head).
The router itself has no learned weights — it is the fixed-threshold AND-gate in `θ`.

## Frozen encoders (downloaded, not shipped)
- `sentence-transformers/all-MiniLM-L6-v2` (384-d) — feeds the Neutro Head and the affect readout.
- `sentence-transformers/all-mpnet-base-v2` (768-d) — feeds the hybrid calibrator.
- The thirty Golden Anchors are in `src/core/golden_anchors.py`; each is embedded once with MiniLM at load time to form the head's principle-space channel.

## How to use
The router loads its weights from the data directory (`src/pea_eval/data/`, i.e.
`pea_eval.config.settings.DATA_DIR`) and reads the head path from the
`PEINN_NEUTRO_HEAD` environment variable. A minimal setup:

```bash
# from the repo root, with PYTHONPATH="$PWD/src"
cp checkpoints/ee_neutro_head_v4.pt            src/pea_eval/data/
cp checkpoints/ee_emotion_readout_embedding.pt src/pea_eval/data/
cp checkpoints/ee_hybrid_calibrator_best.pt    src/pea_eval/data/
export PEINN_NEUTRO_HEAD=ee_neutro_head_v4.pt   # selects the PEINN head
```

The gate is only used when the router is built with `engine="neutro_v21"`, and the
calibrator is loaded by a path relative to `src/`, so run with the current directory set to
`src/`. The benchmark driver `src/scripts/run_v21_bench.py` sets the engine and the head env for
you, so the simplest path is to use it rather than wiring these by hand. The gate thresholds θ
are frozen in code (`src/pea_eval/evaluators/intent_router.py`, `NeutroEERouterV21.THETA`); the
`neutro_gate_theta_v4.json` shipped here is a matching **reference copy**, not a file the router
loads.

Each `.pt` is a standard PyTorch archive; load with:

```python
import torch
ckpt = torch.load("checkpoints/ee_neutro_head_v4.pt", map_location="cpu")
state_dict = ckpt["state_dict"] if "state_dict" in ckpt else ckpt
```

To retrain any component from scratch instead, see
[`../docs/REGENERATE_CHECKPOINTS.md`](../docs/REGENERATE_CHECKPOINTS.md).
