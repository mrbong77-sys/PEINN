# Training-data samples (~20 per type)

These are small, **illustrative** samples — roughly 20 items per type — drawn from each training
corpus used for PEINN v2.1's learned components. They let a reviewer see the exact format,
labels, and provenance of every training input **without** redistributing the full corpora
(which are large and partly derived from third-party datasets).

Full provenance, licensing, the sampling method, and how to regenerate the complete corpora are
documented in [`../docs/DATA_CARD.md`](../docs/DATA_CARD.md). The exact, deterministic sampler is
[`../tools/build_samples.py`](../tools/build_samples.py).

## Contents

```
data_samples/
├── neutro_head_tif/
│   ├── train_sample.csv               20 per source — base T/I/F soft targets
│   ├── v4_labeled_2of3_sample.csv     20 per polar bucket — final v4 masked 2-of-3 labels
│   ├── v4_narrative_sample.jsonl      v4 augmentation: TinyStories narration (¬D → T)
│   ├── v4_jailbreak_sample.jsonl      v4 augmentation: in-the-wild jailbreak frames (→ I)
│   └── v4_illocution_sample.csv       speech-act labels: D (Directive) / S (Subversion)
└── structured_energy/                 synthetic decorrelation corpora (the v4 head's syn_* sources)
    ├── intent_corpus_sample.jsonl     20 per intent type (T1..T6), LLM-generated
    ├── dom_advbenign_sample.jsonl     topic-decorrelation: adversarial-benign
    ├── dom_benignsensitive_sample.jsonl  topic-decorrelation: benign-sensitive
    ├── dom_subtleharm_sample.jsonl    topic-decorrelation: subtle-harm
    ├── cad_corpus_sample.jsonl        CAD minimal pairs (toggle one act/real/def axis)
    └── fusion_real_sample.jsonl       20 per type (carrier_benign/injected_harm/adversarial_benign)
```

The **final v2.1 head (v4)** is trained on the speech-act-aware corpus in `neutro_head_tif/`: the
base T/I/F pool, the 2-of-3 masked labels, the illocution (D/S) labels, and the narrative +
jailbreak augmentation. The `structured_energy/` corpora are the synthetic decorrelation sources
that enter the v4 corpus as `syn_*` (and were also the corpus for the optional v2.0 energy seam).

## Field reference

* **Head T/I/F** (`*.csv`): `text`, `source`, and the soft targets `T` (safe-to-comply),
  `I` (dilemma / latent threat / ambiguity), `F` (harmful) — **independent** values in `[0,1]`.
  `v4_labeled_2of3` adds `polar` and `mask_T/I/F` (the 2-of-3 mask); `v4_illocution` has `D`/`S`.
* **Augmentation / synthetic** (`*.jsonl`): `text`, `source`/`type`, and labels such as
  `polar_hint`, `harm_intent`, `benign_purpose`, plus metadata (`topic`, `toggled_axis`,
  `pair_id`, …). These preserve each item's provenance verbatim.

> Safety note: by design these samples include prompts about harmful topics — they are
> safety-training data. They are short, labeled, and illustrative; handle accordingly.
