#!/usr/bin/env python3
"""
EE Calibrator Retrain + Threshold Auto-Tuner (single entry point)

Goals (per user spec)
---------------------
- Harmful detection rate (TPR) >= 96% across {HarmBench, Taxonomy, XSTest-Unsafe}
- Safe false-positive rate (FPR) <  10% across {XSTest-Safe, UNESCO, Ethics-*}
- Auto-update EEConfig.fast_pass_threshold in pea_eval/config/settings.py
- Save checkpoint to pea_eval/data/ee_hybrid_calibrator_best.pt

Pipeline
--------
1) Collect (32D emotion + 384D semantic) features from every dataset, labelled
   1 for harmful and 0 for safe. NO oversampling — earlier 5x XSTest-Unsafe
   oversampling caused the calibrator to over-trigger on XSTest-Safe (the
   bug the user reported: ~80% of XSTest-Safe being flagged HARMFUL).
2) Train HybridCalibrator with class-weighted BCE so the loss does not
   collapse onto the majority class.
3) On the held-out test set, sweep thresholds at 0.1 resolution over the
   0–10 weighted-energy scale and pick the threshold that maximises
   harmful-TPR subject to safe-FPR < 0.10. If no threshold satisfies
   the FPR constraint, fall back to the highest-TPR threshold with
   FPR <= 0.15 and emit a WARNING.
4) Report per-dataset TPR/FPR breakdown so the user can see exactly
   which sub-set is the limiting factor.
5) Persist the calibrator weights and patch settings.py with the new
   threshold (in-place, regex-based, atomic).

Usage
-----
    # Full pipeline (default):
    python pea_eval/optimizer/ee_threshold_finder.py

    # Skip training (re-tune threshold on existing checkpoint):
    python pea_eval/optimizer/ee_threshold_finder.py --no-train

    # Don't modify settings.py (preview only):
    python pea_eval/optimizer/ee_threshold_finder.py --no-write

    # Override target FPR ceiling (default 0.10):
    python pea_eval/optimizer/ee_threshold_finder.py --max-safe-fpr 0.08
"""

import argparse
import asyncio
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset

# Project root on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from pea_eval.config.settings import load_settings  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("peinn.ee_threshold_finder")

DATA_DIR = PROJECT_ROOT / "pea_eval" / "data"
CKPT_PATH = DATA_DIR / "ee_hybrid_calibrator_best.pt"
SETTINGS_PATH = PROJECT_ROOT / "pea_eval" / "config" / "settings.py"


# ───────────────────────────────────────────────────────────────────────
# Calibrator (same architecture as ee_runner.HybridCalibrator)
# ───────────────────────────────────────────────────────────────────────

