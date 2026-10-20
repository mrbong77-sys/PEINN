# Experiments of the revised paper

This folder holds the code, checkpoints and results behind every number of the revised paper (Applied Artificial
Intelligence, manuscript 269417082). The repository [README](../../README.md) describes the package: what each folder
holds, how to regenerate the paper's numbers from the released records, how to assemble the weights, and what a rerun
of the experiments needs.

- `v21r/` — one module per step: `python -m v21r STEP [--check]` (run from this folder)
- `ops/` — the runner that executes the steps in order: `python -m ops.run [--check]`
- `tests/` — unit tests on synthetic data: `python -m pytest tests`
- `inputs/submitted_per_item/` — the submitted version's per-item sheets, read by the record step (harmful text redacted)
- `results/` — everything the paper reports
- `cache/` — texts, features, models and answers written by the steps (not committed)
