"""DESIGN.md 6 and 7 (steps N, M, K): the response matrix, the other arms and the route-cost probe.

Per base model, one folder (.cache/v21r/<mode>/matrix/<base>/) shares one generation store and one judge store:
    gen phase   PEINN arm forced to each tier (Direct-Answer first, so pass 1 is generated once and reused), then the
                other arms (Vanilla, R2D2 on zephyr, NeMo, Llama Guard) unforced
    judge phase the same tags again, answers from the store, judge qwen3:32b (same question and answer judged once)
Every tag and bench is resumable (the driver's done files). Answers stay in .cache; results/v21r/matrix holds counts.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

from . import common as C
from . import data as D

FORCED = {"Direct-Answer": "da", "Hard-block": "hb", "Reasoned-Refusal": "rr", "Deliberation": "de", "Soft-reasoning": "sr"}
ORDER = ("qwen", "gemma4", "gemma3", "zephyr")
COST_BENCHES = {"xstest": 1, "harmbench": 1}          # K: one run of each (95 texts), every tier, every base


def bases(check: bool) -> tuple:
    """V21R_BASES (comma list) narrows a run to some bases (the zephyr pre-test on the check benches, DESIGN.md 24)."""
    only = tuple(b for b in os.environ.get("V21R_BASES", "").split(",") if b in ORDER)
    return only or (("qwen",) if check else ORDER)


def tags(base: str) -> list[dict]:
    arm = C.ARMS[base]
    out = [{"tag": t, "arms": arm["PEINN"], "force": tier} for tier, t in FORCED.items()]
    others = [arm[k] for k in ("Vanilla", "R2D2", "NeMo", "LlamaGuard") if k in arm]
    out.append({"tag": "others", "arms": ",".join(others), "force": None})
    return out


def mdir(check: bool, base: str) -> Path:
    d = D.wdir(check) / "matrix" / base
    d.mkdir(parents=True, exist_ok=True)
    return d


EMBED = "sentence-transformers/all-MiniLM-L6-v2"           # NeMo's user-message index (fastembed)
EMBED_DIR = C.CACHE / "fastembed"


def _env() -> dict:
    return {"PEINN2_GEN_REUSE": "1", "PEINN2_POSTURE_SHA": "1", "FASTEMBED_CACHE_PATH": str(EMBED_DIR)}


def prefetch_embed(log=print) -> int:
    """NeMo answered 'internal error' in the submitted runs because fastembed could not load all-MiniLM-L6-v2: PEAOS's
    hf_backend forces HF_HUB_OFFLINE=1 at import, so an empty cache cannot be filled. Fill a fixed cache online in a
    separate process, then check an offline reload."""
    import subprocess
    env = {k: v for k, v in os.environ.items() if k not in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    code = ("import os,sys; from fastembed import TextEmbedding as T; d=sys.argv[1]; m=sys.argv[2]; "
            "v=list(T(m, cache_dir=d).embed(['prefetch check'])); os.environ['HF_HUB_OFFLINE']='1'; "
            "w=list(T(m, cache_dir=d).embed(['offline reload'])); print('dim', len(v[0]), len(w[0]))")
    r = subprocess.run([C.PY, "-c", code, str(EMBED_DIR), EMBED], env=env, capture_output=True, encoding="utf-8", errors="replace")
    log(f"  fastembed {EMBED} -> {EMBED_DIR}: rc={r.returncode} {r.stdout.strip()} {r.stderr.strip()[-300:] if r.returncode else ''}")
    return r.returncode


def _drive(d: Path, t: dict, phase: str, runs: dict, extra: list | None = None) -> int:
    cmd = [C.PY, D.DRIVER, "run", "--out", d, "--tag", t["tag"], "--runs", json.dumps(runs), "--arms", t["arms"],
           "--phase", phase, "--judge", C.JUDGE, "--morables", D.morables(), *(extra or [])]
    if t["force"]:
        cmd += ["--force", t["force"]]
    return C.child(cmd, C.peaos(), env=_env())


def models_needed(check: bool) -> list[str]:
    return sorted({C.BASES[b] for b in bases(check)} | {C.JUDGE, "llama-guard3:8b"} |
                  ({C.R2D2} if "zephyr" in bases(check) else set()))


def models_of(base: str) -> list[str]:
    """Models one base's tags call (pulled just before that base, so a missing model stops only its own base)."""
    return [C.BASES[base], C.JUDGE, "llama-guard3:8b"]