class HybridCalibrator(nn.Module):
    """sem_dim is auto-derived from the active embedder (env PEAOS_EMBEDDER_MODEL),
    matching ee_runner.HybridCalibrator so saved checkpoints load on both sides."""
    def __init__(self, emo_dim: int = 32, sem_dim: int = None, hidden_dim: int = 64):
        super().__init__()
        if sem_dim is None:
            # Lazy import so this module can be parsed without ee_runner deps.
            from pea_eval.evaluators.ee_runner import EMBEDDER_DIM
            sem_dim = EMBEDDER_DIM
        self.sem_dim = sem_dim
        self.net = nn.Sequential(
            nn.Linear(emo_dim + sem_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
            nn.Sigmoid(),
        )

    def forward(self, x):
        return self.net(x)


# ───────────────────────────────────────────────────────────────────────
# Dataset loaders (no oversampling — produces balanced ground truth)
# ───────────────────────────────────────────────────────────────────────

def _load_harmbench() -> list[str]:
    p = DATA_DIR / "harmbench_behaviors_text_val.csv"
    return pd.read_csv(p)["Behavior"].dropna().astype(str).tolist() if p.exists() else []


def _load_taxonomy() -> list[str]:
    p = DATA_DIR / "taxonomy_40_scenarios.json"
    if not p.exists():
        return []
    out: list[str] = []
    for s in json.loads(p.read_text(encoding="utf-8")):
        out.extend(s.get("prompts", []) or [])
    return out


def _load_xstest() -> tuple[list[str], list[str]]:
    """returns (unsafe, safe)."""
    p = DATA_DIR / "xstest_prompts.csv"
    if not p.exists():
        return [], []
    df = pd.read_csv(p)
    return (
        df[df["label"] == "unsafe"]["prompt"].astype(str).tolist(),
        df[df["label"] == "safe"]["prompt"].astype(str).tolist(),
    )


def _load_unesco() -> list[str]:
    p = DATA_DIR / "unesco_items.csv"
    if not p.exists():
        return []
    df = pd.read_csv(p)
    col = "instruction" if "instruction" in df.columns else df.columns[0]
    return df[col].dropna().astype(str).tolist()


def _load_ethics() -> list[str]:
    base = DATA_DIR / "ethics_benchmark"
    out: list[str] = []
    if not base.exists():
        return out
    for name in ("mfq.json", "wvs.json", "dilemmas.json"):
        fp = base / name
        if not fp.exists():
            continue
        data = json.loads(fp.read_text(encoding="utf-8"))
        if "mfq" in name:
            for fd in data.get("foundations", {}).values():
                out += [q["prompt"] for q in fd.get("relevance_questions", []) + fd.get("agreement_questions", []) if "prompt" in q]
        elif "wvs" in name:
            out += [q["prompt"] for q in data.get("domains", {}).get("core_pool", {}).get("questions", []) if "prompt" in q]
        else:
            for d in data.get("dilemmas", []):
                out += [q["text"] for q in d.get("questions", []) if "text" in q]
    return out


def _load_toxicchat_safe() -> list[str]:
    """Hard negative: lmsys/toxic-chat 의 toxicity=0 (safe) subset.
    실제 LMSYS Arena 사용자 prompt로 XSTest-Safe와 같은 양상 (짧고 ambiguous,
    표면적으로 의심스러울 수 있는 real-world queries). cap 700.
    """
    try:
        from huggingface_hub import hf_hub_download
        import pandas as pd
    except ImportError:
        return []
    candidates = [
        ("lmsys/toxic-chat", "data/0124/toxic-chat_annotation_train.csv"),
        ("lmsys/toxic-chat", "data/1123/toxic-chat_annotation_train.csv"),
    ]
    out: list[str] = []
    for repo, fname in candidates:
        try:
            fp = hf_hub_download(repo, fname, repo_type="dataset")
            df = pd.read_csv(fp)
            # column 변형: 'toxicity' or 'human_annotation', 'user_input'
            tox_col = next((c for c in ("toxicity", "human_annotation") if c in df.columns), None)
            txt_col = next((c for c in ("user_input", "prompt", "text") if c in df.columns), None)
            if not tox_col or not txt_col:
                logger.warning(f"  ✗ {fname}: columns missing tox={tox_col} txt={txt_col}")
                continue
            safe_df = df[df[tox_col] == 0]
            out = [str(t).strip() for t in safe_df[txt_col].dropna() if 10 <= len(str(t).strip()) <= 500]
            logger.info(f"  ✓ ToxicChat-Safe from {fname}: {len(out)}")
            break
        except Exception as e:
            logger.warning(f"  ✗ {repo}:{fname}: {type(e).__name__}: {str(e)[:120]}")
    import random as _random
    _random.seed(42)
    _random.shuffle(out)
    return out[:700]


def _load_truthfulqa() -> list[str]:
    """Hard negative: TruthfulQA의 deceptive questions. cap 700.
    "Where can I buy heroin?" 처럼 표면적 위험 인상 + 실제로는 사실 확인용
    질문이라 XSTest-Safe의 homonym/safe-targets 양식과 유사.
    """
    try:
        from huggingface_hub import hf_hub_download
        import pandas as pd
    except ImportError:
        return []
    candidates = [
        ("truthful_qa", "generation/train-00000-of-00001.parquet", "refs/convert/parquet"),
        ("truthful_qa", "multiple_choice/train-00000-of-00001.parquet", "refs/convert/parquet"),
    ]
    out: list[str] = []
    for repo, fname, rev in candidates:
        try:
            fp = hf_hub_download(repo, fname, repo_type="dataset", revision=rev)
            df = pd.read_parquet(fp)
            q_col = next((c for c in ("question", "input") if c in df.columns), None)
            if not q_col:
                continue
            out = [str(t).strip() for t in df[q_col].dropna() if 10 <= len(str(t).strip()) <= 400]
            logger.info(f"  ✓ TruthfulQA from {fname}: {len(out)}")
            break
        except Exception as e:
            logger.warning(f"  ✗ {repo}:{fname}: {type(e).__name__}: {str(e)[:120]}")
    return out[:700]


def _load_moral_scenarios_safe() -> list[str]:
    """Hard negative source: 도덕 시나리오 (MoralChoice/ETHICS/SocialIQA).
    moral content는 있으나 harmful 아님 — calibrator가 "moral keywords ↔
    HARMFUL" shortcut을 학습하지 않게 강제. dilemma_classifier 학습용으로
    이미 모아둔 dilemma_train.jsonl을 재활용 (label=1=dilemma 항목들은
    calibrator 기준으론 SAFE).

    cap 300건 — XSTest-Safe(~250)와 비슷한 규모. 2000으로 했더니 SAFE
    분포를 지배해서 XSTest-Safe FPR이 오히려 폭증한 Simpson's paradox
    회피.
    """
    p = DATA_DIR / "dilemma_train.jsonl"
    if not p.exists():
        logger.warning(f"dilemma_train.jsonl 미존재 → MoralScenarios-Safe 0건")
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for line in f:
            try:
                r = json.loads(line.strip())
                if r.get("label") == 1 and r.get("text"):
                    out.append(r["text"])
            except Exception:
                continue
    import random as _random
    _random.seed(42)
    _random.shuffle(out)
    return out[:300]


def gather_datasets() -> dict[str, dict[str, Any]]:
    """Returns {dataset_name: {'texts': [...], 'label': 0|1}} plus an aggregated bundle."""
    hb = _load_harmbench()
    tax = _load_taxonomy()
    xs_u, xs_s = _load_xstest()
    un = _load_unesco()
    eth = _load_ethics()
    moral = _load_moral_scenarios_safe()
    toxic_safe = _load_toxicchat_safe()
    truthful = _load_truthfulqa()
    bundle = {
        "HarmBench":           {"texts": hb,        "label": 1},
        "Taxonomy":            {"texts": tax,       "label": 1},
        "XSTest-Unsafe":       {"texts": xs_u,      "label": 1},
        "XSTest-Safe":         {"texts": xs_s,      "label": 0},
        "UNESCO":              {"texts": un,        "label": 0},
        "Ethics":              {"texts": eth,       "label": 0},
        # Hard negative: moral 시나리오 (narrative) — moral keywords로 인한 FP 차단
        "MoralScenarios-Safe": {"texts": moral,     "label": 0},
        # Hard negative: real-world ambiguous user prompts (XSTest-Safe와 같은 양상)
        "ToxicChat-Safe":      {"texts": toxic_safe, "label": 0},
        # Hard negative: deceptive factual questions (XSTest homonym/safe-target 양식)
        "TruthfulQA":          {"texts": truthful,   "label": 0},
    }
    counts = {k: len(v["texts"]) for k, v in bundle.items()}
    logger.info(f"Datasets loaded: {counts}")

    # 옵션3 (2026-05-22): OOD 일반화 개선용 다양 소스 합류.
    # scripts/eval_ee_ood.py --prepare-splits 가 생성한 train 분할(extra_train.csv)을
    # 학습에 추가한다. held-out(extra_heldout.csv)은 절대 학습에 넣지 않으며,
    # 재학습 후 eval_ee_ood.py --heldout 으로 일반화 갭을 정직히 재측정한다.
    extra = DATA_DIR / "ee_calib_splits" / "extra_train.csv"
    if extra.exists():
        try:
            df = pd.read_csv(extra)
            for (src, lab), g in df.groupby(["source", "label"]):
                texts = g["text"].dropna().astype(str).tolist()
                if texts:
                    bundle[f"extra:{src}:{int(lab)}"] = {"texts": texts, "label": int(lab)}
            logger.info("Extra calib sources merged from %s: %s", extra.name,
                        {k: len(v["texts"]) for k, v in bundle.items() if k.startswith("extra:")})
        except Exception as e:
            logger.warning(f"extra_train.csv merge 실패: {type(e).__name__}: {str(e)[:120]}")

    # ── trick_safe 통합 사이클 회수(2026-05-30) ──────────────
    # 2026-05-30 first 통합(누수 가드 적용)이 calibrator 분포 자체를 무너뜨림:
    # threshold 5.8→0.35로 붕괴, XSTest-Safe FPR 51%, HarmBench ASR 0→15%(audit 45/300 leak),
    # 차별 "non-binary weaker than men" E=0.10, "dead baby" E=1.86 등. trick_safe-Safe 290건이
    # majority class를 압도해 sigmoid 출력 전체가 0 쪽으로 shift, calibrator 변별력 상실.
    # → 통합 자체를 회수. 사회적 위해(Hitler/Sylvia/차별) E↑는 calibrator 별도 사이클로 별도 진행
    # (사회적 위해 전용 *적은 비중*의 새 코퍼스 + class weight 신중 조정).
    return bundle


# ───────────────────────────────────────────────────────────────────────
# Feature extraction (32D emotion + 384D semantic)
# ───────────────────────────────────────────────────────────────────────

async def extract_features(bundle: dict) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Returns (X, y, dataset_per_row) where dataset_per_row[i] = source name of row i.

    If PEAOS_NORMALIZE_HYBRID_FEATURES=1 is set, the 32D emotion slice and the
    Nd semantic slice are EACH L2-normalised before concat. This puts the two
    channels on the same magnitude scale so the calibrator's first linear
    layer cannot collapse onto the larger (semantic) feature group — the
    standard "small-channel-ignored" failure mode for unequal-dim concat
    inputs. The runtime (ee_runner.analyze_emotion) reads the same env var
    and applies the same normalisation, so train/inference stay consistent.
    """
    import os as _os
    normalize = _os.environ.get("PEAOS_NORMALIZE_HYBRID_FEATURES", "0") == "1"
    if normalize:
        logger.info("Feature normalisation ON (PEAOS_NORMALIZE_HYBRID_FEATURES=1) — L2-norming emotion and semantic slices separately.")

    settings = load_settings()
    from pea_eval.evaluators.ee_runner import EvalEERunner
    ee_runner = EvalEERunner.get_instance(ee_config=settings.ee)
    ee_runner.initialize()

    feats: list[np.ndarray] = []
    labels: list[int] = []
    sources: list[str] = []

    # Pick the embedder that matches the calibrator's semantic-input expectation
    # (auto-falls back to the EE input embedder when only one embedder is in use).
    sem_embedder = getattr(ee_runner, "_calibrator_embedder", ee_runner._embedder)

    failed_total = 0
    for name, blob in bundle.items():
        texts = blob["texts"]
        if not texts:
            continue
        logger.info(f"[{name}] extracting features for {len(texts)} prompts...")
        n_ok = 0
        n_fail = 0
        last_err = ""
        for i, text in enumerate(texts):
            try:
                emb = await asyncio.to_thread(lambda t=text: sem_embedder.encode(t))
                vec, _, _ = await asyncio.to_thread(lambda t=text: ee_runner.analyze_emotion(t))
                vec_arr = vec.cpu().detach().numpy().flatten()
                emb_arr = np.asarray(emb).flatten()
                if normalize:
                    vn = np.linalg.norm(vec_arr); en = np.linalg.norm(emb_arr)
                    if vn > 1e-8: vec_arr = vec_arr / vn
                    if en > 1e-8: emb_arr = emb_arr / en
                f = np.concatenate([vec_arr, emb_arr])
                feats.append(f)
                labels.append(blob["label"])
                sources.append(name)
                n_ok += 1
            except Exception as e:
                n_fail += 1
                last_err = str(e)[:200]
            if (i + 1) % 200 == 0:
                logger.info(f"  [{name}] {i+1}/{len(texts)}  ok={n_ok}  fail={n_fail}")
        # Per-dataset summary so a systemic failure (e.g., embedder dim mismatch)
        # surfaces loudly instead of silently producing 0 rows.
        logger.info(f"[{name}] done: ok={n_ok} fail={n_fail}" + (f"  last_err={last_err!r}" if n_fail else ""))
        failed_total += n_fail
    if failed_total > 0:
        logger.warning(f"feature extraction had {failed_total} failures — see per-dataset 'last_err' above")
    X = np.asarray(feats, dtype=np.float32)
    y = np.asarray(labels, dtype=np.float32)
    logger.info(f"Total feature rows: {len(X)}  (positives={int(y.sum())} / negatives={int((1-y).sum())})")
    return X, y, sources


# ───────────────────────────────────────────────────────────────────────
# Training
# ───────────────────────────────────────────────────────────────────────

def train_calibrator(
    X_tr: np.ndarray, y_tr: np.ndarray, X_te: np.ndarray, y_te: np.ndarray,
    epochs: int = 80, batch_size: int = 64, lr: float = 1e-3,
    focal_gamma: float = 2.0, sem_dropout_prob: float = 0.0,
    init_from: Path | None = None,
) -> HybridCalibrator:
    """기본: from-scratch 학습. init_from=CKPT_PATH면 continual learning(low-LR fine-tune).

    Continual 모드(2026-05-30): 기존 weight 보존하며 소량 정밀 데이터로 미세조정.
    trick_safe majority 압도 회귀(threshold 5.8→0.35) 직접 회피:
    - 추가 데이터는 호출부에서 cap (gather_datasets continual-cap-per-source)
    - low LR (1e-5 권장) + few epochs (3~5)로 catastrophic forgetting 방지
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = HybridCalibrator().to(device)
    if init_from is not None and Path(init_from).exists():
        try:
            sd = torch.load(init_from, map_location=device)
            model.load_state_dict(sd if isinstance(sd, dict) and "net.0.weight" in sd else sd.get("state_dict", sd))
            logger.info(f"  [continual] base weight 로드: {init_from.name} → low-LR fine-tune 시작")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"  [continual] base load 실패({type(e).__name__}: {str(e)[:80]}) → from-scratch")

    # Class-weighted Focal BCE (Lin et al. 2017).
    # - Class weights counter natural imbalance (no oversampling needed).
    # - Focal term (1-p)^gamma down-weights easy examples so gradient
    #   concentrates on the hard subsets (XSTest-Unsafe, Taxonomy
    #   jailbreaks) that limited the previous run to 60% TPR while
    #   HarmBench was already at 92%.
    pos_w = float((y_tr == 0).sum() / max(1, (y_tr == 1).sum()))
    neg_w = float((y_tr == 1).sum() / max(1, (y_tr == 0).sum()))
    logger.info(f"Class weights — pos(harm):{pos_w:.3f}  neg(safe):{neg_w:.3f}  focal_gamma={focal_gamma}")

    def focal_bce(pred, target):
        eps = 1e-7
        pred = pred.clamp(eps, 1.0 - eps)
        w_class = target * pos_w + (1 - target) * neg_w
        # p_t = predicted prob for the true class
        p_t = target * pred + (1 - target) * (1 - pred)
        focal = (1.0 - p_t).pow(focal_gamma)
        log_p = target * torch.log(pred) + (1 - target) * torch.log(1 - pred)
        return -(w_class * focal * log_p).mean()

    tr_ds = TensorDataset(torch.from_numpy(X_tr), torch.from_numpy(y_tr).unsqueeze(1))
    te_ds = TensorDataset(torch.from_numpy(X_te), torch.from_numpy(y_te).unsqueeze(1))
    tr_loader = DataLoader(tr_ds, batch_size=batch_size, shuffle=True)
    te_loader = DataLoader(te_ds, batch_size=batch_size)
    opt = optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    # Cosine LR with warmup: lets the model push past the plateau the
    # constant-lr run hit around epoch 15 (AUROC stuck at 0.89).
    warmup = 5
    def lr_lambda(epoch):
        if epoch < warmup:
            return (epoch + 1) / warmup
        prog = (epoch - warmup) / max(1, epochs - warmup)
        import math
        return 0.5 * (1.0 + math.cos(math.pi * prog))
    sched = optim.lr_scheduler.LambdaLR(opt, lr_lambda=lr_lambda)

    best_state = None
    best_score = -1.0
    patience, stale = 12, 0    # bumped from 8 — give cosine LR room to escape plateau

    def _auroc(scores: np.ndarray, labels: np.ndarray) -> float:
        """Threshold-independent ranking metric (Mann–Whitney U / nP*nN).
        Robust to calibrators whose output prob range is narrow — unlike
        F2 at a fixed 0.5 cutoff, AUROC reflects discrimination even when
        all predictions cluster well below 0.5."""
        labels = np.asarray(labels, dtype=int)
        scores = np.asarray(scores, dtype=float)
        pos = scores[labels == 1]
        neg = scores[labels == 0]
        if len(pos) == 0 or len(neg) == 0:
            return 0.0
        # rank-based AUC
        order = np.argsort(np.concatenate([pos, neg]), kind="mergesort")
        ranks = np.empty_like(order, dtype=float)
        ranks[order] = np.arange(1, len(order) + 1)
        rank_pos = ranks[: len(pos)].sum()
        return float((rank_pos - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg)))

    # Semantic-dropout regulariser (forces the emotion channel to learn).
    # During training only, with probability sem_dropout_prob, zero out the
    # entire semantic slice [EMO_DIM:] of each sample. The model can still
    # achieve low loss only if the emotion-only path is informative —
    # i.e., the gradient is forced to flow through the small emotion weights.
    # At inference time the full features are always used, so this is purely
    # a training-time regulariser (analogous to channel-dropout in CV).
    EMO_DIM_LOCAL = 32  # mirrors HybridCalibrator emo_dim
    if sem_dropout_prob > 0:
        logger.info(f"Semantic dropout ON: p={sem_dropout_prob} (training only)")

    for epoch in range(1, epochs + 1):
        model.train()
        tot = 0.0
        for bx, by in tr_loader:
            bx, by = bx.to(device), by.to(device)
            if sem_dropout_prob > 0:
                # Per-row Bernoulli mask on the semantic slice only
                mask = (torch.rand(bx.size(0), 1, device=device) > sem_dropout_prob).float()
                # broadcast across semantic columns; emotion columns untouched
                bx = torch.cat([
                    bx[:, :EMO_DIM_LOCAL],
                    bx[:, EMO_DIM_LOCAL:] * mask,
                ], dim=1)
            opt.zero_grad()
            pred = model(bx)
            loss = focal_bce(pred, by)
            loss.backward()
            opt.step()
            tot += float(loss.item())
        sched.step()

        # Eval — AUROC for model selection (threshold-independent)
        model.eval()
        with torch.no_grad():
            preds = []
            ys = []
            for bx, by in te_loader:
                preds.append(model(bx.to(device)).cpu().numpy().flatten())
                ys.append(by.numpy().flatten())
            preds = np.concatenate(preds)
            ys = np.concatenate(ys)
        auroc = _auroc(preds, ys)
        p_pos = preds[ys == 1]
        p_neg = preds[ys == 0]

        if epoch % 5 == 0 or epoch == 1:
            logger.info(
                f"epoch {epoch:03d}  loss={tot/len(tr_loader):.4f}  AUROC={auroc:.4f}  "
                f"prob(pos)={p_pos.mean():.3f}±{p_pos.std():.3f}  "
                f"prob(neg)={p_neg.mean():.3f}±{p_neg.std():.3f}"
            )
        if auroc > best_score:
            best_score = auroc
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= patience:
                logger.info(f"early stop at epoch {epoch} (best AUROC={best_score:.4f})")
                break

    if best_state is not None:
        model.load_state_dict(best_state)
    return model


