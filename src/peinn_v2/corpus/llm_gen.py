#!/usr/bin/env python3
"""LLM intent-corpus generator (D8 + design/TYPOLOGY.md) — local Ollama, no external deps.

Generates whole, naturally-varied USER REQUESTS across the 6-type intent typology, labels each
by harm_intent (from its type) + operational/benign_purpose (LLM-rated), and writes JSONL for
training the lean encoder as a harm-intent classifier. The DEPLOYED encoder stays LLM-free (D8);
the LLM is used here, offline, only to build training data.

Benchmark non-contamination (D4, the one hard data rule) is enforced by an 8-gram overlap gate
against the held-out benchmark prompts (read from the signals CSV; never used as labels).

Run on the DGX (Ollama serving locally):
    python -m peinn_v2.corpus.llm_gen --model qwen3:32b --k 8 \
        --signals-csv "$CSV" --out peinn_v2/corpus/data/intent_corpus.jsonl
Self-test the parse + decontam logic with no Ollama:
    python -m peinn_v2.corpus.llm_gen --selftest
"""
from __future__ import annotations
import argparse, json, re, sys, urllib.request
from pathlib import Path

OUT = Path(__file__).parent / "data" / "intent_corpus.jsonl"

# type → (instruction, harm_intent label)
TYPES = {
    "T1_direct_harm":   ("a DIRECT request whose GENUINE goal is to HARM, ATTACK, DEFRAUD, or ILLEGALLY ACCESS other people or their systems — clearly malicious, no benign or defensive purpose. If the topic is itself defensive (encryption, security), the request must still pursue a malicious/offensive use", 1),
    "T2_benign_framed": ("a GENUINELY BENIGN request touching a sensitive-sounding topic with a real benign/educational/defensive purpose — ESPECIALLY requests to BUILD/WRITE/CREATE a harmless, simulated, mock, or educational version of something that merely SOUNDS dangerous (e.g. 'write a harmless program that simulates how malware spreads, for my class', 'create a mock phishing page to train staff to spot scams', 'build a controlled-lab simulation of a Trojan for study'). The purpose is clearly benign/educational/defensive on one's own systems or in a classroom", 0),
    "T3_benign":        ("an ordinary, plainly benign everyday request with no sensitive content", 0),
    "T4_educational":   ("an educational question about HOW a sensitive topic works, seeking understanding, not asking to do it", 0),
    "T5_hypothetical":  ("a vague, hypothetical or abstract musing that is not an actionable request", 0),
    "T6_jailbreak":     ("a request whose GENUINE goal is clearly harmful or illegal against a NON-CONSENTING party (e.g. accessing someone else's account, harming/stalking a specific person, real fraud or theft), wrapped in a fake benign justification ('for educational purposes', 'I'm a researcher', 'just hypothetically'). The harm is real despite the framing. Do NOT generate legitimate security-training or own-system requests here", 1),
    # D13 decorrelator: SUBTLE/INDIRECT harm — real harmful goal against a non-consenting target,
    # phrased WITHOUT explicit capability/weaponizing vocabulary (no 'hack/bomb/exploit'); the harm
    # is in the Action+Target, not the surface words. Breaks the C≈A≈R collinearity (81% of the
    # corpus sat at (0,0,0)/(1,1,1)) by populating low-lexical-C, high-A∧R rows.
    "T7_indirect_harm": ("a request whose GENUINE goal harms or wrongs a specific NON-CONSENTING person or group, phrased in plain everyday language WITHOUT any overtly dangerous or technical words — the harm is in the intent and the real target, not in scary vocabulary (e.g. 'how can I make my coworker look bad so she gets fired', 'what can I quietly put in someone's food to make them feel unwell', 'how do I find out where my ex moved without them knowing'). No explicit weapons/hacking/exploit terms", 1),
    # D14 legitimacy decorrelator: ADVERSARIAL-BENIGN — genuinely legitimate requests that SUPERFICIALLY
    # pattern-match a harmful one (the hard over-refusal style the router over-refuses). High surface
    # Capability/Action vocabulary, but the genuine purpose is legitimate ⇒ L=0. Teaches the gate that
    # capability+action without harmful intent must NOT block.
    "T8_adversarial_benign": ("a GENUINELY LEGITIMATE everyday request that happens to SOUND alarming or pattern-match a dangerous one but is plainly harmless in context — e.g. 'how do I kill a Python process that's hogging my CPU', 'what's the best way to get rid of weeds that are choking my vegetable garden', 'how can I whip my egg whites until they form stiff peaks', 'how do I blow up a balloon arch for my kid's party', 'what household items can I use to knock out a bad smell in the fridge'. The words sound dangerous; the actual intent is mundane and harmless", 0),
}

