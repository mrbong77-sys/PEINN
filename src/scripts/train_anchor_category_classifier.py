#!/usr/bin/env python3
"""
AnchorCategoryClassifier 학습 (6-way 윤리 전통 분류).

입력: pea_eval/data/anchor_category_train.jsonl (build_anchor_category_dataset.py)
출력: pea_eval/data/anchor_category_classifier_best.pt
      pea_eval/data/anchor_category_classifier_best.labels.json (라벨 순서)

dilemma classifier와 동일 패턴: mpnet 임베딩 캐시 + cross-entropy + 80/20 split.
class imbalance 대비 class-weighted loss. per-category accuracy + confusion 출력.

DGX:
  python scripts/build_anchor_category_dataset.py
  python scripts/train_anchor_category_classifier.py
"""
from __future__ import annotations

import json
import logging
import os
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("train_anchor_category_classifier")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA = REPO_ROOT / "pea_eval" / "data" / "anchor_category_train.jsonl"
MODEL_OUT = REPO_ROOT / "pea_eval" / "data" / "anchor_category_classifier_best.pt"
LABELS_OUT = MODEL_OUT.with_suffix(".labels.json")
EMB_CACHE = REPO_ROOT / "pea_eval" / "data" / "anchor_category_train_emb.npz"

EMBEDDER = os.environ.get("PEAOS_CALIBRATOR_EMBEDDER", "sentence-transformers/all-mpnet-base-v2")
# "none" = non-moral abstain 클래스 (7-way). 런타임에서 none 예측 시 글로벌
# cosine fallback. dilemma_train NEG가 none으로 라벨됨.
CATEGORIES = ["confucian", "utilitarian", "kantian", "existentialist", "postmodern", "care_meta", "none"]
EPOCHS, BATCH, LR, SEED = 25, 64, 1e-3, 42


class AnchorCategoryClassifier(nn.Module):
    def __init__(self, sem_dim=768, hidden_dim=128, n_classes=6):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(sem_dim, hidden_dim), nn.ReLU(), nn.Dropout(0.2),
            nn.Linear(hidden_dim, 64), nn.ReLU(),
            nn.Linear(64, n_classes),
        )
    def forward(self, x): return self.net(x)


def _embed_or_load():
    if EMB_CACHE.exists():
        d = np.load(EMB_CACHE)
        return d["X"], d["y"]
    if not DATA.exists():
        raise SystemExit(f"학습 데이터 미존재: {DATA}")
    rows = []
    with open(DATA, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    label_to_idx = {c: i for i, c in enumerate(CATEGORIES)}
    rows = [r for r in rows if r.get("category") in label_to_idx and r.get("text")]
    texts = [r["text"] for r in rows]
    y = np.array([label_to_idx[r["category"]] for r in rows], dtype=np.int64)
    from sentence_transformers import SentenceTransformer
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"임베딩 {len(texts)}건 ({EMBEDDER})")
    X = SentenceTransformer(EMBEDDER, device=dev).encode(
        texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True).astype(np.float32)
    np.savez(EMB_CACHE, X=X, y=y)
    return X, y


def main() -> int:
    torch.manual_seed(SEED); np.random.seed(SEED)
    X, y = _embed_or_load()
    dist = Counter(int(v) for v in y)
    logger.info(f"클래스 분포: {{{', '.join(f'{CATEGORIES[k]}:{dist.get(k,0)}' for k in range(len(CATEGORIES)))}}}")

    n = len(X); idx = np.arange(n); np.random.shuffle(idx)
    cut = int(n * 0.8); tr, va = idx[:cut], idx[cut:]
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    Xtr, ytr = torch.from_numpy(X[tr]), torch.from_numpy(y[tr])
    Xva, yva = torch.from_numpy(X[va]), torch.from_numpy(y[va])

    # class-weighted CE (imbalance 대비)
    counts = np.bincount(y[tr], minlength=len(CATEGORIES)).astype(np.float32)
    weights = torch.tensor((counts.sum() / (counts + 1e-6)) / len(CATEGORIES), dtype=torch.float32).to(dev)
    model = AnchorCategoryClassifier(n_classes=len(CATEGORIES)).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-2)
    loss_fn = nn.CrossEntropyLoss(weight=weights)
    loader = DataLoader(TensorDataset(Xtr, ytr), batch_size=BATCH, shuffle=True)

    best_acc = -1.0
    for ep in range(1, EPOCHS + 1):
        model.train()
        for xb, yb in loader:
            xb, yb = xb.to(dev), yb.to(dev)
            opt.zero_grad(); loss = loss_fn(model(xb), yb); loss.backward(); opt.step()
        model.eval()
        with torch.no_grad():
            pred = model(Xva.to(dev)).argmax(-1).cpu().numpy()
        acc = float((pred == yva.numpy()).mean())
        if ep % 5 == 0 or ep == EPOCHS:
            logger.info(f"epoch {ep:02d}  val_acc={acc:.3f}")
        if acc > best_acc:
            best_acc = acc
            MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), MODEL_OUT)
            LABELS_OUT.write_text(json.dumps({"labels": CATEGORIES}, ensure_ascii=False))

    # confusion + per-category
    model.load_state_dict(torch.load(MODEL_OUT, map_location=dev)); model.eval()
    with torch.no_grad():
        pred = model(Xva.to(dev)).argmax(-1).cpu().numpy()
    yv = yva.numpy()
    logger.info(f"best val_acc={best_acc:.3f}  (labels saved: {LABELS_OUT.name})")
    logger.info("per-category recall:")
    for k, c in enumerate(CATEGORIES):
        mask = yv == k
        rec = float((pred[mask] == k).mean()) if mask.any() else float("nan")
        logger.info(f"  {c:15s} n={int(mask.sum()):4d}  recall={rec:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
