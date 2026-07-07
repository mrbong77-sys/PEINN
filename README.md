# PEINN — Principle and Emotion in Neutrosophic Nexus

**Reproducibility package for the paper**
*"PEINN: Neutrosophic-Affective Routing for Inference-Time Artificial Moral Agents"*
(Bongjin Jung, Joongho Chang — submitted to *Applied Artificial Intelligence*, Taylor & Francis).

PEINN is a **deterministic, inference-time routing module** that gates a
*frozen* base language model without retraining it and without loading a second LLM. It fuses two
learned signals through a complementary **AND-gate**:

1. a **speech-act-aware Neutro Head (v4)** that emits a neutrosophic **Truth / Indeterminacy /
   Falsity (T/I/F)** triple — three *independent* sigmoids, not one normalized softmax; and
2. an **Emotion-Engine energy** signal (the frozen `HybridCalibrator`, a small affective network),

and routes every input through **one of five modes** — Direct-Answer, Soft-reasoning,
Deliberation, Reasoned-Refusal, or Hard-block — hard-blocking only definite threats. The
authoritative design is [`docs/PEINN_v2.1.md`](docs/PEINN_v2.1.md).

This repository contains the **source code used in the paper**, **illustrative training-data
samples**, and **detailed guides** so that desk reviewers and independent readers can audit
the architecture and **reproduce the results directly**.

> The finished checkpoints (Neutro Head v4, affect readout, and energy calibrator — ≈ 0.22 M
> parameters, < 1 MB total) are shipped under [`checkpoints/`](checkpoints/), together with the
> frozen gate thresholds and a SHA-256 manifest, so reviewers can run the router without
> retraining. To rebuild any component from scratch instead,
> [`docs/REGENERATE_CHECKPOINTS.md`](docs/REGENERATE_CHECKPOINTS.md) documents how to regenerate
> the data and retrain each component to an identical model.

---

## Repository layout

```
PEINN/
├── README.md                     ← you are here
├── LICENSE                       ← MIT — source code (src/, tools/, scripts)
├── DATA_LICENSE                  ← CC BY 4.0 — data & materials (checkpoints, samples, results)
├── CITATION.cff                  ← how to cite the paper / this package
├── requirements.txt              ← Python dependencies for the research code
│
├── src/                          ← the source code used in the paper (project root for imports)
│   ├── core/                     ← Emotion Engine, Golden Anchors (Principles), PEINN damping
│   ├── pea_eval/                 ← Neutro Head v4 router + energy + benchmark evaluators (code)
│   ├── peinn_v2/                 ← optional experimental energy module (default-off; not the routing energy)
│   ├── config/                   ← runtime configuration
│   ├── scripts/                  ← training, data-build, and bench-driver scripts
│   └── run_stat_batch.py …       ← top-level benchmark drivers
│
├── data_samples/                 ← ~20-per-type illustrative training samples (copyright-aware)
│   ├── neutro_head_tif/          ← T/I/F + v4 (speech-act) head training samples
│   └── structured_energy/        ← optional experimental energy-module corpora samples
│
├── checkpoints/                  ← finished weights (Neutro Head v4, affect readout, energy calibrator) + gate θ + SHA-256 manifest
│
├── results/                      ← final per-arm metrics (six benchmark CSVs) + ANALYSIS.md + xlsx
│   └── per_item/                 ← full per-item sheets (harm-redacted, trace-preserving)
│
├── docs/
│   ├── PEINN_v2.1.md             ← authoritative PEINN design & operation (read this)
│   ├── ARCHITECTURE.md           ← component-by-component architecture overview
│   ├── REPRODUCTION.md           ← end-to-end reproduction map
│   ├── REGENERATE_CHECKPOINTS.md ← step-by-step retraining of the checkpoints
│   └── DATA_CARD.md              ← data provenance, sampling method, licensing
│
└── tools/                        ← build_samples.py (produces data_samples/) +
                                     make/analyze/export helpers that produced results/
```

## Where to start