# ---- N: NeMo must answer before any NeMo arm runs ----------------------------------------------------

def nemo(check: bool = False, log=print) -> int:
    if prefetch_embed(log):
        return 1
    res = {}
    for b in bases(check):
        d = D.wdir(check) / "nemo_probe" / b
        d.mkdir(parents=True, exist_ok=True)
        (d / "nemo_probe.json").unlink(missing_ok=True)
        C.child([C.PY, D.DRIVER, "nemo-probe", "--out", d, "--model", C.BASES[b], "--judge", C.JUDGE,
                 "--morables", D.morables()], C.peaos(), env=_env())
        f = d / "nemo_probe.json"
        if not f.exists():
            res[b] = {"ok": False, "why": "no probe output"}
            continue
        pr = C.jload(f)["probes"]
        bad = [p["user"][:40] for p in pr if "internal error" in (p["out"] or "").lower() or p["exception"] or not p["out"]]
        res[b] = {"ok": not bad and len(pr) == 3, "answered": len(pr) - len(bad), "outputs": [p["out"][:160] for p in pr]}
        log(f"NeMo {b}: {res[b]['answered']}/3")
    f = C.jdump(res, D.odir(check) / "nemo_probe.json")
    if not all(r["ok"] for r in res.values()):
        log("stop: NeMo did not answer the three probe prompts")
        return 1
    if check:
        return 0
    return 0 if C.publish([f], "v21r N: NeMo Guardrails answers the probe prompts on every base (fastembed prefetched)") else 1


# ---- M: the matrix ------------------------------------------------------------------------------------

def collect(check: bool, base: str) -> pd.DataFrame:
    """Every bench CSV of every tag of one base, with tag and bench columns (judge-phase CSVs only)."""
    d = mdir(check, base) / "peaos_out"
    parts = []
    for t in tags(base):
        for b in D.runs(check):
            fs = sorted((d / t["tag"] / b).glob(f"{b}_batch_*.csv"))
            if not fs:
                continue
            x = pd.read_csv(fs[-1], low_memory=False)
            x["tag"], x["bench"], x["base"] = t["tag"], b, base
            parts.append(x)
    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def summary(check: bool, base: str) -> dict:
    d = mdir(check, base)
    df = collect(check, base)
    calls = {f.stem[len("calls_"):]: C.jload(f) for f in sorted(d.glob("calls_*.json"))}
    st = {"rows": {}, "calls": calls}
    if len(df):
        st["rows"] = {f"{t}|{b}|{a}": int(n) for (t, b, a), n in df.groupby(["tag", "bench", "arm_id"]).size().items()}
        txt = df.filter(regex="^response").astype(str).agg(" ".join, axis=1).str.lower()
        st["internal_error_rows"] = {a: int(n) for a, n in df[txt.str.contains("internal error")].groupby("arm_id").size().items()}
        if "error" in df:
            st["error_rows"] = {a: int(n) for a, n in df[df["error"].fillna("").astype(str) != ""].groupby("arm_id").size().items()}
    return st


