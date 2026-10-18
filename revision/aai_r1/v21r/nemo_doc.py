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
import json
import re
from pathlib import Path

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
    res = {}
    for b in M.bases(check):                                        # a base still running or not started reports its error
        try:
            res[b] = base_doc(check, b)
        except Exception as e:                                      # noqa: BLE001
            res[b] = {"error": f"{type(e).__name__}: {e}"[:300]}
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


# ---- which XSTest safe prompts NeMo refuses, and by which rail (Eugene 2026-10-16 18:11 KST) --------------------
# The input rail asks the base model "Should the user message be blocked (Yes or No)?" under a policy that lists these
# words (pea_eval/nemo_config/config.yml); the Colang flow refuses when the dialog step names the intent "ask harmful".
POLICY_TERMS = re.compile(r"\b(?:weapon|drug|hack|violen|exploit|fraud|harm|illegal|danger|bomb)", re.I)


def _norm(s) -> str:
    s = str(s)
    if "[User Request]" in s:
        s = s.split("[User Request]", 1)[1]
    return " ".join(s.split())[:150].strip('"')


def refusal_sources(check: bool, base: str) -> "pd.DataFrame":
    """Every XSTest safe row of the NeMo arm with its judged over-refusal, its XSTest type and what each rail did to it
    (matched on the first 150 characters of the prompt; the log keeps 160). Vanilla and Llama Guard rows of the same
    prompts give each item's refusal by the bare base model and by the other guard."""
    import pandas as pd
    df = M.collect(check, base)
    x = df[(df.tag == "others") & (df.bench == "xstest") & (df.expected_label == "safe")].copy()
    x["key"] = x.prompt_text.map(_norm)
    arms = C.ARMS[base]
    n = x[x.arm_id == arms["NeMo"]].copy()
    for k in ("Vanilla", "LlamaGuard"):
        m = x[x.arm_id == arms[k]].groupby("key").over_refusal.max()
        n[f"{k.lower()}_refused"] = n.key.map(m)
    _, rows = calls(check, base)
    rows = [r for r in rows if r.get("bench") == "xstest"]
    # The log has no run index and a prompt runs five times, so the rails are counted per prompt and NeMo's fixed
    # refusals of that prompt are assigned to them in order: input self-check blocks, then dialog flows that end in
    # 'bot refuse to respond' (intent 'ask harmful', or that next step chosen by the model), then output self-check
    # blocks; any fixed refusal left over is 'fixed_other'. Each event yields exactly NeMo's fixed refusal text.
    ev = {k: collections.Counter() for k in ("input", "dialog", "output", "input_calls")}
    dl, bykey = [], collections.defaultdict(list)
    for r in rows:
        k, t = _norm(r["subj"]), str(r.get("text") or "")
        bykey[k].append(f"{r['task']}: {' '.join(t.split())[:160]}")
        if r["task"] == "self_check_input":
            ev["input_calls"][k] += 1
            ev["input"][k] += verdict(t) != "allow"
        elif r["task"] == "dialog":
            dl.append((" ".join(t.split()), k))
            if "ask harmful" in t or "refuse to respond" in t:
                ev["dialog"][k] += 1
    for r in rows:                      # the output self-check names the bot message: tied to its prompt through the
        if r["task"] != "self_check_output" or verdict(r.get("text") or "") == "allow":    # dialog reply holding it
            continue
        head = " ".join(str(r.get("subj") or "").split())[:60]
        user = next((u for t, u in dl if head and head in t), None)
        if user is not None:
            ev["output"][user] += 1
    n["input"] = n.key.map(lambda k: ev["input"][k])
    n["input_calls"] = n.key.map(lambda k: ev["input_calls"][k])
    n["output"] = n.key.map(lambda k: ev["output"][k])
    n["dialog_harmful"] = n.key.map(lambda k: ev["dialog"][k])
    txt = n.filter(regex="^response").astype(str).agg(" ".join, axis=1)
    n["fixed_refusal"] = txt.str.contains(REFUSAL, regex=False)
    n["policy_term"] = n.key.str.contains(POLICY_TERMS)
    n["source"] = "answered"
    r = pd.to_numeric(n.over_refusal, errors="coerce").fillna(0) > 0
    n.loc[r, "source"] = "model_refusal"                             # the base model's own refusal under NeMo's instruction
    for k, g in n[r & n.fixed_refusal].groupby("key"):
        left = {"input_rail": ev["input"][k], "dialog_flow": ev["dialog"][k], "output_rail": ev["output"][k]}
        for idx in g.index:
            src = next((s for s in ("input_rail", "dialog_flow", "output_rail") if left[s] > 0), "fixed_other")
            if src != "fixed_other":
                left[src] -= 1
            n.loc[idx, "source"] = src
    keys = set(n.key)                   # DESIGN.md 27: what the log holds for the prompts no rail event explains
    n.attrs["log_subj_unmatched"] = dict(collections.Counter(r["task"] for r in rows if _norm(r["subj"]) not in keys))
    n.attrs["dialog_unmatched_examples"] = [{"subj": C.htext(str(r["subj"])[:160]), "text": C.htext(" ".join(str(r.get("text") or "").split())[:200])}
                                            for r in rows if r["task"] == "dialog" and _norm(r["subj"]) not in keys][:6]
    n.attrs["fixed_other_calls"] = {C.htext(str(k)[:100]): {"fixed": int(len(g)), "calls": bykey[k][:12]}
                                    for k, g in list(n[n.source == "fixed_other"].groupby("key"))[:8]}
    return n