| If you want to… | Read |
|---|---|
| Understand the PEINN design | [`docs/PEINN_v2.1.md`](docs/PEINN_v2.1.md) |
| See the code↔component map | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) |
| Reproduce the paper end-to-end | [`docs/REPRODUCTION.md`](docs/REPRODUCTION.md) |
| Run the router with the shipped checkpoints | [`checkpoints/`](checkpoints/) + the [Quick start](#quick-start) below |
| Run the PEINN benchmarks (sets the engine + head env for you) | `src/scripts/run_v21_bench.py` |
| See the headline results | [`results/ANALYSIS.md`](results/ANALYSIS.md) |
| **Put PEINN on your own base LLM** | [Bring your own base model](#bring-your-own-base-model) |
| Rebuild the checkpoints from scratch | [`docs/REGENERATE_CHECKPOINTS.md`](docs/REGENERATE_CHECKPOINTS.md) |
| Inspect / re-sample the training data | [`docs/DATA_CARD.md`](docs/DATA_CARD.md) and [`data_samples/`](data_samples/) |

## Quick start

```bash
# 1) install
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export PYTHONPATH="$PWD/src:$PYTHONPATH"          # code imports assume src/ is the project root

# 2) put the shipped checkpoints where the loaders look for them (src/pea_eval/data/)
cp checkpoints/ee_neutro_head_v4.pt            src/pea_eval/data/
cp checkpoints/ee_emotion_readout_embedding.pt src/pea_eval/data/
cp checkpoints/ee_hybrid_calibrator_best.pt    src/pea_eval/data/
export PEINN_NEUTRO_HEAD=ee_neutro_head_v4.pt    # selects the PEINN head

# 3) dependency-light sanity check — CPU-only, downloads nothing:
cd src && python -m peinn_v2.train.train --smoke  # optional experimental module only — not the routing energy
```

To run the PEINN benchmarks, use the driver (run from `src/`; it sets `engine="neutro_v21"`
and the head env for you):

```bash
cd src && python scripts/run_v21_bench.py harmbench,xstest 1 --arms H07 --no-push
```

This additionally needs: (a) the two frozen sentence encoders (`all-MiniLM-L6-v2`,
`all-mpnet-base-v2`, downloaded on first use); (b) a reachable base LLM (see
[Bring your own base model](#bring-your-own-base-model)); and (c) the third-party
benchmark datasets, which are not redistributed (see [`docs/DATA_CARD.md`](docs/DATA_CARD.md)).
The three shipped checkpoints plus the two encoders are all the router itself consumes; the
routing path runs the Emotion Engine as a frozen feature stage and loads no additional trunk.
The gate thresholds θ are frozen in code (`src/pea_eval/evaluators/intent_router.py`);
`checkpoints/neutro_gate_theta_v4.json` is a matching reference copy, not a file the router loads.

## Bring your own base model

PEINN's router is **base-model-agnostic**: it computes `(T, I, F, energy)` only from the user
prompt via the two frozen sentence encoders and the shipped heads — it never reads the base
model's tokenizer, logits, or hidden states (`src/pea_eval/evaluators/ee_runner.py`,
`intent_router.py`). So grafting PEINN onto a different LLM is a configuration change, not a code
change:

1. **Add an arm.** An *arm* = (base LLM × defense). Edit `src/pea_eval/config/arms_harmbench.yaml`
   and add a block, e.g. to gate a new HuggingFace model with PEINN:
   ```yaml
   H99:
     llm_backend: hf                 # "hf" is the self-contained backend in this repo
     llm_model: "Org/Your-Model"     # any HF causal-LM id (or a local path)
     ee_enabled: true                # true = PEINN routing on
     rag_enabled: false
     nemo_enabled: false
     agent_profile: A
   ```
2. **Select it** at run time with `--arms H99`.
3. **Backend note.** The only base-model backend included here is HuggingFace (`hf`,
   `src/pea_eval/backends/hf_backend.py`); it downloads the model from the Hub by default (set
   `PEAOS_HF_OFFLINE=1` to use only your local cache, or `PEAOS_HF_LOCAL_DIRS=/path/to/models`).
   For Ollama, vLLM, or another server, point an **OpenAI-compatible** endpoint (Ollama and vLLM
   both expose `/v1`) at an arm with `llm_backend: lmstudio` and `base_url` in `user_config.yaml`.
4. The shipped heads are locked to the two named encoders (800-d = 32 affect + 384 MiniLM
   semantic + 384 MiniLM principle); swapping encoders would require retraining the head.

## Scope and honesty notes

* This package ships **the PEINN routing core and the paper's benchmark reproduction**
  (model definitions, the v4 Neutro Head router, the Emotion-Engine energy, the six benchmark
  evaluators, and the training/figure scripts) — everything needed to reproduce the results.
* The serving setup here is **Ollama-based by default** (`llm_backend: local`), with a
  self-contained HuggingFace backend (`llm_backend: hf`) also included. Any other setup —
  vLLM, LM Studio, a hosted API, a different base model — is left to you: point an
  OpenAI-compatible endpoint at an `lmstudio` arm, or add an `hf` arm, and adjust
  `user_config.yaml` / `arms_harmbench.yaml` to your local environment (see
  [Bring your own base model](#bring-your-own-base-model)).
* Third-party benchmark datasets (HarmBench, XSTest, Taxonomy, …) and the LLM-judge-labeled
  training corpora are **not redistributed**. We provide a small ~20-per-type sample of each
  with full provenance, plus instructions to regenerate the full corpora from their original
  sources (see [`docs/DATA_CARD.md`](docs/DATA_CARD.md)).
* All repository-level documentation is written in English. Some inline comments and docstrings
  in `src/` are preserved verbatim from the research codebase (mixed English/Korean) to keep
  the code byte-faithful to what produced the published results.

## License

This repository is **dual-licensed** so that the reproduction materials meet an open-data
standard while the code stays permissively reusable:

* **Source code** (`src/`, `tools/`, and all scripts) — **MIT**; see [`LICENSE`](LICENSE).
* **Data and materials** original to this work — the trained checkpoints and gate-threshold
  config, the original training-data samples in `data_samples/`, the judge prompts, and the
  result sheets / per-run values behind the paper's figures and tables — **CC BY 4.0**; see
  [`DATA_LICENSE`](DATA_LICENSE). Reuse is free (including commercially) with attribution.

Two things are **not** covered by the above: (a) the third-party benchmark datasets and any
upstream-sourced training items, which remain under their own upstream licenses and whose
harmful prompts are not redistributed here (see [`docs/DATA_CARD.md`](docs/DATA_CARD.md)); and
(b) patent rights — CC BY 4.0 grants no patent licence, and releasing this code or data grants
none.

## Citing

See [`CITATION.cff`](CITATION.cff). Please cite the paper if you use this code or data.
