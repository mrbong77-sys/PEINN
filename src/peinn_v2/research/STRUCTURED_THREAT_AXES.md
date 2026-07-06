# Structured-Threat Energy — Research Benchmark & S0 Design Specification

Grounding PEINN's redesigned Emotion-Engine energy (from affect-amplification to a
**structured, topic-invariant threat judgment**) in established threat-detection literature.

> **Sourcing caveat.** This synthesizes 5 parallel web-research passes. `WebFetch` was
> HTTP-403 blocked environment-wide, so quotes come from search-engine extracts of the
> primary sources, not full-text PDF reads. Every load-bearing framework below was
> corroborated across ≥2 independent sources AND ≥2 research passes. **Verify verbatim
> quotes/statistics against the linked PDFs before any external publication.**

---

## 0. Why this matters for PEINN (the two diseases, now literature-explained)

1. **Over-fire on emotionally-charged benign (XSTest-style ORR).** The literature's
   *instrumental vs expressive* / *hunter vs howler* distinction (Meloy; Calhoun & Weston;
   forensic-linguistic stance analysis, Gales) is explicit: **high affective stance often
   marks venting, not intent.** PEINN's current energy *amplifies on affect* → it
   systematically mistakes howlers for hunters. This is a known, named error.

2. **`benign_detector` OOD collapse (train AUC 0.9989 → real-world leak); readout held-out
   ceiling ≈0.61.** This is the **keyword/topic-overfitting failure** documented as the
   central failure mode of abuse/threat classifiers: Wiegand et al. NAACL-2019 (sampling
   topic-bias), Swamy et al. 2019 (cross-dataset collapse), Röttger et al. HateCheck
   ACL-2021 (models encode "keyword-based decision rules"). Training on benchmark content
   = learning topic, not structure → collapses OOD. **This is exactly why benchmarks must
   stay held-out and why the encoder must learn topic-invariant structure.**

The fix the whole field converged on: **measure the topic-invariant ACTION structure;
de-weight belief/affect/topic content.** That is precisely the redesign.

---

## 1. The master frame — Threat = Intent × Capability × Opportunity

Both the counterterrorism and SIGINT/risk literatures decompose a *real* threat identically:

- **DHS Risk Lexicon (2010):** "the threat of an intentional hazard is generally estimated
  as the likelihood of an attack (that accounts for both the **intent and capability** of
  the adversary)…"; "**Intent is the probability an attack is desired, and capability is
  the probability it can be executed**." Adversary-vs-threat rule: "an adversary may have
  the intent, but not the capability… a threat possesses **both**." → multiplicative gating.
  [DHS Risk Lexicon — cisa.gov/sites/default/files/publications/dhs-risk-lexicon-2010_0.pdf]
- **Threat triad:** "In order for threat to exist, there must be a combination of intent,
  capability and opportunity." Removing any one leg mitigates the threat.
  [srmam.com/post/how-do-intent-and-capability-relate-to-assessing-threat]
- **Risk = Threat × Vulnerability × Consequence** (RAND MG388; FEMA). Threat aggregates
  intent+capability; Vulnerability ≈ feasibility/realizability; Consequence = severity.
  [RAND MG388 — rand.org/content/dam/rand/pubs/monographs/2005/RAND_MG388.pdf]

**→ PEINN crosswalk:** `intent → definiteness`, `capability → realizability`,
`opportunity/timing → imminence`. Energy = a calibrated combination of these — **gated**
(any leg ≈0 collapses the score), not affect-amplified.

> **Combiner caveat (National Academies, *Review of DHS Risk Analysis* 2010):** raw
> `T×V×C` "is not an adequate calculation tool… independence does not typically hold."
> Our axes correlate → use a **calibrated combiner** (weighted geometric mean / logistic),
> not a naive product. Axis weights via **AHP** (pairwise elicitation) rather than guesses.

---

## 2. The three axes — operational definitions grounded in the literature

### Axis A — ACTIONABILITY (demand for / description of an executable procedure)
The field's single strongest, most topic-invariant signal: *what the person is doing/asking
to do*, not what they say or believe.

- **"Making a threat" ≠ "posing a threat"** (USSS/Fein & Vossekuil): focus on those who
  *pose* a threat "whether or not they have made a threat"; a directly-communicated threat
  is the **weakest** predictor. [ojp.gov/pdffiles/threat.pdf]
- **Pathway to violence** (Calhoun & Weston): grievance → ideation → research/planning →
  preparation → breach → attack; "targeted violence is by definition planned, emotionless,
  predatory." **Hunters hunt and rarely howl.** [academic.oup.com/book/30016/chapter/255632094]
- **Meloy "pathway" warning behavior** = "any behavior that is part of research, planning,
  preparation, or implementation of an attack." [onlinelibrary.wiley.com/doi/10.1002/bsl.999]
