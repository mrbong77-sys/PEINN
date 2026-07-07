# Regenerating the Checkpoints

The finished checkpoints — the **Neutro Head** (T/I/F), the affect read-out, and the **Emotion
Engine** energy calibrator — are shipped under [`../checkpoints/`](../checkpoints/) (≈ 0.22 M
parameters, < 1 MB total). This guide is for readers who would rather reconstruct each one from
scratch than use the shipped weights: it rebuilds them, plus the supporting learned components,
so an independent reader can obtain functionally identical models.

> **Conventions.** All commands run from the `src/` directory with `PYTHONPATH` pointing at it:
> ```bash
> cd src && export PYTHONPATH="$PWD:$PYTHONPATH"
> ```
> Output paths below are relative to `src/`. Trained artifacts land in `src/pea_eval/data/`
> (heads) or `src/peinn_v2/encoder/` (energy). A CUDA GPU is assumed for real runs.
>
> **Determinism.** Set `PYTHONHASHSEED=0` and pass the `--seed` flag where a script exposes it.
> LLM-judge labeling is the one stochastic step: use a **temperature-0 / greedy** judge and pin
> the judge model + version so labels are reproducible. We used **`qwen3:32b`** as the judge
> (originally `gemma4:26b`, later unified to `qwen3:32b`); any capable instruction model with a
> deterministic decode will reproduce the labels closely.

---

## Prerequisites

* Python ≥ 3.10, `pip install -r ../requirements.txt`.
* A CUDA GPU (24 GB is comfortable; the heads themselves are tiny — the cost is the frozen
  backbones and the judge LLM).
* An **OpenAI-compatible LLM endpoint** for the offline labeling steps. We used a local
  [Ollama](https://ollama.com) server; set `OPENAI_BASE_URL`/`OPENAI_API_KEY` (or the
  `config/` settings) to point at it. The judge LLM is used **offline only**, to label training
  data — never at inference.
* For the structured-threat encoder: `transformers` + a one-time download of
  `microsoft/deberta-v3-base`.

The held-out **evaluation** benchmarks (HarmBench, XSTest, Taxonomy, Ethics, Morables, GGB) are
fetched separately and are **never** training inputs — see [`DATA_CARD.md`](DATA_CARD.md).

---

## §1. Emotion Engine — the base 64 MB network

**What it is.** A frozen affective feature extractor: an MLP trunk
(`h ∈ ℝ²⁵⁶`) → a 32-D emotion head (`Tₑ = 4.0`) and a scalar-energy head (`T_E = 2.0`).
Architecture and the 32-dimension taxonomy are fully specified in
`src/core/emotion_engine.py` and the inline spec it references. Hard constraints: **≤ 15 M
parameters, ≤ 64 MB** in float32, enforced at construction by
`core.utils.check_model_constraints`.

**Note on the base trunk.** The runtime uses the Emotion Engine
as a *frozen feature stage* and does not require a separately trained trunk checkpoint. For reproducing the paper's
**routing** results, what matters is that the EE is consumed as a *frozen* feature extractor —
so you can either (a) train an equivalent trunk with the regime below, or (b) treat the EE as a
fixed embedding stage and focus on the learned heads in §2–§4, which is where PEINN's routing
behavior is determined.

**(a) Rebuild an equivalent trunk.**

1. **Instantiate and verify the architecture** (no training needed to check the spec):
   ```python
   from core.emotion_engine import build_emotion_engine
   from pea_eval.config.settings import load_settings
   ee = build_emotion_engine(load_settings().ee)   # raises if >15M params or >64MB
   ```
2. **Freeze the Golden Anchors.** The 35 principle tensors in `core/golden_anchors.py` are
   `requires_grad=False` and must stay frozen through every training step (the "constant mind"
   invariant). `core/golden_anchors_reverse.py` holds the anti-principle anchors used only for
   analysis.
3. **Train the trunk** *(optional — not included in this repo)*: a
   reflection loop scored each generated stance against the frozen anchors and updated only the
   trunk + the two output heads, with the temperature scaling above applied at read time, keeping
   the ≤ 15 M-param / ≤ 64 MB constraint throughout.
4. **Skip or save.** The runtime uses the Emotion Engine as a *frozen feature stage* and does not
   require a separately trained trunk checkpoint, so most reproducers can skip trunk training and go straight
   to the learned heads in §2–§4, which is where PEINN's routing behavior is determined.

**(b) Use the EE as a fixed stage.** If you only need to reproduce routing, instantiate the EE
once, load any constraint-satisfying checkpoint, and proceed to §2 — the Neutro Head and the
routing energy are what determine PEINN's decisions, and both are fully reproducible here.

**Verify.** `count_parameters(ee) ≤ 15_000_000` and `model_size_mb(ee) ≤ 64`. A forward pass on
a benign vs. an operational-harm prompt should yield a clearly higher scalar energy `E` for the
latter.

---

## §2. Neutro Head — T/I/F (the core new discriminator)