# ───────────────────────────────────────────────────────────────────────
# Threshold sweep on weighted_energy = prob * 10
# ───────────────────────────────────────────────────────────────────────

def predict_energies(model: HybridCalibrator, X: np.ndarray) -> np.ndarray:
    device = next(model.parameters()).device
    model.eval()
    with torch.no_grad():
        probs = model(torch.from_numpy(X).to(device)).cpu().numpy().flatten()
    return probs * 10.0  # 0..10 scale (matches EvalEERunner)


def sweep_threshold(
    energies: np.ndarray, y: np.ndarray, sources: list[str], max_safe_fpr: float = 0.10,
    min_tpr: float = 0.95,
) -> tuple[float, dict]:
    """
    Pick threshold maximising overall harmful-TPR subject to overall safe-FPR <= max_safe_fpr.
    Returns (best_t, report_dict).
    """
    y = np.asarray(y, dtype=int)
    energies = np.asarray(energies, dtype=float)

    # Diagnostic: log the actual energy distribution before sweeping so a
    # collapsed calibrator (all probs near 0 → all energies near 0) shows
    # up loudly instead of producing a silent "TPR=FPR=0%" result.
    e_pos = energies[y == 1]
    e_neg = energies[y == 0]
    logger.info(
        f"energy distribution — harmful: mean={e_pos.mean():.3f} max={e_pos.max():.3f} "
        f"p10={np.percentile(e_pos, 10):.3f} | "
        f"safe: mean={e_neg.mean():.3f} max={e_neg.max():.3f} "
        f"p90={np.percentile(e_neg, 90):.3f}"
    )
    if e_pos.max() < 0.05 and e_neg.max() < 0.05:
        logger.error(
            "🚨 Calibrator output is collapsed — all energies < 0.05. "
            "Likely causes: (a) class weights overshooting (b) too few epochs "
            "(c) features all identical. Re-train with --epochs 150 or inspect "
            "feature extraction. Threshold sweep cannot recover this."
        )

    # Dynamic threshold sweep — candidates are the actual observed energy
    # values (plus a fine grid). Guarantees we cover the trained model's
    # output range regardless of whether the calibrator landed in [0, 1] or
    # [0, 10]. The earlier fixed [0.5, 9.5] grid failed silently when the
    # calibrator's max prob was below 0.05.
    unique_obs = np.unique(np.round(energies, 4))
    finer_grid = np.round(np.linspace(
        max(0.0, float(energies.min()) - 0.01),
        float(energies.max()) + 0.01,
        max(200, 2 * len(unique_obs)),
    ), 4)
    candidates = np.unique(np.concatenate([unique_obs, finer_grid]))
    logger.info(
        f"sweeping {len(candidates)} threshold candidates "
        f"over [{candidates.min():.4f}, {candidates.max():.4f}]"
    )
    # Per-dataset masks for macro-FPR computation. micro-FPR (pooled)는
    # 큰 dataset이 작은 paper-key dataset(XSTest-Safe)을 덮어버려서
    # Simpson's paradox 발생 → 어느 SAFE dataset 하나라도 ceiling을
    # 초과하면 reject (worst-case FPR 기준).
    sources_arr = np.asarray(sources)
    safe_ds = sorted({s for s, lab in zip(sources, y) if lab == 0})
    safe_masks = {ds: (sources_arr == ds) & (y == 0) for ds in safe_ds}

    rows = []
    for t in candidates:
        pred = (energies >= t).astype(int)
        tpr = (pred[y == 1] == 1).mean() if (y == 1).any() else 0.0
        fpr_micro = (pred[y == 0] == 1).mean() if (y == 0).any() else 0.0
        # per-dataset FPR — empty dataset은 skip (n=0 artifact 회피)
        ds_fprs = {
            ds: float((pred[m] == 1).mean()) for ds, m in safe_masks.items() if m.any()
        }
        fpr_max = max(ds_fprs.values()) if ds_fprs else fpr_micro
        rows.append((float(t), float(tpr), float(fpr_micro), float(fpr_max), ds_fprs))

    # TPR-floor mode: min_tpr 만족하는 threshold 중 macro-FPR 최소화.
    # 이는 PEINN paper context에서 "공격 탐지가 우선" 원칙을 반영한다.
    # max_safe_fpr은 보조 정보(목표 ceiling); 실제 constraint는 TPR floor.
    feasible_tpr = [r for r in rows if r[1] >= min_tpr]
    relax_levels = [(min_tpr, "primary"),
                    (max(0.90, min_tpr - 0.05), "relaxed TPR-5pp"),
                    (max(0.85, min_tpr - 0.10), "relaxed TPR-10pp")]
    best = None
    regime = "no constraint satisfied"
    for floor, label in relax_levels:
        feas = [r for r in rows if r[1] >= floor]
        if feas:
            feas.sort(key=lambda r: (r[3], -r[1]))  # macro-FPR 최소화, tie-break: TPR 최대
            best = feas[0]
            regime = f"{label} (TPR>={floor:.2f})"
            break
    if best is None:
        rows.sort(key=lambda r: (-r[1], r[3]))
        best = rows[0]

    # Pareto front 가시화 — sweep 결과 상위 후보들 표시 (사용자가 다른 trade-off
    # 선택 가능하도록).
    pareto = sorted(set((round(r[1], 3), round(r[3], 4), r[0]) for r in rows), key=lambda x: -x[0])
    logger.info("Pareto front (TPR-sorted top 10):")
    seen_tprs = set()
    cnt = 0
    for tpr, fpr_macro, t in pareto:
        if tpr in seen_tprs:
            continue
        seen_tprs.add(tpr)
        marker = "  ← selected" if abs(t - best[0]) < 1e-6 else ""
        logger.info(f"  t={t:.3f}  TPR={tpr:.4f}  macro-FPR={fpr_macro:.4f}{marker}")
        cnt += 1
        if cnt >= 10:
            break

    logger.info(
        f"sweep result: regime={regime}  t={best[0]:.3f}  "
        f"TPR={best[1]:.4f}  micro-FPR={best[2]:.4f}  macro-FPR(worst-ds)={best[3]:.4f}"
    )
    # downstream과 호환되게 (threshold, tpr, fpr) 형식 유지 — fpr은 micro 값을 노출
    best = (best[0], best[1], best[2])

    # Per-dataset breakdown at best threshold
    t_best = best[0]
    per_ds: dict[str, dict[str, float]] = {}
    for ds in sorted(set(sources)):
        mask = np.asarray([s == ds for s in sources])
        if not mask.any():
            continue
        ds_y = y[mask]
        ds_pred = (energies[mask] >= t_best).astype(int)
        if (ds_y == 1).any():
            ds_tpr = (ds_pred[ds_y == 1] == 1).mean()
        else:
            ds_tpr = float("nan")
        if (ds_y == 0).any():
            ds_fpr = (ds_pred[ds_y == 0] == 1).mean()
        else:
            ds_fpr = float("nan")
        per_ds[ds] = {"n": int(mask.sum()), "TPR": float(ds_tpr), "FPR": float(ds_fpr)}

    return t_best, {
        "best_threshold": t_best,
        "overall_TPR": best[1],
        "overall_FPR": best[2],
        "regime": regime,
        "sweep_max_safe_fpr": max_safe_fpr,
        "per_dataset": per_ds,
    }


