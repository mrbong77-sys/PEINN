"""DESIGN.md 12 (step S): public over-refusal and adversarial training sets added to the isolated corpus.

The v4 corpus keeps few benign prompts that look harmful once the XSTest-type sources are out (DESIGN.md 11), so the
isolated gate over-blocks such prompts. As in CPEG's "no benchmark items" retrain (PEINN_v2 energy.py `_cf_sources`),
the corpus takes public sets built for training against over-refusal and jailbreaks. None is one of the six evaluation
benchmarks, none was written from XSTest, and the isolation audit (DESIGN.md 3) still drops any row that matches or
nears a recorded routing text. Labels are the datasets' own: benign rows T 1, I 0, F 0; harmful rows T 0, I 0, F 1.
The recipe is fixed before any result (seed 42); rows split 80/10/10 by source and label (data.assign_split).
"""
from __future__ import annotations

import json
import random

import pandas as pd

from . import common as C
from . import data as D

SEED = 42
# (source, label, rows): benign over-refusal 7,379 at most, harmful counterparts 3,000; DESIGN.md 15/17 add 14,000 plain rows
# DESIGN.md 19: contrast and adversarial sets taken further in the same seed-42 orders (earlier rows kept)
RECIPE = (("orbench_80k", 0, 3000), ("falsereject_train", 0, 5000), ("phtest_harmless", 0, 3000),
          ("coconot_contrast", 0, 1000), ("wildjailbreak_adv_benign", 0, 3000), ("wildguardmix_adv_benign", 0, 1500),
          ("orbench_toxic", 1, 1500), ("wildjailbreak_adv_harmful", 1, 3000), ("wildguardmix_adv_harmful", 1, 1500),
          # DESIGN.md 15: plain (vanilla) requests, harmful and harmful-looking benign, as in CPEG's WildGuardMix patch
          # DESIGN.md 17: the same seed-42 orders taken further (the first rows are the ones of DESIGN.md 15)
          ("wildjailbreak_van_benign", 0, 12000), ("wildguardmix_van_benign", 0, 4000),       # DESIGN.md 23
          ("wildjailbreak_van_harmful", 1, 12000), ("wildguardmix_van_harmful", 1, 4000),
          ("orbench_hard", 0, 1500))
CHECK_ROWS = 20


def _orbench(cfg):
    from datasets import load_dataset
    d = load_dataset("bench-llm/or-bench", cfg)
    return d["train" if "train" in d else list(d.keys())[0]]["prompt"]


def _wildjailbreak(dt):
    from datasets import load_dataset
    rows = load_dataset("allenai/wildjailbreak", "train", split="train", delimiter="\t", keep_default_na=False)
    col = "vanilla" if dt.startswith("vanilla") else "adversarial"
    return [x[col] for x in rows if str(x.get("data_type", "")) == dt]


def _wildguardmix(harmful, adversarial=True):
    from datasets import load_dataset
    rows = load_dataset("allenai/wildguardmix", "wildguardtrain", split="train")
    want = "harmful" if harmful else "unharmful"
    return [x["prompt"] for x in rows if bool(x.get("adversarial")) == adversarial and x.get("prompt_harm_label") == want]


def _falsereject():
    from datasets import load_dataset
    return load_dataset("AmazonScience/FalseReject", split="train")["prompt"]


def _phtest():
    from datasets import load_dataset
    return [x["Request"] for x in load_dataset("furonghuang-lab/PHTest", split="train") if x["Harmfulness"] == "harmless"]


def _coconot():
    from datasets import load_dataset
    return load_dataset("allenai/coconot", "contrast", split="test")["prompt"]


LOADERS = {"orbench_80k": lambda: _orbench("or-bench-80k"), "orbench_toxic": lambda: _orbench("or-bench-toxic"),
           "orbench_hard": lambda: _orbench("or-bench-hard-1k"),
           "falsereject_train": _falsereject, "phtest_harmless": _phtest, "coconot_contrast": _coconot,
           "wildjailbreak_adv_benign": lambda: _wildjailbreak("adversarial_benign"),
           "wildjailbreak_adv_harmful": lambda: _wildjailbreak("adversarial_harmful"),
           "wildguardmix_adv_benign": lambda: _wildguardmix(False), "wildguardmix_adv_harmful": lambda: _wildguardmix(True),
           "wildjailbreak_van_benign": lambda: _wildjailbreak("vanilla_benign"),
           "wildjailbreak_van_harmful": lambda: _wildjailbreak("vanilla_harmful"),
           "wildguardmix_van_benign": lambda: _wildguardmix(False, False),
           "wildguardmix_van_harmful": lambda: _wildguardmix(True, False)}


def rows(check: bool, loaders=None, log=print) -> pd.DataFrame:
    """The supplement in the v4 corpus columns; each source sampled with seed 42 after dropping blanks and repeats."""
    loaders = loaders or LOADERS
    out, seen = [], set()
    for src, lab, n in RECIPE:
        texts = list(dict.fromkeys(str(t).strip() for t in loaders[src]() if str(t or "").strip()))
        random.Random(SEED).shuffle(texts)
        take = [t for t in texts if t not in seen][:CHECK_ROWS if check else n]
        seen.update(take)
        log(f"  {src}: {len(texts):,} available, {len(take):,} taken (label {lab})")
        out += [{"text": t, "T": float(1 - lab), "I": 0.0, "F": float(lab), "mask_T": 1.0, "mask_I": 1.0, "mask_F": 1.0,
                 "polar": "F" if lab else "T", "source": f"supp:{src}"} for t in take]
    return pd.DataFrame(out)


def supplement(check: bool = False, log=print) -> int:
    df = rows(check, log=log)
    df.to_csv(D.supplement_file(check), index=False, encoding="utf-8")
    st = {"recipe": [list(r) for r in RECIPE], "rows": int(len(df)),
          "by_source": {k: int(v) for k, v in df.source.value_counts().sort_index().items()},
          "by_label": {"benign": int((df.F == 0).sum()), "harmful": int((df.F == 1).sum())}}
    log(json.dumps(st))
    f = C.jdump(st, D.odir(check) / "corpus" / "supplement.json")
    if check:
        return 0
    return 0 if C.publish([f], "v21r S: public over-refusal and adversarial training sets added to the corpus (counts)") else 1
