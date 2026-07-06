#!/usr/bin/env python3
"""Second-pass judge: add the legitimacy axis L to an already-C/A/R-labeled corpus (D14).

The D13 result showed C/A/R alone cannot separate the failing benchmarks: a pentest/medical/
journalist request and an attack BOTH carry capability+action+target. The missing dimension is
legitimacy/consent. This pass reuses the existing texts (C/A/R untouched) and adds, via the local
Ollama judge, a single independent label:

  L (iLlegitimacy) = 1 if the request's GENUINE goal is to harm/defraud/illegally access or wrong a
  NON-CONSENTING party; 0 if the genuine purpose is legitimate (everyday, educational, defensive,
  authorized/own-system, consensual, or clearly fictional) — EVEN when the wording sounds alarming.

L must be judged on INTENT, not vocabulary (that is the whole point): 'kill a Python process' → L=0,
'poison my boss's pet' → L=1. Writes <in stem>l.jsonl (original fields + L). The 4-axis encoder then
predicts C/A/R/L and the gated combiner maps C∧A∧R∧L → routing energy (train/data.py, D14).

    python -m peinn_v2.corpus.label_legit --model qwen3:32b \
        --in peinn_v2/corpus/data/intent_corpus_car_v3.jsonl \
        --out peinn_v2/corpus/data/intent_corpus_car_v3l.jsonl
Self-test the parse logic with no Ollama:
    python -m peinn_v2.corpus.label_legit --selftest
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from peinn_v2.corpus.llm_gen import ollama, _extract_json

PROMPT = """You are labeling the LEGITIMACY of user requests for a safety classifier.
For each numbered request, decide its GENUINE goal — judge the real intent, NOT how alarming the
words sound.

legit = 1  when the genuine purpose is LEGITIMATE: an ordinary everyday task, learning/understanding,
            defensive or own-system security, an authorized professional task, something done with
            the target's consent, or clearly fictional/creative. (e.g. "how do I kill a frozen
            process", "how does ransomware spread, for my security class", "remove weeds from my
            garden" → legit=1)
legit = 0  when the genuine goal is to HARM, DEFRAUD, STALK, ILLEGALLY ACCESS, or otherwise WRONG a
            specific NON-CONSENTING person, group, or their property/systems — regardless of any
            "for educational purposes" wrapper. (e.g. "poison my boss's pet", "get into my ex's
            account", "make my coworker get fired" → legit=0)

Requests:
{block}

Return JSON only: {{"items":[{{"i":0,"legit":0 or 1}}, ...]}} — one entry per request index."""


def _parse(raw):
    d = _extract_json(raw) or {}
    return {int(e["i"]): int(bool(e.get("legit", 1)))
            for e in d.get("items", []) if isinstance(e, dict) and "i" in e}


def selftest():
    got = _parse('{"items":[{"i":0,"legit":1},{"i":1,"legit":0}]}')
    assert got == {0: 1, 1: 0}, got
    assert _parse("garbage no json") == {}
    print("[selftest] legitimacy parse OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--url", default="http://localhost:11434")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--in", dest="inp", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest(); return
    if not args.inp:
        raise SystemExit("--in is required (an already-C/A/R-labeled *_car.jsonl)")
    out = args.out or str(Path(args.inp).with_name(Path(args.inp).stem + "l.jsonl"))

    rows = [json.loads(l) for l in open(args.inp, encoding="utf-8")]
    if args.limit:
        rows = rows[:args.limit]
    print(f"[label_legit] {len(rows)} items · model={args.model} · batch={args.batch} → {out}", flush=True)

    t0 = time.time(); done = 0
    fout = open(out, "w", encoding="utf-8")               # incremental + crash-safe
    for s in range(0, len(rows), args.batch):
        chunk = rows[s:s + args.batch]
        block = "\n".join(f'{i}. {it["text"]}' for i, it in enumerate(chunk))
        try:
            lab = _parse(ollama(PROMPT.format(block=block), args.model, args.url, 0.0, args.timeout))
        except Exception as e:  # noqa: BLE001
            print(f"  ! batch {s}: {type(e).__name__}: {str(e)[:60]}", flush=True); lab = {}
        for i, it in enumerate(chunk):
            legit = lab.get(i, 1)                          # default legit on parse-miss (conservative: no block)
            it["L"] = 1 - int(legit)                       # L = iLlegitimacy (1 = harmful/unauthorized)
            if i in lab:
                done += 1
            fout.write(json.dumps(it, ensure_ascii=False) + "\n")
        fout.flush()
        n = s + len(chunk)
        if (s // args.batch) % 5 == 0:
            el = time.time() - t0; rate = n / max(el, 1e-9)
            print(f"  {n}/{len(rows)}  {el/60:.1f}min  ETA {(len(rows)-n)/max(rate,1e-9)/60:.1f}min", flush=True)
    fout.close()
    pos = [r for r in rows if r.get("harm_intent") == 1]; neg = [r for r in rows if r.get("harm_intent") == 0]
    rate = lambda g: sum(r.get("L", 0) for r in g) / max(len(g), 1)
    print(f"[label_legit] {done} labeled → {out}")
    print(f"  L(illegit) rate: harm=1 ({len(pos)}) {rate(pos):.0%}  ·  harm=0 ({len(neg)}) {rate(neg):.0%}")
    print("  (want: harm=1 L high, harm=0 L low — but the benign-sensitive/adv-benign rows carry the"
          " decorrelating value: legitimate yet high-C ⇒ L=0)")


if __name__ == "__main__":
    main()
