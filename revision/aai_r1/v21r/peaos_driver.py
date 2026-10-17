"""DESIGN.md: the submitted v2.1 PEAOS benches for the revision. Runs inside a PEAOS checkout (cwd = PEAOS root) as a
child of peinn2.v21r; loads peaos_patches.py by path (lookup router, generation store, Ollama recovery, langchain shim).

    python peaos_driver.py record --out DIR --runs JSON [--morables F]
        mock LLM, judges off; logs every routing text the PEINN arm sends (record.jsonl) with the run protocol
    python peaos_driver.py run --out DIR --tag TAG --runs JSON --arms H05,... [--force TIER] --phase gen|judge
        real Ollama; TAG names the sub-folder of DIR/peaos_out; --force sends every PEINN-arm text to one tier
        (the response matrix, DESIGN.md 6); the generation store DIR/gen_cache.jsonl is shared by all tags of DIR
        generation seed: 42 + k for the k-th identical request (same model and prompt) in the process, so run r of a
        bench gets the same seed in every tag (the stored answer is reused) and runs differ; judge calls seed 42
        --capture: every generation call is logged (tier, model, prompt) and replayed once against Ollama for its
        token counts and durations (route cost, DESIGN.md 7) -> DIR/cost_<tag>.jsonl
    python peaos_driver.py audit --out DIR --record F --corpus CSV [CSV ...]
        PEAOS ProvenanceGuard (all benchmark files must be found) + every recorded routing text and its pieces;
        writes DIR/audit.jsonl (sha, verdict, reason, containment) for every corpus row
RUNS is a JSON object bench -> number of runs (the submitted protocol: HarmBench and GGB 10, the rest 5).
"""
from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
E2E = HERE / "peaos_patches.py"
PEINN_ARMS = {"H04", "H07", "H10", "H13"}


def _e2e():
    spec = importlib.util.spec_from_file_location("e2e_peaos", E2E)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Forced(dict):
    """A routes table that sends every text to one tier (the driver's Router calls routes.get(sha))."""

    def __init__(self, tier: str):
        super().__init__()
        self.tier = tier

    def get(self, key, default=None):
        return self.tier


def _set_out(work: Path) -> None:
    """Point the harness and every evaluator module at one output folder (keeps the PEAOS checkout untouched)."""
    import importlib
    import run_stat_batch as R
    work.mkdir(parents=True, exist_ok=True)
    R.FINAL_DIR = work
    for name in ("harmbench_eval", "xstest_eval", "taxonomy_eval", "ethics_eval", "morables_eval", "ggb_eval"):
        try:
            m = importlib.import_module(f"pea_eval.evaluators.{name}")
        except ImportError:
            continue
        for attr in ("OUTPUT_DIR", "FINAL_DIR"):
            if hasattr(m, attr):
                setattr(m, attr, work)


async def _benches(E, a, mode: str) -> int:
    import run_stat_batch as R
    from pea_eval.config.settings import load_settings
    settings = load_settings("real")
    settings.enable_judge = mode == "run" and E.PHASE["phase"] != "gen"
    if getattr(settings.ee, "engine", "?") != "neutro_v21":
        print(f"engine={getattr(settings.ee, 'engine', '?')!r}, expected neutro_v21", flush=True)
        return 1
    runs = json.loads(a.runs)
    tag = a.tag if mode == "run" else "record"
    done_f = a.out / f"done_{tag}_{E.PHASE['phase'] if mode == 'run' else 'record'}.json"
    done = json.loads(done_f.read_text(encoding="utf-8")) if done_f.exists() else {}
    for b, n in runs.items():
        if b in done:
            print(f"[skip] {tag} {b} done: {done[b]}", flush=True)
            continue
        E.STATE["bench"] = b
        _set_out(a.out / "peaos_out" / tag / b)
        t0 = time.time()
        print(f"===== {mode} {tag} {b} (arms {a.arms}, {n} runs) =====", flush=True)
        r = await R.RUN_FUNCS[b](settings, int(n), a.arms)
        done[b] = {"csv": Path(r.get("csv_path", "")).name, "total": r.get("total"), "errors": r.get("errors"),
                   "sec": round(time.time() - t0, 1)}
        done_f.write_text(json.dumps(done, indent=1) + "\n", encoding="utf-8")
        print(done[b], flush=True)
    return 0


