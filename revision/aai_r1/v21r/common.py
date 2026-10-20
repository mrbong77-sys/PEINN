"""Shared constants and helpers for the v2.1 revision experiments."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
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
R2D2 = "zephyr-r2d2:latest"                          # the name the PEAOS arm H02 calls
# The submitted run's build is lost (another PC). R2D2 is the canonical checkpoint HarmBench's
# authors evaluated, cais/zephyr_7b_r2d2 (bf16, pinned revision), unquantized (quantization may
# degrade it). Ollama cannot import its safetensors ("unsupported MLX architecture: MistralForCausalLM"), so H02 serves
# mradermacher's F16 GGUF of it, checked tensor by tensor against the checkpoint (v21r.wcheck), with HarmBench's own prompt
# for this model (baselines/model_utils.py ZEPHYR_ROBUST_PROMPT, configs/model_configs/models.yaml zephyr_7b_robust; no
# system block). CPEG's Q8_0 build took zephyr:7b-beta-q8_0's template ("{prompt}\n</s>"), under which R2D2 left 8 of 12
# submitted XSTest safe prompts empty.
R2D2_CPEG = "zephyr-r2d2:7b-q8_0"
R2D2_GGUF = "hf.co/mradermacher/zephyr_7b_r2d2-GGUF:Q8_0"       # CPEG's weights (compared in r2d2-fingerprint only)
R2D2_F16 = "hf.co/mradermacher/zephyr_7b_r2d2-GGUF:F16"         # served (after the weights check)
R2D2_HF = "cais/zephyr_7b_r2d2"
R2D2_HF_REV = "214e3d4e117a1f2b58fbc334e0fe58d93c9365d6"        # the Hub revision of 2024-02-26
R2D2_TEMPLATE = "<|user|>\n{{ .Prompt }}</s>\n<|assistant|>\n"     # HarmBench ZEPHYR_ROBUST_PROMPT
R2D2_STOPS = ("</s>", "<|user|>", "<|assistant|>", "<|system|>")
UNQUANTIZED = ("F16", "BF16", "F32")
EXTRA_MODELS = (R2D2, "llama-guard3:8b")

TIERS = ("Hard-block", "Reasoned-Refusal", "Deliberation", "Soft-reasoning", "Direct-Answer")
LOCKED = {"extreme": 9.4, "harm": 8.5, "F": 0.15, "I": 0.45, "Fref": 0.30, "soft": 8.5, "Fblk": 0.45}



def fx(x, d: int = 1, sign: bool = False) -> str:
    """X printed with d decimals, rounding half up from x's value at 6 decimals (Python's own rounding goes to even and
    works on the binary value, so an exact 68.55 would print 68.5). Every number the paper prints goes through this."""
    from decimal import ROUND_HALF_UP, Decimal
    q = Decimal(repr(round(float(x), 6))).quantize(Decimal(1).scaleb(-d), rounding=ROUND_HALF_UP)
    if q == 0:
        q = abs(q)
    return (f"{q:+}" if sign else f"{q}")

def sha(text: str) -> str:
    """The key the PEAOS driver's lookup router uses (sha1 of the routing text)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()


# ---- the gate ------------------------------------------------------------------------------------

def gate(T, I, F, E, th: dict, order: str = "revised", energy: bool = True, deliberation: bool = True) -> np.ndarray:
    """The v2.1 five-tier gate, vectorised.

    order "paper": Deliberation (I >= I, F < Fblk) is checked first, as in NeutroEERouterV21._gate.
    order "revised": the extreme-energy override comes first, so no input above the benign energy
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

SAFETY = ("harmbench", "taxonomy", "xstest")      # benches whose prompts and answers are not re-hosted


def htext(t) -> str:
    """A safety-bench text as it appears in the public results: 'sha256:<hex>' of the stored string ('' stays '';
    a value already hashed stays as it is)."""
    if not isinstance(t, str) or not t or t.startswith("sha256:"):
        return t if isinstance(t, str) else ""
    return "sha256:" + hashlib.sha256(t.encode("utf-8")).hexdigest()


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
    """Run a helper in another checkout (PEAOS or PEINN) with UTF-8 pipes (Windows cp949, CLAUDE.md). The string hash
    seed is fixed: PEAOS orders the Ethics Dilemma items by a set of ids, and that order makes the judge's batches
   ."""
    e = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1", PYTHONHASHSEED="0", **(env or {}))
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
    """Commit and push results to main when V21R_PUSH=1 (the unattended runner, ops.run); else a no-op."""
    if os.environ.get("V21R_PUSH") != "1":
        return True
    from ops.gitutil import commit_and_push
    return commit_and_push(targets, message)


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


def modelfile_with_weights(base_modelfile: str, source: str) -> str:
    """A served model's Modelfile (chat template, stop words, parameters) with its weights replaced by `source`:
    top-level comment and FROM lines are dropped, triple-quoted blocks are kept as they are."""
    out, inside = [f"FROM {source}"], False
    for line in base_modelfile.splitlines():
        top = not inside
        inside ^= line.count('"""') % 2 == 1
        if top and (line.startswith("#") or line.startswith("FROM ")):
            continue
        out.append(line)
    return "\n".join(out).strip() + "\n"


