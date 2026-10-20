"""The trained components of the revision, for the data availability statement and the public release.

    python -m v21r release [--check]       cache/<mode>/models/*.pt -> results/checkpoints/ (+ manifest), push
    python -m v21r assemble [--check]      results/checkpoints/<dir>/*.part* -> results/checkpoints/<dir>/<file>
    python -m v21r release-extra [--check] A1ft-A3ft heads, A8 adapters, corpus split identifiers (release 2.2.2)

Every head and energy calibrator trained on the isolated corpus is copied to results/checkpoints/ with a manifest (file,
bytes, sha256, the variant it belongs to). PEINN's own head and calibrator carry their fine-tuned encoders (A0ft_head.pt
91 MB, A0ft_energy.pt 438 MB), larger than GitHub takes in one file; they are stored as byte parts of at most 45 MiB in
results/checkpoints/final/, so the repository archive (and the Zenodo release made from it) holds them without Git LFS.
`assemble` joins the parts and checks each file against its SHA-256. The parts are taken only when the file is the one
behind every reported result (FINAL below; the final tuned version is the one pushed now), never the
gate-retrain copies, whose head weights differ.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

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
    """F as byte parts f.name.part00, .part01, ... of at most PART bytes in o."""
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


# ---- release 2.2.2: what release 2.2.1 left in the cache -------------

FT_HEADS = (("A1ft", "tf"), ("A2ft", "softmax"), ("A3ft", "binary"))      # ftv.HEADS
FT_DIR = "ablation_ft"
A8_DIR = "a8"
SIG_TOL = 1e-4               # largest |T|, |I|, |F| difference to the published signals (same weights, same texts)
A8_MATCH = 0.99              # share of a checked merged tensor equal to bf16(base + bf16(B A alpha/r))
A8_CHANGED = 0.95            # the same share among the elements the merge changed
A8_TENSORS = ("model.layers.23.self_attn.q_proj", "model.layers.25.mlp.down_proj", "model.layers.27.self_attn.o_proj")
# all three in the base's last shard (model-00004-of-00004, 3.6 GB), the only file fetched when the HF cache lacks it
SPLIT_COLS = ("sha", "split", "source", "file_role", "polar", "T", "I", "F", "mask_T", "mask_I", "mask_F")
CHECK_ROWS = 200


def _head_outputs(f, texts: list[str], X):
    """T, I, F of a fine-tuned head saved by train_ft (ftv), as ftv exported them (softmax applied, ftv.tif)."""
    import numpy as np
    import torch
    from . import ftv as FV
    from . import models as M
    net, tok, ck = M.ft_load(f)
    dev = next(net.parameters()).device
    out = []
    with torch.no_grad():
        for s in range(0, len(texts), 64):
            enc = tok(texts[s:s + 64], truncation=True, max_length=ck["max_len"], padding=True, return_tensors="pt")
            x = torch.tensor(X[s:s + 64], device=dev, dtype=torch.float32)
            h = net(enc["input_ids"].to(dev), enc["attention_mask"].to(dev), x).float()
            out.append((torch.softmax(h, dim=1) if ck["out"] == "softmax" else h).cpu().numpy())
    return FV.tif(ck["out"], np.concatenate(out)), ck


def check_ft_heads(check: bool, log=print) -> list | None:
    """Each A1ft-A3ft head in the cache must give the published signals (results/forced/signals_<v>.csv.gz, the values
    behind Table 13) on their own texts; None when one does not (e.g. a copy a second runner wrote)."""
    import numpy as np
    import pandas as pd
    md = D.wdir(False) / "models"
    sp = D.load_split(False)
    rec = D.record_texts(False)
    F = D.load_features(False)
    text = dict(zip(sp.sha, sp.text.astype(str)))
    text.update(zip(rec.sha, rec.text.astype(str)))
    hb = np.r_[0:32, 416:800]                                     # emotion | principle around the MiniLM slot (ftv)
    rows = []
    for v, out in FT_HEADS:
        f = md / f"{v}_head.pt"
        pub = pd.read_csv(C.OUT / "forced" / f"signals_{v}.csv.gz", dtype={"sha": str})
        if check:
            pub = pub.groupby("part", sort=False).head(CHECK_ROWS).reset_index(drop=True)
        if not f.exists():
            log(f"stop: {f} not found")
            return None
        got, ck = _head_outputs(f, [text[s] for s in pub.sha], F["head_x"][D.rows_of(F, pub.sha)][:, hb])
        if ck.get("out") != out:
            log(f"stop: {f.name} has head output '{ck.get('out')}', expected '{out}'")
            return None
        diff = max(float(np.max(np.abs(np.asarray(got[k], float) - pub[k].to_numpy(float)))) for k in ("T", "I", "F"))
        log(f"  {v}: {len(pub)} texts, max |signal - published| {diff:.2e}")
        if not diff <= SIG_TOL:
            log(f"stop: {f.name} does not give the published signals of {v} (max difference {diff:.3g} > {SIG_TOL:g})")
            return None
        rows.append({"file": f.name, "path": f, "variant": f"{v}: ablation head with its fine-tuned MiniLM "
                     f"(output '{out}')", "max_signal_diff": float(f"{diff:.3g}"), "texts_checked": len(pub)})
    return rows


def _base_files(model: str, rev: str, names, log=print) -> Path | None:
    """The base snapshot folder holding the index and the shards of `names` at commit `rev`: read from the HF cache when
    there, else downloaded (only those files). A child process without HF_HUB_OFFLINE, which some imports set."""
    import os
    import subprocess
    import sys
    code = ("import json, sys; from pathlib import Path; from huggingface_hub import hf_hub_download as g\n"
            "m, r, names = sys.argv[1], sys.argv[2], sys.argv[3:]\n"
            "i = Path(g(m, 'model.safetensors.index.json', revision=r))\n"
            "wm = json.loads(i.read_text(encoding='utf-8'))['weight_map']\n"
            "for f in sorted({wm[n + '.weight'] for n in names}): g(m, f, revision=r)\n"
            "print(i.parent)\n")
    env = {k: v for k, v in os.environ.items() if k not in ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE")}
    log(f"  base {model}@{rev[:7]}: index and the shards of {len(names)} tensor(s) (cache first, else download)")
    p = subprocess.run([sys.executable, "-c", code, model, rev, *names], env=env, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode:
        log(f"stop: could not get the base shards of {model}@{rev[:7]}\n{p.stderr[-2000:]}")
        return None
    return Path(p.stdout.strip().splitlines()[-1])


def check_a8_adapter(check: bool, log=print) -> dict | None:
    """The LoRA adapters of A8 (a8_train.py, fp32) must be the ones folded into the merged model the benches served:
    for A8_TENSORS, merged == bf16(base + bf16(B A alpha/r)) on nearly every element and on those the merge changed."""
    import json
    from safetensors import safe_open
    from . import a8 as A8
    w = A8.wdir(False)
    f = w / "adapter.safetensors"
    rep = C.jload(C.OUT / "a8" / "a8.json")["train"]
    if not f.exists():
        log(f"stop: {f} not found")
        return None
    base = _base_files(rep["model"], rep["snapshot"], A8_TENSORS[:1] if check else A8_TENSORS, log)
    if base is None:
        return None
    scale = rep["hp"]["alpha"] / rep["hp"]["r"]

    def tensor(d: Path, name: str):
        idx = d / "model.safetensors.index.json"
        shard = json.loads(idx.read_text(encoding="utf-8"))["weight_map"][name] if idx.exists() else "model.safetensors"
        with safe_open(str(d / shard), framework="pt") as fh:
            return fh.get_tensor(name)

    with safe_open(str(f), framework="pt") as fh:
        keys = list(fh.keys())
        if len(keys) != 2 * rep["wrapped"]:
            log(f"stop: {f.name} holds {len(keys)} tensors, expected {2 * rep['wrapped']}")
            return None
        res = {}
        for n in (A8_TENSORS[:1] if check else A8_TENSORS):
            A, B = fh.get_tensor(f"{n}.lora_A"), fh.get_tensor(f"{n}.lora_B")
            b, m = tensor(base, f"{n}.weight"), tensor(w / "merged", f"{n}.weight")
            want = b + (B @ A * scale).to(b.dtype)
            eq, ch = want == m, m != b
            res[n] = {"equal": round(float(eq.float().mean()), 6), "changed": int(ch.sum()),
                      "equal_changed": round(float(eq[ch].float().mean()), 6) if int(ch.sum()) else None}
            log(f"  {n}: {res[n]}")
            if not (res[n]["equal"] >= A8_MATCH and res[n]["changed"] and res[n]["equal_changed"] >= A8_CHANGED):
                log(f"stop: {f.name} is not the adapter folded into the merged A8 model ({n})")
                return None
    return {"file": f.name, "path": f, "variant": f"A8: LoRA adapters on {rep['model']} (snapshot {rep['snapshot'][:7]}), "
            f"rank {rep['hp']['r']}, alpha {rep['hp']['alpha']}, fp32; merged weight = base + B A alpha/r",
            "tensors": len(keys), "merge_check": res}


def split_ids(check: bool, log=print) -> Path | None:
    """Every row of the isolated corpus with its split, source and teacher labels (no text; sha = SHA-1 of the text, the
    key of results/forced); val and test must equal the published split_labels.csv.gz."""
    import pandas as pd
    sp = D.load_split(False)
    x = sp[[c for c in SPLIT_COLS if c in sp]].copy()
    pub = pd.read_csv(C.OUT / "forced" / "split_labels.csv.gz", dtype={"sha": str})
    vt = x[x.split.isin(("val", "test"))]
    if set(zip(vt.sha, vt.split)) != set(zip(pub.sha, pub.split)):
        log("stop: the cached split's val/test rows differ from the published split_labels.csv.gz")
        return None
    want = C.jload(C.OUT / "corpus" / "corpus_audit.json")["split"]
    have = {k: int(v) for k, v in x.split.value_counts().items()}
    if have != {k: int(v) for k, v in want.items()}:
        log(f"stop: split sizes {have} differ from the corpus audit {want}")
        return None
    o = D.odir(check) / "corpus"
    o.mkdir(parents=True, exist_ok=True)
    f = o / "corpus_split_ids.csv.gz"
    x.to_csv(f, index=False, encoding="utf-8", compression="gzip")
    log(f"  corpus_split_ids.csv.gz: {len(x)} rows {have}, columns {list(x.columns)}")
    return f


def release_extra(check: bool = False, log=print) -> int:
    """Release 2.2.2: the A1ft-A3ft heads (in parts, checkpoints/ablation_ft/), A8's LoRA adapters (in parts,
    checkpoints/a8/) and the split identifiers of the whole corpus (corpus/corpus_split_ids.csv.gz), each checked
    against what the manuscript reports before anything is written. --check reads the same cache, checks a few rows
    and one A8 tensor, writes the identifiers under the check results and splits nothing."""
    heads = check_ft_heads(check, log)
    if heads is None:
        return 1
    ad = check_a8_adapter(check, log)
    if ad is None:
        return 1
    ids = split_ids(check, log)
    if ids is None:
        return 1
    if check:
        log(f"release-extra check: {len(heads)} heads, A8 adapter ({ad['tensors']} tensors) and the identifiers pass")
        return 0
    o = D.odir(False) / "checkpoints"
    man = C.jload(o / "manifest.json")
    man["split"] = [r for r in man["split"] if r.get("dir", "final") not in (FT_DIR, A8_DIR)]
    for rows, sub in ((heads, FT_DIR), ([ad], A8_DIR)):
        d = o / sub
        d.mkdir(parents=True, exist_ok=True)
        for r in rows:
            f = r.pop("path")
            row = {"file": f.name, "dir": sub, "bytes": f.stat().st_size, "sha256": sha256(f), **r}
            row["parts"] = split(f, d)
            man["split"].append(row)
            log(f"  {f.name}: {len(row['parts'])} parts in checkpoints/{sub}/")
    C.jdump(man, o / "manifest.json")
    return 0 if C.publish([o, ids], "v21r release 2.2.2: A1ft-A3ft heads and A8 adapters (in parts), corpus split "
                                    "identifiers") else 1


def assemble(check: bool = False, log=print) -> int:
    """Join the parts of each split checkpoint into checkpoints/<dir>/<file> (dir 'final' unless the manifest names
    another) and check its SHA-256."""
    o = D.odir(check) / "checkpoints"
    man = C.jload(o / "manifest.json")
    bad = 0
    for row in man.get("split", []):
        d = o / row.get("dir", "final")
        out = d / row["file"]
        with open(out, "wb") as fh:
            for p in row["parts"]:
                b = (d / p["file"]).read_bytes()
                if hashlib.sha256(b).hexdigest() != p["sha256"]:
                    log(f"  {p['file']}: sha256 mismatch")
                    bad += 1
                fh.write(b)
        ok = sha256(out) == row["sha256"]
        bad += not ok
        log(f"  {row['file']}: {out.stat().st_size} bytes, sha256 {'ok' if ok else 'MISMATCH'}")
    return 1 if bad else 0