def matrix(check: bool = False, log=print) -> int:
    runs = D.runs(check)
    for b in bases(check):
        C.pull_missing(models_of(b), log=log)
        if b == "zephyr":
            mf = C.ensure_r2d2(log)
            if mf and not check and not C.publish([mf], f"v21r M: R2D2 model for Ollama ({C.R2D2_HF}, unquantized, HarmBench's prompt)"):
                return 1
        d = mdir(check, b)
        for phase in ("gen", "judge"):
            for t in tags(b):
                df = d / f"done_{t['tag']}_{phase}.json"
                if df.exists() and set(runs) <= set(C.jload(df)):               # every bench done: no driver start
                    log(f"== {b} {t['tag']} [{phase}] done")
                    continue
                log(f"== {b} {t['tag']} [{phase}] arms {t['arms']} force {t['force']}")
                rc = _drive(d, t, phase, runs)
                if rc:
                    log(f"stop: {b} {t['tag']} {phase} rc={rc}")
                    return rc
        st = summary(check, b)
        f = C.jdump(st, D.odir(check) / "matrix" / f"{b}.json")
        log(json.dumps({k: st[k] for k in st if k != "rows"})[:600])
        if not check:
            if not C.publish([f], f"v21r M: response matrix and other arms on {C.BASES[b]} (counts)"):
                return 1
    return 0


# ---- DESIGN.md 29: NeMo again with the fixed provider ------------------------------------------------------------

def nemo_reset(check: bool = False, log=print) -> int:
    """Moves the 'others' tag's done files, answers and NeMo logs of every base already answered into
    archive_nemo_wrapper_v1/, once per base (marker file), so the matrix runs that tag again: Vanilla, R2D2 and Llama
    Guard come back from the generation and judge stores, NeMo calls (new keys: they now carry options) run live."""
    import shutil
    for b in bases(check):
        d = mdir(check, b)
        mark = d / "nemo_fair.reset"
        if mark.exists():
            log(f"  {b}: already reset ({mark.read_text(encoding='utf-8').strip()})")
            continue
        arch = d / "archive_nemo_wrapper_v1"
        moved = []
        for f in [*d.glob("done_others_*.json"), *d.glob("nemo_calls_others_*.jsonl"), *d.glob("calls_others_*.json"),
                  d / "peaos_out" / "others"]:
            if f.exists():
                arch.mkdir(exist_ok=True)
                shutil.move(str(f), str(arch / f.name))
                moved.append(f.name)
        mark.write_text(f"{len(moved)} moved: {', '.join(moved)}\n", encoding="utf-8")
        log(f"  {b}: {len(moved)} moved to {arch.name}")
    return 0


# ---- DESIGN.md 30: calls Ollama cut with HTTP 500 (token repeat limit) answered again --------------------------------

def _error_rows(df: pd.DataFrame) -> dict:
    """Rows of the 'others' tag per arm whose answer is an internal error, empty, or carries an error field."""
    o = df[df.tag == "others"] if len(df) else df
    if not len(o):
        return {}
    resp = o.filter(regex="^response").fillna("").astype(str)
    bad = resp.agg(" ".join, axis=1).str.lower().str.contains("internal error")
    bad |= resp.apply(lambda c: c.str.strip().isin(("", "nan"))).all(axis=1)
    if "error" in o:
        bad |= o["error"].fillna("").astype(str).str.strip() != ""
    return {a: int(n) for a, n in o[bad.to_numpy()].groupby("arm_id").size().items()}


def repeat_reset(check: bool = False, log=print) -> int:
    """Bases whose 'others' tag has error rows get that tag set aside (done files, answers, call logs into
    archive_repeat_v1/, once per base), so the matrix answers it again with peaos_patches.repeat_guard: every call is
    served from the generation and judge stores except the ones that failed (failed calls were never stored).
    The PEINN tiers are not touched. Counts before are kept in results/matrix/repeat_fix.json."""
    import shutil
    f = D.odir(check) / "matrix" / "repeat_fix.json"
    rec = C.jload(f) if f.exists() else {}
    for b in bases(check):
        d = mdir(check, b)
        mark = d / "repeat_fix.reset"
        if mark.exists():
            log(f"  {b}: already reset ({mark.read_text(encoding='utf-8').strip()})")
            continue
        before = _error_rows(collect(check, b))
        rec.setdefault(b, {})["before"] = before
        if not sum(before.values()):
            mark.write_text("no error rows: nothing set aside\n", encoding="utf-8")
            log(f"  {b}: no error rows")
            continue
        arch = d / "archive_repeat_v1"
        moved = []
        for x in [*d.glob("done_others_*.json"), *d.glob("nemo_calls_others_*.jsonl"), *d.glob("calls_others_*.json"),
                  d / "peaos_out" / "others"]:
            if x.exists():
                arch.mkdir(exist_ok=True)
                shutil.move(str(x), str(arch / x.name))
                moved.append(x.name)
        mark.write_text(f"error rows {before}; {len(moved)} moved: {', '.join(moved)}\n", encoding="utf-8")
        log(f"  {b}: error rows {before}; {len(moved)} moved to {arch.name}")
    C.jdump(rec, f)
    return 0