Three independent sigmoids on top of the **frozen** EE features. Pipeline: gather an
independent corpus → relabel every item with an LLM judge into independent T/I/F soft targets →
train the head → tune the routing gate. **No evaluation benchmark is used for training.**

### 2.1 Gather the candidate corpus

The loaders in `scripts/eval_ee_ood.py` pull a broad, topic-agnostic pool of public
harm/safe/dilemma data via Hugging Face `datasets` and a few raw CSVs:

| Source tag | Origin | Role |
|---|---|---|
| `hh_rlhf` | `Anthropic/hh-rlhf` (red-team = harm; harmless/helpful = safe) | general harm/safe dialogue |
| `beavertails` | `PKU-Alignment/BeaverTails` (`30k_train`) | general harm |
| `do_not_answer` | `LibrAI/do-not-answer` | harm probe — **100 % held out** |
| `alpaca` | `tatsu-lab/alpaca` | general benign instructions |
| `dolly` | `databricks/databricks-dolly-15k` | general benign instructions |
| `toxicchat_safe` | ToxicChat (safe split) | benign-but-edgy |
| `daily_dilemmas`, `moralchoice_highamb`, `classical_dilemma` | dilemma datasets | **I-class** exemplars |
| `ethics`, `taxonomy`, `benign_harm_discuss`, `trick_safe` | ethics + curated | calibration |

Sample shapes (20 per source) are in
[`../data_samples/neutro_head_tif/train_sample.csv`](../data_samples/neutro_head_tif/train_sample.csv).

### 2.2 Relabel with an LLM judge → independent T/I/F soft targets

```bash
python scripts/label_ee_3class.py --max-per-source 600
# → pea_eval/data/ee_3class/judge_labeled_<timestamp>.csv  (text, source, harmful, safe, dilemma; each 0–5)
```

The judge scores **three axes independently** (non-exclusive, neutrosophic-faithful):

* **harmful (→ F)** — real-world harm from *directly complying with the requested act*. The
  rubric scores the **ACT, not the topic**: explaining/analyzing/opposing/preventing a harmful
  topic is `harmful = 0–1`; only operational aid is `harmful ≥ 3`. Homonyms ("kill a process"),
  in-game actions, idioms, fictional-character privacy, and historical analysis are calibrated
  as benign.
* **safe (→ T)** — how acceptable a direct answer is.
* **dilemma (→ I)** — a *genuine* value conflict (the "third answer"); mere sensitivity is not a
  dilemma. Classic philosophical dilemmas (trolley / Heinz / Kohlberg) are `dilemma = 5`.

Source labels are kept only as an **audit prior** (flag judge↔source disagreement); the judge
score is the ground truth. The rubric references **no benchmark answer key**. Normalize the
0–5 scores to `[0,1]` and split into `pea_eval/data/ee_3class/{train,heldout}.csv` with columns
`text, source, T, I, F`. Keep `do_not_answer` and all of XSTest out of `train.csv`.

The base T/I/F labeling above produces the initial labels. The **PEINN head** is the *speech-act-aware
v4 head* — continue with §2.2b.

### 2.2b Speech-act-aware v4 labeling (the PEINN head)

The PEINN head replaces "score all three axes at once" with a 2-of-3 + illocution pipeline
(see [`PEINN_v2.1.md`](PEINN_v2.1.md) §4.1):

```bash
# 1) 2-of-3 judge labels — score only {T,I} or {F,I} per item (0–5), I always scored
python scripts/label_ee_3class_v3.py
# 2) soft-impute the unscored polarity (label smoothing U[0,0.2]) for full supervision
python scripts/fill_neutro_v3_offpolar.py
# 3) illocution: a single-focus judge pass scores Directive force (D) and Subversion/jailbreak (S)
python scripts/label_illocution.py
# 4) synthesis: v3 labels ⊗ illocution → corrected 2-of-3 T/I/F  (¬D∧low-harm→T, D∧S→high I, D∧harm→F)
python scripts/derive_tif_v4.py
# 5) corpus augmentation: narrative (TinyStories, ¬D→T) + jailbreak (in-the-wild, →I), decontaminated
python scripts/build_neutro_v4_corpus.py --narrative-cap 1200 --jailbreak-cap 800
# → pea_eval/data/ee_3class/v4/{train.csv, labeled_2of3.csv, illocution_labels.csv, corpus_unlabeled.jsonl}
```
The narrative/jailbreak augmentation and every source pass through the **ProvenanceGuard**
(`pea_eval/pge/provenance_guard.py`) so no benchmark text leaks in. Samples:
[`../data_samples/neutro_head_tif/v4_labeled_2of3_sample.csv`](../data_samples/neutro_head_tif/v4_labeled_2of3_sample.csv)
and the v4-corpus samples under [`../data_samples/structured_energy/`](../data_samples/structured_energy/).

### 2.3 Train the head

```bash
python scripts/train_neutro_head.py        # masked soft-label training on the v4 corpus
# → pea_eval/data/ee_neutro_head_v4.pt   (the checkpoint loaded by run_v21_bench.py)
```

