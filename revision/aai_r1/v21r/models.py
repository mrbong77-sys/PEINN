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


def head_weights(d: pd.DataFrame, neg_w: float) -> np.ndarray:
    """Per-element loss weights: 1 where the axis is labelled, neg_w where it holds the placeholder 0."""
    M = d[["mask_T", "mask_I", "mask_F"]].to_numpy(dtype="float32")
    return M + (1 - M) * neg_w


# ---- heads on frozen features -------------------------------------------------------------------------

def train_head(Xtr, Ytr, Wtr, Xva, Yva, Wva, kind: str, dim_w=None, hp=HEAD_HP, log=print):
    """kind 'sigmoid': masked soft-target BCE (weights W per element); 'softmax': cross-entropy on class ids (Y 1-d);
    'binary': BCE on a 0/1 target. Model selection by the lowest validation loss."""
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
    if kind == "sigmoid":
        Wt, Wv = torch.tensor(Wtr, device=dev, dtype=torch.float32), torch.tensor(Wva, device=dev, dtype=torch.float32)
        dw = torch.tensor(dim_w if dim_w is not None else [1.0] * k, device=dev, dtype=torch.float32)

    def loss_fn(pred, y, w=None):
        if kind == "softmax":
            return nn.functional.cross_entropy(pred, y)
        el = nn.functional.binary_cross_entropy(pred, y, reduction="none")
        if kind == "binary":
            return el.mean()
        return (el * dw * w).sum() / w.sum().clamp_min(1.0)

    best, best_state, n = 1e18, None, len(Xt)
    for ep in range(hp["epochs"]):
        model.train()
        perm = torch.randperm(n, device=dev)
        for s in range(0, n, hp["batch"]):
            ix = perm[s:s + hp["batch"]]
            loss = loss_fn(model(Xt[ix]), Yt[ix], Wt[ix] if kind == "sigmoid" else None)
            opt.zero_grad()
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = float(loss_fn(model(Xv), Yv, Wv if kind == "sigmoid" else None))
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

