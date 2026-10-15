"""Shared constants and helpers for the v2.1 revision experiments (DESIGN.md)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]          # revision/aai_r1
PEINN = ROOT.parents[1]                             # this repository (the paper's reproducibility package)
OUT = ROOT / "results"                              # committed: ids, counts, metrics, thresholds
CACHE = ROOT / "cache"                              # not committed: texts, answers, features, models

BENCHES = ("harmbench", "xstest", "taxonomy", "ethics", "morables", "ggb")
RUNS = {"harmbench": 10, "ggb": 10, "xstest": 5, "taxonomy": 5, "ethics": 5, "morables": 5}   # submitted protocol
CHECK_BENCHES = ("ggb", "xstest")
CHECK_RUNS = 1

BASES = {"zephyr": "zephyr:7b", "qwen": "qwen2.5:7b-instruct", "gemma4": "gemma4:e4b", "gemma3": "gemma3:12b"}
ARMS = {  # base -> {defense: arm id} (paper Table 2 and Appendix A)
    "zephyr": {"Vanilla": "H01", "R2D2": "H02", "NeMo": "H03", "PEINN": "H04", "LlamaGuard": "H14"},
    "qwen": {"Vanilla": "H05", "NeMo": "H06", "PEINN": "H07", "LlamaGuard": "H15"},
    "gemma4": {"Vanilla": "H08", "NeMo": "H09", "PEINN": "H10", "LlamaGuard": "H16"},
    "gemma3": {"Vanilla": "H11", "NeMo": "H12", "PEINN": "H13", "LlamaGuard": "H17"},
}
JUDGE = "qwen3:32b"                                  # the submitted judge (all LLM-judged benches)
EXTRA_MODELS = ("zephyr-r2d2:latest", "llama-guard3:8b")

TIERS = ("Hard-block", "Reasoned-Refusal", "Deliberation", "Soft-reasoning", "Direct-Answer")
LOCKED = {"extreme": 9.4, "harm": 8.5, "F": 0.15, "I": 0.45, "Fref": 0.30, "soft": 8.5, "Fblk": 0.45}


def sha(text: str) -> str:
    """The key the PEAOS driver's lookup router uses (sha1 of the routing text)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# ---- the gate ------------------------------------------------------------------------------------

def gate(T, I, F, E, th: dict, order: str = "revised", energy: bool = True, deliberation: bool = True) -> np.ndarray:
    """The v2.1 five-tier gate, vectorised.

    order "paper": Deliberation (I >= I, F < Fblk) is checked first, as in NeutroEERouterV21._gate.
    order "revised" (docs/116 1.3): the extreme-energy override comes first, so no input above the benign energy
    ceiling is deliberated; the rest keeps the paper order.
    energy False (A5): no energy terms; Hard-block when F >= th["Fhb"]; no Soft-reasoning.
    deliberation False (A1, A4 block-only): the Deliberation tier is removed.
    """
    T, I, F = (np.asarray(x, dtype=float) for x in (T, I, F))
    n = len(F)
    E = np.zeros(n) if E is None else np.asarray(E, dtype=float)
    out = np.full(n, "Direct-Answer", dtype=object)
    if energy:
        out[E >= th["soft"]] = "Soft-reasoning"
    out[F >= th["Fref"]] = "Reasoned-Refusal"
    if energy:
        hb = (E >= th["extreme"]) | ((E >= th["harm"]) & (F >= th["F"]))
    else:
        hb = F >= th["Fhb"]
    out[hb] = "Hard-block"
    if deliberation:
        delib = (I >= th["I"]) & (F < th["Fblk"])
        if order == "revised" and energy:
            delib &= ~(E >= th["extreme"])
        out[delib] = "Deliberation"
    return out


# ---- teacher classes --------------------------------------------------------------------------------

def teacher_class(T, I, F) -> np.ndarray:
    """Item class from the teacher's soft labels: harm (F >= .5), dilemma (I >= .5, F < .5), safe (else)."""
    I, F = np.asarray(I, dtype=float), np.asarray(F, dtype=float)
    c = np.full(len(F), "safe", dtype=object)
    c[I >= 0.5] = "dilemma"
    c[F >= 0.5] = "harm"
    return c


