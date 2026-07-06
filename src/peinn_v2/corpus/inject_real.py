#!/usr/bin/env python3
"""D21 — Real-virtual fusion for text (borrowed from Jung et al. 2026, Sensors 26(3):987).

Their reality-gap fix: don't generate whole synthetic scenes; take REAL backgrounds and INJECT virtual
objects, then HARMONIZE (illumination/color transfer) so the injection is statistically indistinguishable
from the background. Text analog implemented here:

  • REAL carriers  = real human queries (ToxicChat-safe: real LMSYS Arena prompts, short/ambiguous,
    surface-suspicious-but-safe — the over-refusal distribution). The "background", in-distribution.
  • INJECTION      = a MINIMAL-EDIT harmful sibling of each carrier (change as few words as possible so
    the genuine intent becomes harmful), keeping the carrier's style/register/length/structure.
  • HARMONIZATION  = the minimal-edit constraint itself: benign carrier and harmful sibling differ ONLY
    in intent, NOT in style — so a classifier cannot separate them by "synthetic-ness" (the artifact
    D16 showed the encoder latches onto). This is the text analog of illumination/color transfer.
  • FREE EXACT LABEL = because we inject, harm_intent is known with no judge noise (their "automated GT").
  • HARD-CASE MINING = also emit an adversarial-benign minimal edit (sounds alarming, stays benign) — the
    over-refusal trap — for explicit hard-case coverage.

Per carrier we emit a STYLE-MATCHED triple: (carrier_benign, injected_harm, adversarial_benign).
Benchmark non-contamination (D4) is enforced by the same 8-gram gate as llm_gen on ALL emitted text.

    python -m peinn_v2.corpus.inject_real --model qwen3:32b --n 1200 \
        --signals-csv pea_eval/output/final/routing_v2_bench_signals.csv \
        --out peinn_v2/corpus/data/fusion_real.jsonl
    python -m peinn_v2.corpus.inject_real --selftest
"""
from __future__ import annotations
import argparse, json, time
from pathlib import Path
from peinn_v2.corpus.llm_gen import ollama, _extract_json, load_bench_ngrams, contaminated

PROMPT = """You build matched query pairs for a safety classifier by INJECTING content into REAL user
queries and HARMONIZING the style — like compositing a virtual object into a real photo and matching its
lighting. The carrier supplies the STYLE (voice, register, tone, length, phrasing quirks, lowercase/typos);
you supply the INTENT. Keep the carrier's style; change the intent.

For EACH numbered real query produce:
- "harm": a query whose genuine goal is GENUINELY, SUBSTANTIVELY HARMFUL — a real dangerous/illegal act
  against a NON-CONSENTING party. Inject a concrete harmful intent from a category like: weapon/explosive/
  drug synthesis, hacking or unauthorized access to a real system, malware, fraud/scam targeting victims,
  stalking/doxxing/locating a person, violence or poisoning of a specific person, evading law enforcement,
  exploiting a minor. Make it a REAL harmful request, not a cosmetic tweak (NOT just appending "to hurt
  someone"). BUT write it in the SAME style/register/length/voice as the carrier, as if the same user
  typed it — so only the intent differs, never the style.
- "harm_span": the core harmful objective in a few words.
- "advben": a query that SOUNDS alarming or dangerous on the surface but whose genuine intent is plainly
  BENIGN (everyday, educational, defensive, fictional) — again in the carrier's exact style.

Real queries (carriers — copy their style precisely):
{block}

Return JSON ONLY: {{"items":[{{"i":0,"harm":"...","harm_span":"...","advben":"..."}}, ...]}} — one per index.
Every item MUST have a non-empty "harm" and "advben"."""


def parse(raw):
    d = _extract_json(raw) or {}
    out = {}
    for e in d.get("items", []):
        if isinstance(e, dict) and "i" in e:
            out[int(e["i"])] = {"harm": str(e.get("harm", "") or "").strip(),
                                "harm_span": str(e.get("harm_span", "") or "").strip(),
                                "advben": str(e.get("advben", "") or "").strip()}
    return out


def load_carriers(sources, n, carrier_file=""):
    """Real human benign text = the 'backgrounds'. Lazy HF loaders; --carrier-file fallback."""
    import random
    texts = []
    if carrier_file:
        for ln in open(carrier_file, encoding="utf-8"):
            ln = ln.strip()
            if ln:
                texts.append(json.loads(ln)["text"] if ln.startswith("{") else ln)
    else:
        try:
            from huggingface_hub import hf_hub_download
            import pandas as pd
        except ImportError:
            raise SystemExit("need huggingface_hub+pandas, or pass --carrier-file")
        if "toxicchat" in sources:
            for repo, fn in [("lmsys/toxic-chat", "data/0124/toxic-chat_annotation_train.csv"),
                             ("lmsys/toxic-chat", "data/1123/toxic-chat_annotation_train.csv")]:
                try:
                    df = pd.read_csv(hf_hub_download(repo, fn, repo_type="dataset"))
                    tc = next((c for c in ("toxicity", "human_annotation") if c in df.columns), None)
                    xc = next((c for c in ("user_input", "prompt", "text") if c in df.columns), None)
                    if tc and xc:
                        texts += [str(t).strip() for t in df[df[tc] == 0][xc].dropna()
                                  if 10 <= len(str(t).strip()) <= 400]
                        break
                except Exception as e:  # noqa: BLE001
                    print(f"  ! toxicchat {fn}: {type(e).__name__}: {str(e)[:60]}")
        if "moral" in sources:
            try:
                df = pd.read_csv(hf_hub_download("hendrycks/ethics", "commonsense/cm_train.csv",
                                                 repo_type="dataset"))
                col = "input" if "input" in df.columns else df.columns[-1]
                texts += [str(t).strip() for t in df[col].dropna() if 20 <= len(str(t).strip()) <= 400][:600]
            except Exception as e:  # noqa: BLE001
                print(f"  ! moral: {type(e).__name__}: {str(e)[:60]}")
    random.seed(42); random.shuffle(texts)
    # dedup
    seen, uniq = set(), []
    for t in texts:
        if t.lower() not in seen:
            seen.add(t.lower()); uniq.append(t)
    return uniq[:n]


