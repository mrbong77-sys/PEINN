"""The revision experiments under the ground loop (DESIGN.md 8): every step of v21r in its own process (the GPU is
freed between steps), results committed to main by each step, beacons in results/runner/.

    python -m ops.run --check   # every step small (qwen, GGB + XSTest once) -> results/check/, then the estimate
    python -m ops.run           # the full run; stops before the response matrix until APPROVED_M is set
    (from the station: launch ops.run with args ["--check"] or [])
"""
from __future__ import annotations

import os
import subprocess
import sys

from . import paths, pipeline
from .supervisor import launch, supervise

APPROVED_M = True                   # Eugene's go for the full response matrix (DESIGN.md 8): 2026-10-15 23:43 KST
OTHER_OLLAMA = ("qwen3.8:27b", "qwen3:8b", "gemma4:e4b")   # models other work may have left loaded

STATE = paths.CACHE / "run_state.json"
STATE_CHECK = paths.CACHE / "check_state.json"
RUNNER = paths.RESULTS / "runner"
RUNNER_CHECK = paths.RESULTS / "check_runner"
LOG = paths.CACHE / "run.log"
LOG_CHECK = paths.CACHE / "check_run.log"


def step(name: str, check: bool, *extra: str) -> int:
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", V21R_PUSH="1")
    cmd = [sys.executable, "-u", "-m", "v21r", name, *extra, *(["--check"] if check else [])]
    print(f"[ops] $ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, cwd=str(paths.RUN), env=env).returncode


def approval() -> int:
    if APPROVED_M:
        return 0
    print("waiting for the professor's go for the response matrix (APPROVED_M in ops/run.py)", flush=True)
    return 3


def steps(check: bool) -> list:
    c = check
    run = lambda k: (lambda: step(k, c))                            # noqa: E731
    s = [("record", "routing texts of the benches with a mock LLM", run("record")),
         ("audit", "isolation audit of the v4 corpus (guard + recorded texts)", run("audit")),
         ("unload-1", "free the GPU (any Ollama model)", lambda: step("unload", c, *OTHER_OLLAMA)),
         ("features", "frozen v2.1 features of the corpus and the routing texts", run("features")),
         ("split", "embedding near-duplicates out, train / val / test split", run("split")),
         ("train", "variants A0-A7 and the energy calibrator on the isolated corpus", run("train")),
         ("thresholds", "thresholds of every variant on val, pushed before any answer", run("thresholds")),
         ("routes", "route tables of every variant and operating point", run("routes")),
         ("nemo", "NeMo Guardrails answers three probe prompts on every base", run("nemo"))]
    if not check:
        s.append(("approval", "the professor's go for the full matrix", approval))
    s += [("matrix", "PEINN forced to each tier + Vanilla, R2D2, NeMo, Llama Guard; generate then judge per base", run("matrix")),
          ("cost", "route cost per tier (gate time, calls, tokens)", run("cost")),
          ("analyze", "benchmark results, curves, calibration, I construct", run("analyze"))]
    if check:
        s += [("push-check", "check outputs -> results/check/", run("push-check")),
              ("estimate", "calls and hours for the full matrix", run("estimate"))]
    return s


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    check = "--check" in argv
    rest = [a for a in argv if a != "--check"]
    state, runner, log = (STATE_CHECK, RUNNER_CHECK, LOG_CHECK) if check else (STATE, RUNNER, LOG)
    if "--child" in argv:
        return pipeline.run("v21r" + ("-check" if check else ""), steps(check), state,
                            [a for a in rest if a != "--child"], __doc__)
    if "--inner" in argv:
        return supervise("ops.run", [a for a in argv if a != "--inner"], runner, state, steps(check),
                         "v2.1 심사 대응" + (" 점검" if check else ""), log)
    return launch("ops.run", argv)


if __name__ == "__main__":
    sys.exit(main())
