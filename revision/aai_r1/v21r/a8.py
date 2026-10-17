"""DESIGN.md 10 (step A8): LoRA on the protected model (qwen2.5-7B) with the same supervision, no router.

    python -m v21r a8 [--check]

1. targets: every train and val item of the isolated corpus gets the answer its teacher class asks for: harm -> the
   Hard-block refusal, dilemma -> the model's own answer under the Deliberation prompt, safe -> its own plain answer
   (PEAOS prompt_builder, PEAOS_EE_ENGINE=neutro_v21; Ollama qwen2.5:7b-instruct, temperature 0.3, top-p 0.95, seed 42).
2. train: a8_train.py (LoRA, merged) on Qwen/Qwen2.5-7B-Instruct.
3. ollama: the merged model written as an F16 GGUF (gguf_qwen2), quantised to q4_K_M by llama.cpp's llama-quantize (the quantisation of qwen2.5:7b-instruct) with that model's template.
4. bench: the submitted benches and run protocol on arm H05 (qwen Vanilla, the bare prompt) with its model replaced by
   the LoRA model (peaos_driver_a8.py), generate then judge.
--check: Qwen2.5-0.5B-Instruct, 8 items per class, GGB + XSTest once (the whole path, small).
Each part leaves a marker in the work folder, so a rerun resumes at the first unfinished part.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

from . import common as C
from . import data as D

HF_MODEL = {False: "Qwen/Qwen2.5-7B-Instruct", True: "Qwen/Qwen2.5-0.5B-Instruct"}
SERVED = {False: "qwen2.5-a8:latest", True: "qwen2.5-a8-check:latest"}
QUANT = "q4_K_M"
BASE = C.BASES["qwen"]
ARM = C.ARMS["qwen"]["Vanilla"]                         # H05: the bare prompt, no defence
GEN_OPTS = {"temperature": 0.3, "top_p": 0.95, "seed": 42, "num_predict": 512, "num_ctx": 8192}
CHECK_PER_CLASS = 8
DRIVER = Path(__file__).with_name("peaos_driver_a8.py")
TRAIN = Path(__file__).with_name("a8_train.py")


def wdir(check: bool) -> Path:
    d = D.wdir(check) / "a8"
    d.mkdir(parents=True, exist_ok=True)
    return d


def tier_prompts() -> dict:
    """The neutro_v21 tier prompts of the PEAOS checkout the benches run (so A8 learns what PEINN would send)."""
    os.environ["PEAOS_EE_ENGINE"] = "neutro_v21"
    sys.path.insert(0, str(C.peaos()))
    from pea_eval.evaluators import prompt_builder as P
    delib_system = P.build_judge_pass_prompt("x", "")[0]
    return {"refusal": P.HARD_BLOCK_RESPONSE, "deliberation": delib_system}


def plan(df: pd.DataFrame, check: bool) -> pd.DataFrame:
    """Train and val items with their teacher class; the check run keeps CHECK_PER_CLASS train items per class."""
    x = df[df.split.isin(["train", "val"])].copy()
    x["cls"] = C.teacher_class(x["T"], x["I"], x["F"])
    if check:
        x = x[x.split == "train"]
        x = pd.concat([g.sort_values("sha").head(CHECK_PER_CLASS) for _, g in x.groupby("cls", sort=True)])
        x.loc[x.groupby("cls").head(2).index, "split"] = "val"
    return x.sort_values(["split", "sha"]).reset_index(drop=True)


def request(row, tp: dict) -> dict | None:
    """The Ollama chat request for one item, or None when the target is the fixed refusal."""
    if row["cls"] == "harm":
        return None
    msgs = [{"role": "user", "content": row["text"]}]
    if row["cls"] == "dilemma":
        msgs = [{"role": "system", "content": tp["deliberation"]}] + msgs
    return {"model": BASE, "messages": msgs, "stream": False, "options": dict(GEN_OPTS)}


def targets(check: bool, log=print) -> int:
    w = wdir(check)
    out = w / "targets.jsonl"
    have = {r["sha"] for r in C.jsonl(out)} if out.exists() else set()
    tp = tier_prompts()
    items = plan(D.load_split(check), check)
    todo = items[~items.sha.isin(have)]
    log(f"A8 targets: {len(items)} items ({items.cls.value_counts().to_dict()}), {len(todo)} to do")
    C.pull_missing([BASE], log=log)

    def one(row):
        rq = request(row, tp)
        if rq is None:
            return row, tp["refusal"], None
        try:
            r = json.loads(C._ollama("/api/chat", rq, timeout=900))
            return row, (r.get("message") or {}).get("content", ""), r.get("eval_count")
        except Exception as e:  # noqa: BLE001
            return row, None, f"{type(e).__name__}: {e}"[:200]

    bad = 0
    with open(out, "a", encoding="utf-8") as fh, ThreadPoolExecutor(4) as ex:
        for i, (row, t, info) in enumerate(ex.map(one, [r for _, r in todo.iterrows()])):
            if not t or not t.strip():
                bad += 1
                log(f"  no target for {row['sha'][:10]} ({row['cls']}): {info}")
                continue
            fh.write(json.dumps({"sha": row["sha"], "split": row["split"], "cls": row["cls"], "text": row["text"],
                                 "target": t, "tokens": info if isinstance(info, int) else None}, ensure_ascii=False) + "\n")
            if (i + 1) % 200 == 0:
                fh.flush()
                log(f"  {i + 1}/{len(todo)}")
    if bad:
        log(f"stop: {bad} items without a target (rerun to retry them)")
        return 1
    return 0


def train(check: bool, log=print) -> int:
    w = wdir(check)
    rep = w / "train.json"
    if rep.exists() and (w / "merged" / "config.json").exists():
        log("A8 train: done")
        return 0
    C.unload([BASE, C.JUDGE])
    env = {k: v for k, v in os.environ.items() if k not in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    env.update(PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    hp = {"batch": 2, "accum": 2} if check else {}
    cmd = [C.PY, "-u", str(TRAIN), "--data", str(w / "targets.jsonl"), "--out", str(w / "merged"), "--report", str(rep),
           "--model", HF_MODEL[check], "--hp", json.dumps(hp)]
    log("[v21r] $ " + " ".join(cmd))
    return subprocess.run(cmd, env=env).returncode


def modelfile(check: bool, weights: Path) -> str:
    """FROM the merged model's F16 GGUF, with the template, stop words and parameters of qwen2.5:7b-instruct."""
    r = subprocess.run(["ollama", "show", BASE, "--modelfile"], capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode or "TEMPLATE" not in r.stdout:
        raise SystemExit(f"ollama show {BASE} --modelfile failed: {r.stderr[-300:]}")
    return C.modelfile_with_weights(r.stdout, str(Path(weights).resolve()))


def gguf(check: bool, log=print) -> tuple[Path, dict] | None:
    """The merged folder as an F16 GGUF (Ollama no longer quantises safetensors to q4_K_M), checked tensor by tensor."""
    w = wdir(check)
    out, rep = w / "merged.f16.gguf", w / "gguf.json"
    if out.exists() and rep.exists() and C.jload(rep).get("check", {}).get("ok"):
        return out, C.jload(rep)
    from . import gguf_qwen2 as G
    r = {"write": G.write(w / "merged", out, SERVED[check].split(":")[0], log=log)}
    r["check"] = G.check(w / "merged", out, log=log)
    C.jdump(r, rep)
    if not r["check"]["ok"]:
        log("stop: the F16 GGUF does not match the merged checkpoint")
        return None
    return out, r


LLAMA_API = "https://api.github.com/repos/ggml-org/llama.cpp/releases/latest"
LLAMA_ASSET = re.compile(r"^llama-(b\d+)-bin-win-cpu-x64\.zip$")
LLAMA_EXE = "llama-quantize.exe"
GGUF_Q4_K_M = 15                                        # llama_ftype LLAMA_FTYPE_MOSTLY_Q4_K_M


def _get(url: str, timeout: float = 120):
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "v21r", "Accept": "application/vnd.github+json"})
    return urllib.request.urlopen(req, timeout=timeout)