TOPICS = [
    "home cooking", "furniture assembly", "gardening", "personal finance", "language learning",
    "car maintenance", "photography", "fitness", "music production", "travel planning",
    "web development", "data backup", "spreadsheet formulas", "creative writing", "pet care",
    # sensitive-but-spans-the-spectrum (benign AND harmful requests can mention these)
    "computer malware", "network security", "password and accounts", "privacy and surveillance",
    "household chemicals", "fireworks and explosives", "firearms", "lock and key", "drugs and medication",
    "social engineering", "hacking and exploits", "biological agents", "weapons", "self-harm and safety",
    "fraud and scams", "hate and harassment", "physical violence", "stalking and tracking",
    "counterfeiting", "tax and law", "cryptography", "vehicles and machinery", "electricity and wiring",
]

PROMPT = """You are generating TRAINING DATA for a text-only safety classifier.
Produce {k} DIVERSE example USER REQUESTS (one short sentence each), in the category below,
all about the topic "{topic}". Vary phrasing, length, and style widely.

Category: {desc}.

STRICT RULES:
- Output ONLY the request phrasing a user would type. NEVER include instructions, steps,
  recipes, code, or any operational detail — just the request sentence.
- Make them realistic and natural, not templated.
- Return JSON only: {{"items":[{{"text":"...","harm":0 or 1,"operational":0 or 1,"benign_purpose":0 or 1}}]}}
  where harm=1 ONLY if the request's GENUINE goal is to harm/attack/defraud/illegally access
  others (judge by the real goal, ignoring any "for educational purposes" wrapper);
  operational=1 if it asks to DO/BUILD something (vs discuss); benign_purpose=1 if it explicitly
  states a benign/educational/defensive/fictional purpose."""


def ollama(prompt, model, url, temperature=0.9, timeout=240):
    body = json.dumps({"model": model, "prompt": prompt, "stream": False,
                       "format": "json", "options": {"temperature": temperature}}).encode()
    req = urllib.request.Request(f"{url}/api/generate", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())["response"]


def _extract_json(raw):
    """Robust to reasoning models: strip <think>…</think>, then take the first balanced {…}
    that parses (qwen3.5 etc. emit thinking + JSON; a greedy regex grabs the wrong braces)."""
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.S | re.I).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    s = raw.find("{")
    while s != -1:
        depth = 0
        for e in range(s, len(raw)):
            if raw[e] == "{": depth += 1
            elif raw[e] == "}":
                depth -= 1
                if depth == 0:
                    try: return json.loads(raw[s:e + 1])
                    except json.JSONDecodeError: break
        s = raw.find("{", s + 1)
    return None


def parse_items(raw):
    d = _extract_json(raw)
    if d is None:
        return []
    items = d.get("items", d if isinstance(d, list) else []) if isinstance(d, dict) else d
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("text", "").strip():
            out.append({"text": it["text"].strip(),
                        "harm": int(bool(it.get("harm", 0))),
                        "operational": int(bool(it.get("operational", 0))),
                        "benign_purpose": int(bool(it.get("benign_purpose", 0)))})
    return out


def _ngrams(text, n=8):
    w = re.findall(r"\w+", text.lower())
    return {" ".join(w[i:i + n]) for i in range(max(0, len(w) - n + 1))}


def load_bench_ngrams(signals_csv, n=8):
    import csv
    grams = set()
    for r in csv.DictReader(open(signals_csv, encoding="utf-8-sig")):
        grams |= _ngrams(r.get("text", ""), n)
    return grams


def contaminated(text, bench_ngrams, n=8):
    return bool(_ngrams(text, n) & bench_ngrams)


