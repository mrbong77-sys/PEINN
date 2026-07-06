# S2 — Structured-Threat Encoder Architecture Spec

Freezes the model that turns text into the **structured-threat energy**. Encoder-only,
no-LLM, self-contained (D3); trained only on the independent corpus (D4); reads structure not
topic (D5); axes per D6; attaches to v1.0 via one opt-in seam (D7).

```
text ─► [encoder backbone] ─► pooled h ─► 3 heads ─► (a, r, d) ∈ [0,1]³
                                              └─► [calibrated gated combiner] ─► E_struct∈[0,1] ─►×10─► routing threshold
   (32-D emotion is read SEPARATELY by v1.0; it never enters this encoder — the energy is affect-free)
```

---

## 1. Backbone

| | Recommended | Fallback | Lean variant |
|---|---|---|---|
| model | **DeBERTa-v3-base** (~86 M backbone) | RoBERTa-base (125 M) | DeBERTa-v3-small (~44 M) |
| why | disentangled attention + strong NLU → best at the *structural/pragmatic* cues we need (imperatives, modality, hedging, commitment); encoder-only, not generative | robust, well-understood baseline | edge/latency budget |
| license | MIT | MIT | MIT |

- **Not** an LLM (no generation, no autoregression) — preserves PEINN identity (D3).
- **Must be fine-tuned**, not frozen: the 0.61 ceiling (E1/E3) is precisely the *frozen*
  MiniLM-384 representation. The fix is a deeper, *trainable* encoder.
- **Overfit guard** (small corpus): freeze the bottom ~½ of layers (or LoRA/adapter tuning),
  warm-start the heads on T1 (SwDA / Modality / CoNLL-2010), and lean on CAD+IRM (§3).
- Pooling: mean-pool over tokens (robust) or CLS; choose on the topic-held-out dev.

## 2. Heads (multi-task)

Shared encoder → pooled `h` → **three lightweight MLP heads**, one per axis:
`actionability`, `realizability`, `definiteness`. Each: `Linear(h→128) → GELU → Linear(128→1)
→ sigmoid` ⇒ a score in [0,1]. (Ordinal/regression-ready; pilot labels are binary.)

- Multi-task by design: forcing one shared encoder to serve all three axes is what builds a
  representation that *separates* the axes (a request can be HIGH-actionability yet
  LOW-definiteness — the E3 over-fires).
- **Imminence** is deferred to a 4th head later (temporal markers); not in the pilot.

## 3. Training objective

`L = L_sup + λ_c·L_contrastive + λ_irm·L_irm`  (defaults λ_c=0.5, λ_irm=1.0; tune on dev).

1. **Supervised** `L_sup` — BCE per axis on the CAD labels. Class-reweight the rarer
   HIGH-real / HIGH-def (pilot 60/360) until the corpus is balanced.
2. **Supervised-contrastive** `L_contrastive` (PairCFR-style, arXiv 2406.06633) — over the
   **minimal pairs**: push a pair's two items apart **along the toggled axis**, and pull
   same-axis-value items from **different topics** together. This is what makes each axis
   direction *topic-invariant* rather than a topic cue.
3. **Invariant Risk Minimization** `L_irm` (Arjovsky 2019) with **`topic_id` as the
   environment** — penalize axis-classifier gradient variance across topics so no feature
   whose predictive power depends on topic survives. *Robustness note (Nat. Academies / IRM
   brittleness):* keep **group-DRO** as a drop-in fallback if IRM is unstable.

Split **by topic** (unseen-topic dev/test) — the only split that measures topic-invariant
generalization, mirroring the eventual benchmark transfer.

## 4. Calibrated gated combiner  (a, r, d) → E_struct

Per D6: **gated** (any leg ≈0 collapses the score — Threat = intent×capability×opportunity)
but **calibrated**, not a raw product (Nat. Academies 2010: correlated axes).

- **Form (implemented):** `E_struct = σ( α·logit(g) + b )`, `g = Π_i x_i^{ŵ_i}` (ŵ=softmax) —
  a calibrated **weighted geometric mean**. g is the configural AND-gate (any x_i→0 ⇒ g→0 ⇒
  E→0); the outer logistic (temperature α, bias b) calibrates without breaking the gate.
  *Rejected:* the additive-logit form `σ(Σ w_i·logit x_i + b)` does **not** gate — two high axes
  outvote one low ((.99,.99,.01)→0.96); caught by `encoder/smoke_test`.
- **Weights/calibration:** fit `w,b` (+ temperature) on a **held-out slice of the independent
  corpus + T3 human dev** — **never** the eval benchmarks (D4). Prior on weights via AHP if data is thin.
- **Configural rule (D6):** the gate already enforces "needs corroboration" — a single high
  axis with the others low yields low E_struct (no single-axis trigger).
- **Imminence overlay (later):** a bounded multiplier from temporal markers; off in the pilot.
- **Scale-out:** `energy = 10 · E_struct` so it is a drop-in for the existing routing threshold
  semantics (hard-block ≥ 8.0). The energy's *role* is unchanged (D2); thresholds recalibrate in S4.

## 5. Affect is excluded (the over-fire fix)

The 32-D emotion vector does **not** enter this encoder. The energy is **affect-free** by
construction, and the encoder is trained affect-invariant (affect⟂label, verified |r|=0.000).
This directly removes the E3 failure mode (energy firing on emotional/keyword surface). v1.0
still reads the 32-D emotion separately for the MUX — unchanged.

## 6. Isolation seam (S3 preview, D7)

One opt-in provider, default-off, single touch-point in `core`/`ee_runner`:
```python
# analyze_emotion(...), after the v1.0 calibrated energy is computed:
if os.environ.get("PEINN_V2_ENERGY") == "1":
    from peinn_v2.energy import score_energy        # v2 imports v1 read-only; v1→v2 only here
    weighted_energy = score_energy(text)            # drop-in replacement on the same [0,10] scale
```
Default off ⇒ PEAOS 1.0 behaviour is byte-identical. Lets us **A/B** v1 calibrator vs v2
structured energy on the same router and benchmarks (S4).

## 7. Evaluation

- **Intrinsic (no benchmark):** per-axis AUC on **three** held-out splits — `topic` (unseen
  topics), `tmpl` (unseen marker phrasings), `both` (strict). `tmpl`/`both` are the meaningful
  ones: topic-held-out alone saturates because the markers fully separate the labels (E4).
- **Extrinsic (held-out benchmarks, S4):** energy resolution on held-out harmful vs benign benchmark prompts
  (target **0.629 → ~0.95**), then ORR/UCR via the router (target **ORR 81 % → ≤5 %**, UCR held).

## 8. Risks / open items

- **Small-corpus overfit** → adapters/partial-freeze + T1 warm-start + scale the corpus beyond
  the pilot before trusting numbers.
- **Combiner weights without benchmarks** → corpus-dev + AHP prior; validate sensitivity.
- **IRM instability** → group-DRO fallback.
- **Pilot label imbalance** (real/def HIGH rare) → fix in the scaled corpus (cross-combinations).
- **Latency/footprint** → base encoder adds one forward pass on the routing path; budget it,
  or use the small variant. Still vastly lighter than any LLM.
