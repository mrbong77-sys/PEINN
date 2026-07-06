"""Provenance / contamination-isolation guard reused by the corpus builders.

`ProvenanceGuard` enforces that no evaluation-benchmark item leaks into any training
corpus (exact-SHA + n-gram containment near-dup check). It is the only piece of the
former PGE research note retained in this package.
"""
from pea_eval.pge.provenance_guard import ProvenanceGuard  # noqa: F401
