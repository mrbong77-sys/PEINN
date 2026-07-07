# PEINN Architecture

PEINN is an **inference-time** decision-support layer. It never updates the base model's
weights and never calls a second LLM at inference. For each incoming request it computes two
small signals — a neutrosophic **T/I/F** head and a scalar **energy** — and combines them with a
deterministic **AND-gate** into one of five routing modes. This document maps each signal to the
code that implements it. For the full design see [`PEINN_v2.1.md`](PEINN_v2.1.md).

```
                  ┌───────────────────────────────────────────────┐
 user request ──► │  frozen sentence embedding (no LLM at runtime) │
                  └───────────────────────────────────────────────┘
                                     │
        ┌────────────────────────────┴───────────────────────────┐
        ▼                                                         ▼
 ┌────────────────────┐                                ┌────────────────────────┐
 │  Emotion Engine    │   emotion32 ⊕ semantic_emb384  │  Golden Anchors (RAG)  │
 │  32-D emotion + E  │   ⊕ principle_emb384 = 800-d   │  matched principle 384 │
 └────────────────────┘                                └────────────────────────┘
        │  energy e1 (HybridCalibrator, 0–10)     │ 800-d head features
        │                                         ▼
        │                          ┌─────────────────────────────┐
        │                          │  Neutro Head (T/I/F)        │  3 independent sigmoids
        │                          │  speech-act-aware           │  (energy NOT in head)
        │                          └─────────────────────────────┘
        │                                         │
        └────────────────────┬────────────────────┘
                             ▼
              ┌───────────────────────────────────────────┐
              │  NeutroEERouterV21 — head ⊗ energy AND-gate│  deterministic, locked θ
              │  Hard-block · Reasoned-Refusal ·           │  (F=0.15, extreme=9.4 …)
              │  Deliberation · Soft-reasoning · Direct-Answer
              └───────────────────────────────────────────┘
```

---

## 1. Emotion Engine (EE) — `src/core/emotion_engine.py`

A frozen affective network (~13.4 M parameters, ~54 MB in float32) that turns the input's frozen
MiniLM embedding into affect. Architecture:

* An **MLP/attention trunk** maps the (frozen) sentence embedding to a hidden representation
  `h ∈ ℝ²⁵⁶`. (The routing path uses no retrieval — the memory channel is zero.)
* Two output heads, with temperature scaling applied at inference:
  * `fc_emotion`: a **32-D emotion vector** `e = tanh((Wₑ·h + bₑ)/Tₑ) ∈ [−1,1]³²`, `Tₑ = 4.0`.
    The 32 dimensions are 4 layers × 8 dimensions, fusing Plutchik's emotion wheel, Lazarus &
    Smith cognitive appraisal, Ryan & Deci self-determination theory, and Dasan Jeong's
    *gwonhyeong* (moral weighing). Full spec: the inline docstring in `emotion_engine.py`.
  * `fc_energy`: a **scalar energy** `E = σ((W_E·h + b_E)/T_E) ∈ [0,1]`, `T_E = 2.0`.

The 32-D emotion vector is **the affect** consumed by both the Neutro Head (§3) and the energy
calibrator (§4). The EE is frozen and reused as a feature extractor; it ships as
`checkpoints/ee_checkpoint_agent_a.pt` and is required to reproduce routing. A separate, smaller
*affect read-out* (a MiniLM-384 → 32 MLP, `ee_emotion_readout_embedding.pt`) is **not** the routing
affect — it only supplies the router's `complexity` dilemma-rescue signal.

## 2. Golden Anchors / Principles — `src/core/golden_anchors.py`

35 immutable moral reference statements ("항심 / constant mind") spanning deontology,
utilitarianism, Yangmingism/Confucian ethics, and existentialism. They are **frozen tensors**
(never updated by any training step) and are retrieved by RAG; the embedding of the matched
principle (384-D) is concatenated into the Neutro Head input.

## 3. Neutro Head (T/I/F) — `src/pea_eval/evaluators/intent_router.py`

The core discriminator: a **speech-act-aware** head that learns three **independent** sigmoids on
top of the **frozen EE features**. The triple is *neutrosophic* — T, I, F do **not** sum to 1, so a
request can be simultaneously "slightly harmful **and** a genuine dilemma".