def llama_quantize(log=print) -> tuple[Path, dict]:
    """llama.cpp's llama-quantize from the latest release (Windows CPU build) in the cache, with its tag and sha256.
    Ollama no longer quantises at import: a GGUF must arrive quantised, and a safetensors folder only goes to int4,
    int8, nvfp4, mxfp4 or mxfp8 (a8-check, 2026-10-17). Eugene's card 10-17: use llama.cpp's own tool."""
    import hashlib
    import zipfile
    d = C.CACHE / "llama.cpp"
    info_f = d / "tool.json"
    if info_f.exists():
        info = C.jload(info_f)
        if Path(info["exe"]).exists():
            return Path(info["exe"]), info
    with _get(LLAMA_API, 60) as r:
        rel = json.loads(r.read().decode("utf-8"))
    hits = [a for a in rel.get("assets", []) if LLAMA_ASSET.match(a["name"])]
    if not hits:
        raise SystemExit(f"llama.cpp {rel.get('tag_name')}: no Windows CPU zip among {[a['name'] for a in rel.get('assets', [])]}")
    a = hits[0]
    d.mkdir(parents=True, exist_ok=True)
    z = d / a["name"]
    h = hashlib.sha256()
    log(f"  llama.cpp {rel['tag_name']}: {a['name']} ({a.get('size', 0) / 2**20:.0f} MiB)")
    with _get(a["browser_download_url"]) as r, open(z, "wb") as f:
        while chunk := r.read(1 << 20):
            h.update(chunk)
            f.write(chunk)
    sha = h.hexdigest()
    if a.get("digest") and a["digest"] != f"sha256:{sha}":
        z.unlink()
        raise SystemExit(f"llama.cpp zip sha256 {sha} != GitHub's {a['digest']}")
    out = d / rel["tag_name"]
    with zipfile.ZipFile(z) as zf:
        zf.extractall(out)
    exe = next(iter(sorted(out.rglob(LLAMA_EXE))), None)
    if exe is None:
        raise SystemExit(f"{LLAMA_EXE} not in {a['name']}")
    info = {"tag": rel["tag_name"], "asset": a["name"], "sha256": sha, "github_digest": a.get("digest"), "exe": str(exe)}
    C.jdump(info, info_f)
    return exe, info