# ---- io ----------------------------------------------------------------------------------------------

def jdump(obj, f: Path) -> Path:
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=_np) + "\n", encoding="utf-8")
    return f


def _np(x):
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating,)):
        return float(x)
    if isinstance(x, np.ndarray):
        return x.tolist()
    raise TypeError(type(x))


def jload(f: Path):
    return json.loads(Path(f).read_text(encoding="utf-8"))


def jsonl(f: Path) -> list[dict]:
    if not Path(f).exists():
        return []
    return [json.loads(x) for x in Path(f).read_text(encoding="utf-8").split("\n") if x.strip()]


def child(cmd: list[str], cwd: Path, env: dict | None = None) -> int:
    """Run a helper in another checkout (PEAOS or PEINN) with UTF-8 pipes (Windows cp949, CLAUDE.md)."""
    e = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", **(env or {}))
    print(f"[v21r] $ {' '.join(str(c) for c in cmd)}  (cwd {cwd})", flush=True)
    return subprocess.run([str(c) for c in cmd], cwd=str(cwd), env=e).returncode


def peaos() -> Path:
    """The PEAOS checkout that holds the benchmark harness and the head corpus (env PEINN_PEAOS, else ../PEAOS)."""
    p = Path(os.environ["PEINN_PEAOS"]) if os.environ.get("PEINN_PEAOS") else PEINN.parent / "PEAOS"
    if not (p / "run_stat_batch.py").exists():
        raise SystemExit(f"PEAOS checkout not found at {p}; set PEINN_PEAOS")
    return p


def peinn() -> Path:
    return PEINN


def publish(targets: list[Path], message: str) -> bool:
    """Commit and push results to the current branch when V21R_PUSH=1 (the unattended runner); else a no-op."""
    if os.environ.get("V21R_PUSH") != "1":
        return True
    env = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never")

    def git(*a):
        return subprocess.run(["git", *a], cwd=PEINN, capture_output=True, text=True, encoding="utf-8",
                              errors="replace", env=env, stdin=subprocess.DEVNULL)
    branch = git("rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    git("add", "--", *[str(t) for t in targets])
    if git("diff", "--cached", "--quiet").returncode:
        trailer = os.environ.get("V21R_TRAILER", "")
        r = git("commit", "-m", f"{message}\n\n{trailer}".strip())
        if r.returncode:
            print(f"[git] commit failed: {r.stderr.strip()[:200]}", flush=True)
            return False
    for wait in (0, 2, 4, 8, 16):
        time.sleep(wait)
        git("pull", "--rebase", "--autostash", "origin", branch)
        r = git("push", "-u", "origin", f"HEAD:{branch}")
        if not r.returncode:
            print(f"[git] pushed to {branch}", flush=True)
            return True
        print(f"[git] push failed: {r.stderr.strip()[:200]}", flush=True)
    return False


def ollama_url() -> str:
    return os.environ.get("OLLAMA_HOST_URL", "http://localhost:11434")


def _ollama(path: str, body: dict | None = None, timeout: float = 60):
    import urllib.request
    req = urllib.request.Request(ollama_url() + path, data=None if body is None else json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8")


def pull_missing(models: list[str], log=print) -> int:
    have = {m["name"] for m in json.loads(_ollama("/api/tags"))["models"]}
    for m in models:
        if m in have or f"{m}:latest" in have:
            continue
        log(f"  ollama pull {m}")
        if subprocess.run(["ollama", "pull", m]).returncode:
            raise SystemExit(f"ollama pull {m} failed")
    return 0


def unload(models: list[str]) -> int:
    """Free GPU memory: ask Ollama to unload each model now (keep_alive 0); unknown models are ignored."""
    for m in models:
        try:
            _ollama("/api/generate", {"model": m, "keep_alive": 0})
        except Exception:  # noqa: BLE001
            pass
    return 0


PY = sys.executable
