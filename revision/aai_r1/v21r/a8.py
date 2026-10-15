"""DESIGN.md 10 (step A8): LoRA on the protected model (qwen2.5-7B) with the same supervision, no router.

    python -m v21r a8 [--check]

1. targets: every train and val item of the isolated corpus gets the answer its teacher class asks for: harm -> the
   Hard-block refusal, dilemma -> the model's own answer under the Deliberation prompt, safe -> its own plain answer
   (PEAOS prompt_builder, PEAOS_EE_ENGINE=neutro_v21; Ollama qwen2.5:7b-instruct, temperature 0.3, top-p 0.95, seed 42).
2. train: a8_train.py (LoRA, merged) on Qwen/Qwen2.5-7B-Instruct.
3. ollama: the merged model quantised to q4_K_M (the quantisation of qwen2.5:7b-instruct) with that model's template.
4. bench: the submitted benches and run protocol on arm H05 (qwen Vanilla, the bare prompt) with its model replaced by
   the LoRA model (peaos_driver_a8.py), generate then judge.
--check: Qwen2.5-0.5B-Instruct, 8 items per class, GGB + XSTest once (the whole path, small).
Each part leaves a marker in the work folder, so a rerun resumes at the first unfinished part.
"""
from __future__ import annotations

import json
import os
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


def modelfile(check: bool) -> str:
    """FROM the merged folder, with the template, stop words and parameters of qwen2.5:7b-instruct."""
    r = subprocess.run(["ollama", "show", BASE, "--modelfile"], capture_output=True, encoding="utf-8", errors="replace")
    if r.returncode or "TEMPLATE" not in r.stdout:
        raise SystemExit(f"ollama show {BASE} --modelfile failed: {r.stderr[-300:]}")
    return C.modelfile_with_weights(r.stdout, str((wdir(check) / "merged").resolve()))


def ollama(check: bool, log=print) -> int:
    w = wdir(check)
    done = w / "ollama.json"
    if done.exists():
        log("A8 ollama: done")
        return 0
    f = w / "Modelfile"
    f.write_text(modelfile(check), encoding="utf-8")
    log(f"[v21r] $ ollama create {SERVED[check]} -q {QUANT} -f {f}")
    if subprocess.run(["ollama", "create", SERVED[check], "-q", QUANT, "-f", str(f)]).returncode:
        return 1
    tags = {m["name"]: m for m in json.loads(C._ollama("/api/tags"))["models"]}
    m = tags.get(SERVED[check]) or {}
    smoke = json.loads(C._ollama("/api/chat", {"model": SERVED[check], "stream": False, "options": dict(GEN_OPTS),
                                               "messages": [{"role": "user", "content": "What is the capital of France?"}]},
                                 timeout=600))
    ans = (smoke.get("message") or {}).get("content", "")
    C.jdump({"model": SERVED[check], "digest": m.get("digest"), "size": m.get("size"), "quant": QUANT,
             "details": m.get("details"), "smoke": ans[:200]}, done)
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
