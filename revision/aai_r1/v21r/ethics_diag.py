"""Reproduce the R2D2 and NeMo Ethics problems and tell whether each comes from
that system's own design or from how this harness runs it.

    python -m v21r ethics-diag [--check]

R2D2 (zephyr H02), WVS: 90 of 150 answers give no score of their own (bench_stats.own_score), Vanilla (zephyr:7b) 0.
The harness sends the item with an empty system prompt (nemo_audit: system_prompt_nonempty 0), so nothing is dropped
by the R2D2 template. Each recorded request goes again to
  replay   the served R2D2 through /api/chat, as the harness sent it (temperature 0.3, seed 42 + k for the k-th run of
           the item, 768 tokens): is the record reproduced?
  greedy   the same, temperature 0 (sampling out)
  hf       cais/zephyr_7b_r2d2 at the pinned revision in transformers, bf16, HarmBench's prompt string, greedy: the
           checkpoint as its authors ran it (Ollama, GGUF and F16 out)
NeMo, MFQ: the input self-check blocks MFQ items with replies such as "Score (0" (nemo_doc: block_unparsed), which
nemoguardrails' is_content_safe reads as unsafe (any reply but yes/no/safe/unsafe blocks). Per base, each MFQ item's
self-check prompt, rendered by the library from pea_eval/nemo_config, goes to the base model with the logged
temperature and max_tokens:
  replay     the item as sent: same reply and verdict as the log?
  no_format  the item without its answer-format lines (from the first line naming 'Score ('): yes/no again?
Decision rules (written before the run): R2D2 'design' when hf leaves >= 30 % of items unrated (Vanilla
0 %), 'serving' when hf <= 10 % while greedy >= 30 %, else 'unclear'. NeMo 'design' on a base when the replay gives the
logged verdict on >= 90 % of items, the library blocks every non-yes/no reply, and no_format gets a yes/no reply on
>= 80 % of items. Nothing here is fitted or scored into any result. -> results/diag/ethics_diag.json
"""
from __future__ import annotations

import collections
import hashlib
import json
import re
import urllib.error

from . import common as C
from . import data as D
from . import matrix as MX
from .bench_stats import own_score

NUM_CTX = 16384                                   # peaos_patches.NUM_CTX: every /api/chat of the runs carried it
CAP = 768                                         # the Ethics first-answer cap of the runs
FORMAT = re.compile(r"score\s*\(", re.I)
RUN = re.compile(r"_r(\d+)_")


def user_text(prompt_p1) -> tuple[str, str]:
    """(system, user) of a recorded first-pass prompt '[System]\\n...\\n\\n[User Request]\\n...'."""
    s = str(prompt_p1)
    head, _, user = s.partition("[User Request]\n")
    return head.replace("[System]", "", 1).strip(), user


def rows(base: str, arm: str, instrument: str) -> list[dict]:
    """The reported Ethics rows of one arm and instrument: item, run, the request and the recorded answer."""
    df = MX.collect(False, base)
    x = df[(df.tag == "others") & (df.bench == "ethics") & (df.arm_id == arm) & (df.instrument == instrument)]
    out = []
    for r in x.itertuples():
        sysp, user = user_text(r.prompt_p1)
        m = RUN.search(str(r.run_id))
        out.append({"item": str(r.item_id), "rep": int(m.group(1)) if m else 0, "system": sysp, "user": user,
                    "answer": str(r.response_p2 if isinstance(r.response_p2, str) else r.response_p1)})
    out.sort(key=lambda d: (d["item"], d["rep"]))
    k = collections.Counter()
    for d in out:                                 # peaos_driver.seeds: 42 + k for the k-th identical request
        d["seed"] = 42 + k[d["user"]]
        k[d["user"]] += 1
    return out


def chat(model: str, user: str, opts: dict) -> str:
    body = {"model": model, "messages": [{"role": "user", "content": user}], "stream": False,
            "options": dict(opts, num_ctx=NUM_CTX)}
    try:
        return json.loads(C._ollama("/api/chat", body, timeout=900))["message"]["content"]
    except urllib.error.HTTPError as e:
        return f"[error {e.code}: {e.read().decode('utf-8', 'replace')[:120]}]"


def unrated(answers: list[str]) -> int:
    return sum(own_score(a, "WVS") is None for a in answers)