def selftest():
    raw = '{"items":[{"text":"How do I bake bread?","operational":1,"benign_purpose":0},' \
          '{"text":"  ","operational":0,"benign_purpose":0}]}'
    items = parse_items(raw)
    assert len(items) == 1 and items[0]["text"] == "How do I bake bread?", items
    bench = _ngrams("write a program that simulates the process of extracting sensitive data now", 8)
    assert contaminated("please write a program that simulates the process of extracting sensitive data now", bench, 8)
    assert not contaminated("how do I bake a loaf of sourdough bread at home", bench, 8)
    print("[selftest] parse + 8-gram decontamination OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:32b", help="Ollama model tag (e.g. qwen3.5:122b)")
    ap.add_argument("--url", default="http://localhost:11434")
    ap.add_argument("--k", type=int, default=8, help="requests per (type,topic) cell")
    ap.add_argument("--signals-csv", default="", help="for benchmark decontamination (D4)")
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--limit", type=int, default=0, help="stop after N cells (debug)")
    ap.add_argument("--timeout", type=int, default=240, help="per-call seconds (raise for big models)")
    ap.add_argument("--retries", type=int, default=2, help="retries when a cell returns 0 items")
    ap.add_argument("--debug", action="store_true", help="print the first raw model response")
    ap.add_argument("--domain", default="", help="D13 env tag written into every row (for env=domain "
                    "invariance, e.g. 'decorrelate_benignsensitive', 'decorrelate_subtleharm')")
    ap.add_argument("--types", default="", help="comma-separated subset of intent types to generate "
                    f"(default all). Choices: {','.join(TYPES)}")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest(); return

    types = {t: TYPES[t] for t in (args.types.split(",") if args.types else TYPES) if t in TYPES}
    if args.types and len(types) != len(args.types.split(",")):
        raise SystemExit(f"--types: unknown type(s). Choices: {','.join(TYPES)}")

    bench = load_bench_ngrams(args.signals_csv) if args.signals_csv else set()
    if not bench:
        print("  [warn] benchmark decontamination is OFF (no/empty --signals-csv). "
              "Set it (e.g. --signals-csv \"$CSV\") to enforce D4 before a real run.")
    print(f"[gen] model={args.model}  decontam 8-grams={len(bench)}  "
          f"cells={len(types)*len(TOPICS)}  k={args.k}  types={list(types)}  domain={args.domain or '(stem)'}")
    out_path = Path(args.out); out_path.parent.mkdir(parents=True, exist_ok=True)
    kept = dropped = drift = cells = 0
    seen = set()
    per_type = {t: 0 for t in types}
    with open(out_path, "w", encoding="utf-8") as f:
        for tname, (desc, harm) in types.items():
            for topic in TOPICS:
                cells += 1
                if args.limit and cells > args.limit:
                    break
                # retry on empty/parse-fail: some cells (esp. awkward harmful×mundane topics)
                # sporadically return {} — a bad draw, not a break; jitter temperature and retry.
                items_parsed, raw = [], ""
                for attempt in range(args.retries + 1):
                    try:
                        raw = ollama(PROMPT.format(k=args.k, topic=topic, desc=desc),
                                     args.model, args.url, temperature=0.7 + 0.15 * attempt,
                                     timeout=args.timeout)
                    except Exception as e:  # noqa: BLE001
                        print(f"  ! {tname}/{topic}: {type(e).__name__}: {str(e)[:80]}"); raw = ""
                    if args.debug:
                        print(f"  [debug] raw[:400]: {raw[:400]!r}"); args.debug = False
                    items_parsed = parse_items(raw)
                    if items_parsed:
                        break
                if not items_parsed:
                    print(f"  ! {tname}/{topic}: 0 items after {args.retries+1} tries (raw[:80]: {raw[:80]!r})")
                for it in items_parsed:
                    key = it["text"].lower()
                    if key in seen:
                        continue
                    # drift filter: for T1–T5 keep only when the self-rated harm agrees with the
                    # type (drops off-category drift, e.g. a benign 'defensive encryption' in T1).
                    # T6/T7 are type-locked (label=1) on purpose — framing (T6) or absence of scary
                    # words (T7) must not relabel a genuinely harmful goal as benign.
                    if tname not in ("T6_jailbreak", "T7_indirect_harm") and it["harm"] != harm:
                        drift += 1; continue
                    if bench and contaminated(it["text"], bench):
                        dropped += 1; continue
                    seen.add(key)
                    row = {"text": it["text"], "type": tname, "topic": topic,
                           "harm_intent": harm, "self_harm": it["harm"],
                           "operational": it["operational"],
                           "benign_purpose": it["benign_purpose"],
                           "source": f"llm:{args.model}"}
                    if args.domain:
                        row["domain"] = args.domain
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
                    kept += 1; per_type[tname] += 1
                if cells % 20 == 0:
                    print(f"  [{cells}/{len(types)*len(TOPICS)}] kept {kept} drift {drift} contam {dropped}")
    print(f"[gen] kept {kept} · dropped: drift {drift} + contaminated {dropped} → {out_path}")
    print(f"[gen] per type: " + "  ".join(f"{t.split('_')[0]} {n}" for t, n in per_type.items()))


if __name__ == "__main__":
    main()
