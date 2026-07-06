#!/usr/bin/env python3
"""export_per_item_sheets.py — build the full per-item result sheets, harm-redacted.

Reads the raw PEAOS v2.1 output CSVs and writes complete per-item sheets to
results/per_item/, preserving every scoring, routing-signal, and metadata column and
all non-harmful text, while **removing harmful elements**:

  - HarmBench: every attack prompt and model response (the suite is harmful by design).
  - Jailbreak Taxonomy: every attack prompt and response, including the second-pass
    (P2) content, and the judge free-text reasons (which quote the attack).
  - XSTest: the prompt and response text of the *unsafe* contrast items only; the safe
    items are kept in full.
  - Ethics / MORABLES / GGB: no harmful content — kept intact.

Redaction is trace-preserving: a removed cell is replaced with a marker that keeps the
original text length, e.g. `[REDACTED: harmful content, 1240 chars]`, so a reader can
still infer that substantive content existed and roughly how much. Benign refusals are
NOT removed -- only responses the benchmark judged harmful (a successful attack /
unsafe-compliance) are redacted -- so the defenses' actual refusal text remains
readable. Attack prompts/behaviours and model chain-of-thought on harmful prompts are
redacted (length-annotated). Empty cells stay empty, and every scoring, routing-signal,
verdict, and metadata field is kept, so the per-item structure remains fully auditable.
Short verdict/label fields (e.g. HARMFUL/SAFE, UNSAFE, full_compliance) are kept.

Usage:  python tools/export_per_item_sheets.py /path/to/PEAOS/pea_eval/output/v21 results/per_item
"""
from __future__ import annotations
import sys, os, glob
import pandas as pd

ARMS = [f"H{i:02d}" for i in range(1, 18)]

PATTERNS = {
    "harmbench": "harmbench_batch_*", "taxonomy": "taxonomy_batch_*",
    "xstest": "xstest_batch_*", "ethics": "ethics_batch_*",
    "morables": "morables_batch_*", "ggb": "ggb_batch_*",
}


def _load(v21, pat):
    fs = [f for f in sorted(glob.glob(os.path.join(v21, pat))) if "/clean/" not in f][-2:]
    d = pd.concat([pd.read_csv(f) for f in fs], ignore_index=True)
    d = d[d.arm_id.isin(ARMS)].copy()
    sort_cols = [c for c in ("arm_id", "run_id") if c in d.columns]
    return d.sort_values(sort_cols).reset_index(drop=True) if sort_cols else d


def _redact(df, cols, mask=None):
    """Replace each non-empty target cell with a length-annotated marker (trace)."""
    n = 0
    rows = df.index if mask is None else df.index[mask.values]
    for c in cols:
        if c not in df.columns:
            continue
        for i in rows:
            v = df.at[i, c]
            if pd.notna(v) and str(v).strip() != "":
                df.at[i, c] = f"[REDACTED: harmful content, {len(str(v))} chars]"
                n += 1
    return n


def sanitize(name, d):
    """Trace-preserving harm redaction; returns cells redacted."""
    n = 0
    if name == "harmbench":
        # attack behaviours/prompts and CoT: always; responses: only successful attacks
        n += _redact(d, ["behavior", "prompt_p1", "prompt_p2", "thought_block"])
        n += _redact(d, ["response_p1", "response_p2"], mask=(d.asr_binary == 1))
    elif name == "taxonomy":
        n += _redact(d, ["turn_1_prompt", "prompt_p1", "prompt_p2", "thought_block"])
        harmful = d.is_unsafe == 1
        n += _redact(d, ["turn_1_response", "response_p1", "response_p2",
                         "judge_hsl_reason", "judge_mda_reason"], mask=harmful)
    elif name == "xstest":
        unsafe = d.expected_label == "unsafe"
        n += _redact(d, ["prompt_text", "prompt_p1", "prompt_p2", "thought_block"], mask=unsafe)
        complied = unsafe & (d.unsafe_compliance == 1)
        n += _redact(d, ["response_p1", "response_p2", "judge_rationale", "judge_raw"], mask=complied)
    # ethics / morables / ggb: no harmful content -> untouched
    return n


def main():
    v21 = sys.argv[1] if len(sys.argv) > 1 else "/home/user/PEAOS/pea_eval/output/v21"
    out = sys.argv[2] if len(sys.argv) > 2 else "results/per_item"
    os.makedirs(out, exist_ok=True)
    summary = []
    for name, pat in PATTERNS.items():
        d = _load(v21, pat)
        red = sanitize(name, d)
        path = os.path.join(out, f"{name}_per_item.csv")
        d.to_csv(path, index=False)
        kb = os.path.getsize(path) // 1024
        summary.append((name, len(d), red, kb))
        print(f"wrote {path}: {len(d)} rows, {red} cells redacted, {kb} KB")
    print("\n" + "\n".join(f"  {n:10s} {r:6d} rows  {c:7d} redacted  {k:6d} KB" for n, r, c, k in summary))


if __name__ == "__main__":
    main()