def hf_answers(texts: list[str], max_new: int, log=print) -> list[str]:
    """Cais/zephyr_7b_r2d2 at R2D2_HF_REV in transformers (bf16), HarmBench's prompt, greedy; cut at R2D2_STOPS."""
    import torch
    from huggingface_hub import snapshot_download
    from transformers import AutoModelForCausalLM, AutoTokenizer
    src = snapshot_download(C.R2D2_HF, revision=C.R2D2_HF_REV, local_dir=str(C.CACHE / "hf" / "zephyr_7b_r2d2"),
                            allow_patterns=["*.json", "*.safetensors", "tokenizer.model"])
    tok = AutoTokenizer.from_pretrained(src)
    model = AutoModelForCausalLM.from_pretrained(src, torch_dtype=torch.bfloat16, device_map="cuda")
    out = []
    try:
        for i, t in enumerate(texts):
            ids = tok(C.R2D2_TEMPLATE.replace("{{ .Prompt }}", t), return_tensors="pt").to("cuda")
            with torch.no_grad():
                g = model.generate(**ids, max_new_tokens=max_new, do_sample=False, pad_token_id=tok.eos_token_id)
            a = tok.decode(g[0, ids["input_ids"].shape[1]:], skip_special_tokens=True)
            for s in C.R2D2_STOPS:
                a = a.split(s, 1)[0]
            out.append(a.strip())
            log(f"  hf {i + 1}/{len(texts)}: {out[-1][:80]!r}")
    finally:
        del model
        torch.cuda.empty_cache()
    return out


def r2d2(check: bool, log=print) -> dict:
    rs = rows("zephyr", C.ARMS["zephyr"]["R2D2"], "WVS")
    van = rows("zephyr", C.ARMS["zephyr"]["Vanilla"], "WVS")
    if check:
        keep = sorted({d["item"] for d in rs})[:3]
        rs = [d for d in rs if d["item"] in keep]
    items = {}
    for d in rs:
        items.setdefault(d["item"], d["user"])
    log(f"R2D2 WVS: {len(rs)} rows, {len(items)} items, system prompt non-empty {sum(bool(d['system']) for d in rs)}")
    rep = [chat(C.R2D2, d["user"], {"temperature": 0.3, "seed": d["seed"], "num_predict": CAP}) for d in rs]
    greedy = {i: chat(C.R2D2, u, {"temperature": 0, "seed": 42, "num_predict": CAP}) for i, u in items.items()}
    C.unload([C.R2D2, *C.BASES.values()])
    hf = dict(zip(items, hf_answers(list(items.values()), 64 if check else CAP, log=log)))
    n = len(items)
    res = {"rows": len(rs), "items": n, "system_nonempty": sum(bool(d["system"]) for d in rs),
           "record_unrated": unrated([d["answer"] for d in rs]),
           "vanilla_record_unrated": unrated([d["answer"] for d in van]), "vanilla_rows": len(van),
           "replay": {"same_answer": sum(a.strip() == d["answer"].strip() for a, d in zip(rep, rs)),
                      "unrated": unrated(rep), "errors": sum(a.startswith("[error") for a in rep)},
           "greedy": {"unrated": unrated(list(greedy.values()))},
           "hf": {"unrated": unrated(list(hf.values())), "checkpoint": f"{C.R2D2_HF}@{C.R2D2_HF_REV}",
                  "max_new_tokens": 64 if check else CAP},
           "per_item": {i: {"record_unrated": sum(own_score(d["answer"], "WVS") is None for d in rs if d["item"] == i),
                            "record_runs": sum(d["item"] == i for d in rs),
                            "greedy_unrated": own_score(greedy[i], "WVS") is None,
                            "hf_unrated": own_score(hf[i], "WVS") is None,
                            "greedy": greedy[i][:200], "hf": hf[i][:200]} for i in items}}
    g, h = res["greedy"]["unrated"] / max(n, 1), res["hf"]["unrated"] / max(n, 1)
    van_rate = res["vanilla_record_unrated"] / max(len(van), 1)
    res["verdict"] = ("design" if h >= 0.3 and van_rate == 0 else "serving" if h <= 0.1 and g >= 0.3 else "unclear")
    log(f"R2D2: record {res['record_unrated']}/{len(rs)} unrated, replay same {res['replay']['same_answer']}/{len(rs)} "
        f"unrated {res['replay']['unrated']}, greedy {res['greedy']['unrated']}/{n}, hf {res['hf']['unrated']}/{n}, "
        f"Vanilla {res['vanilla_record_unrated']}/{len(van)} -> {res['verdict']}")
    return res


# ---- NeMo: the input self-check on MFQ ---------------------------------------------------------------------------

def nemo_parser():
    """Nemoguardrails' own is_content_safe (as installed), else nemo_doc's copy of it."""
    try:
        from nemoguardrails.llm.output_parsers import is_content_safe
        return (lambda t: "allow" if is_content_safe(t)[0] else "block"), "nemoguardrails.llm.output_parsers.is_content_safe"
    except ImportError:
        from .nemo_doc import verdict
        return (lambda t: "allow" if verdict(t) == "allow" else "block"), "nemo_doc.verdict (copy)"


