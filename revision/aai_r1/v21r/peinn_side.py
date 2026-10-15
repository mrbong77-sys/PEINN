"""DESIGN.md 4: the frozen v2.1 features for a list of texts, computed with the paper's own runtime code. Runs inside the
public PEINN checkout (cwd = PEINN/src), as run_energy_isolation.py did; no other imports.

    python peinn_side.py features --texts texts.json --out feats.npz
    python peinn_side.py gate-time --texts texts.json --out gate.json     # per-text gate compute (DESIGN.md 7)

texts.json is a JSON list of strings. feats.npz (resumable, keyed by sha1 of the text) holds
    keys     sha1 per text
    head_x   (N, 800) emotion32 + MiniLM-384 + principle-384  (the Neutro Head input)
    cal_x    (N, 800) emotion32 + mpnet-768                    (the energy calibrator input)
    tif      (N, 3)   the shipped v4 head on head_x             (reference only)
    e1       (N,)     the shipped calibrator energy x 10        (reference only)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import numpy as np


def sha(t: str) -> str:
    return hashlib.sha1(t.encode("utf-8")).hexdigest()


class Features:
    def __init__(self, out: Path):
        import torch
        from pea_eval.config.settings import load_settings
        from pea_eval.evaluators.ee_runner import EvalEERunner
        from pea_eval.evaluators.intent_router import build_neutro_head
        self.torch = torch
        self.runner = EvalEERunner.get_instance(ee_config=load_settings("real").ee)
        self.runner.initialize()
        ck = torch.load(Path("pea_eval") / "data" / "ee_neutro_head_v4.pt", map_location="cpu")
        self.head = build_neutro_head(ck["in_dim"])
        self.head.load_state_dict(ck["state_dict"])
        self.head.eval()
        self.calib = self.runner._calibrator
        self.norm = os.environ.get("PEAOS_NORMALIZE_HYBRID_FEATURES", "0") == "1"
        self.out = out
        self.store: dict[str, tuple] = {}
        if out.exists():
            z = np.load(out, allow_pickle=False)
            for i, k in enumerate(z["keys"]):
                self.store[str(k)] = (z["head_x"][i], z["cal_x"][i], z["tif"][i], float(z["e1"][i]))

    def one(self, text: str):
        from pea_eval.evaluators.intent_router import neutro_feature_vector
        f = self.runner.neutro_features(text)
        hx = neutro_feature_vector(f).astype("float32")
        mp = self.runner._calibrator_embedder.encode([text], convert_to_numpy=True)[0].astype("float32")
        emo = f["emotion"].astype("float32")
        if self.norm:
            emo, mp = emo / (np.linalg.norm(emo) + 1e-8), mp / (np.linalg.norm(mp) + 1e-8)
        cx = np.concatenate([emo, mp]).astype("float32")
        with self.torch.no_grad():
            tif = self.head(self.torch.tensor(hx).unsqueeze(0)).numpy()[0].astype("float32")
            dev = next(self.calib.parameters()).device
            e1 = float(self.calib(self.torch.tensor(cx).unsqueeze(0).to(dev)).cpu().numpy().ravel()[0] * 10.0)
        return hx, cx, tif, e1

    def save(self) -> None:
        keys = sorted(self.store)
        tmp = self.out.with_suffix(".tmp.npz")
        np.savez(tmp, keys=np.array(keys), head_x=np.stack([self.store[k][0] for k in keys]),
                 cal_x=np.stack([self.store[k][1] for k in keys]), tif=np.stack([self.store[k][2] for k in keys]),
                 e1=np.array([self.store[k][3] for k in keys], dtype="float32"))
        os.replace(tmp, self.out)

    def run(self, texts: list[str]) -> int:
        todo = [t for t in dict.fromkeys(texts) if sha(t) not in self.store]
        print(f"[features] {len(texts)} texts, {len(todo)} to compute", flush=True)
        t0 = time.time()
        for i, t in enumerate(todo, 1):
            self.store[sha(t)] = self.one(t)
            if i % 500 == 0 or i == len(todo):
                self.save()
                print(f"[features] {i}/{len(todo)} ({(time.time() - t0) / 60:.1f} min)", flush=True)
        if not todo and not self.out.exists() and self.store:
            self.save()
        return 0


def gate_time(texts: list[str], out: Path) -> int:
    """Wall time per text of the whole input gate (emotion trunk, MiniLM, principle anchors, mpnet, head, energy),
    after five warm-up texts, on whatever device torch sees (CUDA_VISIBLE_DEVICES='' for CPU)."""
    import statistics
    import torch
    f = Features(out.with_suffix(".unused.npz"))
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    for t in texts[:5]:
        f.one(t)
    ms = []
    for t in texts:
        if dev == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        f.one(t)
        if dev == "cuda":
            torch.cuda.synchronize()
        ms.append((time.perf_counter() - t0) * 1000)
    ms.sort()
    res = {"device": dev, "threads": torch.get_num_threads(), "n": len(ms), "p50_ms": round(statistics.median(ms), 2),
           "p95_ms": round(ms[int(0.95 * (len(ms) - 1))], 2), "mean_ms": round(sum(ms) / len(ms), 2)}
    if dev == "cuda":
        res["gpu_peak_GB"] = round(torch.cuda.max_memory_allocated() / 1e9, 3)
    out.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    print(f"[gate-time] {res}", flush=True)
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("mode", choices=["features", "gate-time"])
    ap.add_argument("--texts", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    sys.path.insert(0, os.getcwd())
    os.environ.setdefault("PEINN_NEUTRO_HEAD", "ee_neutro_head_v4.pt")
    texts = json.loads(a.texts.read_text(encoding="utf-8"))
    if a.mode == "gate-time":
        if os.environ.get("CUDA_VISIBLE_DEVICES") == "":
            import torch
            torch.set_num_threads(int(os.environ.get("OMP_NUM_THREADS", "1")))
        return gate_time(texts, a.out)
    return Features(a.out).run(texts)


if __name__ == "__main__":
    sys.exit(main())
