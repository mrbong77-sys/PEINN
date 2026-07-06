#!/usr/bin/env python3
"""Redact harmful prompt text from the illustrative training-data samples,
trace-preserving, while keeping benign and adversarial-benign samples (and all
labels/metadata) intact so the head-training data distribution stays auditable.

Rules (an item is redacted if ANY applies):
  * it carries a harm label  (harm_intent == '1');
  * it is a jailbreak sample (source == 'jailbreak');
  * it has a high falsity soft-label (F >= 0.5) in the T/I/F sheets;
  * a small high-severity keyword safety-net matches (belt-and-suspenders for
    the unlabeled benign files).
Benign rows (benign-framed, adversarial-benign, narratives, dilemmas, alpaca
safe items) are kept verbatim.
"""
import csv, json, os, re, glob

BASE = os.path.join(os.path.dirname(__file__), "..", "data_samples")
TEXT_FIELDS = ("text", "harm_span")

# high-severity net for files without a harm label; word-boundary, case-insensitive
KW = re.compile(r"\b(synthesi[sz]e|detonat|explosive|nerve agent|sarin|"
                r"bioweapon|pathogen|ricin|malware|ransomware payload|"
                r"child sexual|cp\b|meth(amphetamine)? synthesis|"
                r"how to (make|build|synthesi[sz]e).{0,30}(bomb|weapon|virus|drug))",
                re.I)


def marker(v):
    return f"[REDACTED: harmful content, {len(v)} chars]"


def is_harmful(row):
    if str(row.get("harm_intent", "")).strip() == "1":
        return True
    if str(row.get("source", "")).strip() == "jailbreak":
        return True
    f = row.get("F", "")
    try:
        if f != "" and float(f) >= 0.5:
            return True
    except (TypeError, ValueError):
        pass
    t = row.get("text", "") or ""
    if KW.search(t):
        return True
    return False


def redact_row(row):
    if not is_harmful(row):
        return 0
    n = 0
    for fld in TEXT_FIELDS:
        v = row.get(fld)
        if v and not str(v).lstrip().startswith("[REDACTED"):
            row[fld] = marker(str(v))
            n += 1
    return n


def do_jsonl(path):
    out, red = [], 0
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            red += redact_row(row)
            out.append(row)
    with open(path, "w", encoding="utf-8") as fh:
        for row in out:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(out), red


def do_csv(path):
    with open(path, encoding="utf-8", newline="") as fh:
        r = csv.DictReader(fh)
        fields = r.fieldnames
        rows = list(r)
    red = sum(redact_row(row) for row in rows)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    return len(rows), red


if __name__ == "__main__":
    for path in sorted(glob.glob(os.path.join(BASE, "**", "*.jsonl"), recursive=True)):
        n, red = do_jsonl(path)
        print(f"{os.path.relpath(path, BASE)}: {n} rows, {red} cells redacted")
    for path in sorted(glob.glob(os.path.join(BASE, "**", "*.csv"), recursive=True)):
        n, red = do_csv(path)
        print(f"{os.path.relpath(path, BASE)}: {n} rows, {red} cells redacted")
