#!/usr/bin/env python3
"""labeled_to_fit_jsonl.py — v4 labeled.csv → fit jsonl for the routing-signal capture step.

θ for the gate must be fit on an INDEPENDENT corpus (D12). The v4 AUGMENTED corpus (narrative +
jailbreak + adversarial-benign + dilemmas) is a good proxy for benchmark difficulty. The signal
capture step needs {text, harm_intent}; this maps the derived label (polar F = harmful,
T = benign) to harm_intent so the v4-head routing signals can be captured over the v4 corpus and
the gate θ fit there.

  python scripts/labeled_to_fit_jsonl.py            # v4/labeled.csv → v4/corpus_fit.jsonl
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
V4_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class" / "v4"


def main() -> int:
    ap = argparse.ArgumentParser(description="v4 labeled.csv → capture fit jsonl")
    ap.add_argument("--labeled", default=str(V4_DIR / "labeled.csv"))
    ap.add_argument("--out", default=str(V4_DIR / "corpus_fit.jsonl"))
    args = ap.parse_args()
    rows = list(csv.DictReader(open(args.labeled, encoding="utf-8")))
    n = Counter()
    with open(args.out, "w", encoding="utf-8") as fh:
        for r in rows:
            hi = 1 if r["polar"] == "F" else 0    # derived polar: F = harmful, T = benign
            n["unsafe" if hi else "benign"] += 1
            fh.write(json.dumps({"text": r["text"], "harm_intent": hi,
                                 "type": r.get("source", "v4")}, ensure_ascii=False) + "\n")
    print(f"wrote {len(rows)} → {args.out}  ({dict(n)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
