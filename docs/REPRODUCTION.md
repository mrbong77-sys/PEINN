# Reproducing PEINN

This is the **map**. It tells you what is reproducible on a laptop, what needs a GPU, and what
needs a full LLM-serving cluster — and points to the exact command for each step. The finished
checkpoints ship under [`../checkpoints/`](../checkpoints/); for the recipe to retrain them from
scratch instead, see [`REGENERATE_CHECKPOINTS.md`](REGENERATE_CHECKPOINTS.md).

## 0. What "reproduction" means here

The paper reports two things:

1. **A model** — the PEINN v2.1 routing module (Emotion Engine + speech-act-aware Neutro Head v4
   + the frozen HybridCalibrator energy + the deterministic AND-gate 5-tier router).
2. **An evaluation** — six safety/ethics benchmarks × four frozen base models, comparing
   `Vanilla`, `NeMo`, `R2D2`, and `PEINN` defenses.

Different parts have very different hardware needs:

| Layer | What it takes | Reproducible by users |
|---|---|---|
| Neutro Head v4 (T/I/F, speech-act-aware) | judge LLM for labels + 1 GPU | **Yes** (judge can be any capable local LLM) |
| Emotion-Engine energy (HybridCalibrator) | 1 GPU | **Yes** |
| Emotion read-out (analysis) | judge LLM + 1 GPU | **Yes** |
| Base Emotion Engine net | (frozen feature stage) | Not needed for the six-benchmark run; the RLAF training loop was part of the removed PEA-OS concept |
| Full benchmark sweep | Ollama/vLLM serving 4 base models + judges | Needs a serving cluster (e.g. a DGX) |

A reviewer can therefore **audit the architecture, rebuild the v4 head and the energy calibrator,
and re-tune the deterministic router on the six benchmarks** without a cluster. The full
6-benchmark × 17-arm sweep that produced the headline numbers requires LLM serving and is provided
as the exact reference code (`src/run_stat_batch.py`, `src/scripts/run_v21_bench.py`).

## 1. Environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="$PWD/src:$PYTHONPATH"      # src/ is the import root
```

Python ≥ 3.10. A CUDA GPU is recommended for any real training; the smoke tests are CPU-only.

## 2. Five-minute sanity check (CPU, no downloads)

```bash
cd src
python -m peinn_v2.train.train --smoke   # OPTIONAL v2.0 energy seam: pipeline wiring check
python -m peinn_v2.encoder.smoke_test    # OPTIONAL: encoder forward pass + gated combiner
```

These exercise the **optional** v2.0 structured-energy seam (no downloads) to confirm a torch
training loop is wired correctly. They are not the v2.1 routing path — the v2.1 energy is the
frozen HybridCalibrator (§3).

## 3. Reproduce each component

The full recipe — data regeneration commands, judge prompts, hyper-parameters, output paths —
is in [`REGENERATE_CHECKPOINTS.md`](REGENERATE_CHECKPOINTS.md). In brief, the **final v2.1**
components are:

1. **Neutro Head v4** (§2 of the regen guide) — speech-act-aware 2-of-3 distillation:
   `label_ee_3class_v3.py` → `fill_neutro_v3_offpolar.py` → `label_illocution.py` →
   `derive_tif_v4.py` → `build_neutro_v4_corpus.py` → `python scripts/train_neutro_head.py`
   (→ `ee_neutro_head_v4.pt`).
2. **Emotion-Engine energy** (§3) — the frozen `HybridCalibrator`
   (`python -m pea_eval.optimizer.ee_threshold_finder` → `ee_hybrid_calibrator_best.pt`).
3. **Emotion read-out** (§4, analysis only)
   `python scripts/label_ee_emotion.py …` → `python scripts/train_ee_emotion_readout.py --feature ee_hidden`.

The router itself (`NeutroEERouterV21`) needs no training — its operating point θ is locked in code.

## 4. Reproduce the evaluation

The benchmark arms (H01–H17) and module plan live in `src/run_stat_batch.py`; the v2.1 router
sweep is `src/scripts/run_v21_bench.py`. Both expect:

* a reachable base LLM. The self-contained backend in this repo is HuggingFace
  (`llm_backend: hf`); the native Ollama/vLLM/Gemini clients live in the excluded operational
  PEA-OS `integrations/` package, so to use an Ollama or vLLM server point its **OpenAI-compatible**
  `/v1` endpoint at an arm with `llm_backend: lmstudio`. See
  [the README "Bring your own base model" section](../README.md#bring-your-own-base-model);
* the two frozen sentence encoders (`all-MiniLM-L6-v2`, `all-mpnet-base-v2`), downloaded on first use;
* the **shipped checkpoints copied into `src/pea_eval/data/`** and the head env exported — the
  loaders read from that directory, not from `checkpoints/`:
  ```bash
  cp ../checkpoints/ee_neutro_head_v4.pt            pea_eval/data/
  cp ../checkpoints/ee_emotion_readout_embedding.pt pea_eval/data/
  cp ../checkpoints/ee_hybrid_calibrator_best.pt    pea_eval/data/
  export PEINN_NEUTRO_HEAD=ee_neutro_head_v4.pt
  ```
* the third-party benchmark datasets fetched into `src/pea_eval/data/` (see
  [`DATA_CARD.md`](DATA_CARD.md) — these datasets are **not** redistributed here).

The three shipped checkpoints plus the two encoders are all the router consumes. The Emotion
Engine runs as a *frozen feature stage*; the repository does not ship or require the earlier
reinforcement-learned (RLAF) Emotion-Engine trunk (that training loop was part of the removed
PEA-OS concept).

Example (subset of the six benchmarks, 1 run, PEINN v2.1 arms):

```bash
cd src
python scripts/run_v21_bench.py harmbench,xstest 1 --arms H04,H07,H10,H13 --no-push
```

> The `--no-push` flag is important: the original scripts auto-commit results to the *private*
> research repo. Always pass `--no-push` (or the equivalent) when running from this public clone.

## 5. Where results go

The paper's final canonical results live in [`../results/`](../results/): the aggregated per-arm
metric CSVs behind every table and figure, per-item sheets (harm-redacted, trace-preserving) with
a `run_id` column so the per-run values behind each mean and SD are recoverable, plus `ANALYSIS.md`
and a summary workbook. Intermediate results written by the bench drivers land under
`src/pea_eval/output/` (git-ignored here).

## 6. Honesty / non-contamination invariants

The training pipeline enforces three rules that any reproduction must keep:

1. **Benchmarks are held out for evaluation only.** The six benchmarks (HarmBench, XSTest,
   Taxonomy, Ethics, Morables, GGB) are never training data — training on them is the
   keyword-overfitting OOD failure v2.1 was built to avoid.
2. **No LLM at inference.** Both routing signals are small frozen nets (the v4 head and the
   HybridCalibrator energy); LLMs are used only *offline* to label training data and *online*
   only as the base model being gated.
3. **Learn structure / speech-act, not topic.** The head learns pragmatic structure (Directive
   force, Subversion frame, harm), not subject-matter keywords or affect intensity.

See [`PEINN_v2.1.md`](PEINN_v2.1.md) §5 for the full statement of these invariants.