def repeat_review(check: bool = False, log=print) -> int:
    """After the 'others' tag ran again: error rows per arm before and after, and the calls the repeat guard answered."""
    f = D.odir(check) / "matrix" / "repeat_fix.json"
    rec = C.jload(f) if f.exists() else {}
    for b in bases(check):
        d = mdir(check, b)
        g = d / "repeat_guard.jsonl"
        rows = C.jsonl(g) if g.exists() else []
        r = rec.setdefault(b, {})
        r["after"] = _error_rows(collect(check, b))
        r["guard_calls"] = len(rows)
        r["guard_stopped"] = sum(1 for x in rows if x.get("repeat_stop"))
        r["guard_models"] = sorted({x.get("model") for x in rows if x.get("model")})
        log(f"  {b}: error rows before {r.get('before')} after {r['after']}; repeat guard {len(rows)} calls "
            f"({r['guard_stopped']} cut)")
    C.jdump(rec, f)
    if check:
        return 0
    return 0 if C.publish([f], "v21r M: error rows before and after the Ollama repeat guard (counts)") else 1


def _means_before_after(A, bench: str, o: pd.DataFrame, n: pd.DataFrame) -> dict:
    """The paper's metrics of one arm on the old and the new rows: {metric: [before, after]}."""
    mo, mn = A.bench_metrics(bench, o), A.bench_metrics(bench, n)
    return {k: [mo[k]["mean"], mn[k]["mean"]] for k in mo if k in mn}


REPEAT_METRIC = {"harmbench": ["asr_binary"], "xstest": ["over_refusal", "unsafe_compliance"], "taxonomy": ["is_unsafe"],
                 "ethics": ["alignment", "rqi"], "morables": ["correct"], "ggb": ["score"]}


def repeat_diff(check: bool = False, log=print) -> int:
    """The 'others' rows before (archive_repeat_v1/) and after the rerun with the repeat guard, joined per arm, bench
    item and run: how many answers and scores changed, and which rows were error rows before. Answers to calls that
    were stored are replayed, so a change outside the failed calls points at an unstored call (inference to check).
    PEAOS judges five answers per call (xstest_eval JUDGE_BATCH_SIZE, ethics judge_dilemmas_batch): an error row
    that now has an answer enters the judged list and shifts every later batch, and the Dilemma list follows the
    order of a set of item ids (ethics_eval run_dilemmas), so a verdict can change on an unchanged answer
    ('score_changed_same_answer'). 'means' gives each arm's metrics before and after (DESIGN.md 31)."""
    from . import analyze as A
    out = {}
    for b in bases(check):
        d = mdir(check, b)
        old_root = d / "archive_repeat_v1" / "others"
        if not old_root.exists():
            continue
        res = {}
        for bench, cols in REPEAT_METRIC.items():
            fo = sorted((old_root / bench).glob(f"{bench}_batch_*.csv"))
            fn = sorted((d / "peaos_out" / "others" / bench).glob(f"{bench}_batch_*.csv"))
            if not fo or not fn:
                continue
            o, n = (pd.read_csv(x[-1], low_memory=False) for x in (fo, fn))
            for x in (o, n):
                x["rep"] = A.rep(x)
                x["resp"] = x.filter(regex="^response").fillna("").astype(str).agg(" | ".join, axis=1)
            k = ["arm_id", *A.KEYS[bench], "rep"]
            o, n = o.drop_duplicates(k), n.drop_duplicates(k)
            m = o.merge(n, on=k, suffixes=("_old", "_new"))
            for arm, g in m.groupby("arm_id"):
                ch = g.resp_old != g.resp_new
                sc = pd.Series(False, index=g.index)
                for c in cols:
                    if f"{c}_old" in g:
                        a, z = pd.to_numeric(g[f"{c}_old"], errors="coerce"), pd.to_numeric(g[f"{c}_new"], errors="coerce")
                        sc |= ~((a == z) | (a.isna() & z.isna()))
                err = g.resp_old.str.lower().str.contains("internal error") | g.resp_old.str.strip().isin(("", "nan", "nan | nan"))
                r = {"rows": int(len(g)), "unmatched_old": int(len(o[o.arm_id == arm]) - len(g)),
                     "answer_changed": int(ch.sum()), "score_changed": int(sc.sum()),
                     "score_changed_same_answer": int((sc & ~ch).sum()),
                     "changed_from_error_rows": int((ch & err).sum()),
                     "means": _means_before_after(A, bench, o[o.arm_id == arm], n[n.arm_id == arm])}
                if sc.any():
                    r["examples"] = [{"key": {c: str(v) for c, v in zip(k, row[k])},
                                      "old": row.resp_old[:160], "new": row.resp_new[:160],
                                      **{c: [str(row.get(f"{c}_old")), str(row.get(f"{c}_new"))] for c in cols}}
                                     for _, row in g[sc].head(3).iterrows()]
                res[f"{bench}|{arm}"] = r
        out[b] = res
        log(f"  {b}: " + ", ".join(f"{k} {v['answer_changed']}/{v['rows']} answers, {v['score_changed']} scores"
                                   for k, v in res.items() if v["answer_changed"]))
    f = C.jdump(out, D.odir(check) / "matrix" / "repeat_diff.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r M: 'others' answers and scores before and after the repeat-guard rerun (counts)") else 1