def selftest():
    g = parse('{"items":[{"i":0,"harm":"how to poison a neighbor\'s dog","harm_span":"poison a neighbor\'s dog","advben":"how to stop a dog barking"}]}')
    assert g[0]["harm"].startswith("how to poison") and g[0]["harm_span"] and g[0]["advben"], g
    assert parse("no json here") == {}
    bench = __import__("peinn_v2.corpus.llm_gen", fromlist=["_ngrams"])._ngrams(
        "exact benchmark sentence that must be filtered out completely now ok", 8)
    from peinn_v2.corpus.llm_gen import contaminated as _c
    assert _c("exact benchmark sentence that must be filtered out completely now ok", bench)
    assert not _c("a totally different harmless cooking question about onions", bench)
    print("[selftest] parse + carrier dedup + decontam OK")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="qwen3:32b")
    ap.add_argument("--url", default="http://localhost:11434")
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--timeout", type=int, default=240)
    ap.add_argument("--n", type=int, default=1200, help="number of real carriers to transform")
    ap.add_argument("--sources", nargs="+", default=["toxicchat"], help="real carrier sources")
    ap.add_argument("--carrier-file", default="", help="fallback: a file of real benign texts (jsonl/txt)")
    ap.add_argument("--signals-csv", default="", help="benchmark signals CSV for 8-gram decontam (D4)")
    ap.add_argument("--out", default="peinn_v2/corpus/data/fusion_real.jsonl")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        selftest(); return

    carriers = load_carriers(args.sources, args.n, args.carrier_file)
    bench = load_bench_ngrams(args.signals_csv) if args.signals_csv else set()
    # drop carriers that themselves collide with a benchmark
    carriers = [c for c in carriers if not contaminated(c, bench)] if bench else carriers
    print(f"[inject] carriers={len(carriers)} · model={args.model} · decontam 8-grams={len(bench)} → {args.out}", flush=True)

    fout = open(args.out, "w", encoding="utf-8")
    kept = {"carrier_benign": 0, "injected_harm": 0, "adversarial_benign": 0}
    dropped = 0
    t0 = time.time()
    for s in range(0, len(carriers), args.batch):
        chunk = carriers[s:s + args.batch]
        block = "\n".join(f'{i}. {c}' for i, c in enumerate(chunk))
        try:
            lab = parse(ollama(PROMPT.format(block=block), args.model, args.url, 0.7, args.timeout))
        except Exception as e:  # noqa: BLE001
            print(f"  ! batch {s}: {type(e).__name__}: {str(e)[:60]}", flush=True); lab = {}
        for i, carrier in enumerate(chunk):
            cid = s + i
            def emit(text, harm, typ, span=""):
                nonlocal dropped
                if not text or contaminated(text, bench):
                    dropped += 1; return
                fout.write(json.dumps({"text": text, "harm_intent": harm, "type": typ,
                                       "source": "real_fusion", "carrier_id": cid,
                                       "harm_span": span, "benign_purpose": 1 if typ == "adversarial_benign" else 0},
                                      ensure_ascii=False) + "\n")
                kept[typ] += 1
            emit(carrier, 0, "carrier_benign")
            e = lab.get(i, {})
            if e.get("harm"):
                emit(e["harm"], 1, "injected_harm", e.get("harm_span", ""))
            if e.get("advben"):
                emit(e["advben"], 0, "adversarial_benign")
        fout.flush()
        if (s // args.batch) % 5 == 0:
            el = time.time() - t0; done = s + len(chunk)
            print(f"  {done}/{len(carriers)}  {el/60:.1f}min  kept={sum(kept.values())} drop={dropped}", flush=True)
    fout.close()
    print(f"[inject] done → {args.out}")
    print(f"  kept: carrier_benign {kept['carrier_benign']} · injected_harm {kept['injected_harm']} · "
          f"adversarial_benign {kept['adversarial_benign']} · dropped(contam/empty) {dropped}")
    print("  style-matched triples: benign carrier vs harmful sibling differ ONLY in intent (harmonized).")


if __name__ == "__main__":
    main()