def quantize(check: bool, f16: Path, log=print) -> tuple[Path, dict] | None:
    """F16 GGUF -> q4_K_M GGUF with llama-quantize; the file type in the result is checked."""
    from . import wcheck as W
    w = wdir(check)
    q, rep = w / "merged.q4_k_m.gguf", w / "quantize.json"
    if q.exists() and rep.exists():
        return q, C.jload(rep)
    exe, info = llama_quantize(log)
    tmp = q.with_suffix(".part.gguf")
    cmd = [str(exe), str(f16), str(tmp), QUANT.upper()]
    log("[v21r] $ " + " ".join(cmd))
    if subprocess.run(cmd).returncode or not tmp.exists():
        log("stop: llama-quantize failed")
        return None
    meta, _ = W.read_gguf(tmp)
    if meta.get("general.file_type") != GGUF_Q4_K_M:
        log(f"stop: quantised file type {meta.get('general.file_type')}, wanted {GGUF_Q4_K_M} (Q4_K_M)")
        return None
    tmp.replace(q)
    r = {"tool": info, "file_type": meta.get("general.file_type"), "bytes": q.stat().st_size}
    C.jdump(r, rep)
    return q, r


def ollama(check: bool, log=print) -> int:
    w = wdir(check)
    done = w / "ollama.json"
    if done.exists():
        log("A8 ollama: done")
        return 0
    g = gguf(check, log)
    if g is None:
        return 1
    qz = quantize(check, g[0], log)
    if qz is None:
        return 1
    f = w / "Modelfile"
    with open(f, "w", encoding="utf-8", newline="\n") as h:
        h.write(modelfile(check, qz[0]))
    log(f"[v21r] $ ollama create {SERVED[check]} -f {f}")
    if subprocess.run(["ollama", "create", SERVED[check], "-f", str(f)]).returncode:
        return 1
    tags = {m["name"]: m for m in json.loads(C._ollama("/api/tags"))["models"]}
    m = tags.get(SERVED[check]) or {}
    smoke = json.loads(C._ollama("/api/chat", {"model": SERVED[check], "stream": False, "options": dict(GEN_OPTS),
                                               "messages": [{"role": "user", "content": "What is the capital of France?"}]},
                                 timeout=600))
    ans = (smoke.get("message") or {}).get("content", "")
    C.jdump({"model": SERVED[check], "digest": m.get("digest"), "size": m.get("size"), "quant": QUANT,
             "details": m.get("details"), "gguf_f16": g[1], "quantize": qz[1], "smoke": ans[:200]}, done)
    log(f"A8 smoke: {ans[:120]!r}")
    if not ans.strip():
        done.unlink()
        log("stop: the A8 model gave an empty answer")
        return 1
    return 0


