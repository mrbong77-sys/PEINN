"""PEINN v2.0 encoder subpackage — the structured-threat model (S2 spec → code).

Backbone-pluggable so the architecture (3 heads + gated combiner) can be smoke-tested with a
deps-light TinyBackbone (torch only) before training the real DeBERTa-v3-base on GPU.
"""
from .model import (
    StructuredThreatEncoder, AxisHead, GatedLogisticCombiner,
    HFMeanPoolBackbone, TinyBackbone, AXES,
)