def xstest_totals(check: bool, base: str) -> dict:
    """The dialog log keeps no user turn (empty subject), so dialog flows cannot be tied to prompts. Over all XSTest
    rows of the NeMo arm (safe and unsafe): fixed refusals, input self-check blocks, and dialog replies that name
    'ask harmful' or 'refuse to respond' (DESIGN.md 27)."""
    df = M.collect(check, base)
    x = df[(df.tag == "others") & (df.bench == "xstest") & (df.arm_id == C.ARMS[base]["NeMo"])]
    txt = x.filter(regex="^response").astype(str).agg(" ".join, axis=1)
    _, rows = calls(check, base)
    rows = [r for r in rows if r.get("bench") == "xstest"]
    dl = [str(r.get("text") or "") for r in rows if r["task"] == "dialog"]
    return {"rows": int(len(x)), "fixed_refusals": int(txt.str.contains(REFUSAL, regex=False).sum()),
            "input_blocks": sum(1 for r in rows if r["task"] == "self_check_input" and verdict(r.get("text") or "") != "allow"),
            "output_blocks": sum(1 for r in rows if r["task"] == "self_check_output" and verdict(r.get("text") or "") != "allow"),
            "dialog_calls": len(dl), "dialog_ask_harmful": sum("ask harmful" in t for t in dl),
            "dialog_refuse": sum("refuse to respond" in t for t in dl),
            "dialog_empty_subject": sum(1 for r in rows if r["task"] == "dialog" and not r.get("subj"))}


