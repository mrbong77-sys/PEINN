# S0 — Independent Training Corpus Design

How we build the data that teaches the structured-threat encoder its three axes
**topic-invariantly, without the eval benchmarks (D4) and without any LLM (D3)**.
Implements the labeling protocol in `CAD_SCHEMA.md`.

---

## 0. The load-bearing insight (safety + transfer in one move)

We do **NOT** generate operational harmful content. The encoder learns the **structure**
(actionability × realizability × definiteness) on **benign and sensitive-but-non-operational**
topics; **topic-invariance (IRM + CAD, D5) carries it to harmful topics**, which appear
**only at evaluation**. This is simultaneously:
- the **safety posture** — no harmful procedures are ever written or memorized;
- the **central hypothesis** — if the structure is truly topic-invariant, a structurally
  HIGH request on a never-seen harmful topic scores high by structure alone; a high-affect
  benign request scores low by structure alone. S1/S4 measure whether this holds.

**Corollary (critical):** harmful-operational topics must NOT appear on the *low* side either —
otherwise the model learns "harmful topic → low threat." The clean resolution: harmful-
operational topics are **entirely absent from training** (eval-only). Sensitive topics that
*can* be benign-realizable (e.g. "safely store a hunting rifle", defensive security concepts)
**do** appear on both HIGH and LOW sides — these break the "sensitive word → block" shortcut.

---

## 1. Data tiers

| Tier | Purpose | Source | LLM? | Benchmark? |
|---|---|---|---|---|
| **T1 — structural pretraining** | give the heads a head-start on the *markers* (directive/modality/hedge) on general-domain text | public linguistic corpora: SwDA/DAMSL (dialogue acts → actionability), OnlpLab Modality (Pyatkin ACL-2021 → realizability/definiteness), CoNLL-2010 hedging (→ definiteness) | no | **no** (these are general NLP corpora, *not* AI-safety eval sets; D4 forbids only the held-out evaluation benchmarks: XSTest/HarmBench/Taxonomy/Ethics/Morables/GGB) |
| **T2 — synthetic CAD pairs** | the core: minimal pairs that flip one axis with topic held fixed; guarantees topic⟂label & affect⟂label by construction | our **procedural template generator** (below) | no | no |
| **T3 — human seed/dev** | naturalness + hard cases + a human-authored held-out dev set | human-authored | no | no |

T2 is the bulk and the heart. T1 is optional warm-start. T3 keeps T2 honest.

---

## 2. Topic pool (the held-fixed variable / IRM environments)

- **Composition:** benign topics (cooking, assembly, software, gardening, travel, admin…) +
  **sensitive-non-operational** topics that can be benign-realizable (lawful firearm storage,
  defensive cybersecurity, medication adherence, chemistry-in-general-education). **No
  harmful-operational topics. No benchmark prompts.**
- **Representation:** each topic is an abstract *action-frame* `{domain, object, neutral-verb}`,
  not a copied sentence — the generator renders surface text from the frame.
- **Each topic = one IRM environment** (`topic_id`). Target ~200–500 frames across ≥15 domains
  so topic cannot proxy the label.
- **Provenance manifest:** every frame tagged with its origin; a build-time list proves the
  pool is independent of the benchmarks.

---

## 3. The procedural CAD generator (LLM-free, deterministic)

A slot grammar renders, **per topic frame**, a set of minimal pairs. Markers come from small
**public lexicons**, never an LLM:

- **Actionability** toggle — illocution slot:
  - HIGH: `{imperative_verb} {procedure_ref(topic)}` ("Give me step-by-step instructions to …")
  - LOW:  `How/why does {topic} {happen}?` / `What is {topic}?` (assertive/interrogative-about)
  - lexicons: imperative/action-verb list; interrogative-about frames.
- **Realizability** toggle — means-completeness slot (both sides may be directive):
  - HIGH: procedure filled with `{ordered_steps + quantities + named_tools}`
  - LOW:  procedure filled with `{vague_gesture}` ("somehow", missing params)
  - lexicons: completeness fillers vs vagueness markers. (Benign topics only → safe to write.)
