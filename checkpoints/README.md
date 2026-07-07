# Finished checkpoints

The trained/frozen PEINN components, shipped for direct standalone reproduction.
The base LLM and the two sentence encoders are **not** here — they are downloaded
from their original sources at run time.

Verify integrity with `sha256sum -c MANIFEST.sha256`.

| File | Size | Params | Component / architecture |
|---|---|---|---|
| `ee_checkpoint_agent_a.pt` | ~54 MB | 13,414,433 | **Emotion Engine trunk** (agent A). Frozen affect network: MiniLM-384 embedding → cross-attention + MLP → a **32-d affect vector** (`tanh`, range `[-1,1]`) plus a scalar energy. This 32-d affect is the value consumed by the Neutro Head and the calibrator. |
| `ee_neutro_head_v4.pt` | 447 KB | 110,979 | **Neutro Head** (speech-act–aware). MLP `800→128→64→3`, three *independent* sigmoids → `T/I/F`. Input 800-d = 32 affect (from the trunk) + 384 MiniLM semantic + 384 MiniLM principle-anchor. |
| `ee_hybrid_calibrator_best.pt` | 217 KB | 53,377 | **Hybrid energy calibrator**. concat(32-d affect from the trunk, 768-d mpnet) → MLP → sigmoid ×10 = gating energy `E ∈ [0,10]`. |
| `ee_emotion_readout_embedding.pt` | 242 KB | 59,616 | **Affect read-out** (analysis / complexity signal only). MLP `384→128→64→32` on the frozen MiniLM embedding. **Not the routing affect** — that comes from the trunk above; the read-out only supplies the router's `complexity` dilemma-rescue signal. |
| `neutro_gate_theta_v4.json` | 107 B | — | **Frozen gate thresholds θ** (extreme 9.4, harm 8.5, F 0.15, I 0.45, Fref 0.30, soft 8.5, Fblk 0.45). |

The three small components (head 110.9K + calibrator 53.4K + read-out 59.6K ≈ 0.22 M,
< 1 MB) sit on top of the **Emotion Engine trunk**, a separate frozen ~13.4 M net that
produces the 32-d affect. The trunk is shipped here because — unlike the two sentence
encoders — it is a custom network and cannot be downloaded from a public source.

Only the Neutro Head is trained against the `T/I/F` objective; the calibrator and the
read-out are trained separately and frozen, and the Emotion Engine trunk is a frozen
feature extractor (not trained jointly with the head). The router itself has no learned
weights — it is the fixed-threshold AND-gate in `θ`.

## Frozen encoders (downloaded, not shipped)
- `sentence-transformers/all-MiniLM-L6-v2` (384-d) — the Emotion Engine trunk's input, and the Neutro Head's semantic + principle-anchor channels.
- `sentence-transformers/all-mpnet-base-v2` (768-d) — feeds the hybrid calibrator.
- The Golden Anchors are in `src/core/golden_anchors.py`; each is embedded once with MiniLM at load time to form the head's principle-space channel.

## How to use
The router loads its weights from the data directory (`src/pea_eval/data/`, i.e.
`pea_eval.config.settings.DATA_DIR`) and reads the head path from the
`PEINN_NEUTRO_HEAD` environment variable. Copy all shipped checkpoints there:

```bash
# from the repo root, with PYTHONPATH="$PWD/src"
cp checkpoints/ee_checkpoint_agent_a.pt        src/pea_eval/data/
cp checkpoints/ee_neutro_head_v4.pt            src/pea_eval/data/
cp checkpoints/ee_emotion_readout_embedding.pt src/pea_eval/data/
cp checkpoints/ee_hybrid_calibrator_best.pt    src/pea_eval/data/
export PEINN_NEUTRO_HEAD=ee_neutro_head_v4.pt   # selects the head
```

The calibrator uses the mpnet encoder by default (its shipped weights expect a 800-d
input = 32 affect + 768 mpnet), so no embedder env var is needed. The gate is only used
when the router is built with `engine="neutro_v21"`. The benchmark driver
`src/scripts/run_v21_bench.py` sets the engine and the head env for you, so the simplest
path is to use it rather than wiring these by hand. The gate thresholds θ are frozen in
code (`src/pea_eval/evaluators/intent_router.py`, `NeutroEERouterV21.THETA`); the
`neutro_gate_theta_v4.json` shipped here is a matching **reference copy**, not a file the
router loads.

Each `.pt` is a standard PyTorch archive; load with:

```python
import torch
ckpt = torch.load("checkpoints/ee_neutro_head_v4.pt", map_location="cpu")
state_dict = ckpt["state_dict"] if "state_dict" in ckpt else ckpt
```

The Emotion Engine trunk (`ee_checkpoint_agent_a.pt`) is a raw `state_dict` and is loaded
into `core.emotion_engine.EmotionEngine` automatically by the runner.

To retrain any component from scratch instead, see
[`../docs/REGENERATE_CHECKPOINTS.md`](../docs/REGENERATE_CHECKPOINTS.md).