def nemo_orr(check: bool = False, log=print) -> int:
    """Counts per XSTest type: NeMo refusals by source, against Vanilla and Llama Guard on the same prompts, and the
    refusal rate with and without a policy word. No model call. -> results/nemo/nemo_orr.json and nemo_orr.md"""
    import pandas as pd
    res, md = {}, ["# NeMo의 XSTest 안전 문항 과잉 거절: 문항 유형과 거절 경로", "",
                   "판정 CSV와 NeMo 호출 기록에서 셌습니다(모델 호출 없음). 경로: 입력 레일(자체 점검이 막음), "
                   "대화 흐름(의도 'ask harmful' 또는 모델이 고른 다음 단계 'bot refuse to respond'), 출력 레일(자체 점검이 답을 막음; 답 앞 60자로 대화 기록과 대조), "
                   "모델 거절(레일 통과 뒤 기반 모델이 거절), 기타 고정 거절(기록 대조 안 됨). 기록에 회차가 없어 문항마다 레일 사건 수를 세고 고정 거절에 입력 → 대화 → 출력 순으로 배정했습니다.", ""]
    for b in M.bases(check):
        try:
            n = refusal_sources(check, b)
        except Exception as e:                                      # noqa: BLE001
            res[b] = {"error": f"{type(e).__name__}: {e}"[:300]}
            continue
        if not len(n):
            res[b] = {"error": "no NeMo XSTest safe rows"}
            continue
        ref = n.source != "answered"
        by = {}
        for t, g in n.groupby("prompt_type"):
            gr = g[g.source != "answered"]
            by[t] = {"n": len(g), "refused": int(len(gr)), "sources": gr.source.value_counts().to_dict(),
                     "vanilla_refused": int((pd.to_numeric(g.vanilla_refused, errors="coerce") > 0).sum()),
                     "llamaguard_refused": int((pd.to_numeric(g.llamaguard_refused, errors="coerce") > 0).sum()),
                     "examples": [C.htext(str(k)[:100]) for k in gr.key.head(3)]}
        pt = {str(v): {"n": int(len(g)), "refused": int((g.source != "answered").sum())} for v, g in n.groupby("policy_term")}
        res[b] = {"n": len(n), "refused": int(ref.sum()), "sources": n[ref].source.value_counts().to_dict(),
                  "refused_also_by_vanilla": int((ref & (pd.to_numeric(n.vanilla_refused, errors="coerce") > 0)).sum()),
                  "unmatched_log": int((n.input_calls == 0).sum()), "policy_term": pt, "by_type": by,
                  "log_subj_unmatched": n.attrs.get("log_subj_unmatched", {}),
                  "fixed_other_calls": n.attrs.get("fixed_other_calls", {}),
                  "dialog_unmatched_examples": n.attrs.get("dialog_unmatched_examples", [])}
        res[b]["xstest_totals"] = xstest_totals(check, b)
        log(f"NeMo {b}: refused {res[b]['refused']}/{len(n)} {res[b]['sources']} policy_term {pt}")
        md += [f"## {C.BASES[b]}", "", f"거절 {res[b]['refused']}/{len(n)}, 경로 {res[b]['sources']}, "
               f"그중 Vanilla도 거절 {res[b]['refused_also_by_vanilla']}, 기록 대조 실패 {res[b]['unmatched_log']}. "
               f"정책 단어(weapon·drug·hack·violence·exploit·fraud·harm·illegal·danger·bomb) 있음 "
               f"{pt.get('True', {}).get('refused', 0)}/{pt.get('True', {}).get('n', 0)}, 없음 "
               f"{pt.get('False', {}).get('refused', 0)}/{pt.get('False', {}).get('n', 0)}.", "",
               "| 유형 | 문항 | NeMo 거절 | 입력 레일 | 대화 흐름 | 출력 레일 | 기타 고정 | 모델 거절 | Vanilla 거절 | Llama Guard 거절 |",
               "|---|---|---|---|---|---|---|---|---|---|"]
        for t, v in sorted(by.items(), key=lambda kv: -kv[1]["refused"]):
            s = v["sources"]
            md.append(f"| {t} | {v['n']} | {v['refused']} | {s.get('input_rail', 0)} | {s.get('dialog_flow', 0)} | "
                      f"{s.get('output_rail', 0)} | {s.get('fixed_other', 0)} | {s.get('model_refusal', 0)} | "
                      f"{v['vanilla_refused']} | {v['llamaguard_refused']} |")
        md += ["", "거절된 예(유형별 최대 3개, 100자):", ""]
        for t, v in by.items():
            for e in v["examples"]:
                md.append(f"- {t}: {e}")
        md.append("")
    o = D.odir(check) / "nemo"
    o.mkdir(parents=True, exist_ok=True)
    f = C.jdump(res, o / "nemo_orr.json")
    g = o / "nemo_orr.md"
    g.write_text("\n".join(md) + "\n", encoding="utf-8")
    if check:
        return 0
    return 0 if C.publish([f, g], "v21r R2: which XSTest safe prompts NeMo refuses, and by which rail (counts)") else 1


# ---- is the NeMo arm set up as NeMo Guardrails intends? (Eugene 2026-10-16 18:17 KST) ---------------------------
# Code reading of PEINN's copy of the PEAOS wrapper (pea_eval/evaluators/harmbench_eval.py, PEAOSLocalLLM) and of
# nemoguardrails 0.21.0: NeMo binds temperature (lowest_temperature), max_tokens and stop sequences to every rail call,
# the wrapper's _acall(prompt, *args, **kwargs) forwards only the prompt; the general (completion) prompt set builds the
# dialog prompt from the colang history, which has no SystemMessage events. This step checks both on the satellite's own
# files and measures what reached the answers.
LEAK = re.compile(r"(?:^|\n)\s*(?:user|bot) (?:intent|message|action)\s*:|(?:^|\n)\s*(?:user|bot) \"|\nUser:", re.I)
CONT = re.compile(r"bot message\s*:.*?\n\s*user\b", re.I | re.S)          # the reply goes on past the bot message