- **McCauley & Moskalenko two-pyramids:** *action* pyramid ≠ *opinion* pyramid; "99% of
  those with radical ideas never act." [apa.org/pubs/journals/releases/amp-amp0000062.pdf]
- **NCTC/FBI/DHS Mobilization Indicators:** "Mobilization/Preparation" indicators are
  defined by *action + time-to-act*; only "Motivation" is belief-laden.
  [dni.gov/files/NCTC/documents/news_documents/NCTC-FBI-DHS-HVE-Mobilization-Indicators-Booklet-2019.pdf]

**Topic-invariant linguistic operationalization (encoder-implementable, no LLM):**
- Searle **directive** speech act; imperative mood + action verbs.
  [Actionable Phrase Detection — arxiv.org/abs/2210.16841]
- Dialogue-act `Action-directive` (DAMSL/SwDA, domain-independent).
  [Stolcke et al. — web.stanford.edu/~jurafsky/ws97/CL-dialog.pdf]
- Procedural/instructional "how-to" structure as a domain-orthogonal property.
  [Instructional-text survey — arxiv.org/abs/2410.18529]
- **Proof of encoder-only feasibility:** BERT + linear head detects "actionable" reports.
  [PMC8436473]

### Axis B — REALIZABILITY (feasibility / capability / opportunity)
- **Capability leg** (DHS) = "the probability it can be executed." Capability-acquisition
  is a first-class indicator everywhere: Grabo's indicator list (logistics, materiel,
  deployments — "things that would *have* to happen"); NCTC "weapons training / target
  research / acquiring blueprints"; CERT insider **technical precursors** (recon, access-
  mapping, staging/exfiltration, AV-disable/backdoor = circumvention).
  [Grabo, *Anticipating Surprise*; CERT SEI — sei.cmu.edu/documents/302/2012_019_001_52399.pdf]
- **ISO/IEC 18045 "attack potential"** rubric: point-sum over *elapsed time, expertise,
  knowledge, window of opportunity, equipment* → "basic"→"beyond-high" feasibility. A
  ready-made, interpretable realizability scale. [arxiv.org/abs/2307.02261]
- **Chained conditional success** (Sandia): a *complete ordered procedure* yields higher
  cumulative success probability than one with gaps → reward **step-completeness**.
  [osti.gov/servlets/purl/1264231]

**Operationalization:** feasibility-**modality** markers (Event-Based Modality, Pyatkin et
al. ACL-2021 — possible/plausible/feasible) + ISO-18045-style presupposed-means scoring +
step-completeness. [aclanthology.org/2021.acl-long.77/]

### Axis C — DEFINITENESS (specificity + commitment + fixed intent)
- **True-threat doctrine:** a "serious expression of an intent to commit… unlawful
  violence to a particular individual or group" (*Virginia v. Black* 2003) + speaker
  **recklessness** floor (*Counterman v. Colorado* 2023). [supreme.justia.com/cases/federal/us/538/343/]
- **Conditionality LOWERS definiteness:** *Watts v. United States* — "expressly conditional"
  + jocular context = hyperbole, not a true threat. [michiganlawreview.org/.../searching-for-truth...]
- **Direct-threat tetrad** (forensic linguistics, Gales): direct threats "identify the
  **target, time, mode, and method**"; realized threats are "serious… direct, specific,
  detailed," non-realized are "vague, veiled, nonspecific… conditional."
  [onlinelibrary.wiley.com/doi/10.1002/9781405198431.wbeal0711 ; ler.letras.up.pt/uploads/ficheiros/14124.pdf]