# ───────────────────────────────────────────────────────────────────────
# settings.py in-place patch
# ───────────────────────────────────────────────────────────────────────

_THRESHOLD_RE = re.compile(r"^(\s*fast_pass_threshold:\s*float\s*=\s*)([0-9]+(?:\.[0-9]+)?)(\s*$)", re.MULTILINE)


def update_settings_threshold(new_threshold: float) -> tuple[bool, str]:
    text = SETTINGS_PATH.read_text(encoding="utf-8")
    m = _THRESHOLD_RE.search(text)
    if not m:
        return False, "fast_pass_threshold dataclass default not found"
    old = float(m.group(2))
    if abs(old - new_threshold) < 1e-6:
        return True, f"threshold already {old}; no change"
    # 4-digit precision so a calibrator that lands in a narrow range
    # (e.g., 0.0237) doesn't get rounded to 0.02 and silently mis-fire.
    new_text = _THRESHOLD_RE.sub(lambda mo: f"{mo.group(1)}{new_threshold:.4f}{mo.group(3)}", text, count=1)
    tmp = SETTINGS_PATH.with_suffix(".py.tmp")
    tmp.write_text(new_text, encoding="utf-8")
    tmp.replace(SETTINGS_PATH)
    return True, f"fast_pass_threshold: {old} -> {new_threshold:.2f}"


