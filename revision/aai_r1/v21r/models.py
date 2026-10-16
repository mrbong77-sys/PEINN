"""DESIGN.md 4 (step T): every variant trained on the same isolated corpus, the same teacher labels and seed 42.

Signals for the val/test splits and every recorded routing text are written to .cache/v21r/<mode>/signals/<V>.npz
(keys: sha plus the variant's outputs). Small checkpoints go to .cache/v21r/<mode>/models/.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import numpy as np
import pandas as pd

from . import common as C
from . import data as D

SEED = 42
EMO, SEM, PRI = slice(0, 32), slice(32, 416), slice(416, 800)
HEAD_HP = dict(epochs=60, lr=1e-3, batch=128, wd=1e-4, i_weight=2.5)      # train_neutro_head.py defaults (v4 head)
CAL_HP = dict(epochs=80, batch=64, lr=1e-3, wd=1e-2, focal_gamma=2.0, warmup=5, patience=12)   # ee_threshold_finder
# DESIGN.md 4 (corrected 2026-10-16, results/diag/gate_diag.md 2): the shipped head was trained on every axis (its
# report: n_sup 1,880 = the whole held-out file on T, I and F), so an unlabelled axis's placeholder 0 is a negative
# target. neg_weight 1.0 reproduces that; the 2-of-3 mask with neg_weight 0 left F almost without negatives.
SHIPPED_NEG_W = 1.0
# DESIGN.md 12 (Eugene 2026-10-16 09:28 KST: diverse isolated data, finer head training): every row's loss is weighted by
# sqrt(N / (K * n_source)) from the train split (mean 1 on train), so the many small sources of the supplement are not
# drowned by the large ones and no single source decides the boundary. Same weights for every variant and the calibrator.
ROW_WEIGHT = "sqrt_inverse_source_frequency"
SBERT_HP = dict(model="sentence-transformers/all-MiniLM-L6-v2", epochs=3, lr=2e-5, batch=32, max_len=256)


def _seed(s: int = SEED) -> None:
    import torch
    random.seed(s)
    np.random.seed(s)
    torch.manual_seed(s)
    torch.cuda.manual_seed_all(s)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def _dev():
    import torch
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def mlp(in_dim: int, out: int, sigmoid: bool):
    """The Neutro Head architecture (intent_router.build_neutro_head) with `out` outputs."""
    import torch.nn as nn
    layers = [nn.Linear(in_dim, 128), nn.ReLU(), nn.Dropout(0.2), nn.Linear(128, 64), nn.ReLU(), nn.Linear(64, out)]
    return nn.Sequential(*layers, nn.Sigmoid()) if sigmoid else nn.Sequential(*layers)


def shipped_meta() -> dict:
    """Recipe fields stored in the shipped v4 head (labels, neg_weight)."""
    import torch
    ck = torch.load(C.peinn() / "checkpoints" / "ee_neutro_head_v4.pt", map_location="cpu", weights_only=False)
    return {k: ck.get(k) for k in ("labels", "neg_weight", "in_dim", "arch")}


def three_class(T, I, F) -> np.ndarray:
    """A2 labels (DESIGN.md 4): harmful if F >= .5 and F >= I; else ambiguous if I >= .5; else safe. 0 safe, 1 amb, 2 harm."""
    T, I, F = (np.asarray(x, dtype=float) for x in (T, I, F))
    y = np.zeros(len(F), dtype=int)
    y[I >= 0.5] = 1
    y[(F >= 0.5) & (F >= I)] = 2
    return y


def row_weights(train: pd.DataFrame, d: pd.DataFrame) -> np.ndarray:
    """sqrt(N / (K * n_s)) per row of d, n_s counted on the train split; scaled to mean 1 over the train split."""
    n = train.source.value_counts()
    w = np.sqrt(len(train) / (len(n) * n))
    scale = float(w.reindex(train.source).mean())
    return (d.source.map(w).fillna(float(w.max())) / scale).to_numpy(dtype="float32")


def head_weights(d: pd.DataFrame, neg_w: float) -> np.ndarray:
    """Per-element loss weights: 1 where the axis is labelled, neg_w where it holds the placeholder 0."""
    M = d[["mask_T", "mask_I", "mask_F"]].to_numpy(dtype="float32")
    return M + (1 - M) * neg_w


# ---- heads on frozen features -------------------------------------------------------------------------

def train_head(Xtr, Ytr, Wtr, Xva, Yva, Wva, kind: str, dim_w=None, hp=HEAD_HP, log=print, rtr=None, rva=None):
    """kind 'sigmoid': masked soft-target BCE (weights W per element); 'softmax': cross-entropy on class ids (Y 1-d);
    'binary': BCE on a 0/1 target. rtr / rva: row weights (DESIGN.md 12). Model selection by the lowest validation loss."""
    import torch
    import torch.nn as nn
    _seed()
    dev = _dev()
    k = {"sigmoid": Ytr.shape[1] if Ytr.ndim > 1 else 1, "softmax": 3, "binary": 1}[kind]
    model = mlp(Xtr.shape[1], k, sigmoid=kind != "softmax").to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=hp["lr"], weight_decay=hp["wd"])
    Xt, Xv = torch.tensor(Xtr, device=dev), torch.tensor(Xva, device=dev)
    if kind == "softmax":
        Yt, Yv = torch.tensor(Ytr, device=dev, dtype=torch.long), torch.tensor(Yva, device=dev, dtype=torch.long)
    else:
        Yt = torch.tensor(Ytr.reshape(len(Ytr), -1), device=dev, dtype=torch.float32)
        Yv = torch.tensor(Yva.reshape(len(Yva), -1), device=dev, dtype=torch.float32)
    Rt = torch.tensor(np.ones(len(Xtr)) if rtr is None else rtr, device=dev, dtype=torch.float32)
    Rv = torch.tensor(np.ones(len(Xva)) if rva is None else rva, device=dev, dtype=torch.float32)
    if kind == "sigmoid":
        Wt = torch.tensor(Wtr, device=dev, dtype=torch.float32) * Rt[:, None]
        Wv = torch.tensor(Wva, device=dev, dtype=torch.float32) * Rv[:, None]
        dw = torch.tensor(dim_w if dim_w is not None else [1.0] * k, device=dev, dtype=torch.float32)
    else:
        Wt, Wv = Rt, Rv

    def loss_fn(pred, y, w):
        if kind == "softmax":
            return (nn.functional.cross_entropy(pred, y, reduction="none") * w).sum() / w.sum().clamp_min(1e-8)
        el = nn.functional.binary_cross_entropy(pred, y, reduction="none")
        if kind == "binary":
            return (el.squeeze(1) * w).sum() / w.sum().clamp_min(1e-8)
        return (el * dw * w).sum() / w.sum().clamp_min(1.0)

    best, best_state, n = 1e18, None, len(Xt)
    for ep in range(hp["epochs"]):
        model.train()
        perm = torch.randperm(n, device=dev)
        for s in range(0, n, hp["batch"]):
            ix = perm[s:s + hp["batch"]]
            loss = loss_fn(model(Xt[ix]), Yt[ix], Wt[ix])
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(loss_fn(model(Xv), Yv, Wv))
        if vl < best:
            best, best_state = vl, {k_: v.detach().cpu().clone() for k_, v in model.state_dict().items()}
        if ep == 0 or (ep + 1) % 10 == 0:
            log(f"    epoch {ep + 1:3d}  val {vl:.4f}")
    model.load_state_dict(best_state)
    model.cpu().eval()
    return model, best


def predict(model, X, kind: str) -> np.ndarray:
    import torch
    with torch.no_grad():
        p = model(torch.tensor(X))
        if kind == "softmax":
            p = torch.softmax(p, dim=1)
    return p.numpy()


# ---- energy calibrator ----------------------------------------------------------------------------------

def calibrator(in_dim: int = 800):
    import torch.nn as nn
    return nn.Sequential(nn.Linear(in_dim, 64), nn.ReLU(), nn.Dropout(0.2), nn.Linear(64, 32), nn.ReLU(),
                         nn.Linear(32, 1), nn.Sigmoid())


def _auroc(y, s) -> float:
    y, s = np.asarray(y, dtype=int), np.asarray(s, dtype=float)
    pos, neg = s[y == 1], s[y == 0]
    if not len(pos) or not len(neg):
        return 0.0
    order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
    r = np.empty(len(order))
    r[order] = np.arange(1, len(order) + 1)
    return float((r[:len(pos)].sum() - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))


def train_calibrator(Xtr, ytr, Xva, yva, hp=CAL_HP, log=print, rtr=None):
    """ee_threshold_finder.train_calibrator: class-weighted focal BCE, AdamW, cosine LR with warm-up, selection by
    validation AUROC, patience 12. rtr: row weights (DESIGN.md 12) times the class weights."""
    import torch
    from torch.utils.data import DataLoader, TensorDataset
    _seed()
    dev = _dev()
    m = calibrator().to(dev)
    pos_w = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    neg_w = float((ytr == 1).sum() / max(1, (ytr == 0).sum()))

    def focal(pred, t, r):
        pred = pred.clamp(1e-7, 1 - 1e-7)
        w = (t * pos_w + (1 - t) * neg_w) * r
        pt = t * pred + (1 - t) * (1 - pred)
        lp = t * torch.log(pred) + (1 - t) * torch.log(1 - pred)
        return -(w * (1 - pt).pow(hp["focal_gamma"]) * lp).mean()

    g = torch.Generator().manual_seed(SEED)
    R = torch.tensor(np.ones(len(Xtr)) if rtr is None else rtr, dtype=torch.float32).unsqueeze(1)
    dl = DataLoader(TensorDataset(torch.tensor(Xtr), torch.tensor(ytr, dtype=torch.float32).unsqueeze(1), R),
                    batch_size=hp["batch"], shuffle=True, generator=g)
    opt = torch.optim.AdamW(m.parameters(), lr=hp["lr"], weight_decay=hp["wd"])
    E, wu = hp["epochs"], hp["warmup"]
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda e: (e + 1) / wu if e < wu else 0.5 * (1 + math.cos(math.pi * (e - wu) / max(1, E - wu))))
    best, best_state, stale = -1.0, None, 0
    Xv = torch.tensor(Xva, device=dev)
    for ep in range(1, E + 1):
        m.train()
        for bx, by, br in dl:
            bx, by, br = bx.to(dev), by.to(dev), br.to(dev)
            opt.zero_grad()
            focal(m(bx), by, br).backward()
            opt.step()
        sched.step()
        m.eval()
        with torch.no_grad():
            a = _auroc(yva, m(Xv).cpu().numpy().ravel())
        if a > best:
            best, best_state, stale = a, {k: v.detach().cpu().clone() for k, v in m.state_dict().items()}, 0
        else:
            stale += 1
        if ep == 1 or ep % 10 == 0:
            log(f"    epoch {ep:3d}  val AUROC {a:.4f}")
        if stale >= hp["patience"]:
            log(f"    early stop at epoch {ep}")
            break
    m.load_state_dict(best_state)
    m.cpu().eval()
    return m, best


def energy(model, X) -> np.ndarray:
    import torch
    with torch.no_grad():
        return model(torch.tensor(X)).numpy().ravel() * 10.0


# ---- A7: fine-tuned sentence encoder ----------------------------------------------------------------------

def train_sbert(tr: pd.DataFrame, va: pd.DataFrame, neg_w: float, hp=SBERT_HP, log=print):
    """MiniLM-L6 fine-tuned end to end with three sigmoid outputs and the head's masked loss (DESIGN.md 4, A7)."""
    import torch
    import torch.nn as nn
    from transformers import AutoModel, AutoTokenizer
    _seed()
    dev = _dev()
    tok = AutoTokenizer.from_pretrained(hp["model"])

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = AutoModel.from_pretrained(hp["model"])
            self.out = nn.Sequential(nn.Dropout(0.1), nn.Linear(self.enc.config.hidden_size, 3), nn.Sigmoid())

        def forward(self, ids, att):
            h = self.enc(input_ids=ids, attention_mask=att).last_hidden_state
            m = att.unsqueeze(-1).float()
            return self.out((h * m).sum(1) / m.sum(1).clamp_min(1.0))

    net = Net().to(dev)
    opt = torch.optim.AdamW(net.parameters(), lr=hp["lr"], weight_decay=0.01)
    dw = torch.tensor([1.0, HEAD_HP["i_weight"], 1.0], device=dev)

    def batches(df, shuffle):
        ix = np.arange(len(df))
        if shuffle:
            np.random.default_rng(SEED).shuffle(ix)
        for s in range(0, len(ix), hp["batch"]):
            b = df.iloc[ix[s:s + hp["batch"]]]
            enc = tok(b.text.tolist(), truncation=True, max_length=hp["max_len"], padding=True, return_tensors="pt")
            Y = torch.tensor(b[["T", "I", "F"]].to_numpy(dtype="float32"), device=dev)
            M = torch.tensor(b[["mask_T", "mask_I", "mask_F"]].to_numpy(dtype="float32"), device=dev)
            R = torch.tensor(b["rw"].to_numpy(dtype="float32") if "rw" in b else np.ones(len(b), dtype="float32"),
                             device=dev)
            yield enc["input_ids"].to(dev), enc["attention_mask"].to(dev), Y, (M + (1 - M) * neg_w) * R[:, None]

    def loss(p, Y, W):
        el = nn.functional.binary_cross_entropy(p, Y, reduction="none")
        return (el * dw * W).sum() / W.sum().clamp_min(1.0)

    best, best_state = 1e18, None
    for ep in range(hp["epochs"]):
        net.train()
        for i, (ids, att, Y, W) in enumerate(batches(tr, True)):
            l_ = loss(net(ids, att), Y, W)
            opt.zero_grad()
            l_.backward()
            opt.step()
            if i % 200 == 0:
                log(f"    epoch {ep + 1} batch {i} loss {float(l_):.4f}")
        net.eval()
        tot, cnt = 0.0, 0.0
        with torch.no_grad():
            for ids, att, Y, W in batches(va, False):
                el = nn.functional.binary_cross_entropy(net(ids, att), Y, reduction="none")
                tot += float((el * dw * W).sum())
                cnt += float(W.sum())
        vl = tot / max(cnt, 1.0)
        log(f"    epoch {ep + 1} val {vl:.4f}")
        if vl < best:
            best, best_state = vl, {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
    net.load_state_dict(best_state)
    net.eval()

    def infer(texts: list[str]) -> np.ndarray:
        out = []
        with torch.no_grad():
            for s in range(0, len(texts), 64):
                enc = tok(texts[s:s + 64], truncation=True, max_length=hp["max_len"], padding=True, return_tensors="pt")
                out.append(net(enc["input_ids"].to(dev), enc["attention_mask"].to(dev)).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 3), dtype="float32")
    return infer, best