```
x = [ emotion32 (32) ⊕ semantic_emb (384) ⊕ principle_emb (384) ]    # 800-D  (energy is NOT here)
NeutroHead(x): Linear(800→128) → ReLU → Dropout → Linear(128→64) → ReLU → Linear(64→3) → Sigmoid
            → T ∈ [0,1]  (safe-to-comply)
            → I ∈ [0,1]  (dilemma ∪ latent threat ∪ ambiguity)
            → F ∈ [0,1]  (harmful if directly complied with)
```

The energy is **not** part of the head input — it is used only by the routing gate (§5).
`build_neutro_head` and `neutro_feature_vector` in `intent_router.py` are the single source shared
by training and inference. Engine selection is `EEConfig.engine`; `neutro_v21` selects the PEINN
routing path.

## 4. Emotion-Engine energy (e1) — the routing energy

The routing energy is the **frozen `HybridCalibrator`**: `concat(emotion32, mpnet-768) → MLP →
sigmoid ×10`, a harm probability on a 0–10 scale (`src/pea_eval/evaluators/ee_runner.py`,
checkpoint `ee_hybrid_calibrator_best.pt`). Its role is the head-independent **override for definite
harm** and the **target of the head-F veto** (over-fire correction). The head reads *meaning /
speech-act* (energy's blind spot); the energy reads *affect intensity* (the head's blind spot) —
the AND-gate (§5) combines them. See [`PEINN_v2.1.md`](PEINN_v2.1.md) §3 for the complementarity
argument.

## 5. NeutroEERouterV21 — head ⊗ energy AND-gate (deterministic)

The router combines the head posture (T/I/F) with the energy `e1` into exactly one of five tiers,
with a **locked** operating point `θ = {extreme 9.4, harm 8.5, F 0.15, I 0.45, Fref 0.30, soft 8.5,
Fblk 0.45}` (`NeutroEERouterV21.THETA`):

```
if I ≥ θ_I  and F < θ_Fblk:                       → Deliberation       # genuine dilemma / latent threat
if e1 ≥ θ_extreme  or (e1 ≥ θ_harm and F ≥ θ_F):  → Hard-block         # definite threat (no 2nd pass)
if F ≥ θ_Fref:                                     → Reasoned-Refusal   # head flags harm
if e1 ≥ θ_soft:                                    → Soft-reasoning     # energy over-fire rescue band
else:                                              → Direct-Answer      # clearly safe
```

| Tier | Effect | internal route constant |
|---|---|---|
| **Hard-block** | fixed refusal, no LLM 2nd pass | `hard-block` |
| **Reasoned-Refusal** | reason then refuse (2-pass) | `2-pass-refusal` |
| **Deliberation** | delegate to moral reasoning (2-pass) | `2-pass-reasoning` |
| **Soft-reasoning** | light reasoning, keep a useful answer (2-pass) | `2-pass-reasoning-soft` |
| **Direct-Answer** | answer directly (1-pass) | `1-pass` |

The three 2-pass tiers generate the user-facing answer by **re-posing the original question** with
a tier-specific posture (no draft transcript) — see `prompt_builder.py` and
[`PEINN_v2.1.md`](PEINN_v2.1.md) §2.1. Determinism (only the user text enters head/energy, fixed
thresholds, no sampling) is what makes routing reproducible. The benchmark arms (H01–H17) live in
`src/run_stat_batch.py` and `src/scripts/run_v21_bench.py`.

---

### Component → checkpoint map

| Component | Checkpoint file | In `checkpoints/`? | Rebuild |
|---|---|---|---|
| Emotion Engine trunk (affect source, ~13.4 M) | `ee_checkpoint_agent_a.pt` (~54 MB) | ✓ | REGENERATE_CHECKPOINTS §1 |
| Neutro Head (T/I/F) | `ee_neutro_head_v4.pt` | ✓ | REGENERATE_CHECKPOINTS §2 |
| Emotion-Engine energy (calibrator) | `ee_hybrid_calibrator_best.pt` | ✓ | REGENERATE_CHECKPOINTS §3 |
| Affect read-out (complexity signal) | `ee_emotion_readout_embedding.pt` | ✓ | REGENERATE_CHECKPOINTS §4 |
| Golden Anchors | in code (`golden_anchors.py`) | ✓ | n/a (frozen tensors) |
| Gate thresholds θ | `neutro_gate_theta_v4.json` (reference copy) | ✓ | frozen in code |