def bench(check: bool, log=print) -> int:
    d = D.wdir(check) / "matrix" / "a8"
    d.mkdir(parents=True, exist_ok=True)
    C.pull_missing([BASE, C.JUDGE], log=log)
    from . import matrix as M
    for phase in ("gen", "judge"):
        cmd = [C.PY, DRIVER, "run", "--out", d, "--tag", "a8", "--runs", json.dumps(D.runs(check)), "--arms", ARM,
               "--phase", phase, "--judge", C.JUDGE, "--morables", D.morables(),
               "--model-map", json.dumps({BASE: SERVED[check]})]
        rc = C.child(cmd, C.peaos(), env=M._env())
        if rc:
            log(f"stop: A8 {phase} rc={rc}")
            return rc
    return 0


def collect(check: bool) -> pd.DataFrame:
    """The judged bench CSVs of the A8 arm, with tag, bench and base columns (as matrix.collect)."""
    d = D.wdir(check) / "matrix" / "a8" / "peaos_out" / "a8"
    parts = []
    for b in D.runs(check):
        fs = sorted((d / b).glob(f"{b}_batch_*.csv"))
        if fs:
            x = pd.read_csv(fs[-1], low_memory=False)
            x["tag"], x["bench"], x["base"] = "a8", b, "qwen"
            parts.append(x)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def summary(check: bool) -> dict:
    w, d = wdir(check), D.wdir(check) / "matrix" / "a8"
    tr = C.jload(w / "train.json") if (w / "train.json").exists() else {}
    tr.pop("loss_curve", None)
    calls = {f.stem[len("calls_"):]: C.jload(f) for f in sorted(d.glob("calls_*.json"))}
    tg = pd.DataFrame(C.jsonl(w / "targets.jsonl")) if (w / "targets.jsonl").exists() else pd.DataFrame()
    return {"hf_model": HF_MODEL[check], "served": SERVED[check], "train": tr, "calls": calls,
            "ollama": C.jload(w / "ollama.json") if (w / "ollama.json").exists() else None,
            "targets": {f"{s}|{c}": int(n) for (s, c), n in tg.groupby(["split", "cls"]).size().items()} if len(tg) else {}}


def a8(check: bool = False, log=print) -> int:
    for part in (targets, train, ollama, bench):
        rc = part(check, log)
        if rc:
            return rc
    o = D.odir(check) / "a8"
    o.mkdir(parents=True, exist_ok=True)
    f = C.jdump(summary(check), o / "a8.json")
    files = [f]
    for name in ("Modelfile",):
        src = wdir(check) / name
        if src.exists():
            (o / name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
            files.append(o / name)
    C.unload([SERVED[check]])
    if check:
        return 0
    return 0 if C.publish(files, "v21r A8: LoRA on qwen2.5-7B with the same supervision, benches on the merged model") else 1
