#!/usr/bin/env python3
"""Deterministically sample ~20 items per type from each PEINN training corpus.

Copyright-aware: we redistribute only a small, illustrative ~20-per-type sample of
each corpus (never the full corpora). Provenance fields (`source`, `type`, etc.) are
preserved verbatim so reviewers can trace every row. Full corpora are regenerated
from the original sources following docs/REGENERATE_CHECKPOINTS.md.

Run from the PEAOS checkout:  python build_samples.py <PEAOS_DIR> <OUT_DIR>
"""
from __future__ import annotations
import csv, json, random, sys, collections
from pathlib import Path

SEED = 20260627
PER_TYPE = 20

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/user/PEAOS")
OUT = Path(sys.argv[2] if len(sys.argv) > 2 else "/home/user/PEINN/data_samples")


def _rng():
    r = random.Random(SEED)
    return r


def sample_by_key(rows, key, per=PER_TYPE):
    """Stable: sort rows, group by key, take up to `per` from each group (seeded)."""
    groups = collections.OrderedDict()
    for row in rows:
        groups.setdefault(row.get(key, "?"), []).append(row)
    out = []
    for k in sorted(groups):
        g = groups[k]
        r = _rng()
        r.shuffle(g)
        out.extend(g[:per])
    return out


def read_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write_jsonl(path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def write_csv(path, rows, fieldnames):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for row in rows:
            w.writerow(row)
    return len(rows)


def main():
    log = []

    # 1) Neutro Head T/I/F training pool (production head) — sample 20 per source dataset
    rows = read_csv(SRC / "pea_eval/data/ee_3class/train.csv")
    s = sample_by_key(rows, "source")
    n = write_csv(OUT / "neutro_head_tif/train_sample.csv", s, ["text", "source", "T", "I", "F"])
    log.append(("neutro_head_tif/train_sample.csv", n, "20 per source dataset (T/I/F soft targets)"))

    # 1b) Neutro Head v4 (2-of-3 masked) — sample 20 per polar bucket
    p = SRC / "pea_eval/data/ee_3class/v4/labeled_2of3.csv"
    if p.exists():
        rows = read_csv(p)
        s = sample_by_key(rows, "polar")
        n = write_csv(OUT / "neutro_head_tif/v4_labeled_2of3_sample.csv", s, rows[0].keys())
        log.append(("neutro_head_tif/v4_labeled_2of3_sample.csv", n, "20 per polar bucket (v4 masked 2-of-3 head)"))

    # 2) Structured-threat energy — LLM-generated intent corpus, 20 per type (T1..T6)
    rows = read_jsonl(SRC / "peinn_v2/corpus/data/intent_corpus.jsonl")
    s = sample_by_key(rows, "type")
    n = write_jsonl(OUT / "structured_energy/intent_corpus_sample.jsonl", s)
    log.append(("structured_energy/intent_corpus_sample.jsonl", n, "20 per intent type T1..T6"))

    # 3) Domain decorrelation pairs — 20 per file (one type each)
    for name in ["dom_advbenign", "dom_benignsensitive", "dom_subtleharm"]:
        rows = read_jsonl(SRC / f"peinn_v2/corpus/data/{name}.jsonl")
        r = _rng(); r.shuffle(rows)
        n = write_jsonl(OUT / f"structured_energy/{name}_sample.jsonl", rows[:PER_TYPE])
        log.append((f"structured_energy/{name}_sample.jsonl", n, "topic-decorrelation domain pairs"))

    # 4) CAD minimal pairs — 20 per toggled axis (act/real/def)
    rows = read_jsonl(SRC / "peinn_v2/corpus/data/cad_corpus.jsonl")
    s = sample_by_key(rows, "toggled_axis", per=8)  # 8*3 axes ~= 24
    n = write_jsonl(OUT / "structured_energy/cad_corpus_sample.jsonl", s)
    log.append(("structured_energy/cad_corpus_sample.jsonl", n, "~8 per toggled axis (act/real/def CAD minimal pairs)"))

    # 5) Fusion-real composed requests — 20 per type
    rows = read_jsonl(SRC / "peinn_v2/corpus/data/fusion_real_v2.jsonl")
    s = sample_by_key(rows, "type")
    n = write_jsonl(OUT / "structured_energy/fusion_real_sample.jsonl", s)
    log.append(("structured_energy/fusion_real_sample.jsonl", n, "20 per type (carrier_benign/injected_harm/adversarial_benign)"))

    # 6) v4 head corpus augmentation — narrative (TinyStories→T) + jailbreak (in-the-wild→I)
    p = SRC / "pea_eval/data/ee_3class/v4/corpus_unlabeled.jsonl"
    if p.exists():
        rows = read_jsonl(p)
        for src_tag, label in [("narrative", "TinyStories narration → ¬D → polar_hint T"),
                               ("jailbreak", "in-the-wild jailbreak frames → polar_hint I")]:
            g = [r for r in rows if r.get("source") == src_tag]
            r = _rng(); r.shuffle(g)
            n = write_jsonl(OUT / f"neutro_head_tif/v4_{src_tag}_sample.jsonl", g[:PER_TYPE])
            log.append((f"neutro_head_tif/v4_{src_tag}_sample.jsonl", n, label))

    # 7) v4 illocution labels — Directive force (D) / Subversion (S), ~20 per D value
    p = SRC / "pea_eval/data/ee_3class/v4/illocution_labels.csv"
    if p.exists():
        rows = read_csv(p)
        s = sample_by_key(rows, "D", per=10)
        n = write_csv(OUT / "neutro_head_tif/v4_illocution_sample.csv", s, rows[0].keys())
        log.append(("neutro_head_tif/v4_illocution_sample.csv", n, "speech-act labels D (Directive) / S (Subversion)"))

    print(f"{'file':52s} {'rows':>5s}  note")
    for f, c, note in log:
        print(f"{f:52s} {c:5d}  {note}")


if __name__ == "__main__":
    main()
