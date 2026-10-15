# Revision experiments — Applied Artificial Intelligence, manuscript 269417082 (round 1)

This folder holds the supplementary experiments for the first revision of the PEINN v2.1 paper. The submitted
version of the package (code, checkpoints, per-item results) is unchanged elsewhere in this repository.

- `DESIGN.md` — the experiment design, fixed before the runs (Korean, internal working document).
- `v21r/` — the code. Each step is one command, run from this folder: `python -m v21r STEP [--check]`.
- `results/` — counts, thresholds and metrics written by the steps (no benchmark text, no model answers).
- `cache/` — texts, features, models and answers; not committed.
- `ops/` — the unattended runner: a station that waits for commands, a supervisor that sends beacons
  (`results/station/`, `results/runner/`) and resumes after fixes, and git pushes of each step's results.
- `commands/` — command files the station reads from `origin/main` (`station.json`, `run.json`).
- `tests/` — unit tests on synthetic data and fake git: `python -m pytest tests`.

Unattended run on the GPU PC, from the PEINN checkout: `python revision/aai_r1/station.py` (then the command
`{"action": "launch", "module": "ops.run", "args": ["--check"]}` in `commands/station.json` starts the check run).
Without the station: `cd revision/aai_r1 && python -m ops.run --check`.

Steps, in order: `record`, `audit`, `features`, `split`, `train`, `thresholds`, `routes`, `nemo`, `matrix`, `cost`,
`analyze`. They need a PEAOS checkout (the benchmark harness and the head corpus; `PEINN_PEAOS`, default `../PEAOS`),
Ollama with the four base models, `qwen3:32b`, `llama-guard3:8b` and `zephyr-r2d2`, and a GPU.
