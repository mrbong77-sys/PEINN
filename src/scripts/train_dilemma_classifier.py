#!/usr/bin/env python3
"""
DilemmaClassifier 학습 스크립트.

입력: pea_eval/data/dilemma_train.jsonl  (build_dilemma_dataset.py 산출물)
출력: pea_eval/data/dilemma_classifier_best.pt  (DilemmaRunner가 자동 로드)

설계 메모:
  - mpnet (all-mpnet-base-v2, 768d) 임베딩을 한 번 계산해 캐시 → 학습 빠름
  - HybridCalibrator 학습 패턴과 동일하게 BCE + Adam + 20% holdout
  - 임계값(τ)은 val PR curve에서 F1 최대점으로 자동 선택, 로그에 출력

DGX에서:
  python scripts/build_dilemma_dataset.py
  python scripts/train_dilemma_classifier.py
"""
from __future__ import annotations

import json
import logging
import os
import random
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("train_dilemma_classifier")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = REPO_ROOT / "pea_eval" / "data" / "dilemma_train.jsonl"
MODEL_OUT = REPO_ROOT / "pea_eval" / "data" / "dilemma_classifier_best.pt"
EMB_CACHE = REPO_ROOT / "pea_eval" / "data" / "dilemma_train_emb.npz"

EMBEDDER_NAME = os.environ.get(
    "PEAOS_CALIBRATOR_EMBEDDER", "sentence-transformers/all-mpnet-base-v2"
)
SEM_DIM = 768
RANDOM_SEED = 42
EPOCHS = 15
BATCH = 64
LR = 1e-3