# ---- FT: PEINN with its sentence encoders fine-tuned (DESIGN.md 13) ------------------------------------------

FT_ON = True
FT_HP = dict(epochs=3, lr_enc=2e-5, lr_out=1e-3, batch=32, accum=1, max_len=256, amp=False)
FT_ENC = {"energy": "sentence-transformers/all-mpnet-base-v2",       # the v2.1 calibrator's embedder (ee_runner.py)
          "head": "sentence-transformers/all-MiniLM-L6-v2"}          # the v2.1 head's embedder


def _fp32_model(cls, name: str):
    """transformers 5 keeps a checkpoint's fp16 weights (DeBERTa-v3-large ships fp16), and AdamW on fp16 weights gives
    NaN (PEINN_v2 peinn2/c/ftenc.py): load in float32 and check."""
    import torch
    try:
        m = cls.from_pretrained(name, dtype=torch.float32)
    except TypeError:
        m = cls.from_pretrained(name, torch_dtype=torch.float32)
    m = m.float()
    assert all(p.dtype == torch.float32 for p in m.parameters())
    return m


def train_ft(kind: str, tr: pd.DataFrame, va: pd.DataFrame, Xtr, Xva, neg_w: float = SHIPPED_NEG_W, hp=FT_HP, log=print):
    """The v2.1 network with its encoder trained end to end. kind 'energy': [emotion 32 | mpnet 768] -> calibrator,
    focal BCE on F >= .5 with class and row weights, selection by val AUROC. kind 'head': [emotion 32 | MiniLM 384 |
    principle 384] -> neutro head, BCE on T/I/F on every axis with row weights, selection by val loss.
    Xtr / Xva: the frozen blocks around the encoder slot (energy: emotion; head: emotion and principle).
    Returns (infer(texts, X) -> outputs, best val score)."""
    import torch
    import torch.nn as nn
    from transformers import AutoModel, AutoTokenizer
    _seed()
    dev = _dev()
    name = hp.get("enc") or FT_ENC[kind]
    tok = AutoTokenizer.from_pretrained(name)
    energy_kind = kind == "energy"

    class Net(nn.Module):
        def __init__(self):
            super().__init__()
            self.enc = _fp32_model(AutoModel, name)
            h = self.enc.config.hidden_size
            self.out = calibrator(32 + h) if energy_kind else mlp(32 + h + 384, 3, sigmoid=True)

        def forward(self, ids, att, x):
            h = self.enc(input_ids=ids, attention_mask=att).last_hidden_state
            m = att.unsqueeze(-1).float()
            e = (h * m).sum(1) / m.sum(1).clamp_min(1e-9)
            e = nn.functional.normalize(e, dim=1)              # both sentence-transformers models end in Normalize
            z = torch.cat([x[:, :32], e], 1) if energy_kind else torch.cat([x[:, :32], e, x[:, 32:]], 1)
            return self.out(z)

    net = Net().to(dev)
    opt = torch.optim.AdamW([{"params": net.enc.parameters(), "lr": hp["lr_enc"]},
                             {"params": net.out.parameters(), "lr": hp["lr_out"]}], weight_decay=0.01)
    acc = int(hp.get("accum") or 1)
    steps = max(1, hp["epochs"] * math.ceil(len(tr) / hp["batch"]) // acc)
    warm = max(1, int(0.06 * steps))                                       # linear warm-up 6 % then linear decay (ftenc)
    sched = torch.optim.lr_scheduler.LambdaLR(opt, lambda k: min((k + 1) / warm, max(0.0, (steps - k) / max(1, steps - warm))))
    ytr = (tr.F.to_numpy() >= 0.5).astype("float32")
    pos_w = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    neg_cw = float((ytr == 1).sum() / max(1, (ytr == 0).sum()))
    dw = torch.tensor([1.0, HEAD_HP["i_weight"], 1.0], device=dev)

    def batches(df, X, shuffle):
        ix = np.arange(len(df))
        if shuffle:
            np.random.default_rng(SEED).shuffle(ix)
        for s in range(0, len(ix), hp["batch"]):
            j = ix[s:s + hp["batch"]]
            b = df.iloc[j]
            enc = tok(b.text.astype(str).tolist(), truncation=True, max_length=hp["max_len"], padding=True,
                      return_tensors="pt")
            r = torch.tensor(b["rw"].to_numpy(dtype="float32") if "rw" in b else np.ones(len(b), "float32"), device=dev)
            x = torch.tensor(X[j], device=dev, dtype=torch.float32)
            if energy_kind:
                y = torch.tensor((b.F.to_numpy() >= 0.5).astype("float32"), device=dev).unsqueeze(1)
                w = (y * pos_w + (1 - y) * neg_cw) * r[:, None]
            else:
                y = torch.tensor(b[["T", "I", "F"]].to_numpy(dtype="float32"), device=dev)
                w = torch.tensor(head_weights(b, neg_w), device=dev) * r[:, None]
            yield enc["input_ids"].to(dev), enc["attention_mask"].to(dev), x, y, w

    def loss(p, y, w):
        p = p.clamp(1e-7, 1 - 1e-7)
        if energy_kind:                                                   # focal BCE as train_calibrator
            pt = y * p + (1 - y) * (1 - p)
            lp = y * torch.log(p) + (1 - y) * torch.log(1 - p)
            return -(w * (1 - pt).pow(CAL_HP["focal_gamma"]) * lp).mean()
        el = nn.functional.binary_cross_entropy(p, y, reduction="none")
        return (el * dw * w).sum() / w.sum().clamp_min(1.0)

    def predict(df, X):
        out = []
        net.eval()
        with torch.no_grad():
            for ids, att, x, _, _ in batches(df, X, False):
                out.append(fwd(ids, att, x).cpu().numpy())
        return np.concatenate(out) if out else np.zeros((0, 1 if energy_kind else 3), dtype="float32")

    amp = bool(hp.get("amp")) and dev.type == "cuda"

    def step_():
        torch.nn.utils.clip_grad_norm_(net.parameters(), 1.0)
        opt.step()
        sched.step()
        opt.zero_grad()

    def fwd(ids, att, x):
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=amp):
            h = net(ids, att, x)
        return h.float()

    best, best_state = None, None
    for ep in range(hp["epochs"]):
        net.train()
        opt.zero_grad()
        for i, (ids, att, x, y, w) in enumerate(batches(tr, Xtr, True)):
            l_ = loss(fwd(ids, att, x), y, w)
            (l_ / acc).backward()
            if (i + 1) % acc == 0:
                step_()
            if i % 200 == 0:
                log(f"    {kind} epoch {ep + 1} batch {i} loss {float(l_.detach()):.4f}")
        opt.zero_grad()                                                      # a last partial accumulation is dropped
        pv = predict(va, Xva)
        if energy_kind:
            if not np.isfinite(pv).all():
                raise SystemExit(f"{kind} ({name}): non-finite validation output at epoch {ep + 1}")
            sc = _auroc((va.F.to_numpy() >= 0.5).astype(int), pv.ravel())
            better = best is None or sc > best
        else:
            yv, wv = va[["T", "I", "F"]].to_numpy(dtype="float32"), head_weights(va, neg_w) * va["rw"].to_numpy()[:, None]
            el = -(yv * np.log(np.clip(pv, 1e-7, 1)) + (1 - yv) * np.log(np.clip(1 - pv, 1e-7, 1)))
            sc = float((el * np.array([1.0, HEAD_HP["i_weight"], 1.0]) * wv).sum() / max(wv.sum(), 1.0))
            better = best is None or sc < best
        log(f"    {kind} epoch {ep + 1} val {'AUROC' if energy_kind else 'loss'} {sc:.4f}")
        if better:
            best, best_state = sc, {k: v.detach().cpu().clone() for k, v in net.state_dict().items()}
    net.load_state_dict(best_state)

    def infer(texts: list[str], X) -> np.ndarray:
        df = pd.DataFrame({"text": texts, "F": 0.0, "T": 0.0, "I": 0.0, "mask_T": 1.0, "mask_I": 1.0, "mask_F": 1.0})
        return predict(df, X)
    return infer, best


