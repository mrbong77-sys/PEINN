"""PEINN v2.0 — structured-threat energy module.

Self-contained, separable from the PEAOS 1.0 backbone (core/, pea_eval/).
Isolation contract (see DECISIONS.md D7):
  - this module MAY import from the v1.0 backbone READ-ONLY (e.g. the frozen
    EmotionEngine) — it never mutates it;
  - the v1.0 backbone NEVER imports from peinn_v2, except through one explicit,
    opt-in seam added at S3 (the energy provider), default-off.
PEAOS 1.0 is preserved unchanged.
"""