def _embed_or_load() -> tuple[np.ndarray, np.ndarray]:
    """텍스트를 mpnet으로 임베딩. 이미 캐시된 .npz가 있으면 재사용."""
    if EMB_CACHE.exists():
        d = np.load(EMB_CACHE)
        return d["X"], d["y"]

    from sentence_transformers import SentenceTransformer
    if not DATA_PATH.exists():
        raise SystemExit(f"학습 데이터 미존재: {DATA_PATH} (build_dilemma_dataset.py 먼저 실행)")
    # NOTE: str.splitlines()은 U+2028/U+2029도 줄 구분자로 인식하지만 json.dumps
    # 는 이를 escape하지 않아 JSON 레코드가 깨질 수 있다. file iterator는 \n
    # 만 줄로 인식하므로 안전.
    rows = []
    with open(DATA_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    texts = [r["text"] for r in rows]
    labels = np.array([r["label"] for r in rows], dtype=np.float32)
    logger.info(f"임베딩 시작: {len(texts)}건 ({EMBEDDER_NAME})")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(EMBEDDER_NAME, device=device)
    X = model.encode(texts, batch_size=64, show_progress_bar=True, convert_to_numpy=True)
    X = X.astype(np.float32)
    np.savez(EMB_CACHE, X=X, y=labels)
    logger.info(f"임베딩 캐시 저장: {EMB_CACHE}")
    return X, labels


class DilemmaClassifier(nn.Module):
    def __init__(self, sem_dim: int = SEM_DIM, hidden_dim: int = 128):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(sem_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x)


def _best_threshold(probs: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """val 집합에서 F1을 최대화하는 임계값."""
    best_f1, best_t = -1.0, 0.5
    for t in np.linspace(0.05, 0.95, 91):
        pred = (probs >= t).astype(np.int32)
        tp = int(((pred == 1) & (y == 1)).sum())
        fp = int(((pred == 1) & (y == 0)).sum())
        fn = int(((pred == 0) & (y == 1)).sum())
        if tp == 0:
            continue
        prec = tp / (tp + fp + 1e-9)
        rec = tp / (tp + fn + 1e-9)
        f1 = 2 * prec * rec / (prec + rec + 1e-9)
        if f1 > best_f1:
            best_f1, best_t = float(f1), float(t)
    return best_t, best_f1


def main() -> int:
    torch.manual_seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    random.seed(RANDOM_SEED)

    X, y = _embed_or_load()
    n = len(X)
    logger.info(f"전체 임베딩: {n}건")

    # Shortcut 진단: POS/NEG 텍스트 길이 분포 비교.
    # 길이 갭이 크면 분류기가 "긴 텍스트 = dilemma" 라는 spurious cue를
    # 학습할 위험. F1 1.0 + 높은 val_loss는 정확히 이 신호.
    if DATA_PATH.exists():
        import statistics
        lens = {0: [], 1: []}
        with open(DATA_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                lens[r["label"]].append(len(r["text"]))
        if lens[0] and lens[1]:
            m0, m1 = statistics.median(lens[0]), statistics.median(lens[1])
            logger.info(f"길이 분포 (median chars): NEG={m0:.0f}, POS={m1:.0f}, ratio={m1/max(m0,1):.2f}")
            if max(m0, m1) / max(min(m0, m1), 1) > 3.0:
                logger.warning(
                    "⚠ POS/NEG 길이가 3배 이상 차이남 — 분류기가 길이 shortcut을 "
                    "학습할 위험. val F1가 비현실적으로 높으면 의심."
                )

    idx = np.arange(n)
    np.random.shuffle(idx)
    cut = int(n * 0.8)
    tr, va = idx[:cut], idx[cut:]
    X_tr, y_tr = torch.from_numpy(X[tr]), torch.from_numpy(y[tr]).unsqueeze(1)
    X_va, y_va = torch.from_numpy(X[va]), torch.from_numpy(y[va]).unsqueeze(1)
    logger.info(f"train={len(tr)}, val={len(va)}, pos_ratio_tr={y_tr.mean().item():.3f}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DilemmaClassifier().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=LR)
    loss_fn = nn.BCELoss()

    loader = DataLoader(TensorDataset(X_tr, y_tr), batch_size=BATCH, shuffle=True)
    best_val_loss = float("inf")
    for epoch in range(1, EPOCHS + 1):
        model.train()
        total = 0.0
        for xb, yb in loader:
            xb, yb = xb.to(device), yb.to(device)
            opt.zero_grad()
            p = model(xb)
            loss = loss_fn(p, yb)
            loss.backward()
            opt.step()
            total += loss.item() * xb.size(0)
        tr_loss = total / len(X_tr)

        model.eval()
        with torch.no_grad():
            p_va = model(X_va.to(device)).cpu().numpy().flatten()
            va_loss = float(nn.BCELoss()(torch.from_numpy(p_va).unsqueeze(1), y_va).item())
        acc = float(((p_va >= 0.5).astype(np.int32) == y_va.numpy().flatten()).mean())
        logger.info(f"epoch {epoch:02d} | train_loss={tr_loss:.4f} val_loss={va_loss:.4f} acc@0.5={acc:.3f}")

        if va_loss < best_val_loss:
            best_val_loss = va_loss
            MODEL_OUT.parent.mkdir(parents=True, exist_ok=True)
            torch.save(model.state_dict(), MODEL_OUT)
            logger.info(f"  → best 갱신, 저장: {MODEL_OUT}")

    # 최적 임계값
    model.load_state_dict(torch.load(MODEL_OUT, map_location=device))
    model.eval()
    with torch.no_grad():
        p_va = model(X_va.to(device)).cpu().numpy().flatten()
    t, f1 = _best_threshold(p_va, y_va.numpy().flatten())
    logger.info(f"권장 임계값(τ) = {t:.3f}  (val F1={f1:.3f})")
    # Sidecar로 저장 — DilemmaRunner가 자동 로드 (env var override 가능)
    sidecar = MODEL_OUT.with_suffix(".threshold.json")
    sidecar.write_text(json.dumps({"threshold": round(t, 4), "val_f1": round(f1, 4)}, ensure_ascii=False))
    logger.info(f"  → sidecar 저장: {sidecar}  (런타임 자동 로드)")
    logger.info(f"  → env override 원하면: export PEAOS_DILEMMA_THRESHOLD={t:.3f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
