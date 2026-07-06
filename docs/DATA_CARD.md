# Data Card

This package redistributes **only a small, illustrative ~20-per-type sample** of each training
corpus, never the full corpora. Samples are provided so reviewers can see the exact format and
labeling of every training input and trace its provenance. This section documents what each
sample is, where the full data comes from, how to regenerate it, and the licensing position.

> **Harmful prompts in the samples are redacted.** The training corpora include attack/harmful
> requests (jailbreaks, direct-harm and subtle-harm intents). In the shipped samples the
> free-text of any harmful item — an item carrying a harm label (`harm_intent=1`), a jailbreak
> item, or a high-falsity (`F ≥ 0.5`) T/I/F item — is replaced with a length-annotated marker
> (`[REDACTED: harmful content, N chars]`); every label, type, and metadata column is kept, and
> benign / adversarial-benign / narrative / dilemma samples are kept verbatim. The full text is
> regenerable from the original sources (see [`REGENERATE_CHECKPOINTS.md`](REGENERATE_CHECKPOINTS.md)).
> Re-apply with `python tools/reredact_data_samples.py`.

## What ships, and what does not

| Data | Ships here | Why |
|---|---|---|
| ~20-per-type training samples | ✅ `data_samples/` | small, illustrative, fully attributed |
| Full LLM-judge-labeled training corpora | ❌ | size + derived from third-party datasets — regenerate via [`REGENERATE_CHECKPOINTS.md`](REGENERATE_CHECKPOINTS.md) |
| Evaluation benchmarks (HarmBench, XSTest, Taxonomy, Ethics, Morables, GGB) | ❌ (harmful prompts) | third-party licenses; the *harmful* prompts are not redistributed — fetch from origin (see below) |
| Trained checkpoints | ✅ `checkpoints/` | finished v2.1 weights (≈ 0.22 M params, < 1 MB) + gate θ + SHA-256 manifest; also rebuildable via [`REGENERATE_CHECKPOINTS.md`](REGENERATE_CHECKPOINTS.md) |
| Final canonical experiment results (aggregated) | ✅ `results/` (per-arm metrics) | scored numbers behind the paper's tables |
| Full per-item result sheets | ✅ `results/per_item/` (harm-redacted) | every prompt/response/signal/verdict/score per item, **with harmful content intentionally removed** (trace-preserving; benign refusals kept) so scoring is auditable item-by-item — see [`../results/per_item/README.md`](../results/per_item/README.md) |

## Sampling method

`tools/build_samples.py` is the exact, deterministic script that produced `data_samples/`
(`SEED = 20260627`, ~20 items per type). It groups each corpus by its type field, shuffles with a
fixed seed, and takes the first ~20 of each group. Every original field — including provenance
(`source`), labels (`T/I/F`, `harm_intent`, axes), and generation metadata — is preserved
verbatim. To re-sample (e.g. a different N or seed) against a local PEAOS checkout:

```bash
python tools/build_samples.py /path/to/PEAOS data_samples
```

## Sample inventory

### `data_samples/neutro_head_tif/` — Neutro Head v4 (the final head)

| File | Rows | Grouped by | Notes |
|---|---|---|---|
| `train_sample.csv` | ~300 | `source` (15 datasets) | base `text, source, T, I, F`; soft targets in `[0,1]` |
| `v4_labeled_2of3_sample.csv` | ~40 | `polar` | final v4 masked 2-of-3 labels (`mask_T/I/F`) |
| `v4_narrative_sample.jsonl` | 20 | `source=narrative` | TinyStories narration augmentation (¬D → polar_hint T) |
| `v4_jailbreak_sample.jsonl` | 20 | `source=jailbreak` | in-the-wild jailbreak frames (→ polar_hint I) |
| `v4_illocution_sample.csv` | ~60 | `D` | speech-act labels: D (Directive force), S (Subversion) |

Provenance of the underlying sources (full list and HF repos in
[`REGENERATE_CHECKPOINTS.md`](REGENERATE_CHECKPOINTS.md) §2.1–§2.2b): `Anthropic/hh-rlhf`,
`PKU-Alignment/BeaverTails`, `LibrAI/do-not-answer` (held out), `tatsu-lab/alpaca`,
`databricks/databricks-dolly-15k`, ToxicChat, daily/moral/classical dilemma sets, ETHICS,
curated `trick_safe` / `benign_harm_discuss`, plus the v4 augmentation `roneneldan/TinyStories`
(narrative) and `TrustAIRLab/in-the-wild-jailbreak-prompts` (jailbreak). Final labels are
LLM-judge soft targets (2-of-3 + illocution); source labels are kept only as an audit prior.

### `data_samples/structured_energy/` — synthetic decorrelation corpora (`syn_*` head sources)

| File | Rows | Grouped by | Notes |
|---|---|---|---|
| `intent_corpus_sample.jsonl` | 120 | `type` (T1–T6) | LLM-generated (`llm:qwen3:32b`); intent typology |
| `dom_advbenign_sample.jsonl` | 20 | (one type) | topic-decorrelation: adversarial-benign |
| `dom_benignsensitive_sample.jsonl` | 20 | (one type) | topic-decorrelation: benign-sensitive |
| `dom_subtleharm_sample.jsonl` | 20 | (one type) | topic-decorrelation: subtle-harm |
| `cad_corpus_sample.jsonl` | ~24 | `toggled_axis` (act/real/def) | minimal pairs toggling one threat axis |
| `fusion_real_sample.jsonl` | 60 | `type` | carrier_benign / injected_harm / adversarial_benign |

These LLM-generated synthetic corpora enter the **v4 head** corpus as the `syn_*` decorrelation
sources (and were also the training corpus for the optional v2.0 energy seam). They are
**independent of the evaluation benchmarks** (non-contamination invariant #1) and largely
LLM-generated, so they carry minimal third-party copyright. Regenerate them with
`peinn_v2/corpus/*.py`.

## Evaluation benchmarks (not redistributed)

The held-out benchmarks are fetched from their original distributions by the helper scripts in
`src/scripts/` — e.g. `fetch_benchmark_data.py`, `fetch_ggb_morables.py` — into
`src/pea_eval/data/`. Consult and comply with each benchmark's own license. These datasets are
used for **evaluation only** and never enter training.

## Licensing

* **Code** (`src/`, `tools/`): MIT — see [`../LICENSE`](../LICENSE).
* **Data and materials original to this work** — the trained checkpoints (`checkpoints/`) and the
  gate-threshold config, the LLM-generated training-data samples in `data_samples/` (intent /
  domain / CAD / fusion), the judge prompts, and the result sheets / per-run values behind the
  paper's figures and tables (`results/`): **CC BY 4.0** — see [`../DATA_LICENSE`](../DATA_LICENSE).
* **Samples derived from third-party datasets** (the Neutro Head source pool) remain under their
  respective upstream licenses; we redistribute only a small illustrative sample under
  fair-use/research terms, with provenance preserved. If you are an upstream rights-holder and
  want a sample removed, please open an issue.
* **Trained checkpoints** (Neutro Head v4, energy calibrator, affect read-out; ≈ 0.22 M params,
  < 1 MB) **are shipped** under [`../checkpoints/`](../checkpoints/), under CC BY 4.0.
* **Patents.** CC BY 4.0 does not grant patent rights (see `DATA_LICENSE`, Section 2(b)); the
  release of this code or data grants no patent licence.

## Privacy / safety

The samples contain prompts about harmful topics by design (they are safety-training data). They
are short, illustrative, and labeled; none contain operational harm content beyond what is needed
to characterize the input distribution. Handle accordingly.
