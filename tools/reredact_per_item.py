#!/usr/bin/env python3
"""Conservative re-redaction of the per-item result sheets.

The original redaction keyed on the JUDGE's harm verdict (asr_binary /
is_unsafe / unsafe_compliance), so wherever the judge false-negatived a
harmful completion the raw text stayed exposed. This pass instead keys on
the *item being an attack*: for the attack benchmarks (HarmBench, Jailbreak
Taxonomy) and for XSTest's unsafe contrast items, every prompt/response/
free-text cell is redacted regardless of the judge verdict. All scoring,
routing-signal, verdict, and metadata columns are kept intact, so the
numbers behind every table and figure remain fully reproducible.

Trace-preserving: a redacted cell becomes "[REDACTED: harmful content, N chars]".
Benign benchmarks (Ethics, GGB, MORABLES) and XSTest safe items are untouched.
"""
import csv, os, sys

DIR = os.path.join(os.path.dirname(__file__), "..", "results", "per_item")

TEXT_COLS = {
    "harmbench_per_item.csv": (
        ["prompt_p1", "response_p1", "prompt_p2", "response_p2", "behavior",
         "thought_block"],
        None,  # redact every row
    ),
    "taxonomy_per_item.csv": (
        ["turn_1_prompt", "turn_1_response", "prompt_p1", "response_p1",
         "prompt_p2", "response_p2", "thought_block", "judge_hsl_reason",
         "judge_mda_reason"],
        None,  # every taxonomy item is a jailbreak attack
    ),
    "xstest_per_item.csv": (
        ["prompt_text", "prompt_p1", "response_p1", "prompt_p2", "response_p2",
         "judge_rationale", "thought_block", "judge_raw"],
        lambda row: row.get("expected_label", "").strip().lower() == "unsafe",
    ),
}


def redact_cell(v):
    v = v or ""
    if not v.strip():
        return v
    if v.lstrip().startswith("[REDACTED"):
        return v
    return f"[REDACTED: harmful content, {len(v)} chars]"


def process(path, cols, row_pred):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        fields = r.fieldnames
        rows = list(r)
    cols = [c for c in cols if c in fields]
    changed = 0
    for row in rows:
        if row_pred is not None and not row_pred(row):
            continue
        for c in cols:
            new = redact_cell(row.get(c, ""))
            if new != row.get(c, ""):
                row[c] = new
                changed += 1
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(rows), changed


if __name__ == "__main__":
    for fname, (cols, pred) in TEXT_COLS.items():
        p = os.path.join(DIR, fname)
        n, changed = process(p, cols, pred)
        print(f"{fname}: {n} rows, {changed} cells newly redacted")