def nemo_fair_review(check: bool = True, log=print) -> int:
    """The NeMo arm on the pre-test after nemo_reset: every rail call carries a temperature (forwarded), the input and
    output self-checks run at NeMo's near-zero temperature, and NeMo answered every
    check bench with few empty or internal-error rows. Prints XSTest over-refusal of NeMo and Vanilla."""
    from . import nemo_doc as N
    bad = []
    for b in bases(check):
        _, rows = N.calls(check, b)
        if not rows:
            bad.append(f"{b}: no NeMo log")
            continue
        t = [r.get("temperature") for r in rows]
        sc = [r for r in rows if r["task"] in ("self_check_input", "self_check_output")]
        dl = [r for r in rows if r["task"] == "dialog"]
        log(f"{b}: NeMo calls {len(rows)}, without temperature {sum(x is None for x in t)}, self-check temperatures "
            f"{sorted({r.get('temperature') for r in sc}, key=str)[:5]}, self-check max_tokens "
            f"{sorted({r.get('max_tokens') for r in sc}, key=str)[:5]}, dialog with stop {sum(1 for r in dl if r.get('stop'))}/{len(dl)}")
        if any(x is None for x in t):
            bad.append(f"{b}: calls without temperature")
        if any((r.get("temperature") or 1) > 0.05 for r in sc):
            bad.append(f"{b}: self-check above NeMo's lowest temperature")
        # stop words: nemoguardrails 0.21 sets none for the Colang 1.0 intent, next-step and bot-message calls of this
        # config (generation.py binds only the temperature there), so they are reported, not required
        df = collect(check, b)
        o = df[df.tag == "others"] if len(df) else df
        n = o[o.arm_id == C.ARMS[b]["NeMo"]] if len(o) else o
        if not len(n):
            bad.append(f"{b}: no NeMo rows")
            continue
        resp = n.filter(regex="^response").fillna("").astype(str)
        empty = resp.apply(lambda c: c.str.strip().isin(("", "nan"))).all(axis=1)
        ie = resp.agg(" ".join, axis=1).str.lower().str.contains("internal error|\\[nemo blocked|\\[nemo error")
        share = float((empty | ie).mean())
        benches = set(n.bench.unique())
        x = o[o.bench == "xstest"]
        orr = {k: round(float(pd.to_numeric(x[(x.arm_id == C.ARMS[b][k]) & (x.expected_label == "safe")].over_refusal,
                                             errors="coerce").mean()), 3) for k in ("NeMo", "Vanilla")} if len(x) else {}
        log(f"{b}: NeMo rows {len(n)}, empty or internal error {share:.3f}, benches {sorted(benches)}, XSTest ORR {orr}")
        if share > 0.05:
            bad.append(f"{b}: NeMo empty or internal error {share:.3f}")
        if benches != set(o.bench.unique()):
            bad.append(f"{b}: NeMo missing benches {sorted(set(o.bench.unique()) - benches)}")
    if bad:
        log(f"NeMo pre-test failed: {bad}")
        return 1
    return 0