Features are extracted **once** via `intent_router.neutro_feature_vector` /
`ee_runner.neutro_features` over the **frozen** EE — `[emotion32 ⊕ semantic_emb(384) ⊕
principle_emb(384)] = 800-D` (the energy is **not** in the head) — and cached to
`neutro_feats_<split>.npz` (keyed by a content fingerprint, so it recomputes when the corpus
changes). The head `Linear(800→128)→ReLU→Dropout→3×[Linear→Sigmoid]` is trained with a **masked
soft-target loss**. Validation is **held-out judge reproducibility** (measured T/I/F AUC ≈ 0.93 /
0.95 / 0.95).

### 2.4 The routing gate is already locked

PEINN **locks** the operating point in `NeutroEERouterV21.THETA`
(`extreme 9.4, harm 8.5, F 0.15, I 0.45, Fref 0.30, soft 8.5, Fblk 0.45`) — fit on the independent
corpus and frozen. To reproduce that fit, `scripts/tune_neutro_gate.py` reads a routing-signal CSV
(`bench, subset, T, I, F, e1`), fits θ on the corpus split, and evaluates on the six held-out
benchmarks — never tuned on the benchmarks.

**Verify.** Held-out F-dimension AUC clearly exceeds chance; the dilemma set routes mostly to
**Deliberation**, and the harm set to **Reasoned-Refusal** / **Hard-block**.

---

## §3. Emotion-Engine energy (the PEINN routing energy)

The PEINN routing energy `e1` is the **frozen `HybridCalibrator`** (`emotion32 ⊕ semantic →
harm prob × 10`, range 0–10) — it is reused frozen (see
[`PEINN_v2.1.md`](PEINN_v2.1.md) §4.2). If you need to rebuild the calibrator checkpoint:

```bash
python -m pea_eval.optimizer.ee_threshold_finder    # trains HybridCalibrator → ee_hybrid_calibrator_best.pt
```
The calibrator is a small head over `[emotion32 ⊕ semantic]` trained with class-weighted BCE; the
architecture mirrors `ee_runner.HybridCalibrator` so the checkpoint loads on both sides. Its role
is the head-independent **override for definite harm** and the **target of the head-F
veto**; the head reads meaning/speech-act, the energy reads affect intensity, and the AND-gate
(`NeutroEERouterV21`, §2.4) combines them.

> **Optional — the DeBERTa "structured-threat energy" module.** `src/peinn_v2/` is an
> encoder-only experimental energy (`text → DeBERTa-v3-base → act × real × def → E_struct`) that
> can be swapped in via `PEINN_V2_ENERGY=1`. **It is not the routing energy** and is off by
> default. To experiment with it: regenerate its corpus (`python -m peinn_v2.corpus.llm_gen`,
> `python -m peinn_v2.corpus.cad_generator`, …), then `python -m peinn_v2.train.train --backbone hf
> --model-name microsoft/deberta-v3-base --out peinn_v2/encoder/ckpt.pt` (CPU smoke:
> `python -m peinn_v2.train.train --smoke`). See `src/peinn_v2/README.md`.

---

## §4. Emotion read-out (32-D, analysis only — not on the routing path)

Used for the paper's interpretability figures, **not** for routing decisions.

```bash
python scripts/label_ee_emotion.py            # judge → 32-D emotion-intensity targets
python scripts/train_ee_emotion_readout.py --labeled auto --feature ee_hidden
# → pea_eval/data/ee_emotion_readout_ee_hidden.pt  + a per-dimension MAE/AUC report
```
A frequency-inverse weighted loss (after Kratzwald et al., *Decision Support Systems* 115:24–35,
2018, §3.3.3) keeps low-activation emotion dimensions from being washed out. `--feature embedding`
uses a clean MiniLM encoder instead of the frozen EE hidden state.

---

## Checkpoint inventory

| Artifact | Built by | Default path (under `src/`) | Loaded by |
|---|---|---|---|
| Emotion Engine trunk | §1 (rebuild or fixed stage) | per `config/` | EE feature extraction |
| `ee_neutro_head_v4.pt` | §2.3 `train_neutro_head.py` | `pea_eval/data/` | `intent_router` (PEINN routing) |
| `ee_hybrid_calibrator_best.pt` | §3 `ee_threshold_finder.py` | `pea_eval/data/` | `ee_runner` energy (e1) |
| `ee_emotion_readout_*.pt` | §4 `train_ee_emotion_readout.py` | `pea_eval/data/` | analysis figures only |
| (optional) `peinn_v2/encoder/ckpt.pt` | §3 note `peinn_v2.train.train` | `peinn_v2/encoder/` | `PEINN_V2_ENERGY` module (off by default) |

Once the v4 head (§2) and the EE feature/energy stage (§1, §3) are in place, the PEINN routing
module is complete and the benchmark drivers in [`REPRODUCTION.md`](REPRODUCTION.md) §4 will
exercise it.