def _digests() -> dict:
    return {m["name"]: m.get("digest", "") for m in json.loads(_ollama("/api/tags"))["models"]}


def _show(name: str) -> dict:
    return json.loads(_ollama("/api/show", {"model": name}))


def _blob_path(show: dict) -> Path | None:
    """The weights file a served model reads (its Modelfile's FROM line)."""
    p = next((l[5:].strip() for l in show.get("modelfile", "").splitlines() if l.startswith("FROM ")), "")
    return Path(p) if p else None


def _r2d2_marker() -> Path:
    return CACHE / "r2d2_canonical.json"


def r2d2_served() -> dict:
    """What H02 is served with now: the model this code built after the weights check (same digest as recorded),
    unquantized, with HarmBench's prompt."""
    have = _digests()
    if R2D2 not in have:
        return {"ok": False, "missing": [R2D2]}
    me = _show(R2D2)
    mk = jload(_r2d2_marker()) if _r2d2_marker().exists() else {}
    rep = {"digest": have[R2D2], "built_digest": mk.get("digest"), "source": mk.get("source"),
           "weights_check": mk.get("weights_check"), "quantization": me.get("details", {}).get("quantization_level", ""),
           "template": me.get("template", ""), "harmbench_template": R2D2_TEMPLATE}
    rep["ok"] = (rep["digest"] == rep["built_digest"] and rep["source"] == f"{R2D2_F16} = {R2D2_HF}@{R2D2_HF_REV}"
                 and rep["weights_check"] is True and rep["quantization"] in UNQUANTIZED
                 and rep["template"] == R2D2_TEMPLATE)
    return rep


def ensure_r2d2(log=print) -> Path | None:
    """R2D2 (arm H02) under the name H02 calls: R2D2_F16 with HarmBench's prompt (R2D2_TEMPLATE), served only after its
    tensors equal cais/zephyr_7b_r2d2 at R2D2_HF_REV (bf16 cast to float16). Any other model of that name is replaced.
    Returns the record written to results/ (None if already in place)."""
    if r2d2_served().get("ok"):
        return None
    from huggingface_hub import snapshot_download
    from . import wcheck
    log(f"  download {R2D2_HF}@{R2D2_HF_REV[:12]} (bf16 safetensors, for the weights check)")
    src_dir = snapshot_download(R2D2_HF, revision=R2D2_HF_REV, local_dir=str(CACHE / "hf" / "zephyr_7b_r2d2"),
                                allow_patterns=["*.json", "*.safetensors", "tokenizer.model"])
    pull_missing([R2D2_F16], log=log)
    blob = _blob_path(_show(R2D2_F16))
    chk = wcheck.compare(Path(src_dir), blob, log=log)
    chk["gguf"], chk["checkpoint"] = R2D2_F16, f"{R2D2_HF}@{R2D2_HF_REV}"
    jdump(chk, OUT / "diag" / "r2d2_weights_check.json")
    if not chk["ok"]:
        publish([OUT / "diag" / "r2d2_weights_check.json"], f"v21r R2D2: weights check failed ({R2D2_F16})")
        raise SystemExit(f"{R2D2_F16} does not hold {R2D2_HF}'s weights (diag/r2d2_weights_check.json)")
    if R2D2 in _digests():
        log(f"  ollama rm {R2D2} (not the checked F16 import)")
        subprocess.run(["ollama", "rm", R2D2])
    mf = CACHE / "r2d2.Modelfile"
    mf.parent.mkdir(parents=True, exist_ok=True)
    with open(mf, "w", encoding="utf-8", newline="\n") as h:        # no CRLF on Windows: the template is compared as is
        h.write(f'FROM {R2D2_F16}\nTEMPLATE """{R2D2_TEMPLATE}"""\n' + "".join(f'PARAMETER stop "{s}"\n' for s in R2D2_STOPS))
    log(f"  ollama create {R2D2} -f {mf}")
    if subprocess.run(["ollama", "create", R2D2, "-f", str(mf)]).returncode:
        raise SystemExit(f"ollama create {R2D2} failed")
    jdump({"source": f"{R2D2_F16} = {R2D2_HF}@{R2D2_HF_REV}", "weights_check": True, "digest": _digests().get(R2D2)},
          _r2d2_marker())
    rep = r2d2_served()
    f = OUT / "r2d2_Modelfile"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(f"# built from\n{mf.read_text(encoding='utf-8')}\n# ollama show {R2D2} (api/show)\n"
                 + json.dumps({k: rep.get(k) for k in ("source", "digest", "quantization", "template", "ok")}, indent=1)
                 + "\n", encoding="utf-8")
    return f


def unload(models: list[str]) -> int:
    """Free GPU memory: ask Ollama to unload each model now (keep_alive 0); unknown models are ignored."""
    for m in models:
        try:
            _ollama("/api/generate", {"model": m, "keep_alive": 0})
        except Exception:  # noqa: BLE001
            pass
    return 0


PY = sys.executable
