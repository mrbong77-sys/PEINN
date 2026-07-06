# S0-redux — Intent Typology & LLM Data-Generation Schema

Supersedes the act/real/def slot-template scheme (E5: it learned markers, not the concept, and
*structure ⟂ harmfulness*). New plan: an **LLM-generated, benchmark-decontaminated** corpus of
whole, naturally-varied request sentences **labeled by harm-intent**, used to train the lean
encoder as a **harm-intent classifier** (deployed LLM-free, D8). Whole sentences + the right
labels = the standard supervised setup the slot-templates were a poor substitute for.

---

## 1. Labels (what the multi-head decoder predicts)

- **harm_intent ∈ [0,1]** — *primary.* Does the request seek to cause/enable real harm to
  others? The LLM labels this directly (it understands intent). This is the signal E5 lacked.
- **operational ∈ [0,1]** — requests executable capability/procedure vs discusses/asks-about.
- **benign_purpose ∈ {0,1}** — explicit educational / defensive / simulated / "harmless"
  framing present. (Interpretability + the over-refusal lever; NOT trusted alone — see T6.)

Routing energy = a calibrated function of these (harm_intent dominant; the gated combiner and
calibration from ENCODER_SPEC §4 carry over). harm_intent alone is the core discriminator; the
others aid interpretation and the configural gate.

## 2. Typology of generated forms (ensures coverage of the hard edges)

| type | description | harm_intent | why it matters |
|---|---|---|---|
| **T1** direct-harmful | plainly asks to do/enable real harm, no framing | high | the positive class |
| **T2** benign-purpose-framed sensitive | sensitive topic + explicit harmless/educational/defensive/simulation framing | **low** | **the over-refusal class** — v1's failure |
| **T3** plainly benign | benign topic, ordinary request | low | the easy negatives |
| **T4** educational/discussion | "how does X work?" about a sensitive topic | low | sensitive-keyword negatives |
| **T5** hypothetical/abstract | "what would X even look like?" | low | abstract negatives |
| **T6** obfuscated/jailbreak | real harmful intent *hidden behind* benign framing | **high** | teaches framing ≠ safe (robustness; stops T2-style framing from being a loophole) |

T2 vs T6 is the crux: same surface framing, opposite harm_intent → forces the model to read
*genuine* intent, not the "for educational purposes" keyword. Generate **minimal pairs** here
(hold topic+framing, flip genuine harm) → reuse the CAD/contrastive machinery on the new labels.

## 3. Topic diversity (independent of benchmarks)

Many domains incl. sensitive (security, privacy, chemistry-ed, weapons-context, public-health),
spanning the harm spectrum. **We generate the REQUESTS and label intent — never operational
harmful procedures/content.** Topic is a covariate, not the label; balance harm_intent across
topics so topic can't proxy the label (IRM environment = topic, carried over).

## 4. Generation (LLM, offline — D8)

- Few-shot prompt per type; temperature for natural diversity; balanced quotas across
  type × topic × framing; request paraphrase variety explicitly.
- Self-label at generation (the LLM emits text + harm_intent/operational/benign_purpose), with
  a second-pass LLM verification on a sample for label quality.
- Provider-agnostic: any capable LLM (API or local); the **deployed encoder remains LLM-free**.

## 5. Benchmark-decontamination gate (the one hard invariant, D4)

Before a generated item enters the corpus: reject if its n-gram (e.g. 8-gram) overlap or high
embedding similarity with ANY held-out benchmark prompt exceeds a low threshold; near-dup
filter within the corpus. The benchmarks are read **only to exclude overlap**, never as labels.
A decontamination report is committed with each build.

## 6. Reused infra (unchanged from S2/S3)

Encoder (DeBERTa-v3-base, fp32) + multi-head decoder + gated calibrated combiner; CAD minimal
pairs (now harm-flip & framing-flip) + supervised-contrastive + IRM(topic); split by topic AND
by template/source; the held-out benchmark-transfer arbiter (target v2 AUC ≫ 0.629 with
harmful HIGH / benign LOW, and the benign over-fires collapsing while harmful stays blocked).

## 7. Open items

- generation volume/balance targets (start ~few k, scale); label-noise budget + verification.
- the harm_intent threshold ↔ energy calibration on a corpus-dev (never benchmarks).
- residual: a perfectly-disguised harmful request may still read low — T6 mitigates; the v1 +
  2-pass net remains the backstop for UCR.