- **Definiteness** toggle — commitment slot:
  - HIGH: `{commissive} {future_agency} {named target/time/method}` ("I will … at 9 a.m. …")
  - LOW:  `{conditional}{hedge}{hypothetical}` ("maybe someone could possibly … if …")
  - lexicons: commissive/future markers; **hedge lexicon from CoNLL-2010**; the
    target/time/method "direct-threat tetrad" slots.

**Minimal-pair guarantee:** the generator changes **only the toggled slot** between a pair;
all other slots (topic, the two non-toggled axes, affect) are byte-identical. `pair_id` links them.

---

## 4. Orthogonality enforcement (the two discipline rules, by construction)

- **Topic ⟂ label (rule 2):** generate a **balanced factorial grid** — every topic frame is
  rendered at every axis combination, so each `topic_id` carries the full HIGH/LOW range of
  every axis. Topic has **zero** marginal correlation with any axis label by design. IRM uses
  `topic_id` as the environment to penalize any residual topic-dependence.
- **Affect ⟂ label (rule 3):** an independent **affect slot** decorates each item as
  `neutral` or `high-affect` (emotional framing), sampled **independently** of the axis labels
  → high-affect appears equally on HIGH- and LOW-threat items. Affect words from a **public
  emotion/VAD lexicon (e.g. NRC-VAD / NRC-EmoLex)** — no LLM. This is the direct antidote to
  the over-fire (affective stance ≠ commitment).

---

## 5. Record schema (JSONL)

```json
{
  "id": "t2_000123_hi",
  "text": "...",
  "topic_id": "kitchen.sourdough",        // IRM environment
  "domain": "cooking",
  "act": 1, "real": 1, "def": 0,           // per-axis labels {0,1}
  "affect": 1,                              // affect decoration, ⟂ labels
  "pair_id": "t2_000123",                   // links the minimal pair
  "toggled_axis": "def",                    // which axis differs across the pair
  "source": "template"                      // template | human | swda | modality | conll
}
```

---

## 6. Benchmark-independence gate (operationalizes D4)

A **build-time contamination check**: reject any generated/seed text whose n-gram overlap
with the held-out benchmark prompts (XSTest/HarmBench/Taxonomy/Ethics/Morables/GGB) exceeds a low threshold,
and assert the topic pool shares no frame with benchmark categories. The check runs in CI for
the corpus build and its report is committed alongside the data. (Benchmarks are read here only
to *exclude* overlap — never as labels.)

---

## 7. Size & pilot plan

- **Pilot (first build):** ~30 topic frames × 3 axes × (HIGH/LOW) × 2 affect, fully factorial
  → a few thousand labeled pairs. Enough to (a) train the 3 heads, (b) sanity-check
  topic-invariance on held-out topic frames, (c) dry-run the encoder pipeline.
- **Scale:** expand topic frames to 200–500 and add T3 human cases once the pilot validates
  the generator + invariance.
- **Held-out splits:** split by **topic** (unseen-topic dev/test) to measure topic-invariant
  generalization — the metric that matters, mirroring the eventual benchmark transfer.

---

## 8. Risks / open items

- **Template naturalness:** procedural text may be stylized → distribution gap vs real prompts.
  Mitigate with T3 human seeds + style variation slots; validate on T3 dev.
- **Transfer assumption:** benign-trained structure → harmful-topic eval is the core bet; if
  S1 shows the multivariate gate already strong (scenario 1) the bar is lower; either way
  S4 measures it on the real benchmarks.
- **T1 licensing:** SwDA is LDC-licensed; OnlpLab Modality & CoNLL-2010 are open. T1 is
  optional warm-start, so licensing is not blocking.
- **Lexicon coverage:** hedge/commissive/imperative lexicons must be broad enough to avoid the
  generator itself becoming a keyword tell — randomize and diversify markers.