- **Fixation** (Meloy) = "increasingly pathological preoccupation with a person or cause."
- **Leakage** (Meloy & O'Toole) = "communication to a third party of an intent to do harm
  to a target" — externalized, directed intent. [drreidmeloy.com/.../2011_theconceptofleakage.pdf]

**Operationalization:** Searle **commissive** + first-person future commitment ("I will") +
**low hedging** (CoNLL-2010 uncertainty/certainty lexicons) + named target/time/mode/method.
[Morante & Sporleder CL-2012 — aclanthology.org/J12-2001.pdf]

> **Critical caveat → directly explains PEINN's over-fire:** *affective* stance ≠ commitment.
> Gales: epistemic/affective markers must be separated; high *affective* intensity marks
> **venting (expressive)**, not instrumental intent. The energy must read commitment
> (epistemic/commissive), NOT affect intensity — the exact inversion of today's calibrator.

### Imminence (temporal overlay, not a content axis)
Last-resort "violent-action imperative + time imperative" + energy-burst (Meloy); NCTC
"Mobilization = days/hours"; SIGINT **chatter volume-change** (spike=mobilization,
drop="going dark") and Grabo's counterintuitive **buildup-then-lull**. Imminence is inferred
from *pattern/timing*, never from topic. [en.wikipedia.org/wiki/Chatter_(signals_intelligence)]

---

## 3. The "different way" to learn structure (no benchmarks, no LLM)

The user's constraint — *learn structured/actionable/definite risk WITHOUT benchmark labels
and WITHOUT LLM dependency* — maps onto a mature ML toolset for **topic-invariance**:

1. **Counterfactually-Augmented Data (CAD)** — minimal edits that flip the axis label while
   holding topic fixed; "models… rely less on semantically irrelevant words and generalize
   better OOD." [Kaushik, Hovy, Lipton, ICLR-2020 — arxiv.org/abs/1909.12434]
   → *Build minimal pairs that toggle ONE axis (imperative↔descriptive for actionability;
   committed/future↔hedged for definiteness; complete-steps↔vague for realizability) with
   subject held constant.* This is the operational core of the contrastive approach.
2. **Supervised contrastive on the pairs (PairCFR)** — pulls same-axis examples together
   across topics, pushes minimal-pair opposites apart. [arxiv.org/abs/2406.06633]
3. **Invariant Risk Minimization / invariant rationalization** — treat each **topic as an
   environment**; penalize features whose predictive power varies by topic → keep only
   causal (structural) features. [Arjovsky et al. — arxiv.org/abs/1907.02893]
   Threat/hate-specific realizations: CATCH, HATE-WATCH, CADET (causal disentanglement of
   *target/topic/style* from *intent/structure*); invariant rationalization for toxicity.
   [arxiv.org/abs/2308.02080 ; arxiv.org/abs/2106.07240]

**Independent labeled corpora (NOT eval benchmarks, NOT LLM-labeled):** SwDA/DAMSL
(dialogue-acts → actionability), OnlpLab Modality (Pyatkin → realizability/definiteness),
CoNLL-2010 hedging (→ definiteness). Plus a **self-constructed minimal-pair corpus**
(rule/template- or human-authored), benchmark-free by construction.

---

## 4. Proposed architecture (S0 spec)

```
input text
   │
   ▼
[encoder-only backbone]          # RoBERTa/DeBERTa-base class — NOT generative, NO LLM,
   │                             # lean & self-contained; general-text pretraining only
   ├─► head A: actionability     # directive/imperative/procedural   (Searle directive)
   ├─► head B: realizability     # feasibility-modality + means/steps (ISO-18045 rubric)
   └─► head C: definiteness      # commissive + low-hedge + target/time/mode/method
   │
   ▼
[calibrated combiner]            # gated geometric-mean / logistic of A,B,C (+ imminence
   │                             # overlay); AHP/elicited weights; NOT raw product
   ▼
structured-threat ENERGY  ──►  existing routing threshold (role unchanged)
```
- **Training:** CAD minimal pairs + supervised-contrastive + topic-as-environment IRM, on
  the independent corpora above. Emotion-Engine 32-D affect head stays frozen and is read
  *separately* (affect ≠ threat; affect must NOT inflate energy).
- **Configural rule** (NCTC Group A vs B/C; warning behaviors are configural): single-axis
  hits should not max the energy — require corroboration across axes. Maps naturally to the
  multi-tier router (hard-block = strong multi-axis; 2pass = single-axis / needs corroboration).

---

## 5. What we were MISSING / refinements to the original axis sketch

| Item | Source | Change to design |
|---|---|---|
| **Leakage** (externalized intent to 3rd party) | Meloy & O'Toole 2011 | add as a definiteness signal |
| **intent × capability × opportunity** as *master gate* | DHS; threat triad | combiner is multiplicative-gated, not additive |
| **Imminence** as separate temporal overlay | Meloy last-resort; SIGINT chatter-change | not an axis — a timing/pattern modifier |
| **Conditionality LOWERS definiteness** | *Watts*; realized/non-realized corpus | explicit negative feature ("if…then" ↓) |
| **Affective stance ≠ commitment** | Gales; hunter/howler | energy must de-weight affect (fixes over-fire) |
| **Configural / clusters, not single hits** | NCTC B/C; warning behaviors | thresholds require multi-axis corroboration |
| **Calibrated combiner, not raw product** | Nat. Academies 2010 | logistic/weighted-geo-mean + AHP weights |
| **Admiralty 6×6: separate reliability vs credibility** | NATO AJP-2.1 / STANAG 2511 | keep "source/affect" apart from "corroborated structure" |

---

## 6. Bottom line

Every mature threat-detection field independently converged on the **exact principle PEINN
needs**: separate the **topic-invariant ACTION structure** (strongly predictive, observable)
from **belief/affect/topic content** (weakly predictive, often protected). The redesigned
energy = a calibrated, gated combination of **actionability × realizability × definiteness**
(+ imminence), learned topic-invariantly (CAD + contrastive + IRM) on an **independent,
non-benchmark, non-LLM** corpus, emitted as the routing-threshold scalar (role unchanged).

The biggest open gap the literature itself flags: the topic-invariance machinery is mature
in *hate-speech* but **not yet applied to *threat/actionability* detection** — i.e., this is
a genuinely novel, well-grounded direction, not a re-tread.