# ---- generation seeds and the cost capture (DESIGN.md 6, 7) -------------------------------------------

NEMO_TASKS = (("Should the user message be blocked", "self_check_input"),
              ("Should the bot response be blocked", "self_check_output"),
              ("express greeting", "dialog"))                 # rails.co examples appear in every Colang 1.0 dialog prompt
NEMO_SUBJECT = {"self_check_input": 'User message: "', "self_check_output": 'Bot response: "', "dialog": 'user "'}


def nemo_task(system_prompt: str, user_prompt: str) -> str:
    """The NeMo Guardrails task of a local call (NeMo sends its prompts with an empty system prompt), or ''."""
    if system_prompt:
        return ""
    return next((t for m, t in NEMO_TASKS if m in (user_prompt or "")), "")


def nemo_subject(task: str, prompt: str) -> str:
    """The text a NeMo prompt is about: the checked user message or bot response, the last user turn of a dialog."""
    key = NEMO_SUBJECT.get(task, "")
    if not key or key not in prompt:
        return ""
    s = prompt.rsplit(key, 1)[1] if task == "dialog" else prompt.split(key, 1)[1]
    q = s.rfind("Question:")
    s = s[:q] if q >= 0 and task != "dialog" else s.split("\n", 1)[0]
    return s.rstrip().rstrip('"')