def calibrator():
    import torch.nn as nn
    return nn.Sequential(nn.Linear(800, 64), nn.ReLU(), nn.Dropout(0.2), nn.Linear(64, 32), nn.ReLU(),
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


def train_calibrator(Xtr, ytr, Xva, yva, hp=CAL_HP, log=print):
    """ee_threshold_finder.train_calibrator: class-weighted focal BCE, AdamW, cosine LR with warm-up, selection by
    validation AUROC, patience 12."""
    import torch
    from torch.utils.data import DataLoader, TensorDataset
    _seed()
    dev = _dev()
    m = calibrator().to(dev)
    pos_w = float((ytr == 0).sum() / max(1, (ytr == 1).sum()))
    neg_w = float((ytr == 1).sum() / max(1, (ytr == 0).sum()))

    def focal(pred, t):
        pred = pred.clamp(1e-7, 1 - 1e-7)
        w = t * pos_w + (1 - t) * neg_w
        pt = t * pred + (1 - t) * (1 - pred)
        lp = t * torch.log(pred) + (1 - t) * torch.log(1 - pred)
        return -(w * (1 - pt).pow(hp["focal_gamma"]) * lp).mean()

    g = torch.Generator().manual_seed(SEED)
    dl = DataLoader(TensorDataset(torch.tensor(Xtr), torch.tensor(ytr, dtype=torch.float32).unsqueeze(1)),
                    batch_size=hp["batch"], shuffle=True, generator=g)
    opt = torch.optim.AdamW(m.parameters(), lr=hp["lr"], weight_decay=hp["wd"])
    E, wu = hp["epochs"], hp["warmup"]
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda e: (e + 1) / wu if e < wu else 0.5 * (1 + math.cos(math.pi * (e - wu) / max(1, E - wu))))
    best, best_state, stale = -1.0, None, 0
    Xv = torch.tensor(Xva, device=dev)
    for ep in range(1, E + 1):
        m.train()
        for bx, by in dl:
            bx, by = bx.to(dev), by.to(dev)
            opt.zero_grad()
            focal(m(bx), by).backward()
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
            yield enc["input_ids"].to(dev), enc["attention_mask"].to(dev), Y, M + (1 - M) * neg_w

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
    Y = lambda d: d[["T", "I", "F"]].to_numpy(dtype="float32")                       # noqa: E731
    W = lambda d: head_weights(d, neg_w)                                              # noqa: E731
    hp = dict(HEAD_HP, epochs=3) if check else HEAD_HP
    chp = dict(CAL_HP, epochs=3) if check else CAL_HP
    md = D.wdir(check) / "models"
    md.mkdir(parents=True, exist_ok=True)
    report = {"neg_weight": neg_w, "n": {"train": len(tr), "val": len(va), "test": len(te), "bench": len(rec)}}

    log("== energy calibrator (label F >= 0.5)")
    ytr, yva = (tr.F.to_numpy() >= 0.5).astype("float32"), (va.F.to_numpy() >= 0.5).astype("float32")
    cal, auc = train_calibrator(Cx[rtr], ytr, Cx[rva], yva, chp, log)
    torch.save(cal.state_dict(), md / "calibrator.pt")
    E = energy(cal, Cx[ru])
    report["calibrator_val_auroc"] = auc

    def save(name, **arrs):
        np.savez(sigdir(check) / f"{name}.npz", sha=uni.sha.to_numpy(), part=uni.part.to_numpy(), E=E, **arrs)

    cols = {"A0": slice(0, 800), "A6p": np.r_[0:416], "A6e": np.r_[32:800]}
    for name, ix in cols.items():
        log(f"== {name}: T/I/F head on {'all 800' if name == 'A0' else ('no principle block' if name == 'A6p' else 'no affect block')}")
        m, vl = train_head(Hx[rtr][:, ix], Y(tr), W(tr), Hx[rva][:, ix], Y(va), W(va), "sigmoid",
                           [1.0, hp["i_weight"], 1.0], hp, log)
        torch.save(m.state_dict(), md / f"{name}.pt")
        p = predict(m, Hx[ru][:, ix], "sigmoid")
        save(name, T=p[:, 0], I=p[:, 1], F=p[:, 2])
        report[f"{name}_val_loss"] = vl

    log("== A1: T/F head (no I)")
    m, vl = train_head(Hx[rtr], Y(tr)[:, [0, 2]], W(tr)[:, [0, 2]], Hx[rva], Y(va)[:, [0, 2]], W(va)[:, [0, 2]],
                       "sigmoid", [1.0, 1.0], hp, log)
    torch.save(m.state_dict(), md / "A1.pt")
    p = predict(m, Hx[ru], "sigmoid")
    save("A1", T=p[:, 0], I=np.zeros(len(p)), F=p[:, 1])
    report["A1_val_loss"] = vl

    log("== A2: softmax safe / ambiguous / harmful")
    ctr, cva = three_class(tr["T"], tr["I"], tr["F"]), three_class(va["T"], va["I"], va["F"])
    m, vl = train_head(Hx[rtr], ctr, None, Hx[rva], cva, None, "softmax", None, hp, log)
    torch.save(m.state_dict(), md / "A2.pt")
    p = predict(m, Hx[ru], "softmax")
    save("A2", T=p[:, 0], I=p[:, 1], F=p[:, 2])
    report["A2_val_loss"] = vl
    report["A2_class_counts_train"] = {k: int(v) for k, v in zip(("safe", "ambiguous", "harmful"), np.bincount(ctr, minlength=3))}

    log("== A3: binary harm classifier (F >= 0.5)")
    m, vl = train_head(Hx[rtr], ytr, None, Hx[rva], yva, None, "binary", None, hp, log)
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