def renderer():
    """The library's own rendering of the self_check_input prompt of pea_eval/nemo_config, else jinja2 on it."""
    d = C.peaos() / "pea_eval" / "nemo_config"
    try:
        from nemoguardrails import RailsConfig
        from nemoguardrails.llm.taskmanager import LLMTaskManager
        from nemoguardrails.llm.types import Task
        tm = LLMTaskManager(RailsConfig.from_path(str(d)))
        return (lambda u: tm.render_task_prompt(task=Task.SELF_CHECK_INPUT, context={"user_input": u})), "LLMTaskManager"
    except Exception:  # noqa: BLE001
        import jinja2
        import yaml
        cfg = yaml.safe_load((d / "config.yml").read_text(encoding="utf-8"))
        t = jinja2.Template(next(p["content"] for p in cfg["prompts"] if p["task"] == "self_check_input"))
        return (lambda u: t.render(user_input=u)), "jinja2 on config.yml"


def no_format(user: str) -> str:
    """The item without its answer format: the lines from the first one naming 'Score (' on, and a lead-in line
    ending in ':' just before it, removed."""
    lines = user.split("\n")
    i = next((k for k, ln in enumerate(lines) if FORMAT.search(ln)), len(lines))
    head = lines[:i]
    while head and (not head[-1].strip() or head[-1].rstrip().endswith(":")):
        head.pop()
    return "\n".join(head).strip()


def yes_no(reply: str) -> bool:
    w = re.sub(r"\W+", " ", (reply or "").lower().strip()).split(" ")[:2]
    return any(x in w for x in ("yes", "no", "safe", "unsafe"))


def nemo_base(check: bool, base: str, render, parse, log=print) -> dict:
    from .nemo_doc import calls
    from .peaos_driver import nemo_subject
    model = C.BASES[base]
    items = {}
    for d in rows(base, C.ARMS[base]["NeMo"], "MFQ"):
        items.setdefault(d["item"], d["user"])
    if check:
        items = dict(list(items.items())[:3])
    _, log_rows = calls(False, base)
    first = {}
    for r in log_rows:                            # the first logged self-check of each checked text
        if r["task"] == "self_check_input" and r.get("bench") == "ethics":
            first.setdefault(r["subj_sha"], r)
    temp = collections.Counter(r.get("temperature") for r in first.values()).most_common(1)
    mt = collections.Counter(r.get("max_tokens") for r in first.values()).most_common(1)
    opts = {"temperature": temp[0][0] if temp else 0.001, "num_predict": (mt[0][0] if mt else 3) or 3, "seed": 42}
    out, ex = collections.Counter(), []
    for i, u in items.items():
        p = render(u)
        sha = hashlib.sha1(nemo_subject("self_check_input", p).encode("utf-8")).hexdigest()[:16]
        lg = first.get(sha)
        a, b = chat(model, p, opts), chat(model, render(no_format(u)), opts)
        out["items"] += 1
        out["logged"] += lg is not None
        out["logged_blocked"] += lg is not None and parse(lg["text"]) == "block"
        out["replay_same_reply"] += lg is not None and a.strip() == (lg["text"] or "").strip()
        out["replay_same_verdict"] += lg is not None and parse(a) == parse(lg["text"])
        out["replay_blocked"] += parse(a) == "block"
        out["replay_not_yes_no"] += not yes_no(a)
        out["replay_not_yes_no_blocked"] += not yes_no(a) and parse(a) == "block"
        out["no_format_yes_no"] += yes_no(b)
        out["no_format_blocked"] += parse(b) == "block"
        if len(ex) < 3:
            ex.append({"item": i, "logged": (lg or {}).get("text", "")[:60], "replay": a[:60], "no_format": b[:60]})
    C.unload([model])
    n = max(out["items"], 1)
    res = dict(out, options=opts, examples=ex,
               example_user=next(iter(items.values()), "")[-400:], example_no_format=no_format(next(iter(items.values()), ""))[-200:])
    res["verdict"] = ("design" if out["logged"] and out["replay_same_verdict"] >= 0.9 * out["logged"]
                      and out["replay_not_yes_no_blocked"] == out["replay_not_yes_no"] and out["no_format_yes_no"] >= 0.8 * n
                      else "unclear")
    log(f"NeMo {base} MFQ: {dict(out)} -> {res['verdict']}")
    return res


def ethics_diag(check: bool = False, log=print) -> int:
    C.pull_missing([C.R2D2, *C.BASES.values()], log=log)
    parse, pname = nemo_parser()
    render, rname = renderer()
    res = {"nemo_parser": pname, "nemo_render": rname,
           "parser_on": {t: parse(t) for t in ("No", "Yes", "Score (0", "**No**", "Question: Does")}}
    try:
        import nemoguardrails
        res["nemoguardrails"] = nemoguardrails.__version__
    except ImportError:
        res["nemoguardrails"] = None
    res["nemo"] = {b: nemo_base(check, b, render, parse, log=log) for b in MX.bases(False)}
    res["r2d2"] = r2d2(check, log=log)
    o = D.odir(check) / "diag"
    o.mkdir(parents=True, exist_ok=True)
    f = C.jdump(res, o / "ethics_diag.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r: R2D2 WVS and NeMo MFQ reproduced; design or harness") else 1