# ---- step T ------------------------------------------------------------------------------------------------

VARIANTS = ("A0", "A1", "A2", "A3", "A6p", "A6e", "A7")


def sigdir(check: bool) -> Path:
    d = D.wdir(check) / "signals"
    d.mkdir(parents=True, exist_ok=True)
    return d


def train_all(check: bool = False, log=print) -> int:
    import torch
    sp = D.load_split(check)
    F = D.load_features(check)
    rec = D.record_texts(check)
    meta = shipped_meta()
    neg_w = SHIPPED_NEG_W
    log(f"shipped head recipe: {json.dumps({k: v for k, v in meta.items() if k != 'arch'})}; trained on every axis "
        f"(neg_weight {neg_w}, DESIGN.md 4)")
    tr, va, te = (sp[sp.split == s].reset_index(drop=True) for s in ("train", "val", "test"))
    if check:
        tr = tr if len(tr) else sp
        va = va if len(va) else sp.head(20)
    uni = pd.DataFrame({"sha": list(va.sha) + list(te.sha) + list(rec.sha),
                        "part": ["val"] * len(va) + ["test"] * len(te) + ["bench"] * len(rec),
                        "text": list(va.text) + list(te.text) + list(rec.text)})
    ru = D.rows_of(F, uni.sha)
    Hx, Cx = F["head_x"], F["cal_x"]
    rtr, rva = D.rows_of(F, tr.sha), D.rows_of(F, va.sha)
    wtr, wva = row_weights(tr, tr), row_weights(tr, va)                              # DESIGN.md 12
    tr, va = tr.assign(rw=wtr), va.assign(rw=wva)
    rw_src = {k: round(float(v), 3) for k, v in tr.groupby("source").rw.first().items()}
    Y = lambda d: d[["T", "I", "F"]].to_numpy(dtype="float32")                       # noqa: E731
    W = lambda d: head_weights(d, neg_w)                                              # noqa: E731
    hp = dict(HEAD_HP, epochs=3) if check else HEAD_HP
    chp = dict(CAL_HP, epochs=3) if check else CAL_HP
    md = D.wdir(check) / "models"
    md.mkdir(parents=True, exist_ok=True)
    report = {"neg_weight": neg_w, "row_weight": ROW_WEIGHT, "row_weight_by_source": rw_src, "n": {"train": len(tr), "val": len(va), "test": len(te), "bench": len(rec)}}

    log("== energy calibrator (label F >= 0.5)")
    ytr, yva = (tr.F.to_numpy() >= 0.5).astype("float32"), (va.F.to_numpy() >= 0.5).astype("float32")
    cal, auc = train_calibrator(Cx[rtr], ytr, Cx[rva], yva, chp, log, rtr=wtr)
    torch.save(cal.state_dict(), md / "calibrator.pt")
    E = energy(cal, Cx[ru])
    report["calibrator_val_auroc"] = auc

    def save(name, E_=None, **arrs):
        bad = [k for k, v in {"E": E if E_ is None else E_, **arrs}.items() if not np.isfinite(np.asarray(v, float)).all()]
        if bad:
            raise SystemExit(f"{name}: non-finite {bad} (training diverged)")
        np.savez(sigdir(check) / f"{name}.npz", sha=uni.sha.to_numpy(), part=uni.part.to_numpy(),
                 E=E if E_ is None else E_, **arrs)

    cols = {"A0": slice(0, 800), "A6p": np.r_[0:416], "A6e": np.r_[32:800]}
    for name, ix in cols.items():
        log(f"== {name}: T/I/F head on {'all 800' if name == 'A0' else ('no principle block' if name == 'A6p' else 'no affect block')}")
        m, vl = train_head(Hx[rtr][:, ix], Y(tr), W(tr), Hx[rva][:, ix], Y(va), W(va), "sigmoid",
                           [1.0, hp["i_weight"], 1.0], hp, log, wtr, wva)
        torch.save(m.state_dict(), md / f"{name}.pt")
        p = predict(m, Hx[ru][:, ix], "sigmoid")
        save(name, T=p[:, 0], I=p[:, 1], F=p[:, 2])
        report[f"{name}_val_loss"] = vl

    log("== A1: T/F head (no I)")
    m, vl = train_head(Hx[rtr], Y(tr)[:, [0, 2]], W(tr)[:, [0, 2]], Hx[rva], Y(va)[:, [0, 2]], W(va)[:, [0, 2]],
                       "sigmoid", [1.0, 1.0], hp, log, wtr, wva)
    torch.save(m.state_dict(), md / "A1.pt")
    p = predict(m, Hx[ru], "sigmoid")
    save("A1", T=p[:, 0], I=np.zeros(len(p)), F=p[:, 1])
    report["A1_val_loss"] = vl

    log("== A2: softmax safe / ambiguous / harmful")
    ctr, cva = three_class(tr["T"], tr["I"], tr["F"]), three_class(va["T"], va["I"], va["F"])
    m, vl = train_head(Hx[rtr], ctr, None, Hx[rva], cva, None, "softmax", None, hp, log, wtr, wva)
    torch.save(m.state_dict(), md / "A2.pt")
    p = predict(m, Hx[ru], "softmax")
    save("A2", T=p[:, 0], I=p[:, 1], F=p[:, 2])
    report["A2_val_loss"] = vl
    report["A2_class_counts_train"] = {k: int(v) for k, v in zip(("safe", "ambiguous", "harmful"), np.bincount(ctr, minlength=3))}

    log("== A3: binary harm classifier (F >= 0.5)")
    m, vl = train_head(Hx[rtr], ytr, None, Hx[rva], yva, None, "binary", None, hp, log, wtr, wva)
    torch.save(m.state_dict(), md / "A3.pt")
    p = predict(m, Hx[ru], "binary").ravel()
    save("A3", T=1 - p, I=np.zeros(len(p)), F=p)
    report["A3_val_loss"] = vl

    log("== A7: fine-tuned MiniLM (T/I/F, same loss)")
    shp = dict(SBERT_HP, epochs=1) if check else SBERT_HP
    trs = tr.sample(n=min(len(tr), 64), random_state=0) if check else tr
    infer, vl = train_sbert(trs, va, neg_w, shp, log)
    p = infer(uni.text.tolist())
    save("A7", T=p[:, 0], I=p[:, 1], F=p[:, 2])
    report["A7_val_loss"] = vl

    if FT_ON:
        log("== A0ft: PEINN with the calibrator's mpnet and the head's MiniLM fine-tuned (DESIGN.md 13)")
        fhp = dict(FT_HP, epochs=1) if check else FT_HP
        hb = np.r_[0:32, 416:800]                                                  # emotion | principle
        e_inf, e_auc = train_ft("energy", trs, va, Cx[D.rows_of(F, trs.sha)][:, :32], Cx[rva][:, :32], neg_w, fhp, log)
        E_ft = e_inf(uni.text.tolist(), Cx[ru][:, :32]).ravel() * 10.0
        h_inf, h_vl = train_ft("head", trs, va, Hx[D.rows_of(F, trs.sha)][:, hb], Hx[rva][:, hb], neg_w, fhp, log)
        p = h_inf(uni.text.tolist(), Hx[ru][:, hb])
        save("A0ft", E_=E_ft, T=p[:, 0], I=p[:, 1], F=p[:, 2])
        report["A0ft_energy_val_auroc"], report["A0ft_head_val_loss"] = e_auc, h_vl

    # reference: the shipped (bench-contaminated) system, never used for fitting or reported as a result
    save("SHIPPED", T=F["tif"][ru, 0], I=F["tif"][ru, 1], F=F["tif"][ru, 2])
    np.savez(sigdir(check) / "SHIPPED_E.npz", sha=uni.sha.to_numpy(), E=F["e1"][ru])
    C.jdump(report, D.odir(check) / "train_report.json")
    log(json.dumps(report))
    if check:
        return 0
    return 0 if C.publish([D.odir(check) / "train_report.json"], "v21r T: variants A0-A7 trained on the isolated corpus (seed 42)") else 1


def load_signals(check: bool, name: str) -> dict:
    z = np.load(sigdir(check) / f"{name}.npz", allow_pickle=True)
    d = {k: z[k] for k in z.files}
    if name == "SHIPPED":
        e = np.load(sigdir(check) / "SHIPPED_E.npz", allow_pickle=True)
        d["E"] = e["E"]
    return d
