"""Step dev-guard: Llama Guard 3's input verdict on the corpus test split, the reference the PEINN
variants are compared with before any evaluation benchmark is looked at (ORR and ASR at
least on par with Llama Guard).

The call is the one the LlamaGuard arms make for input moderation (pea_eval harmbench_eval.llamaguard_moderate): the
text as the only user message, temperature 0, unsafe when the reply starts with "unsafe". Verdicts are cached per
sha in the work dir (resumable); only counts are pushed (results/diag/dev_guard.json).
"""
from __future__ import annotations

import json

import numpy as np

from . import common as C
from . import data as D

GUARD = "llama-guard3:8b"


def verdict(text: str) -> tuple[bool, str]:
    body = {"model": GUARD, "messages": [{"role": "user", "content": text}], "stream": False, "keep_alive": "5m",
            "options": {"temperature": 0.0, "num_predict": 64, "seed": 42}}
    raw = (json.loads(C._ollama("/api/chat", body, timeout=300)).get("message") or {}).get("content", "").strip()
    low = raw.lower()
    return low.startswith("unsafe") or "\nunsafe" in low, raw[:40]


def cache_file(check: bool):
    return D.wdir(check) / "dev_guard.jsonl"


def load(check: bool) -> dict:
    f = cache_file(check)
    out = {}
    if f.exists():
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except json.JSONDecodeError:                                    # a line cut by a stop
                continue
            out[r["sha"]] = bool(r["unsafe"])
    return out


def dev_guard(check: bool = False, log=print) -> int:
    from . import gate_diag as G
    sp = D.load_split(check)
    groups = G.dev_groups(sp)
    rows = sp[sp.split == "test"]
    if check:
        rows = rows.head(40)
    C.pull_missing([GUARD], log=log)
    have = load(check)
    todo = rows[~rows.sha.isin(have)]
    log(f"dev-guard: {len(rows)} test rows, {len(todo)} to call")
    with open(cache_file(check), "a", encoding="utf-8") as fh:
        for i, (sha, text) in enumerate(zip(todo.sha, todo.text.astype(str))):
            u, raw = verdict(text)
            fh.write(json.dumps({"sha": sha, "unsafe": u, "raw": raw}, ensure_ascii=False) + "\n")
            fh.flush()
            have[sha] = u
            if i % 200 == 0:
                log(f"  {i}/{len(todo)}")
    res = {"guard": GUARD, "groups": {}}
    for g, d in groups.items():
        v = [have[s] for s in d.sha if s in have]
        if v:
            res["groups"][g] = {"rows": len(v), "refusal": round(float(np.mean(v)), 4)}
    log(json.dumps(res))
    f = C.jdump(res, D.odir(check) / "diag" / "dev_guard.json")
    C.unload([GUARD])
    if check:
        return 0
    return 0 if C.publish([f], "v21r G: Llama Guard input verdicts on the corpus test split (dev reference, counts)") else 1
