# PEINN — Principle and Emotion in Neutrosophic Nexus

Reproducibility package for the paper *"PEINN: Neutrosophic-Affective Routing for Inference-Time Artificial Moral
Agents"* (Bongjin Jung and Joongho Chang; *Applied Artificial Intelligence*, manuscript 269417082, revised version).

PEINN is a deterministic, inference-time router that gates a frozen base language model. A neutrosophic head gives
each prompt a Truth / Indeterminacy / Falsity triple, an energy calibrator gives an affective energy, and a
fixed-threshold AND-gate sends the prompt to one of five routes: Direct-Answer, Soft-reasoning, Deliberation,
Reasoned-Refusal or Hard-block. The base model is not retrained and no second large model is loaded.

Every number, table and figure of the revised paper is produced from the files in this repository.

## Layout

```
PEINN/
├── checkpoints/          frozen components shared by every configuration (Emotion Engine, v2.1 head and calibrator,
│                         affect read-out, v2.1 gate thresholds) with SHA-256 checksums
├── src/                  the router and the benchmark harness the experiments call (Emotion Engine, principle
│                         anchors, PEINN router, benchmark evaluators, judge prompts, NeMo Guardrails configuration)
└── revision/aai_r1/      the experiments of the paper
    ├── v21r/             one module per step: python -m v21r STEP [--check]
    ├── ops/              the unattended runner that executes the steps in order (python -m ops.run)
    ├── tests/            unit tests on synthetic data (python -m pytest tests)
    ├── inputs/           the submitted version's per-item sheets, read by the record step (harmful text redacted)
    └── results/          everything the paper reports (below)
```

## Results (`revision/aai_r1/results/`)

| Path | Contents |
|---|---|
| `paper/` | every table body, figure and number of the paper (`numbers.json`, `ablation.json`, `methods.json`) |
| `benches/` | the rows behind every reported number, per benchmark and base model, with judge verdicts and scores; `bench_stats.json` |
| `forced/` | each base model's answer to every item under each of the five routes, the routes and gate signals of every variant, the validation and test labels |
| `analysis/` | per-defence and per-variant results, cost curves, the Indeterminacy analysis |
| `ggb/`, `nemo/`, `matrix/`, `a8/` | GGB re-scoring, NeMo Guardrails rail verdicts, call counts per base, the LoRA baseline (A8) |
| `corpus/` | the isolated training corpus: audit, supplement sources, and every row's SHA-1, split, source and teacher T/I/F |
| `checkpoints/` | PEINN's head and energy calibrator with their fine-tuned encoders, the OOD statistics, the heads of every ablation variant, A8's LoRA adapters, `manifest.json` |
| `thresholds.json`, `routes_summary.json`, `train_report.json`, `ftv_report.json`, `gate_retrain.json`, `route_cost.json`, `record_stats.json` | fitted thresholds, route counts, training reports, gate cost |

PEINN in the paper is variant `A0ftM` at the safe Hard-block cap of 3 % (`A0ftM@0.03` in `thresholds.json`).

The prompts and answers of HarmBench, the jailbreak taxonomy and XSTest are not re-hosted: in `benches/` and
`forced/` their text columns hold the SHA-256 of the text (`sha256:…`); ids, verdicts, scores and routes remain.
Ethics, MORABLES and GGB answers are kept as text, because they are re-scored from it.

## Reproducing the paper

All commands run from `revision/aai_r1/`.

1. **Numbers, tables and figures from the released records** (CPU, no model):

   ```
   pip install numpy pandas scipy matplotlib
   python -m v21r bench-stats
   python -m v21r paper-tables
   python -m v21r paper-ablation
   python -m v21r paper-methods
   ```

   They rewrite `results/benches/bench_stats.json` and `results/paper/` from `benches/`, `forced/`, `ggb/`,
   `analysis/`, `thresholds.json` and `route_cost.json`; the files they write are the values printed in the paper.

2. **Weights.** Large checkpoints are stored as byte parts of at most 45 MiB. `python -m v21r assemble` joins them,
   checks their SHA-256 against `results/checkpoints/manifest.json` and writes the joined files next to the parts.

3. **The experiments from the start** (`python -m ops.run --check` for a small pre-test, then `python -m ops.run`).
   The runner executes every step in order, resumes after an interruption and skips finished steps. It needs:
   - a GPU and [Ollama](https://ollama.com) with the base models `zephyr:7b`, `qwen2.5:7b-instruct`, `gemma4:e4b`,
     `gemma3:12b`, the judge `qwen3:32b`, `llama-guard3:8b`, and R2D2 (`cais/zephyr_7b_r2d2` at revision
     `214e3d4e`, served unquantized; the `r2d2-cpeg` step builds it);
   - the benchmark harness the experiments called (PEAOS; `PEINN_PEAOS`, default `../PEAOS`), whose code is in
     `src/`, with the benchmark data its fetch scripts download (`src/scripts/fetch_benchmark_data.py`,
     `fetch_ggb_morables.py`, `build_morables_dataset.py`);
   - the Python packages in [`requirements.txt`](requirements.txt);
   - the head corpus. Its texts are not redistributed; `results/corpus/corpus_split_ids.csv.gz` lists every row's
     source and the SHA-1 of its text, so a rebuilt corpus can be matched row by row.


## License and citation

Code (`src/`, `revision/aai_r1/v21r`, `ops`, `tests`): MIT ([`LICENSE`](LICENSE)). Data, checkpoints and results:
CC BY 4.0 ([`DATA_LICENSE`](DATA_LICENSE)). Archived releases: Zenodo, concept DOI
[10.5281/zenodo.21219265](https://doi.org/10.5281/zenodo.21219265). How to cite: [`CITATION.cff`](CITATION.cff).
