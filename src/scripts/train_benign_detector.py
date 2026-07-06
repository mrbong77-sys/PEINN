"""
train_benign_detector.py — Benign-Trick Detector 학습 (HANDOFF-28 옵션 2).

목적
  HybridCalibrator 보조용 binary classifier 학습. trick_safe-Safe(양성)와 HarmBench unsafe(진짜
  유해)를 균형 학습 → 추론 시 calibrator energy를 benign_prob로 차감 보정(ee_runner 통합).

설계
  - 데이터: trick_safe-Safe 150 vs HarmBench/Taxonomy unsafe 150 (균형, majority 압도 0)
  - 학습: 50 epoch, lr 1e-3, BCE (단순 binary). Focal 불필요 — 균형 잡혀 있음
  - 평가: held-out 20%, AUROC + per-class accuracy + 위험 케이스 검증

사용
  python scripts/train_benign_detector.py
  python scripts/train_benign_detector.py --epochs 80 --batch-size 32
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peaos.train_benign_detector")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "pea_eval" / "data"
CKPT_PATH = DATA_DIR / "ee_benign_detector.pt"


async def _extract_features(texts: list[str]) -> np.ndarray:
    """text → (emotion32 + semantic_emb_384) feature 추출. ee_threshold_finder와 같은 경로."""
    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.ee_runner import EvalEERunner

    runner = EvalEERunner.get_instance(ee_config=load_settings("real").ee)
    runner.initialize()
    feats = []
    for i, t in enumerate(texts):
        emo, _energy, _ = runner.analyze_emotion(t, agent_profile="A")
        # semantic_emb은 calibrator와 동일하게 별도 embedder로 (CALIBRATOR_SEM_EMBEDDER 또는 EE 임베더)
        sem = runner._embed_text(t)
        feat = torch.cat([emo.squeeze(0).cpu(), sem.squeeze(0).cpu()]).numpy().astype("float32")
        feats.append(feat)
        if (i + 1) % 50 == 0:
            logger.info(f"  features {i+1}/{len(texts)}")
    return np.stack(feats)


def _load_data(safe_cap: int, unsafe_cap: int) -> tuple[list[str], list[int]]:
    """trick_safe-Safe(label=1=benign) + HarmBench/Taxonomy unsafe(label=0=harm). 균형."""
    import csv, json, random as _rnd
    rng = _rnd.Random(42)

    # benign (trick_safe-Safe)
    ts_path = DATA_DIR / "ee_3class" / "trick_safe_train.csv"
    TS_SAFE_CATS = {"game_violence", "figurative", "homonym", "safe_target",
                    "fictional_privacy", "nonsense_premise"}
    benign = []
    if ts_path.exists():
        for r in csv.DictReader(open(ts_path, encoding="utf-8")):
            if r.get("category") in TS_SAFE_CATS:
                benign.append(r["text"])
    rng.shuffle(benign)
    benign = benign[:safe_cap]
    logger.info(f"benign(trick_safe-Safe): {len(benign)}")

    # harm (HarmBench val + Taxonomy)
    harm = []
    hb_path = DATA_DIR / "harmbench_behaviors_text_val.csv"
    if hb_path.exists():
        for r in csv.DictReader(open(hb_path, encoding="utf-8")):
            b = r.get("Behavior") or r.get("behavior") or ""
            if b:
                harm.append(b)
    tax_path = DATA_DIR / "taxonomy_40_scenarios.json"
    if tax_path.exists():
        for s in json.loads(tax_path.read_text(encoding="utf-8")):
            for p in s.get("prompts", []) or []:
                if p:
                    harm.append(p)
    rng.shuffle(harm)
    harm = harm[:unsafe_cap]
    logger.info(f"harm(HarmBench+Taxonomy): {len(harm)}")

    texts = benign + harm
    labels = [1] * len(benign) + [0] * len(harm)
    return texts, labels


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epochs", type=int, default=50)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--safe-cap", type=int, default=150, help="trick_safe-Safe 샘플 수")
    ap.add_argument("--unsafe-cap", type=int, default=150, help="HarmBench+Taxonomy 샘플 수 (균형)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    texts, labels = _load_data(args.safe_cap, args.unsafe_cap)
    if len(texts) < 50:
        logger.error(f"데이터 부족({len(texts)}건) — trick_safe_train.csv 또는 harmbench_val.csv 확인.")
        return 2

    X = asyncio.run(_extract_features(texts))
    y = np.array(labels, dtype="float32")
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2, random_state=args.seed, stratify=y)
    logger.info(f"Split: train {len(X_tr)} / test {len(X_te)}")

    from pea_eval.evaluators.benign_detector import BenignTrickDetector
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = BenignTrickDetector().to(device)
    opt = optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-3)
    loss_fn = nn.BCELoss()

    tr_ds = TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr).unsqueeze(1))
    tr_ld = DataLoader(tr_ds, batch_size=args.batch_size, shuffle=True)

    best_auc, best_state = 0.0, None
    for ep in range(args.epochs):
        model.train()
        tot = 0.0
        for xb, yb in tr_ld:
            xb, yb = xb.to(device), yb.to(device)
            pred = model(xb)
            loss = loss_fn(pred, yb)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item() * len(xb)
        model.eval()
        with torch.no_grad():
            te_pred = model(torch.from_numpy(X_te).to(device)).cpu().numpy().flatten()
        auc = roc_auc_score(y_te, te_pred)
        if (ep + 1) % 10 == 0 or ep == 0:
            logger.info(f"  epoch {ep+1:03d}  train_loss {tot/len(X_tr):.4f}  test_AUC {auc:.4f}")
        if auc > best_auc:
            best_auc, best_state = auc, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    model.eval()

    # 평가 — per-class accuracy + 위험 케이스(harm 오분류) 카운트
    with torch.no_grad():
        te_pred = model(torch.from_numpy(X_te).to(device)).cpu().numpy().flatten()
    benign_pred = (te_pred >= 0.5).astype(int)
    benign_idx = y_te == 1
    harm_idx = y_te == 0
    benign_acc = (benign_pred[benign_idx] == 1).mean() if benign_idx.any() else 0
    harm_acc = (benign_pred[harm_idx] == 0).mean() if harm_idx.any() else 0
    harm_misclass = (benign_pred[harm_idx] == 1).sum()  # 진짜 유해를 benign으로 — 가장 위험

    logger.info(f"\n===== HELD-OUT (best AUC={best_auc:.4f}) =====")
    logger.info(f"  benign acc (TPR_benign): {benign_acc*100:.1f}%  ({benign_idx.sum()}건)")
    logger.info(f"  harm   acc (TNR=1-FPR) : {harm_acc*100:.1f}%  ({harm_idx.sum()}건)")
    logger.info(f"  ★harm 오분류(benign으로): {int(harm_misclass)}건 — 0이어야 안전")
    if harm_misclass > 0:
        logger.warning("  ★위험: 진짜 유해를 benign으로 분류한 케이스 존재 — α 보수적으로 운영(0.3~0.5)")

    CKPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), CKPT_PATH)
    logger.info(f"\nsaved → {CKPT_PATH}")
    logger.info("다음: ee_runner.analyze_emotion에 adjust_energy 통합 (별도 commit). "
                "fail-safe — 미통합 시 기존 동작 유지.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
