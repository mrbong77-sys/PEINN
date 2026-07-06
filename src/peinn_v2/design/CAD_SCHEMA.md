# S0 — Axis Minimal-Pair (CAD) Labeling Schema

The labeling protocol for PEINN v2.0's independent training corpus. It defines, for each of
the three threat axes, the **minimal edit that flips ONLY that axis** while holding the
**topic/subject constant** — so the encoder must key on *structure*, not topic keywords or
affect (D5/D6; grounded in `../research/STRUCTURED_THREAT_AXES.md`).

> Method: Counterfactually-Augmented Data (Kaushik, Hovy & Lipton, ICLR-2020). "Edits that are
> not necessary to flip the applicable label are prohibited." Topic is the held-fixed variable;
> the axis is the flipped variable. Each topic becomes an IRM *environment*.

---

## 0. Core rules (apply to every pair)

1. **One axis per pair.** A pair flips exactly one axis; the other two axes **and the topic**
   are held constant. (Independent control of each axis = the whole point.)
2. **Topic ⟂ label.** Across the corpus, each axis label must be **uncorrelated with topic**.
   Every topic appears with BOTH the high and low value of each axis. (Prevents the
   keyword-overfit failure, E1/D4; enforced as IRM environments at train time.)
3. **Affect ⟂ label.** Affect intensity must **not** correlate with any axis label. Include
   *high-affect / low-threat* and *low-affect / high-threat* items. (Directly fixes the
   over-fire: affective stance ≠ commitment — Gales; hunter≠howler.)
4. **Topics are NOT drawn from the eval benchmarks** (D4). Use an independent topic pool
   spanning benign, sensitive, and harmful subjects; structure — not subject — carries the label.
5. **Minimal edit.** Change only the markers that carry the axis; keep length/register/topic
   words otherwise identical.

Labels are per-axis ordinal `{0 = low, 1 = high}` for pairs (heads may train as regression /
ordinal later). The threat **energy** is a calibrated, gated combination of the three axis
scores + an imminence overlay (D6) — NOT defined here; this schema only labels the axes.

---

## 1. Axis A — ACTIONABILITY  (demand for / description of an executable procedure)

| | HIGH (1) | LOW (0) |
|---|---|---|
| **Definition** | requests/【supplies】 an executable procedure — "do X", "how to do X step by step" | discusses/asks-about the phenomenon — "how/why does X happen", "what is X" |
| **Illocution** | **directive / imperative** (Searle directive) | **assertive / interrogative-about** |
| **Markers** | imperative mood, 2nd-person procedure request, action verbs, "step-by-step / instructions / how do I" | nominalization, past/generic tense, explanatory "how does it work / why / what causes" |
| **Edit operator** | rewrite directive ⇄ descriptive, holding topic noun fixed |
| **Grounding** | pathway = research/planning/implementation; "making ≠ posing"; Actionable Phrase Detection (imperative + action-verb); DAMSL Action-directive |

**Minimal pair (benign topic = bookshelf assembly, held fixed):**
- HIGH: *"Give me step-by-step instructions to assemble this bookshelf."*
- LOW:  *"How are flat-pack bookshelves usually assembled in factories?"*

The harmful/benign judgment is NOT here — actionability is topic-blind. A harmful topic in
LOW (assertive/educational) form is low-actionability; a benign topic in HIGH form is
high-actionability. The energy combines axes; actionability alone never decides.

---

## 2. Axis B — REALIZABILITY  (feasibility: concrete, sufficient means/steps present)

| | HIGH (1) | LOW (0) |
|---|---|---|
| **Definition** | the content provides/【presupposes】 the **actual executable means** — complete, ordered, specific (materials, parameters, sequence) | abstract / gestural — names an aim but lacks the means; missing steps, vague parameters |
| **Markers** | concrete quantities, named tools/materials, ordered steps, specific parameters, completeness | "somehow", "some way", missing quantities, unordered, hand-wavy |
| **Edit operator** | add/remove operational completeness & specificity of MEANS, holding actionability + topic fixed |
| **Grounding** | capability leg (DHS Threat = intent × capability); ISO/IEC 18045 attack-potential (time/expertise/knowledge/opportunity/equipment); Sandia chained-conditional completeness; feasibility-modality (Pyatkin ACL-2021) |

**Minimal pair (benign topic = sourdough bread, both directive — only realizability flips):**
- HIGH: *"Mix 500 g flour, 350 g water, 100 g starter, 10 g salt; autolyse 1 h, fold every 30 min ×4, proof 4 h at 24 °C, bake 20 min covered at 245 °C then 25 min uncovered."*
- LOW:  *"Somehow combine flour and water with some starter and bake it until it's bread."*

Realizability ⟂ actionability: both above are directive (HIGH actionability); they differ only
in whether the executable means are actually supplied.

---

## 3. Axis C — DEFINITENESS  (specificity + commitment + fixed, directed intent)

| | HIGH (1) | LOW (0) |
|---|---|---|
| **Definition** | committed, unconditional, **first-person future agency**; named **target / time / method** | hedged, conditional, speculative, abstract; no named target/time |
| **Markers** | **commissive** ("I will"), future tense + agency, low hedging, named target/time/place/method (the direct-threat tetrad) | conditionals ("if…then maybe"), hedges ("possibly/might"), 3rd-person hypotheticals ("what if someone…") |
| **Edit operator** | toggle commitment & specificity markers, holding topic + actionability fixed |
| **Grounding** | true-threat "serious expression of intent" (Virginia v. Black) + recklessness floor (Counterman); conditionality LOWERS it (Watts); target/time/mode/method tetrad (Gales); commissive (Searle); hedging (CoNLL-2010); fixation/leakage (Meloy) |
| **⚠ Caveat** | do **NOT** toggle definiteness via emotional intensity — affective stance ≠ commitment. Toggle epistemic/commissive commitment only. |

**Minimal pair (neutral topic = meeting a colleague, held fixed):**
- HIGH: *"I will be at the north entrance at 9 a.m. tomorrow to hand him the documents."*
- LOW:  *"Maybe someone could possibly meet him around there sometime, if it works out."*

---

## 4. How the axes compose (preview — not labeled here)

A genuinely dangerous request is HIGH on **all three** (actionable ∧ realizable ∧ definite) —
the multiplicative-gated combiner (D6). The over-refusal cases this fixes:
- high-affect benign (venting / distress) → LOW actionability, LOW definiteness → low energy;
- educational/discussion of a harmful topic → LOW actionability (assertive) → low energy;
- vague "what if" on a harmful topic → LOW definiteness / LOW realizability → low energy.

So no single axis — and crucially no topic keyword or affect spike — can drive the energy.

---

## 5. Open items for the next S0 step (corpus design)

- topic pool sourcing (independent of benchmarks) + size/diversity targets;
- pair-generation method: rule/template procedural generation vs human authoring (both
  benchmark-free, LLM-free per D3/D4) — and how to guarantee rules 2–3 (topic ⟂ label,
  affect ⟂ label);
- mapping to existing labeled corpora that already isolate one axis (SwDA/DAMSL → actionability;
  OnlpLab Modality → realizability/definiteness; CoNLL-2010 → definiteness) for pretraining;
- per-axis label granularity (binary pairs vs ordinal severity).