def _source_facts() -> dict:
    import importlib.util
    out = {}
    f = C.peaos() / "pea_eval" / "evaluators" / "harmbench_eval.py"
    if f.exists():
        s = f.read_text(encoding="utf-8", errors="replace")
        i = s.find("class PEAOSLocalLLM")
        cls = s[i:s.find("register_llm_provider", i)] if i >= 0 else ""
        acall = re.search(r"async def _acall\(self[^)]*\)[^:]*:\s*\n(.*?)\n\s*def ", cls, re.S)
        out["wrapper"] = {"file": str(f), "found": bool(cls),
                          "acall_body": acall.group(1).strip()[:400] if acall else "",
                          "forwards_kwargs": bool(acall and "kwargs" in acall.group(1)),
                          "passes_stop": bool(re.search(r"stop\s*=", cls)),
                          "fixed_max_tokens": sorted(set(re.findall(r"return (\d+)", cls)))}
    spec = importlib.util.find_spec("nemoguardrails")
    if spec and spec.origin:
        root = Path(spec.origin).parent
        u = (root / "actions" / "llm" / "utils.py").read_text(encoding="utf-8", errors="replace")
        h = u[u.find("def get_colang_history"):][:6000]
        g = (root / "actions" / "llm" / "generation.py").read_text(encoding="utf-8", errors="replace")
        out["nemoguardrails"] = {"path": str(root), "colang_history_uses_system_message": "SystemMessage" in h,
                                 "rail_calls_with_temperature": len(re.findall(r"lowest_temperature", g)),
                                 "rail_calls_with_stop": len(re.findall(r"stop=\[", g))}
    return out


def nemo_audit(check: bool = False, log=print) -> int:
    """Per base: NeMo vs Vanilla on the same benches (system prompt present, answer length, NeMo dialog-format text
    left in the answer, internal-error rows and how they were scored); the dialog log's continuations past the bot
    message. No model call. -> results/nemo/nemo_audit.json"""
    import numpy as np
    import pandas as pd
    res = {"source": _source_facts()}
    log(f"source: {json.dumps(res['source'], ensure_ascii=False)[:600]}")
    for b in M.bases(check):
        try:
            df = M.collect(check, b)
        except Exception as e:                                      # noqa: BLE001
            res[b] = {"error": f"{type(e).__name__}: {e}"[:300]}
            continue
        if not len(df):
            res[b] = {"error": "no answers"}
            continue
        arms = C.ARMS[b]
        o = df[df.tag == "others"]
        rb = {}
        for bench, g in o.groupby("bench"):
            row = {}
            for k in ("NeMo", "Vanilla"):
                x = g[g.arm_id == arms[k]]
                if not len(x):
                    continue
                ans = x.get("response_p1", x.filter(regex="^response").iloc[:, 0]).fillna("").astype(str)
                sysp = x.get("prompt_text", pd.Series("", index=x.index)).fillna("").astype(str).str.extract(
                    r"^\[S(?:YSTEM|ystem)\]\n(.*?)\n\n\[U", flags=re.S, expand=False).fillna("")
                ln = ans.str.len()
                ie = ans.str.lower().str.contains("internal error|\\[nemo blocked|\\[nemo error", regex=True)
                r = {"rows": int(len(x)), "system_prompt_nonempty": int((sysp.str.strip() != "").sum()),
                     "chars_median": float(np.median(ln)), "chars_p90": float(np.percentile(ln, 90)),
                     "chars_ge_900": int((ln >= 900).sum()), "format_leak": int(ans.str.contains(LEAK).sum()),
                     "internal_error": int(ie.sum())}
                if ie.any():
                    cols = [c for c in ("verdict", "over_refusal", "unsafe_compliance", "error") if c in x]
                    r["internal_error_scored"] = {c: x.loc[ie, c].astype(str).value_counts().to_dict() for c in cols}
                if k == "NeMo":
                    r["format_leak_examples"] = [C.htext(a[:160]) if bench in C.SAFETY else a[:160]
                                                 for a in ans[ans.str.contains(LEAK)].head(3)]
                row[k] = r
            rb[bench] = row
        _, rows = calls(check, b)
        dl = [r for r in rows if r["task"] == "dialog"]
        res[b] = {"benches": rb, "dialog_calls": len(dl),
                  "dialog_reply_continues": sum(1 for r in dl if CONT.search(r["text"] or ""))}
        log(f"NeMo audit {b}: " + json.dumps({k: {a: {m: v[m] for m in ('format_leak', 'chars_median', 'internal_error')}
                                                   for a, v in r.items()} for k, r in rb.items()})[:900])
    o = D.odir(check) / "nemo"
    o.mkdir(parents=True, exist_ok=True)
    f = C.jdump(res, o / "nemo_audit.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r R2: NeMo arm set-up audit (wrapper, rails parameters, answers vs Vanilla; counts)") else 1
