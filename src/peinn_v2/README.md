# peinn_v2 — Structured-Threat Energy (optional v2.0 seam)

> **Not the final v2.1 energy.** PEINN **v2.1** routes on the frozen `HybridCalibrator` energy
> (see `../../docs/PEINN_v2.1.md` §4.2). This package is an **optional, default-off experimental
> energy seam** from the earlier v2.0 research line — activated only with `PEINN_V2_ENERGY=1` (the
> sanctioned D7 touch-point in `pea_eval/evaluators/ee_runner.py`). It is kept for completeness and
> for its design notes; the final routing path does not use it.

The seam is an **encoder-only (no-LLM)** model that scores a request's **structure** —
*actionability × realizability × definiteness* — learned **topic-invariantly** on an **independent
corpus (never the evaluation benchmarks)**, as an alternative to the affect-classifier energy that
over-fired on emotionally charged but benign input.

> Repository-level docs: `../../docs/PEINN_v2.1.md` (authoritative design), `../../docs/ARCHITECTURE.md`,
> `../../docs/REPRODUCTION.md`, `../../docs/REGENERATE_CHECKPOINTS.md`.

## Invariants (non-negotiable constraints)

1. **Benchmarks are held-out for evaluation ONLY.** The six evaluation benchmarks (HarmBench,
   XSTest, Taxonomy, Ethics, Morables, GGB) are never training data. (Training on them =
   contamination = the keyword-overfit OOD failure.)
2. **No LLM at INFERENCE.** The deployed encoder is encoder-only (DeBERTa class), self-contained,
   deterministic — core to PEINN's identity. Training data **may** be LLM-generated; the one
   binding data rule is invariant #1 (no benchmark contamination).
3. **Learn STRUCTURE, not TOPIC.** The discriminator scores pragmatic structure (the requested
   action), not subject-matter keywords or affect intensity.
4. **Preserve the spine:** the EE 32-D emotion extraction stays frozen; the energy keeps its
   routing-threshold role; the Neutro Head (T/I/F) attaches via one opt-in seam.
5. **Composed objective, not a single discriminator:** unsafe-compliance and over-refusal are met
   by the multi-tier router (hard-block precision + 2-pass catch rate), not by one perfect
   threshold.
6. **Modular isolation:** PEAOS 1.0 (`core/`, `pea_eval/`) is preserved unchanged. All v2 work
   lives in this self-contained `peinn_v2/` package; it imports v1.0 read-only and attaches via
   one opt-in seam (`energy.py`). v1.0 never depends on v2.

## Package layout

| Path | Purpose |
|---|---|
| `design/ENCODER_SPEC.md` | encoder / heads / gated-combiner architecture spec |
| `design/CORPUS_DESIGN.md` | independent training-corpus design |
| `design/CAD_SCHEMA.md` | axis minimal-pair (CAD) labeling schema |
| `design/TYPOLOGY.md` | intent typology (T1–T8) + LLM data-generation schema |
| `research/STRUCTURED_THREAT_AXES.md` | literature → threat-axes design |
| `corpus/` | corpus generators: `llm_gen.py`, `cad_generator.py`, `inject_real.py`, `label_car.py`, … |
| `encoder/model.py` | the model: pluggable backbone + 3 axis heads + gated logistic combiner |
| `train/` | topic-split loader, CAD + supervised-contrastive + IRM losses, `train.py` (`--smoke`) |
| `energy.py` | the opt-in seam (`PEINN_V2_ENERGY=1`) that swaps the energy slot |

## Quick start

```bash
# CPU smoke test (no model download, no GPU) — validates the pipeline learns:
python -m peinn_v2.train.train --smoke

# real run (GPU):
python -m peinn_v2.train.train --backbone hf --model-name microsoft/deberta-v3-base \
    --epochs 8 --batch-pairs 16 --freeze-bottom 6 --out peinn_v2/encoder/ckpt.pt
```

`act × real × def` (after Threat = intent × capability × opportunity) feed a **gated** but
**calibrated** logistic combiner → `E_struct ∈ [0,1]`. The 32-D emotion vector never enters here:
the energy is affect-free, which is the over-fire fix.