def seeds(E, L, judge: str | None, out: Path, tag: str, phase: str, capture: list | None = None) -> None:
    """Outermost wrapper of call_local: the seed goes into options (so the generation store keys on it) and into
    the client before the inner call reads it (no await in between, so concurrent calls cannot swap seeds).
    Judge calls (seed 42, so deterministic) are stored in DIR/judge_cache.jsonl and reused across tags: the same
    question and answer get the same verdict once. Call counts per kind -> DIR/calls_<tag>_<phase>.json."""
    import atexit
    import collections
    import hashlib
    inner = L.EvalLLMClient.call_local
    seen = collections.Counter()
    jk = (judge or "").split(":latest")[0]
    jstore = out / "judge_cache.jsonl"
    jcache = {}
    if jstore.exists():
        for x in jstore.read_text(encoding="utf-8").split("\n"):
            if x.strip():
                try:                                                          # a line cut by a stop is skipped
                    r = json.loads(x)
                except json.JSONDecodeError:
                    continue
                jcache[r["k"]] = r
    n = collections.Counter()

    async def call(self, system_prompt="", user_prompt="", model_override="", max_tokens=None, stop=None, options=None):
        model = model_override or ""
        is_judge = bool(jk) and model.split(":latest")[0] == jk
        base = [model, system_prompt, user_prompt, max_tokens, stop]
        if is_judge:
            s = E.SEED
            o = {k: v for k, v in (options or {}).items() if k != "keep_alive"}
            jkey = hashlib.sha1(json.dumps(base + [o], sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
            if jkey in jcache:
                n["judge_reused"] += 1
                c = jcache[jkey]
                return L.LLMResponse(text=c["text"], latency_ms=0, model_name=model, thought_block=c.get("tb", ""))
        else:
            k = hashlib.sha1(json.dumps(base, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()
            s = E.SEED + seen[k]
            seen[k] += 1
        opts = dict(options or {}, seed=s)
        self._eval_seed = s
        t0 = time.perf_counter()
        r = await inner(self, system_prompt=system_prompt, user_prompt=user_prompt, model_override=model_override,
                        max_tokens=max_tokens, stop=stop, options=opts)
        if is_judge:
            n["judge_live"] += 1
            if not getattr(r, "error", ""):
                jcache[jkey] = {"k": jkey, "text": r.text, "tb": getattr(r, "thought_block", "")}
                with open(jstore, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(jcache[jkey], ensure_ascii=False) + "\n")
        else:
            n["gen_reused" if getattr(r, "latency_ms", 1) == 0 else "gen_live"] += 1
        task = "" if is_judge else nemo_task(system_prompt, user_prompt)
        if task:                                                    # R2: why NeMo answers or refuses (nemo-doc step)
            subj = nemo_subject(task, user_prompt or "")
            row = {"tag": tag, "phase": phase, "bench": E.STATE.get("bench", ""), "model": model, "task": task,
                   "subj_sha": hashlib.sha1(subj.encode("utf-8")).hexdigest()[:16], "subj": subj[:160],
                   "text": (r.text or "")[:300], "error": str(getattr(r, "error", "") or "")[:200],
                   "max_tokens": max_tokens, "stop": stop, "temperature": (options or {}).get("temperature")}
            with open(out / f"nemo_calls_{tag}_{phase}.jsonl", "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        if capture is not None and not is_judge:
            capture.append({"model": model, "system": system_prompt, "user": user_prompt, "max_tokens": max_tokens,
                            "stop": stop, "seed": s, "temperature": self._eval_temperature,
                            "wall_ms": round((time.perf_counter() - t0) * 1000, 1), "chars": len(r.text or "")})
        return r
    L.EvalLLMClient.call_local = call
    atexit.register(lambda: (out / f"calls_{tag}_{phase}.json").write_text(json.dumps(dict(n)) + "\n", encoding="utf-8"))


def replay(E, capture: list, f: Path) -> None:
    """Token counts and Ollama durations of every captured call (same model, prompt, seed, temperature)."""
    with open(f, "w", encoding="utf-8") as fh:
        for c in capture:
            msgs = ([{"role": "system", "content": c["system"]}] if c["system"] else []) + [{"role": "user", "content": c["user"]}]
            opts = {"seed": c["seed"], "num_predict": c["max_tokens"] or 256, "num_ctx": E.NUM_CTX}
            if c["temperature"] is not None:
                opts["temperature"] = c["temperature"]
            if c["stop"]:
                opts["stop"] = c["stop"]
            try:
                r = E._http("/api/chat", {"model": c["model"], "messages": msgs, "stream": False, "options": opts}, timeout=600)
                m = {k: r.get(k) for k in ("prompt_eval_count", "eval_count", "total_duration", "load_duration",
                                          "prompt_eval_duration", "eval_duration")}
            except Exception as e:  # noqa: BLE001
                m = {"error": f"{type(e).__name__}: {e}"[:200]}
            fh.write(json.dumps({"model": c["model"], "seed": c["seed"], "wall_ms": c["wall_ms"], "chars": c["chars"], **m}) + "\n")


# ---- isolation audit (DESIGN.md 3) ----------------------------------------------------------------

def audit(a) -> int:
    from pea_eval.pge import provenance_guard as pg
    g = pg.ProvenanceGuard.build()
    expected = sum(1 for rel, _, _ in pg.BENCH_SOURCES[:8])          # the six benchmarks' files (harm, xs, mor, ggb, 3 eth, tax)
    found = {rel: (pg.PEAOS / rel).exists() for rel, _, _ in pg.BENCH_SOURCES}
    missing = [rel for rel, ok in list(found.items())[:8] if not ok]
    rec = [json.loads(x) for x in Path(a.record).read_text(encoding="utf-8").split("\n") if x.strip()]
    n0 = len(g.hashes)
    for r in rec:                                                   # the texts the harness actually sends, and pieces
        t = r["text"]
        for piece in [t] + [p for p in re.split(r"\n+", t) if len(p.split()) >= 5]:
            piece = re.sub(r"^\[(?:Turn \d+|Current)\] User: ", "", piece.strip())
            g.hashes.add(pg._sha(piece))
            g.shingles |= pg._shingles(piece, 5)
    meta = {"bench_files": found, "missing_bench_files": missing, "expected_files": expected,
            "guard_items": g.n_items, "guard_hashes_files": n0, "guard_hashes_total": len(g.hashes),
            "recorded_texts": len(rec)}
    print(json.dumps(meta), flush=True)
    if missing:
        (a.out / "audit_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
        print(f"stop: benchmark files missing from the guard: {missing}", flush=True)
        return 2
    import csv
    import hashlib
    out = a.out / "audit.jsonl"
    n = 0
    with open(out, "w", encoding="utf-8") as fh:
        for path in a.corpus:
            for row in csv.DictReader(open(path, encoding="utf-8")):
                t = row.get("text", "")
                ok, why = g.check(t)
                sh = pg._shingles(t, 5)
                cont = len(sh & g.shingles) / len(sh) if sh else 0.0
                fh.write(json.dumps({"file": Path(path).name, "sha": hashlib.sha1(t.encode("utf-8")).hexdigest(),
                                     "source": row.get("source", ""), "ok": ok, "why": why.split("(")[0],
                                     "containment": round(cont, 4)}) + "\n")
                n += 1
    meta["corpus_rows"] = n
    (a.out / "audit_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")
    print(f"audit: {n} corpus rows -> {out}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["record", "run", "audit", "nemo-probe"])
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tag", default="main")
    ap.add_argument("--runs", default="{}")
    ap.add_argument("--arms", default="H07")
    ap.add_argument("--force", choices=["Hard-block", "Reasoned-Refusal", "Deliberation", "Soft-reasoning", "Direct-Answer"])
    ap.add_argument("--phase", choices=["gen", "judge"], default="gen")
    ap.add_argument("--judge")
    ap.add_argument("--morables", type=Path)
    ap.add_argument("--record", type=Path)
    ap.add_argument("--corpus", nargs="*", default=[])
    ap.add_argument("--model", default="gemma4:e4b")
    ap.add_argument("--capture", action="store_true", help="log and replay every generation call (route cost)")
    a = ap.parse_args(argv)
    a.arms = [x for x in a.arms.split(",") if x]
    a.out.mkdir(parents=True, exist_ok=True)
    sys.path.insert(0, os.getcwd())
    os.environ["PEAOS_EE_ENGINE"] = "neutro_v21"
    os.environ.setdefault("PEINN_NEUTRO_HEAD", str(Path.cwd() / "pea_eval" / "data" / "ee_neutro_head_v4.pt"))
    if a.mode == "audit":
        return audit(a)
    E = _e2e()
    E.quiet_noise()
    E.langchain_shim()
    E.nemo_fair()
    E.repeat_guard(a.out / "repeat_guard.jsonl")                              # DESIGN.md 30
    if a.mode == "nemo-probe":
        E.patch("run", a.out, {}, a.morables, a.judge)
        return asyncio.run(E.nemo_probe(a.out, a.model))
    if a.mode == "record":
        E.patch("record", a.out, None, a.morables, None)
        return asyncio.run(_benches(E, a, "record"))
    E.PHASE["phase"] = a.phase
    if a.force:
        bad = [x for x in a.arms if x not in PEINN_ARMS]
        if bad:
            print(f"--force applies to the PEINN arms only; got {bad}", flush=True)
            return 2
    routes = Forced(a.force) if a.force else {}
    E.patch("run", a.out, routes, a.morables, a.judge)
    from pea_eval.evaluators import llm_client as L
    cap = [] if a.capture else None
    seeds(E, L, a.judge, a.out, a.tag, a.phase, cap)
    rc = asyncio.run(_benches(E, a, "run"))
    if cap and not rc:                                              # a resumed, already finished tag keeps its file
        replay(E, cap, a.out / f"cost_{a.tag}.jsonl")
    return rc


if __name__ == "__main__":
    sys.exit(main())
