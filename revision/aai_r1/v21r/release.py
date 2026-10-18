"""The trained components of the revision, for the data availability statement and the public release.

    python -m v21r release [--check]       cache/<mode>/models/*.pt -> results/checkpoints/ (+ manifest), push
    python -m v21r assemble [--check]      results/checkpoints/final/*.part* -> results/checkpoints/final/*.pt

Every head and energy calibrator trained on the isolated corpus is copied to results/checkpoints/ with a manifest (file,
bytes, sha256, the variant it belongs to). PEINN's own head and calibrator carry their fine-tuned encoders (A0ft_head.pt
91 MB, A0ft_energy.pt 438 MB), larger than GitHub takes in one file; they are stored as byte parts of at most 45 MiB in
results/checkpoints/final/, so the repository archive (and the Zenodo release made from it) holds them without Git LFS.
`assemble` joins the parts and checks each file against its SHA-256. The parts are taken only when the file is the one
behind every reported result (FINAL below; Eugene 2026-10-18: the final tuned version is the one pushed now), never the
gate-retrain copies (DESIGN.md 37), whose head weights differ.
"""
from __future__ import annotations

import hashlib
import shutil

from . import common as C
from . import data as D

VARIANT = {"A0": "frozen-encoder head (ablation A0; T/I/F, 800-d)", "calibrator": "energy calibrator on frozen mpnet (ablation A0)",
           "A1": "no I channel", "A2": "softmax head", "A3": "binary harm classifier (uncertainty routing)",
           "A6p": "no principle anchors", "A6e": "no emotion feature",
           "A0ft_energy": "PEINN energy calibrator with its fine-tuned mpnet (A0ftM; also A0ft)",
           "A0ft_head": "PEINN T/I/F head with its fine-tuned MiniLM (A0ftM; also A0ft)",
           "A0ftM_ood": "PEINN out-of-distribution statistics (A0ftM: class means, precision, tau)"}
LIMIT = 5_000_000
PART = 45 * 2**20
# SHA-256 of the files that produced every reported result (recorded by the release of 2026-10-17, manifest.json).
FINAL = {"A0ft_energy.pt": "a3927ff4c1ff0e06fdd8312d6356c98038cc3f626f42671c1bff3d76ebfd521d",
         "A0ft_head.pt": "27ccc93336c110b232234d0e745b0ecbe13e4f5753f42efa35c970ba67c0bd04"}


def sha256(f) -> str:
    h = hashlib.sha256()
    with open(f, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def split(f, o) -> list[dict]:
    """f as byte parts f.name.part00, .part01, ... of at most PART bytes in o."""
    for old in o.glob(f"{f.name}.part*"):
        old.unlink()
    parts = []
    with open(f, "rb") as fh:
        for i, b in enumerate(iter(lambda: fh.read(PART), b"")):
            p = o / f"{f.name}.part{i:02d}"
            p.write_bytes(b)
            parts.append({"file": p.name, "bytes": len(b), "sha256": hashlib.sha256(b).hexdigest()})
    return parts


def release(check: bool = False, log=print) -> int:
    src = D.wdir(check) / "models"
    o = D.odir(check) / "checkpoints"
    fo = o / "final"
    fo.mkdir(parents=True, exist_ok=True)
    man = {"files": [], "split": [], "kept_out": []}
    for f in sorted(src.glob("*.pt")):
        row = {"file": f.name, "bytes": f.stat().st_size, "sha256": sha256(f), "variant": VARIANT.get(f.stem, f.stem)}
        if row["bytes"] <= LIMIT:
            shutil.copy2(f, o / f.name)
            man["files"].append(row)
        elif f.name in FINAL or check:
            if not check and row["sha256"] != FINAL[f.name]:
                log(f"stop: {f.name} is not the file behind the reported results "
                    f"(sha256 {row['sha256'][:12]} != {FINAL[f.name][:12]})")
                return 1
            row["parts"] = split(f, fo)
            man["split"].append(row)
            log(f"  {f.name}: {len(row['parts'])} parts in checkpoints/final/")
        else:
            man["kept_out"].append(row)
    missing = sorted(set(FINAL) - {r["file"] for r in man["split"]})
    if missing and not check:
        log(f"stop: {missing} not found in {src}")
        return 1
    C.jdump(man, o / "manifest.json")
    log(f"release: {len(man['files'])} checkpoints, {len(man['split'])} split into parts, {len(man['kept_out'])} kept out of git")
    if check:
        return 0
    return 0 if C.publish([o], "v21r release: PEINN's final head and calibrator (fine-tuned encoders, in parts) and the ablation heads") else 1


def assemble(check: bool = False, log=print) -> int:
    """Join the parts of each split checkpoint into checkpoints/final/<file> and check its SHA-256."""
    o = D.odir(check) / "checkpoints"
    man = C.jload(o / "manifest.json")
    bad = 0
    for row in man.get("split", []):
        out = o / "final" / row["file"]
        with open(out, "wb") as fh:
            for p in row["parts"]:
                b = (o / "final" / p["file"]).read_bytes()
                if hashlib.sha256(b).hexdigest() != p["sha256"]:
                    log(f"  {p['file']}: sha256 mismatch")
                    bad += 1
                fh.write(b)
        ok = sha256(out) == row["sha256"]
        bad += not ok
        log(f"  {row['file']}: {out.stat().st_size} bytes, sha256 {'ok' if ok else 'MISMATCH'}")
    return 1 if bad else 0
