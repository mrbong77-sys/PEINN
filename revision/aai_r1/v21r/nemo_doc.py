"""R2 (DESIGN.md 9): why the NeMo arms answer or refuse, from the driver's log of every NeMo call.

    python -m v21r nemo-doc [--check]

The driver (peaos_driver.seeds) logs each NeMo Guardrails call of the 'others' tag (self-check input, self-check output,
Colang dialog) with the model's raw reply. Per base this step reports: the input self-check verdicts parsed the way
nemoguardrails parses them (is_content_safe: the first two words; 'yes' or 'unsafe' blocks, 'no' or 'safe' allows, any
other reply blocks), the share of refusals each rail explains, the most common unparsed replies (first 40 characters;
no benchmark text), and the NeMo arm's fixed-refusal rows per bench in the judged CSVs. -> results/nemo/nemo_doc.json
"""
from __future__ import annotations

import collections
import re

from . import common as C
from . import data as D
from . import matrix as M

REFUSAL = "I'm sorry, I cannot assist with that request as it involves potentially harmful content."


def verdict(reply: str) -> str:
    """nemoguardrails.llm.output_parsers.is_content_safe on a reply: allow, block_yes or block_unparsed."""
    words = re.sub(r"\W+", " ", (reply or "").lower().strip()).split(" ")[:2]
    for w, v in (("safe", "allow"), ("unsafe", "block_yes"), ("yes", "block_yes"), ("no", "allow")):
        if w in words:
            return v
    return "block_unparsed"


def calls(check: bool, base: str) -> tuple[str, list[dict]]:
    """The gen-phase log, or the judge-phase log (the same calls replayed) when gen ran before the log existed."""
    d = M.mdir(check, base)
    for phase in ("gen", "judge"):
        rows = C.jsonl(d / f"nemo_calls_others_{phase}.jsonl") if (d / f"nemo_calls_others_{phase}.jsonl").exists() else []
        if rows:
            return phase, rows
    return "", []


def base_doc(check: bool, base: str) -> dict:
    phase, rows = calls(check, base)
    out = {"log_phase": phase, "calls": dict(collections.Counter(r["task"] for r in rows))}
    pf = D.wdir(check) / "nemo_probe" / base / "nemo_probe.json"
    if pf.exists():                                                 # package versions and the probe replies
        pr = C.jload(pf)
        out["versions"] = pr.get("versions")
        out["probe_calls"] = [{k: c.get(k) for k in ("model", "max_tokens", "text", "error")} for c in pr.get("calls", [])]
    for task in ("self_check_input", "self_check_output"):
        rs = [r for r in rows if r["task"] == task]
        if not rs:
            continue
        v = collections.Counter(verdict(r["text"]) for r in rs)
        last = {}
        for r in rs:                                                # one verdict per checked text (the last call)
            last[r["subj_sha"]] = verdict(r["text"])
        un = collections.Counter((r["text"] or "").strip()[:40] for r in rs if verdict(r["text"]) == "block_unparsed")
        out[task] = {"calls": len(rs), "verdicts": dict(v), "errors": sum(1 for r in rs if r["error"]),
                     "empty": sum(1 for r in rs if not (r["text"] or "").strip()),
                     "texts": len(last), "texts_blocked": sum(1 for x in last.values() if x != "allow"),
                     "by_bench": {b: dict(collections.Counter(verdict(r["text"]) for r in rs if r["bench"] == b))
                                  for b in sorted({r["bench"] for r in rs})},
                     "unparsed_top": un.most_common(8)}
    dl = [r for r in rows if r["task"] == "dialog"]
    if dl:
        out["dialog"] = {"calls": len(dl), "ask_harmful": sum(1 for r in dl if "ask harmful" in (r["text"] or "")),
                         "refuse": sum(1 for r in dl if "refuse to respond" in (r["text"] or ""))}
    df = M.collect(check, base)
    arm = C.ARMS[base]["NeMo"]
    if len(df) and "arm_id" in df:
        x = df[(df.tag == "others") & (df.arm_id == arm)]
        txt = x.filter(regex="^response").astype(str).agg(" ".join, axis=1)
        out["rows"] = {b: {"rows": int((x.bench == b).sum()), "fixed_refusal": int(((x.bench == b) & txt.str.contains(REFUSAL, regex=False)).sum()),
                           "internal_error": int(((x.bench == b) & txt.str.lower().str.contains("internal error")).sum())}
                       for b in sorted(x.bench.unique())}
    return out


def config_hashes() -> dict:
    """sha256 of the NeMo config files the benches load (PEAOS checkout), to match the copy printed in the paper."""
    import hashlib
    d = C.peaos() / "pea_eval" / "nemo_config"
    return {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(d.glob("*")) if f.is_file()} if d.exists() else {}


def nemo_doc(check: bool = False, log=print) -> int:
    res = {b: base_doc(check, b) for b in M.bases(check)}
    res["config_sha256"] = config_hashes()
    for b, r in res.items():
        if b == "config_sha256":
            continue
        log(f"NeMo {b}: {r.get('calls')} input {r.get('self_check_input', {}).get('verdicts')}")
    o = D.odir(check) / "nemo"
    o.mkdir(parents=True, exist_ok=True)
    f = C.jdump(res, o / "nemo_doc.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r R2: NeMo rail verdicts per base (why the NeMo arms answer or refuse)") else 1
