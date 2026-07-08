# PEINN Routing Demo

A standalone, self-contained demo of PEINN's **routing decision** — the part that runs
**without any LLM**. Type a jailbreak attempt or a moral dilemma and see which of PEINN's
five modes it routes to, and *why*.

This is "PEINN minus the base model's 2nd-pass reasoning": the real T/I/F head, the real
energy calibrator, and the real locked AND-gate (`NeutroEERouterV21.THETA`) — no language
model at inference.

## Run

From the repo root:

```bash
pip install -r demo/requirements-demo.txt
python demo/peinn_demo.py             # web UI at http://localhost:7860
```

Terminal-only sanity check (no UI):

```bash
python demo/peinn_demo.py --selftest
```

Windows PowerShell is fine; a GPU is **not** required (CPU is plenty for one prompt at a
time).

## What it shows

For each prompt:

- **Routing mode** — one of `Hard-block`, `Reasoned-Refusal`, `Deliberation`,
  `Soft-reasoning`, `Direct-Answer` (with the internal route constant).
- **Rationale** — which gate condition fired, in plain language.
- **Signals** — T (safe-to-comply), I (dilemma / latent threat), F (harmful), and energy
  e1 (0–10), plus the frozen gate thresholds θ.

## How it works

```
prompt ─▶ MiniLM / mpnet embeddings ─▶ Emotion Engine trunk (32-d affect)
        ├─▶ Neutro Head v4 ─▶ (T, I, F)
        └─▶ Hybrid Calibrator ─▶ energy e1 (0–10)
                    └─▶ NeutroEERouterV21 AND-gate (locked θ) ─▶ mode + reason
```

The demo **reuses the repo's real code** (`pea_eval.evaluators.ee_runner`,
`intent_router.NeutroEERouterV21`) — it does not re-implement the router, so its decisions
match the paper's routing.

## First run

- The shipped checkpoints (`checkpoints/*.pt`) are copied into `src/pea_eval/data/`
  automatically.
- The two frozen sentence encoders (`all-MiniLM-L6-v2`, `all-mpnet-base-v2`) are downloaded
  from Hugging Face on first use (**internet required once**, a few hundred MB). To run
  fully offline afterwards, set `HF_HUB_OFFLINE=1`.
- Model bring-up takes ~10–30 s on CPU; subsequent prompts are fast.

## Note on the examples

The built-in examples are benign or illustrative by design (classic dilemmas, mild
jailbreak *framings* with no operational content, benign homonyms). The demo only displays
signals and which rule fired — it never emits harmful content.
