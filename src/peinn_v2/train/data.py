"""Data loading, topic-split, tokenization, batching for the intent corpus (post-E5, D8; D9 C/A/R; D14 +L).

Schema (corpus/label_car.py + label_legit.py): {text, type, topic, harm_intent, …, C, A, R, L}.
The 4 heads predict the COMPOSITIONAL elements (C harmful-Capability, A operational-Action,
R real-Target, L iLlegitimacy = harmful/unauthorized intent vs legitimate purpose); the energy is
their gated AND-combiner (threat = C∧A∧R∧L, D14), NOT a single holistic head. L is the legitimacy
axis (D14): a legitimate-but-sensitive request has high C/A/R but L≈0 ⇒ the gate collapses ⇒ no
block — the dimension C/A/R alone could not separate on the benchmarks.
The legacy holistic axes (harm/op/bp on intent_corpus.jsonl) are kept commented for reference.
"""
from __future__ import annotations
import json, random, hashlib
from pathlib import Path

CORPUS = Path(__file__).parents[1] / "corpus" / "data" / "intent_corpus_car.jsonl"
AXES = ("C", "A", "R", "L")
LABEL_KEYS = ("C", "A", "R", "L")
# pre-D14 (D9) compositional scheme: AXES=LABEL_KEYS=("C","A","R")  — no legitimacy gate.
# legacy holistic scheme (pre-D9): CORPUS=intent_corpus.jsonl, AXES=("harm","op","bp"),
#   LABEL_KEYS=("harm_intent","operational","benign_purpose")


def load(paths=CORPUS):
    """Load one or more corpora. `paths` may be a Path/str (optionally comma-separated) or a
    list. Each row gets a `domain` env tag (D13): its own `domain` field if present, else the
    file stem — so IRM/SupCon can enforce invariance ACROSS data-source domains, not just topics
    within one corpus (the corpus→benchmark covariate shift the topic-IRM could not see)."""
    if isinstance(paths, (str, Path)):
        paths = str(paths).split(",")
    out = []
    for p in paths:
        p = Path(str(p).strip())
        if not p.exists():
            raise SystemExit(f"intent corpus missing: {p}\n  generate it on a box with Ollama:\n"
                             "  python -m peinn_v2.corpus.llm_gen --model qwen3:32b --k 8 "
                             '--signals-csv "$CSV" --out ' + str(p))
        dom = p.stem
        with open(p, encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                r["domain"] = r.get("domain") or dom
                out.append(r)
    return out


def make_splits(records, dev_topic_frac=0.2, seed=0):
    """Split BY TOPIC (unseen-topic dev) — intrinsic generalization. The real arbiter is the
    held-out benchmark transfer measured by the v2.1 bench sweep (scripts/run_v21_bench.py)."""
    topics = sorted({r["topic"] for r in records})
    rng = random.Random(seed); rng.shuffle(topics)
    n_dev = max(1, int(round(len(topics) * dev_topic_frac)))
    dev_topics = set(topics[:n_dev])
    train = [r for r in records if r["topic"] not in dev_topics]
    devs = {"topic": [r for r in records if r["topic"] in dev_topics]}
    return train, devs, sorted(dev_topics)


def pos_weights(records):
    import torch
    w = []
    for k in LABEL_KEYS:
        pos = sum(int(r.get(k, 0)) for r in records); neg = len(records) - pos
        w.append(neg / max(pos, 1))
    return torch.tensor(w, dtype=torch.float32)


class HashTokenizer:
    def __init__(self, vocab=512, max_len=32):
        self.vocab, self.max_len = vocab, max_len

    def __call__(self, texts):
        import torch
        ids, masks = [], []
        for t in texts:
            toks = t.lower().split()[:self.max_len]
            row = [int(hashlib.md5(w.encode()).hexdigest(), 16) % (self.vocab - 1) + 1 for w in toks]
            pad = self.max_len - len(row)
            ids.append(row + [0] * pad); masks.append([1] * len(row) + [0] * pad)
        return torch.tensor(ids), torch.tensor(masks)


class HFTokenizer:
    def __init__(self, model_name, max_len=64):
        from transformers import AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(model_name); self.max_len = max_len

    def __call__(self, texts):
        enc = self.tok(list(texts), padding=True, truncation=True,
                       max_length=self.max_len, return_tensors="pt")
        return enc["input_ids"], enc["attention_mask"]


def batches(records, batch_size=32, seed=0, shuffle=True):
    idx = list(range(len(records)))
    if shuffle:
        random.Random(seed).shuffle(idx)
    for i in range(0, len(idx), batch_size):
        yield [records[j] for j in idx[i:i + batch_size]]


def to_tensors(items, env_key="topic"):
    import torch
    texts = [it["text"] for it in items]
    labels = torch.tensor([[int(it.get(k, 0)) for k in LABEL_KEYS] for it in items], dtype=torch.float32)
    envs = [it.get(env_key, it.get("topic", "")) for it in items]
    return texts, labels, envs
