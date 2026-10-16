"""The revision experiments, one step per call (DESIGN.md 8). Run from revision/aai_r1:

    python -m v21r STEP [--check]

Steps in order: record, supplement, audit, features, split, train, thresholds, routes, nemo, matrix, nemo-doc, gate-diag, a8, cost, analyze, release; with --check
also push-check (copy cache/check/results to results/check/) and estimate (calls and hours for the full matrix, scaled from the check run). --check runs every step small (qwen
only, GGB and XSTest once) into cache/check/. Results are committed and pushed only when V21R_PUSH=1.
"""
from __future__ import annotations

import sys

from . import a8, analyze, data, devguard, gate_diag, matrix, models, nemo_doc, r2d2_probe, release, supplement, theta

STEPS = {
    "record": data.record, "supplement": supplement.supplement, "audit": data.audit, "features": data.features, "split": data.split,
    "train": models.train_all, "thresholds": theta.thresholds, "routes": theta.routes, "nemo": matrix.nemo,
    "matrix": matrix.matrix, "nemo-doc": nemo_doc.nemo_doc, "gate-diag": gate_diag.gate_diag, "dev-guard": devguard.dev_guard, "a8": a8.a8, "cost": matrix.cost, "analyze": analyze.analyze, "preview": analyze.preview, "release": release.release,
    "r2d2-probe": r2d2_probe.r2d2_probe, "r2d2-diag": r2d2_probe.r2d2_diag,
}


def push_check() -> int:
    """The check outputs hold counts, thresholds and metrics only (no text)."""
    import shutil
    from . import common as C
    src, dst = data.odir(True), C.OUT / "check"
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    return 0 if C.publish([dst], "v21r check: every step on GGB + XSTest, one run, qwen (counts and metrics)") else 1


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in (*STEPS, "estimate", "unload", "push-check", "ft-gate-time"):
        print(__doc__)
        return 2
    step, check = argv[0], "--check" in argv
    if step == "push-check":
        return push_check()
    if step == "ft-gate-time":                  # helper of cost (one process per device)
        import json
        from pathlib import Path
        a = {argv[i]: argv[i + 1] for i in range(1, len(argv) - 1) if argv[i] in ("--texts", "--out")}
        return models.ft_gate_time(json.loads(Path(a["--texts"]).read_text(encoding="utf-8")), Path(a["--out"]), check)
    if step == "estimate":
        return matrix.estimate()
    if step == "unload":
        from . import common as C
        return C.unload(matrix.models_needed(False) + [m for m in argv[1:] if not m.startswith("--")])
    return STEPS[step](check)


if __name__ == "__main__":
    sys.exit(main())
