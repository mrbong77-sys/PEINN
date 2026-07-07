#!/usr/bin/env python3
"""build_neutro_v4_corpus.py — augment the v3 corpus with the two illocution domains.

NeutroEE v4 teaches the head the speech-act axes (Directive D / Subversion S). For that the
training corpus must contain examples the v3 corpus lacks:
  · NARRATIVE (¬D): 3rd-person stories/fables → the energy-over-fire suppression ground truth
    (a fable narrates actions but requests nothing → D≈0 → T). Source: roneneldan/TinyStories.
  · JAILBREAK frame (D∧S, harm un-uttered → latent I): safety-subversion / unrestricted-persona
    preambles. Source: TrustAIRLab/in-the-wild-jailbreak-prompts. (Payload-bearing jailbreaks
    are a later reinforcement decision — frames first.)

Base = the decontaminated v3 corpus. Both new domains pass ProvenanceGuard (exact + 5-gram) so
they never overlap the 8 benchmarks (Aesop↔morables, jailbreaks↔taxonomy caught). dedup + length.

RUN ON DGX (network for HF). This box generates + pushes the code.
  python scripts/build_neutro_v4_corpus.py --narrative-cap 1200 --jailbreak-cap 800
  → pea_eval/data/ee_3class/v4/{corpus_unlabeled.jsonl, corpus_report.txt}
Next: label_ee_3class_v3 (2-of-3) + label_illocution (D,S) on this corpus → derive_tif_v4.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peinn.build_neutro_v4_corpus")

V3_CORPUS = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class" / "v3" / "corpus_unlabeled.jsonl"
V4_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class" / "v4"
CORPUS_OUT = V4_DIR / "corpus_unlabeled.jsonl"
REPORT_OUT = V4_DIR / "corpus_report.txt"


def load_base() -> list[tuple[str, str, str]]:
    out = []
    if not V3_CORPUS.exists():
        logger.warning(f"v3 corpus 없음: {V3_CORPUS} — base 생략")
        return out
    for line in open(V3_CORPUS, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        out.append((o["text"], o.get("source", "v3"), o.get("polar_hint", "T")))
    logger.info(f"base v3 corpus: {len(out)}")
    return out


def load_narrative(cap: int) -> list[tuple[str, str, str]]:
    """3rd-person stories (¬D) → polar_hint T. roneneldan/TinyStories."""
    out = []
    try:
        from datasets import load_dataset
        ds = load_dataset("roneneldan/TinyStories", split="train", streaming=True)
        for r in ds:
            t = " ".join(str(r.get("text", "")).split())
            if 40 <= len(t) <= 1500:
                out.append((t, "narrative", "T"))
            if len(out) >= cap:
                break
    except Exception as e:
        logger.warning(f"narrative 로더 실패: {type(e).__name__}: {str(e)[:140]}")
    logger.info(f"narrative: {len(out)}")
    return out


def load_jailbreak(cap: int) -> list[tuple[str, str, str]]:
    """Jailbreak frames (D∧S, harm un-uttered) → polar_hint I (latent threat)."""
    out = []
    candidates = [
        ("TrustAIRLab/in-the-wild-jailbreak-prompts", "jailbreak_2023_12_25", "prompt"),
        ("rubend18/ChatGPT-Jailbreak-Prompts", None, "Prompt"),
    ]
    for repo, config, field in candidates:
        try:
            from datasets import load_dataset
            ds = (load_dataset(repo, config, split="train") if config
                  else load_dataset(repo, split="train"))
            for r in ds:
                t = " ".join(str(r.get(field, "") or "").split())
                if 20 <= len(t) <= 1500:
                    out.append((t, "jailbreak", "I"))
                if len(out) >= cap:
                    break
            if out:
                logger.info(f"jailbreak source: {repo}")
                break
        except Exception as e:
            logger.warning(f"jailbreak 로더 {repo} 실패: {type(e).__name__}: {str(e)[:120]}")
    logger.info(f"jailbreak: {len(out)}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="NeutroEE v4 corpus augmentation (narrative + jailbreak)")
    ap.add_argument("--narrative-cap", type=int, default=1200)
    ap.add_argument("--jailbreak-cap", type=int, default=800)
    ap.add_argument("--min-len", type=int, default=8)
    ap.add_argument("--max-len", type=int, default=1500)
    ap.add_argument("--no-guard", action="store_true")
    args = ap.parse_args()
    V4_DIR.mkdir(parents=True, exist_ok=True)

    pool = load_base() + load_narrative(args.narrative_cap) + load_jailbreak(args.jailbreak_cap)

    guard = None
    if not args.no_guard:
        from pea_eval.pge.provenance_guard import ProvenanceGuard
        guard = ProvenanceGuard.build()
        guard.report()

    seen, kept, drop = set(), [], Counter()
    for txt, src, hint in pool:
        txt = " ".join((txt or "").split())
        if not (args.min_len <= len(txt) <= args.max_len):
            drop["len"] += 1
            continue
        key = txt.lower()
        if key in seen:
            drop["dup"] += 1
            continue
        if guard is not None:
            ok, reason = guard.check(txt)
            if not ok:
                drop[f"guard:{reason.split('(')[0]}"] += 1
                continue
        seen.add(key)
        kept.append((txt, src, hint))

    with open(CORPUS_OUT, "w", encoding="utf-8") as fh:
        for txt, src, hint in kept:
            fh.write(json.dumps({"text": txt, "source": src, "polar_hint": hint},
                                ensure_ascii=False) + "\n")
    by_src = Counter(s for _, s, _ in kept)
    by_hint = Counter(h for _, _, h in kept)
    lines = ["# NeutroEE v4 corpus (v3 + narrative + jailbreak) — composition",
             f"total kept: {len(kept)}", f"polar_hint: {dict(by_hint)}", f"drops: {dict(drop)}",
             "", "per-source (top):"]
    for s, n in by_src.most_common(25):
        lines.append(f"  {n:6d}  {s}")
    report = "\n".join(lines)
    REPORT_OUT.write_text(report + "\n", encoding="utf-8")
    logger.info("\n" + report)
    logger.info(f"\nwrote {len(kept)} → {CORPUS_OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
