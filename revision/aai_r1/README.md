# Revision — Applied Artificial Intelligence, manuscript 269417082 (round 1)

This folder holds the code, checkpoints and results of the revised PEINN v2.1 paper. The submitted version of the
package (code, checkpoints, per-item results) is unchanged elsewhere in this repository; every number of the revised
manuscript comes from this folder.

## The revised PEINN

PEINN in the revised paper is the configuration **A0ftM at the safe Hard-block cap of 3 %** (`DESIGN.md` 24): the T/I/F
head with its fine-tuned all-MiniLM-L6-v2 encoder, the energy calibrator with its fine-tuned all-mpnet-base-v2 encoder,
the Mahalanobis out-of-distribution check, and the thresholds fitted on the validation split of the isolated corpus.
The frozen Emotion Engine and principle anchors are those of the submitted package.

| File (under `results/`) | What it is |
|---|---|
| `checkpoints/final/A0ft_head.pt.part*` | PEINN's head with its fine-tuned MiniLM (91 MB, in parts) |
| `checkpoints/final/A0ft_energy.pt.part*` | PEINN's energy calibrator with its fine-tuned mpnet (438 MB, in parts) |
| `checkpoints/A0ftM_ood.pt` | out-of-distribution statistics (class means, precision, τ) |
| `checkpoints/A0.pt`, `calibrator.pt`, `A1.pt` … `A6p.pt` | heads of the ablation variants (A0: frozen encoders) |
| `checkpoints/manifest.json` | bytes and SHA-256 of every file and every part |
| `thresholds.json` | the fitted thresholds of every variant and cap (`A0ftM@0.03` is PEINN) |

The two large files are stored as byte parts of at most 45 MiB so that the repository archive holds them. Join and
check them with `python -m v21r assemble` (run from this folder); the joined files appear next to the parts.

## Results

- `results/paper/` — every table body, figure and number of the revised manuscript (`numbers.json`, `ablation.json`,
  `methods.json`), written by `python -m v21r paper-tables`, `paper-ablation` and `paper-methods`. These steps read
  only the files below and need no model; they reproduce the manuscript's values exactly.
- `results/benches/` — the rows behind every reported number, per benchmark and base model, with judge verdicts and
  scores; `bench_stats.json` is recomputed from them by `python -m v21r bench-stats`.
- `results/forced/` — each base model's answer to every item under each of the five routes, the routes of every
  variant (`routes.csv.gz`), the gate signals of every variant and the validation/test labels; the ablations are
  scored from these.
- The prompts and answers of HarmBench, the jailbreak taxonomy and XSTest are **not re-hosted**: in `benches/` and
  `forced/` their text columns hold the SHA-256 of the text (`sha256:…`), while ids, verdicts, scores and the
  routing-text hash remain. Ethics, MORABLES and GGB answers are kept as text, since they are re-scored from it.
- `results/corpus/` — the audit of the isolated training corpus (sources, counts, isolation checks).
- `DESIGN.md` — the decisions log of the revision (Korean, internal working document).

## Running the experiments

- `v21r/` — the code. Each step is one command, run from this folder: `python -m v21r STEP [--check]`.
- `cache/` — texts, features, models and answers; not committed.
- `ops/` — the unattended runner (station, supervisor, beacons in `results/station/`, `results/runner/`, git pushes).
- `commands/` — command files the station reads from `origin/main`.
- `tests/` — unit tests on synthetic data and fake git: `python -m pytest tests`.

Unattended run on the GPU PC, from the PEINN checkout: `python revision/aai_r1/station.py`. Without the station:
`cd revision/aai_r1 && python -m ops.run --check`. The steps need a PEAOS checkout (the benchmark harness and the head
corpus; `PEINN_PEAOS`, default `../PEAOS`), Ollama with the four base models, `qwen3:32b`, `llama-guard3:8b` and
`zephyr-r2d2`, and a GPU.