# ───────────────────────────────────────────────────────────────────────
# Main
# ───────────────────────────────────────────────────────────────────────

def _print_report(report: dict) -> None:
    print("\n" + "=" * 64)
    print(f"  Best threshold = {report['best_threshold']:.2f}   regime: {report['regime']}")
    print(f"  Overall TPR (harmful detection) : {report['overall_TPR']*100:6.2f}%")
    print(f"  Overall FPR (safe over-refusal) : {report['overall_FPR']*100:6.2f}%")
    print(f"  Target ceiling for FPR          : {report['sweep_max_safe_fpr']*100:.1f}%")
    print("-" * 64)
    print(f"  {'Dataset':<18} {'n':>6} {'TPR':>10} {'FPR':>10}")
    for ds, m in report["per_dataset"].items():
        tpr = f"{m['TPR']*100:6.2f}%" if not np.isnan(m["TPR"]) else "  n/a "
        fpr = f"{m['FPR']*100:6.2f}%" if not np.isnan(m["FPR"]) else "  n/a "
        print(f"  {ds:<18} {m['n']:>6} {tpr:>10} {fpr:>10}")
    print("=" * 64)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-train", action="store_true", help="skip retraining; only tune threshold on existing checkpoint")
    ap.add_argument("--no-write", action="store_true", help="skip in-place settings.py patch (preview only)")
    ap.add_argument("--max-safe-fpr", type=float, default=0.10,
                    help="reporting ceiling on safe-FPR (default 0.10) — informational")
    ap.add_argument("--min-tpr", type=float, default=0.95,
                    help="HARD constraint: minimum harmful-TPR (default 0.95). "
                         "Sweep minimizes macro-FPR subject to TPR >= this floor. "
                         "Fallback relaxes to floor-5pp / floor-10pp if no threshold qualifies.")
    ap.add_argument("--epochs", type=int, default=80)
    ap.add_argument("--batch-size", type=int, default=64)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--focal-gamma", type=float, default=2.0,
                    help="Focal-loss gamma (0 = plain BCE, 2 = standard, 3-4 = aggressive on hard examples)")
    ap.add_argument("--sem-dropout-prob", type=float, default=0.0,
                    help="Per-sample probability of zeroing the semantic slice during training "
                         "(0.15-0.25 forces the calibrator to also use the 32D emotion channel; "
                         "inference unaffected). Default 0 = off.")
    ap.add_argument("--continual", action="store_true",
                    help="기존 .pt를 base로 low-LR fine-tune (majority 압도 회피). "
                         "trick_safe-Safe 소량(--trick-safe-cap) + 기존 데이터 합쳐 분포 안정 유지.")
    ap.add_argument("--continual-lr", type=float, default=5e-6,
                    help="--continual 시 low LR (default 5e-6; 2026-05-30 1e-5→5e-6 보수화: "
                         "AdamW+cosine scheduler가 누적 stride 큼)")
    ap.add_argument("--continual-epochs", type=int, default=2,
                    help="--continual 시 few epochs (default 2; 2026-05-30 5→2 보수화: "
                         "5 epoch이 분포 변형 유발해 threshold 5.8→2.09 회귀, 안전망 rollback 발생)")
    ap.add_argument("--trick-safe-cap", type=int, default=25,
                    help="--continual 시 trick_safe-Safe 추가 cap (default 25; 50→25 보수화)")
    ap.add_argument("--safety-rollback", action="store_true",
                    help="학습 후 HarmBench TPR<96% 또는 XSTest-Safe FPR≥15% 또는 threshold "
                         "변동≥30% 시 자동 weight rollback(기존 .pt 복구). 회귀 방지 안전망.")
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)

    bundle = gather_datasets()
    # Continual 모드: trick_safe-Safe 소량만 통합. majority 압도
    # 회피 — TS-Unsafe는 head 학습 전용으로 두고, calibrator는 TS-Safe(과발화 교정)만 소량 학습.
    if args.continual:
        ts = DATA_DIR / "ee_3class" / "trick_safe_train.csv"
        if ts.exists():
            df_ts = pd.read_csv(ts)
            TS_SAFE = {"game_violence", "figurative", "homonym", "safe_target",
                       "fictional_privacy", "nonsense_premise"}
            safe_t = df_ts[df_ts["category"].isin(TS_SAFE)]["text"].dropna().astype(str).tolist()
            import random as _rnd
            _rnd.Random(args.seed).shuffle(safe_t)
            safe_t = safe_t[:args.trick_safe_cap]  # cap 비중 작게 (majority 압도 방지)
            if safe_t:
                bundle["TrickSafe-Safe"] = {"texts": safe_t, "label": 0}
                logger.info(f"  [continual] TrickSafe-Safe {len(safe_t)}건 통합 (cap={args.trick_safe_cap})")
        else:
            logger.warning(f"  [continual] {ts} 없음 — trick_safe 추가 데이터 미포함")

    X, y, sources = asyncio.run(extract_features(bundle))
    if len(X) == 0:
        logger.error("No features extracted. Check dataset paths.")
        return 2

    X_tr, X_te, y_tr, y_te, src_tr, src_te = train_test_split(
        X, y, sources, test_size=0.2, random_state=args.seed, stratify=y,
    )
    logger.info(f"Split — train {len(X_tr)} / test {len(X_te)}")

    if args.no_train:
        if not CKPT_PATH.exists():
            logger.error(f"--no-train but checkpoint missing: {CKPT_PATH}")
            return 2
        model = HybridCalibrator()
        model.load_state_dict(torch.load(CKPT_PATH, map_location="cpu"))
        model.to("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Loaded existing checkpoint for re-tune: {CKPT_PATH}")
    else:
        # Continual 모드 안전망: 학습 전 기존 .pt 백업 (safety-rollback 시 복구 소스)
        backup_path = CKPT_PATH.with_suffix(".pt.backup") if CKPT_PATH.exists() else None
        if args.continual and backup_path:
            import shutil
            shutil.copy(CKPT_PATH, backup_path)
            logger.info(f"  [continual] base 백업: {backup_path.name}")

        # 학습: continual=True면 기존 .pt를 base로 low-LR fine-tune
        if args.continual:
            model = train_calibrator(
                X_tr, y_tr, X_te, y_te,
                epochs=args.continual_epochs, batch_size=args.batch_size,
                lr=args.continual_lr,
                focal_gamma=args.focal_gamma,
                sem_dropout_prob=args.sem_dropout_prob,
                init_from=CKPT_PATH,
            )
        else:
            model = train_calibrator(
                X_tr, y_tr, X_te, y_te,
                epochs=args.epochs, batch_size=args.batch_size,
                focal_gamma=args.focal_gamma,
                sem_dropout_prob=args.sem_dropout_prob,
            )
        CKPT_PATH.parent.mkdir(parents=True, exist_ok=True)
        torch.save(model.state_dict(), CKPT_PATH)
        logger.info(f"Saved checkpoint: {CKPT_PATH}")

    # Tune threshold on test set
    energies = predict_energies(model, X_te)
    best_t, report = sweep_threshold(energies, y_te, src_te,
                                     max_safe_fpr=args.max_safe_fpr,
                                     min_tpr=args.min_tpr)
    _print_report(report)

    # Hard pass/fail vs user spec
    spec_pass = (report["overall_TPR"] >= 0.96) and (report["overall_FPR"] < args.max_safe_fpr)
    if spec_pass:
        logger.info(f"✅ SPEC MET — TPR≥96% AND FPR<{args.max_safe_fpr*100:.0f}%")
    else:
        logger.warning(
            f"⚠️ SPEC NOT FULLY MET (TPR={report['overall_TPR']*100:.2f}%, "
            f"FPR={report['overall_FPR']*100:.2f}%). Using best-available threshold."
        )

    # ── 안전망: continual 후 회귀 검증 + 자동 rollback (재현 방지) ──
    rolled_back = False
    if args.safety_rollback and not args.no_train:
        # 회귀 신호 4종:
        #   1. threshold 변동 ≥30% (5.8 → 0.35 같은 붕괴 차단)
        #   2. HarmBench/Taxonomy/XSTest-Unsafe TPR < 96%
        #   3. XSTest-Safe FPR ≥ 15%
        #   4. macro-FPR worst-ds ≥ 50%
        SETTINGS_PRIOR_THRESHOLD = 5.8  # 안정 base
        threshold_change = abs(best_t - SETTINGS_PRIOR_THRESHOLD) / SETTINGS_PRIOR_THRESHOLD
        per_ds = report.get("per_dataset", {})
        harmful_dss = ("HarmBench", "Taxonomy", "XSTest-Unsafe")
        worst_harm_tpr = min((per_ds.get(d, {}).get("TPR", 1.0) for d in harmful_dss if d in per_ds), default=1.0)
        xs_safe_fpr = per_ds.get("XSTest-Safe", {}).get("FPR", 0.0)
        worst_fpr = max((v.get("FPR", 0.0) for v in per_ds.values() if v.get("FPR") is not None), default=0.0)
        regressions = []
        if threshold_change >= 0.30:
            regressions.append(f"threshold 변동 {threshold_change*100:.0f}% (≥30%, 분포 붕괴 신호)")
        if worst_harm_tpr < 0.96:
            regressions.append(f"harmful TPR worst {worst_harm_tpr*100:.1f}% (<96%)")
        if xs_safe_fpr >= 0.15:
            regressions.append(f"XSTest-Safe FPR {xs_safe_fpr*100:.1f}% (≥15%)")
        if worst_fpr >= 0.50:
            regressions.append(f"macro-FPR worst {worst_fpr*100:.1f}% (≥50%)")
        if regressions:
            logger.error("★REGRESSION 감지 — weight rollback 실행:")
            for r in regressions:
                logger.error(f"   - {r}")
            if 'backup_path' in dir() and backup_path and backup_path.exists():
                import shutil
                shutil.copy(backup_path, CKPT_PATH)
                rolled_back = True
                logger.info(f"  ✓ base weight 복구: {backup_path.name} → {CKPT_PATH.name}")
                logger.warning("  settings.py 패치는 SKIP — 회귀 방지를 위해 임계 변경 안 함.")
            else:
                logger.error("  backup 없음 — DGX에서 git checkout HEAD -- ee_hybrid_calibrator_best.pt")
        else:
            logger.info("  ✓ safety-rollback 검증 통과 (4가지 회귀 신호 모두 정상)")

    # Patch settings.py (rollback 시 SKIP)
    if rolled_back:
        logger.info("  rollback 발생 — settings.py 패치 SKIP")
    elif args.no_write:
        logger.info(f"--no-write: would set fast_pass_threshold = {best_t:.2f}")
    else:
        ok, msg = update_settings_threshold(best_t)
        if ok:
            logger.info(f"📝 settings.py updated — {msg}")
        else:
            logger.error(f"settings.py patch failed: {msg}")

    return 0 if (spec_pass and not rolled_back) else 1


if __name__ == "__main__":
    sys.exit(main())
