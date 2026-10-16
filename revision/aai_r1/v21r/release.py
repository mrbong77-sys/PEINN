"""The trained components of the revision, for the data availability statement.

    python -m v21r release [--check]

Copies every head and the energy calibrator trained on the isolated corpus (cache/<mode>/models/*.pt, the small ones
well under 1 MB) to results/checkpoints/ with a manifest (file, bytes, sha256, the variant it belongs to). The A8 LoRA
adapters and the fine-tuned encoders of A0ft / A0ftM (hundreds of MB) stay out of git; the manifest records their size
and sha256 for the archived release.
"""
from __future__ import annotations

import hashlib
import shutil

from . import common as C
from . import data as D

VARIANT = {"A0": "PEINN head (T/I/F, 800-d)", "calibrator": "energy calibrator (affect 32 + mpnet 768)",
           "A1": "no I channel", "A2": "softmax head", "A3": "binary harm classifier (uncertainty routing)",
           "A6p": "no principle anchors", "A6e": "no emotion feature",
           "A0ft_energy": "fine-tuned mpnet energy calibrator (A0ft, A0ftM)", "A0ft_head": "fine-tuned MiniLM T/I/F head (A0ft, A0ftM)",
           "A0ftM_ood": "Mahalanobis OOD of A0ftM (class means, precision, tau)"}
LIMIT = 5_000_000


def sha256(f) -> str:
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def release(check: bool = False, log=print) -> int:
    src = D.wdir(check) / "models"
    o = D.odir(check) / "checkpoints"
    o.mkdir(parents=True, exist_ok=True)
    man = {"files": [], "kept_out": []}
    for f in sorted(src.glob("*.pt")):
        row = {"file": f.name, "bytes": f.stat().st_size, "sha256": sha256(f), "variant": VARIANT.get(f.stem, f.stem)}
        if row["bytes"] > LIMIT:
            man["kept_out"].append(row)
            continue
        shutil.copy2(f, o / f.name)
        man["files"].append(row)
    ad = D.wdir(check) / "a8" / "adapter.safetensors"
    if ad.exists():
        man["kept_out"].append({"file": "a8/adapter.safetensors", "bytes": ad.stat().st_size, "sha256": sha256(ad),
                                "variant": "A8 LoRA adapters on qwen2.5-7B-Instruct"})
    f = C.jdump(man, o / "manifest.json")
    log(f"release: {len(man['files'])} checkpoints, {len(man['kept_out'])} kept out of git")
    if check:
        return 0
    return 0 if C.publish([o], "v21r release: heads and energy calibrator trained on the isolated corpus (+ manifest)") else 1