# ---- K: route cost ------------------------------------------------------------------------------------

# one CPU thread and no GPU: "-1" because Windows drops an empty variable from a child's environment
CPU1_ENV = {"CUDA_VISIBLE_DEVICES": "-1", "V21R_CPU_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}

def gate_time(check: bool, log=print) -> dict:
    """Gate compute per text (features + head + energy) on the GPU and on one CPU thread; ft_* is what the main
    variant A0ftM adds (its fine-tuned encoder passes and the Mahalanobis distance, DESIGN.md 24)."""
    texts = D.record_texts(check).text.tolist()[: 20 if check else 200]
    d = D.wdir(check) / "cost"
    d.mkdir(parents=True, exist_ok=True)
    tf = d / "gate_texts.json"
    tf.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    src = C.peinn() / "src"
    D._ensure_peinn_checkpoints(src)
    out = {}
    for dev, env in (("gpu", {}), ("cpu1", CPU1_ENV)):
        want = "cpu" if dev == "cpu1" else "cuda"
        for key, cmd, cwd, extra in (
                (dev, [C.PY, D.SIDE, "gate-time", "--texts", tf], src, {"PEINN_NEUTRO_HEAD": "ee_neutro_head_v4.pt"}),
                (f"ft_{dev}", [C.PY, "-m", "v21r", "ft-gate-time", "--texts", tf, *(["--check"] if check else [])],
                 C.ROOT, {})):
            f = d / f"{'gate' if key == dev else 'ft_gate'}_{dev}.json"
            f.unlink(missing_ok=True)
            rc = C.child([*cmd, "--out", f], cwd, env={**extra, **env})
            r = C.jload(f) if f.exists() else {"error": f"rc {rc}, no result"}
            if r.get("device") not in (None, want):
                r["error"] = f"ran on {r.get('device')}, wanted {want}"
            out[key] = r
            log(f"gate time {key}: {r}")
    return out


def cost_gate(check: bool = False, log=print) -> int:
    """K, gate part again: the CPU run of the first cost step ran on the GPU (an empty CUDA_VISIBLE_DEVICES is
    dropped on Windows) or gave no result; route_cost.json keeps the tiers and gets the new gate block."""
    f = D.odir(check) / "route_cost.json"
    res = C.jload(f) if f.exists() else {"tiers": {}}
    res["gate"] = gate_time(check, log)
    bad = {k: v["error"] for k, v in res["gate"].items() if "error" in v}
    C.jdump(res, f)
    if check:
        return 1 if bad else 0
    ok = C.publish([f], "v21r K: gate time per text on the GPU and on one CPU thread")
    if bad:
        log(f"stop: gate time {bad}")
        return 1
    return 0 if ok else 1


def cost(check: bool = False, log=print) -> int:
    runs = {"xstest": 1} if check else COST_BENCHES
    res = {"gate": gate_time(check, log), "tiers": {}}
    for b in bases(check):
        d = D.wdir(check) / "cost" / b                        # own folder: every call is live and replayed
        for tier, tag in FORCED.items():
            t = {"tag": tag, "arms": C.ARMS[b]["PEINN"], "force": tier}
            rc = C.child([C.PY, D.DRIVER, "run", "--out", d, "--tag", tag, "--runs", json.dumps(runs), "--arms", t["arms"],
                          "--phase", "gen", "--morables", D.morables(), "--force", tier, "--capture"], C.peaos(),
                         env={"FASTEMBED_CACHE_PATH": _env()["FASTEMBED_CACHE_PATH"]})
            if rc:
                return rc
            rows = C.jsonl(d / f"cost_{tag}.jsonl")
            n_req = sum(1 for r in C.jsonl(d / "routed.jsonl") if r.get("tier") == tier)
            res["tiers"][f"{b}|{tier}"] = cost_summary(rows, n_req, tier)
            log(f"{b} {tier}: {json.dumps(res['tiers'][f'{b}|{tier}'])}")
    f = C.jdump(res, D.odir(check) / "route_cost.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r K: route cost per tier (gate time, generation calls, tokens, Ollama durations)") else 1


def cost_summary(rows: list[dict], n_req: int, tier: str) -> dict:
    """Per request. 'harness' counts every call the evaluation makes; 'deployed' drops the pass-1 answer a
    Hard-block request never shows (the harness generates it for bookkeeping)."""
    ok = [r for r in rows if "error" not in r]
    n = max(1, n_req)
    tot = lambda k: sum(r.get(k) or 0 for r in ok)                # noqa: E731
    h = {"calls": round(len(rows) / n, 3), "prompt_tokens": round(tot("prompt_eval_count") / n, 1),
         "output_tokens": round(tot("eval_count") / n, 1), "ollama_s": round(tot("total_duration") / 1e9 / n, 3),
         "load_s": round(tot("load_duration") / 1e9 / n, 3), "wall_s": round(sum(r["wall_ms"] for r in rows) / 1000 / n, 3)}
    dep = {k: 0 for k in h} if tier == "Hard-block" else dict(h)
    return {"requests": n_req, "replay_errors": len(rows) - len(ok), "harness": h, "deployed": dep}


def estimate(log=print) -> int:
    """Calls and hours for the full matrix, scaled from the check run (qwen, GGB + XSTest, one run) per answered row:
    rows per tag at the full protocol = the submitted rows of one arm (2,315) times the arms in the tag. A rough
    figure (the check benches are short; gemma3:12b is slower than qwen) reported before step M (DESIGN.md 8)."""
    d = mdir(True, "qwen")
    df = collect(True, "qwen")
    if not len(df):
        log("no check matrix yet")
        return 1
    full_arm = sum(D.sheet_rows().values())
    out = {"full_rows_per_arm": full_arm, "per_tag": {}, "total": {"gen_live": 0, "judge_live": 0, "hours": 0.0}}
    for t in tags("qwen"):
        rows = int((df.tag == t["tag"]).sum())
        if not rows:
            continue
        n_arms = len(t["arms"].split(","))
        scale = full_arm * n_arms / rows
        rec = {"check_rows": rows}
        for ph in ("gen", "judge"):
            c = C.jload(d / f"calls_{t['tag']}_{ph}.json") if (d / f"calls_{t['tag']}_{ph}.json").exists() else {}
            dn = C.jload(d / f"done_{t['tag']}_{ph}.json") if (d / f"done_{t['tag']}_{ph}.json").exists() else {}
            sec = sum(v.get("sec") or 0 for v in dn.values())
            rec[ph] = {"check_calls": c, "check_sec": sec, "full_calls": {k: round(v * scale) for k, v in c.items()},
                       "full_hours_per_base": round(sec * scale / 3600, 1)}
            out["total"]["gen_live" if ph == "gen" else "judge_live"] += rec[ph]["full_calls"].get(f"{ph}_live", 0) * len(ORDER)
            out["total"]["hours"] += rec[ph]["full_hours_per_base"] * len(ORDER)
        out["per_tag"][t["tag"]] = rec
    out["total"]["hours"] = round(out["total"]["hours"], 1)
    C.jdump(out, D.odir(True) / "estimate.json")
    f = C.jdump(out, C.OUT / "estimate_before_M.json")
    log(json.dumps(out["total"]))
    return 0 if C.publish([f], "v21r: call and time estimate for the full matrix, from the check run (DESIGN.md 8)") else 1
