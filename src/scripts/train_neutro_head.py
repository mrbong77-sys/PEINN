"""
NeutroEE S3 — NeutroHead 학습.

FROZEN EmotionEngine 특징(emotion32 + base energy) + 매칭 원칙 임베딩(principle_emb)
을 입력으로, judge soft target (T=safe, I=dilemma, F=harmful, 각 [0,1])에 회귀하는
독립 3-sigmoid head를 학습한다 (docs/neutro_ee_design.md S3).

- 특징 추출은 ee_runner.neutro_features (train/inference 공유) → FROZEN EE, 학습 X.
- 손실: 독립 soft-target BCE, dilemma(I) 차원 가중(소수 클래스 보정).
- 평가: held-out per-dim MAE/AUC + thirdanswer.Compass zone 라우팅 분포(judge primary 대비).
- 산출물: pea_eval/data/ee_neutro_head.pt (state_dict + meta). 기존 EE/calibrator 불변.

DGX 실행 (S2 split 이후):
    pip install thirdanswer scikit-learn
    python scripts/train_neutro_head.py --epochs 60 --i-weight 2.0
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peaos.train_neutro_head")

DATA_DIR = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class"
TRAIN_CSV = DATA_DIR / "train.csv"
HELDOUT_CSV = DATA_DIR / "heldout.csv"
OUT_PT = PROJECT_ROOT / "pea_eval" / "data" / "ee_neutro_head.pt"
# v3 (2-of-3 masked) — separate paths so the production head is never overwritten.
V3_TRAIN_CSV = DATA_DIR / "v3" / "train.csv"
V3_HELDOUT_CSV = DATA_DIR / "v3" / "heldout.csv"
OUT_PT_V3 = PROJECT_ROOT / "pea_eval" / "data" / "ee_neutro_head_v3.pt"
DIMS = ["T", "I", "F"]  # safe / dilemma / harmful


# 학습/추론 단일 소스 — head 아키텍처·feature 조립·라우팅 분기는 intent_router에서.
from pea_eval.evaluators.intent_router import (  # noqa: E402
    build_neutro_head as build_head,
    neutro_feature_vector,
    neutro_route as _route,
)


def extract_features(split: str, texts: list[str], runner) -> np.ndarray:
    """[emotion32 ⊕ energy ⊕ principle_emb] (N, 417). npz 캐시.

    캐시 무효화: 행 수 + 텍스트 내용 해시(fingerprint)로 판정. 코퍼스 증강
    (예: trick_safe 추가)으로 train.csv가 바뀌면 fingerprint 불일치 → 자동 재계산.
    (구 버전은 행 수만 비교해, 행 수가 우연히 같으면 stale feature를 그대로 썼다.)
    """
    import hashlib
    cache = DATA_DIR / f"neutro_feats_{split}.npz"
    fp = hashlib.sha1(("\n".join(texts)).encode("utf-8")).hexdigest()
    if cache.exists():
        z = np.load(cache, allow_pickle=True)
        X = z["X"]
        cached_fp = str(z["fp"]) if "fp" in z else ""
        if X.shape[0] == len(texts) and cached_fp == fp:
            logger.info(f"  feature cache hit: {cache.name} {X.shape}")
            return X
        logger.info(f"  feature cache STALE({cache.name}) → 재계산 "
                    f"(rows {X.shape[0]}→{len(texts)}, fp {'match' if cached_fp==fp else 'diff'})")
    feats = []
    n = len(texts)
    for i, t in enumerate(texts):
        d = runner.neutro_features(t)
        feats.append(neutro_feature_vector(d))
        if (i + 1) % 200 == 0 or (i + 1) == n:
            logger.info(f"  [{split}] features {i+1}/{n}")
    X = np.stack(feats)
    np.savez_compressed(cache, X=X, fp=fp)
    logger.info(f"  saved features → {cache.name} {X.shape}")
    return X


MASK_DIMS = ["mask_T", "mask_I", "mask_F"]


def _load_csv(path: Path):
    """Returns texts, Y(N,3), src, M(N,3).

    v3 (2-of-3) CSVs carry mask_T/I/F → only the labeled 2 components are supervised.
    Legacy CSVs (no mask cols) get M=ones, so the masked loss reduces EXACTLY to the
    original mean — production path numerically unchanged.
    """
    import pandas as pd
    df = pd.read_csv(path)
    texts = df["text"].astype(str).tolist()
    Y = df[DIMS].astype("float32").to_numpy()
    src = df["source"].astype(str).tolist()
    if all(c in df.columns for c in MASK_DIMS):
        M = df[MASK_DIMS].astype("float32").to_numpy()
    else:
        M = np.ones_like(Y, dtype="float32")
    return texts, Y, src, M


def evaluate(model, Xte, Yte, src_te, Mte=None):
    """held-out per-dim 지표 + Compass zone 라우팅 분포.

    Mte (mask) 주어지면 per-dim MAE/AUC를 **supervised 항목(mask==1)만**으로 계산 —
    v3 2-of-3에서 미라벨 극성(placeholder 0)이 지표를 오염시키지 않게 한다.
    """
    import torch
    from sklearn.metrics import roc_auc_score, mean_absolute_error
    model.eval()
    with torch.no_grad():
        P = model(torch.tensor(Xte)).cpu().numpy()
    if Mte is None:
        Mte = np.ones_like(Yte)
    report = {}
    for j, dim in enumerate(DIMS):
        sel = Mte[:, j] > 0.5
        yt, yp = Yte[sel, j], P[sel, j]
        if len(yt) == 0:
            report[dim] = {"mae": None, "auc_at_0.5": None, "n_sup": 0}
            continue
        mae = float(mean_absolute_error(yt, yp))
        auc = None
        yb = (yt >= 0.5).astype(int)
        if 0 < yb.sum() < len(yb):
            auc = round(float(roc_auc_score(yb, yp)), 4)
        report[dim] = {"mae": round(mae, 4), "auc_at_0.5": auc, "n_sup": int(len(yt))}

    # Compass zone 라우팅 (thirdanswer 있으면)
    routing = None
    try:
        from thirdanswer import Compass
        ZONE2BR = {"consensus": "1-pass", "consensus_against": "2-pass-refusal",
                   "contradiction": "2-pass-reasoning", "ambiguity": "2-pass-reasoning",
                   "ignorance": "2-pass-reasoning"}
        # judge primary (label) vs predicted branch
        from collections import Counter, defaultdict
        conf = defaultdict(Counter)
        for k in range(len(P)):
            t, i, f = float(P[k, 0]), float(P[k, 1]), float(P[k, 2])
            br = ZONE2BR.get(Compass(T=min(t, 1), I=min(i, 1), F=min(f, 1)).zone, "?")
            primary = DIMS[int(np.argmax(Yte[k]))]  # T/I/F label primary
            conf[{"T": "safe", "I": "dilemma", "F": "harm"}[primary]][br] += 1
        routing = {k: dict(v) for k, v in conf.items()}
    except Exception as e:
        logger.warning(f"Compass 라우팅 평가 skip: {type(e).__name__}: {str(e)[:80]}")
    return report, routing


ROUTING_JSON = PROJECT_ROOT / "pea_eval" / "data" / "ee_neutro_routing.json"

# 안전 게이트의 라우팅 비용 (FP-허용/FN-고비용 비대칭). 행=judge primary(true), 열=예측 분기.
#   이상적 대각선: safe→1-pass, harm→refusal, dilemma→reasoning (각 0).
#   2-pass-reasoning은 *딜레마 심화*용이지 유해 차단이 아니다 → harm→reasoning은
#   안전 결과가 아니므로 명확히 비용 부과(이걸 0에 가깝게 두면 "전부 reasoning"
#   퇴화 해가 나온다). safe→reasoning은 낭비지만 안전하므로 경비용.
#   최대 패널티: harm→1-pass(miss), safe→refusal(과잉거부 ORR).
def _route_cost(w_miss=1.0, w_orr=1.0, w_harm_reason=0.5, w_safe_reason=0.2, w_dilemma=1.0):
    # w_dilemma: dilemma 오라우팅 비용 배율. dilemma는 소수 클래스(n~42)라 기본 가중으론
    # 튜너가 다수(safe/harm) 최적화에 묻혀 τ_I를 과하게 높여 dilemma→reasoning을 희생함
    # (관측: τ_I=0.8 → dilemma 31%만 reasoning). w_dilemma↑로 dilemma 라우팅 보호.
    return {
        ("safe", "1-pass"): 0.0, ("safe", "reasoning"): w_safe_reason, ("safe", "refusal"): w_orr,
        ("harm", "refusal"): 0.0, ("harm", "reasoning"): w_harm_reason, ("harm", "1-pass"): w_miss,
        ("dilemma", "reasoning"): 0.0, ("dilemma", "1-pass"): 0.6 * w_dilemma, ("dilemma", "refusal"): 0.4 * w_dilemma,
    }
_TRUE = ["safe", "dilemma", "harm"]  # DIMS=[T,I,F] argmax → safe/dilemma/harm


def tune_routing(cost: dict) -> int:
    """학습된 head + held-out으로 라우팅 임계(τ_safe, τ_harm, τ_I) 그리드 탐색."""
    import json
    import torch
    from collections import Counter, defaultdict
    if not OUT_PT.exists():
        logger.error(f"{OUT_PT} 없음. 먼저 학습하세요.")
        return 1
    ckpt = torch.load(OUT_PT, map_location="cpu")
    model = build_head(ckpt["in_dim"]); model.load_state_dict(ckpt["state_dict"]); model.eval()
    cache = DATA_DIR / "neutro_feats_heldout.npz"
    if not cache.exists():
        logger.error(f"{cache} 없음. 먼저 학습(특징 추출)을 실행하세요.")
        return 1
    Xho = np.load(cache)["X"]
    _, Yho, _ = _load_csv(HELDOUT_CSV)
    with torch.no_grad():
        P = model(torch.tensor(Xho)).cpu().numpy()
    true = [_TRUE[int(np.argmax(Yho[k]))] for k in range(len(Yho))]

    grid_s = np.round(np.arange(0.40, 0.86, 0.05), 2)
    grid_h = np.round(np.arange(0.30, 0.86, 0.05), 2)
    grid_i = np.round(np.arange(0.25, 0.86, 0.05), 2)
    T, I, F = P[:, 0], P[:, 1], P[:, 2]
    true_arr = np.array(true)
    best = {"cost": 1e9}
    for ts in grid_s:
        for th in grid_h:
            for ti in grid_i:
                br = np.where(I >= ti, "reasoning",
                     np.where((F >= th) & (F >= T), "refusal",
                     np.where((T >= ts) & (F < th), "1-pass", "reasoning")))
                tot = 0.0
                for (tc, bc), w in cost.items():
                    if w:
                        tot += w * np.count_nonzero((true_arr == tc) & (br == bc))
                c = tot / len(P)
                if c < best["cost"]:
                    best = {"cost": round(float(c), 4),
                            "tau_safe": float(ts), "tau_harm": float(th), "tau_I": float(ti)}

    # 최적 임계에서 라우팅 분포 + 핵심 비교지표
    ts, th, ti = best["tau_safe"], best["tau_harm"], best["tau_I"]
    conf = defaultdict(Counter)
    for k in range(len(P)):
        conf[true[k]][_route(float(P[k, 0]), float(P[k, 1]), float(P[k, 2]), ts, th, ti)] += 1
    logger.info(f"\n===== TUNED ROUTING (cost={best['cost']}) =====")
    logger.info(f"  thresholds: tau_safe={ts}  tau_harm={th}  tau_I={ti}")
    for cls in ("safe", "harm", "dilemma"):
        d = dict(conf[cls]); n = sum(d.values()) or 1
        logger.info(f"  {cls:8} → {d}  (n={n})")
    h = conf["harm"]; s = conf["safe"]; nh = sum(h.values()) or 1; ns = sum(s.values()) or 1
    logger.info(f"  harm→1-pass miss = {h['1-pass']/nh:.3f} | harm→2-pass = {(h['refusal']+h['reasoning'])/nh:.3f}")
    logger.info(f"  safe→refusal(ORR) = {s['refusal']/ns:.3f} | safe→2-pass = {(s['refusal']+s['reasoning'])/ns:.3f}")
    ROUTING_JSON.write_text(json.dumps({**best, "cost_weights": {f"{a}->{b}": w for (a, b), w in cost.items()}}, indent=2))
    logger.info(f"saved thresholds → {ROUTING_JSON}")
    return 0


def _selftest() -> int:
    """CPU-only: masked reduction == legacy .mean() when M=ones; ignores unsupervised entries."""
    rng = np.random.default_rng(0)
    B = 7
    bce = rng.random((B, 3)).astype("float32")
    dim_w = np.array([1.0, 2.5, 1.0], dtype="float32")
    sw = np.ones((B, 1), dtype="float32")
    M1 = np.ones((B, 3), dtype="float32")
    legacy = float((bce * dim_w * sw).mean())
    masked1 = float((bce * dim_w * sw * M1).sum() / M1.sum())
    assert abs(legacy - masked1) < 1e-6, (legacy, masked1)            # M=ones ≡ legacy
    M = M1.copy(); M[0, 2] = 0.0                                       # drop one F (unsupervised)
    keep = M > 0.5
    masked = float((bce * dim_w * sw * M).sum() / M.sum())
    ref = float((bce * dim_w * sw)[keep].sum() / keep.sum())
    assert abs(masked - ref) < 1e-6
    bce2 = bce.copy(); bce2[0, 2] = 999.0                             # masked target can't leak
    masked2 = float((bce2 * dim_w * sw * M).sum() / M.sum())
    assert abs(masked - masked2) < 1e-6
    # _load_csv mask detection (needs pandas — present on DGX; skipped if absent here)
    loadmsg = "; v3/legacy mask-load"
    try:
        import pandas  # noqa: F401
        import tempfile, csv as _csv
        d = Path(tempfile.mkdtemp())
        v3 = d / "v3.csv"
        with open(v3, "w", newline="") as fh:
            w = _csv.writer(fh)
            w.writerow(["text", "source", "polar", "T", "I", "F", "mask_T", "mask_I", "mask_F"])
            w.writerow(["a", "s", "T", 1.0, 0.0, 0.0, 1, 1, 0])
            w.writerow(["b", "s", "F", 0.0, 0.8, 0.6, 0, 1, 1])
        _, _, _, Mv = _load_csv(v3)
        assert Mv.tolist() == [[1, 1, 0], [0, 1, 1]]
        leg = d / "leg.csv"
        with open(leg, "w", newline="") as fh:
            w = _csv.writer(fh); w.writerow(["text", "source", "T", "I", "F"]); w.writerow(["a", "s", 1.0, 0.0, 0.0])
        _, _, _, Ml = _load_csv(leg)
        assert Ml.tolist() == [[1, 1, 1]]                              # legacy → all supervised
    except ImportError:
        loadmsg = "; (pandas absent → mask-load test skipped, runs on DGX)"
    print("SELFTEST OK — masked≡legacy(M=ones); unsupervised ignored" + loadmsg)
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NeutroEE S3 — train NeutroHead / tune routing")
    ap.add_argument("--tune-routing", action="store_true",
                    help="학습된 head로 라우팅 임계(τ_safe/τ_harm/τ_I) 그리드 탐색")
    ap.add_argument("--w-miss", type=float, default=1.0, help="harm→1-pass(miss) 비용")
    ap.add_argument("--w-orr", type=float, default=1.0, help="safe→refusal(과잉거부) 비용")
    ap.add_argument("--w-harm-reason", type=float, default=0.5, help="harm→reasoning 비용(reasoning≠refusal→비용 부과)")
    ap.add_argument("--w-safe-reason", type=float, default=0.2, help="safe→reasoning 비용(낭비지만 안전)")
    ap.add_argument("--w-dilemma", type=float, default=1.0,
                    help="dilemma 오라우팅 비용 배율(소수클래스 보호; τ_I 과상승 방지). 권장 3~5")
    ap.add_argument("--epochs", type=int, default=60)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--batch", type=int, default=128)
    ap.add_argument("--i-weight", type=float, default=2.5,
                    help="dilemma(I) 차원 손실 가중 (2026-05-30 HANDOFF-37: 3.0→2.5 보수화. "
                         "3.0이 F AUC 0.943→0.875 회귀 유발 — 절충 2.5로 F 보존+I 강화 양립)")
    ap.add_argument("--upweight-source", default="", help="이 source의 샘플 손실 가중(예: trick_safe)")
    ap.add_argument("--upweight-factor", type=float, default=1.0, help="--upweight-source 배수(기본 1.0=무효과)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--train-csv", default=str(TRAIN_CSV),
                    help="override train CSV (e.g. ee_3class/train_v2.csv with structural I-floor)")
    ap.add_argument("--heldout-csv", default=str(HELDOUT_CSV), help="override heldout CSV")
    ap.add_argument("--out", default=str(OUT_PT),
                    help="head checkpoint out (default = production; use *_v2.pt to preserve PEAOS 1.0)")
    ap.add_argument("--labels", choices=["legacy", "v3"], default="legacy",
                    help="v3 = 2-of-3 masked labels (ee_3class/v3/{train,heldout}.csv → ee_neutro_head_v3.pt)")
    ap.add_argument("--selftest", action="store_true", help="CPU: verify masked-mean math, no torch/EE")
    ap.add_argument("--neg-weight", type=float, default=0.0,
                    help="v3: weight for the IMPLIED-negative off-polar target (polar=T ⟹ F=0, "
                         "polar=F ⟹ T=0). 0=full mask (positive-only); 1=full negative supervision. "
                         "Recovers the clear-safe/clear-harm consensus the pure mask collapses.")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    # v3 preset: switch CSVs + out to the v3 paths unless explicitly overridden.
    if args.labels == "v3":
        if args.train_csv == str(TRAIN_CSV):
            args.train_csv = str(V3_TRAIN_CSV)
        if args.heldout_csv == str(HELDOUT_CSV):
            args.heldout_csv = str(V3_HELDOUT_CSV)
        if args.out == str(OUT_PT):
            args.out = str(OUT_PT_V3)
    train_csv = Path(args.train_csv); heldout_csv = Path(args.heldout_csv); out_pt = Path(args.out)

    if args.tune_routing:
        return tune_routing(_route_cost(args.w_miss, args.w_orr, args.w_harm_reason,
                                        args.w_safe_reason, args.w_dilemma))

    if not train_csv.exists():
        logger.error(f"{train_csv} 없음. 먼저 `label_ee_3class.py --split-from auto`.")
        return 1

    import torch
    import torch.nn as nn
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.ee_runner import EvalEERunner, EE_INPUT_EMBEDDER
    # real 모드 필수 — deploy(xstest/harmbench 러너)와 동일하게 EE 체크포인트 +
    # MemoryBank를 로드해야 feature가 일치한다. mock이면 memory_vectors=zeros로
    # 추출돼(emotion L2 급감) 추론(memory 로드)과 분포가 어긋나 head가 붕괴한다.
    runner = EvalEERunner.get_instance(ee_config=load_settings("real").ee)
    runner.initialize()

    tr_texts, Ytr, tr_src, Mtr = _load_csv(train_csv)
    ho_texts, Yho, ho_src, Mho = _load_csv(heldout_csv)
    sup = {DIMS[j]: int(Mtr[:, j].sum()) for j in range(3)}
    logger.info(f"train {len(tr_texts)}  heldout {len(ho_texts)}  supervised/dim (train) = {sup}")
    Xtr = extract_features("train", tr_texts, runner)
    Xho = extract_features("heldout", ho_texts, runner)

    model = build_head(Xtr.shape[1]).to(dev)
    opt = torch.optim.Adam(model.parameters(), lr=args.lr, weight_decay=1e-4)
    dim_w = torch.tensor([1.0, float(args.i_weight), 1.0], device=dev)
    Xtr_t = torch.tensor(Xtr, device=dev)
    Ytr_t = torch.tensor(Ytr, device=dev)
    Mtr_t = torch.tensor(Mtr, device=dev)
    Mho_t = torch.tensor(Mho, device=dev)
    # Effective weight: judge-labeled axes weight 1.0; the un-chosen polar (target 0, the
    # IMPLIED negative from the polarity choice) weight neg_weight. neg_weight=0 → pure mask.
    neg_w = float(args.neg_weight)
    Weff_tr = Mtr_t + (1.0 - Mtr_t) * neg_w
    Weff_ho = Mho_t + (1.0 - Mho_t) * neg_w
    logger.info(f"neg_weight={neg_w} (off-polar implied-zero supervision weight)")
    N = len(Xtr_t)
    # 샘플별 가중(옵션): trick_safe 등 특정 source slice를 up-weight해 FPR 교정 강도 조절.
    sample_w = torch.ones(N, device=dev)
    if args.upweight_source and args.upweight_factor != 1.0:
        n_up = 0
        for i, s in enumerate(tr_src):
            if s == args.upweight_source:
                sample_w[i] = args.upweight_factor
                n_up += 1
        logger.info(f"up-weight source='{args.upweight_source}' ×{args.upweight_factor}: {n_up}건")

    best, best_state = 1e9, None
    for ep in range(args.epochs):
        model.train()
        perm = torch.randperm(N, device=dev)
        tot = 0.0
        for s in range(0, N, args.batch):
            idx = perm[s:s + args.batch]
            pred = model(Xtr_t[idx])
            loss_el = nn.functional.binary_cross_entropy(pred, Ytr_t[idx], reduction="none")
            we = Weff_tr[idx]
            # weighted reduction: labeled axes (w=1) + implied-negative off-polar (w=neg_w).
            # With neg_w=0 ⇒ pure mask; with M=ones (legacy) ⇒ byte-identical to old .mean().
            loss = (loss_el * dim_w * sample_w[idx].unsqueeze(1) * we).sum() / we.sum().clamp_min(1.0)
            opt.zero_grad(); loss.backward(); opt.step()
            tot += loss.item() * len(idx)
        # held-out loss (early stop 기준) — masked
        model.eval()
        with torch.no_grad():
            ho_pred = model(torch.tensor(Xho, device=dev))
            ho_bce = nn.functional.binary_cross_entropy(
                ho_pred, torch.tensor(Yho, device=dev), reduction="none")
            ho_loss = ((ho_bce * dim_w * Weff_ho).sum() / Weff_ho.sum().clamp_min(1.0)).item()
        if (ep + 1) % 10 == 0 or ep == 0:
            logger.info(f"  epoch {ep+1:03d}  train {tot/N:.4f}  heldout {ho_loss:.4f}")
        if ho_loss < best:
            best, best_state = ho_loss, {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    report, routing = evaluate(model.cpu(), Xho, Yho, ho_src, Mho)
    logger.info(f"\n===== HELD-OUT (best heldout loss {best:.4f}) =====")
    for d in DIMS:
        logger.info(f"  {d}: MAE={report[d]['mae']}  AUC@0.5={report[d]['auc_at_0.5']}  "
                    f"n_sup={report[d].get('n_sup')}")
    if routing:
        logger.info("  Compass 라우팅 (judge-primary → 분기 분포):")
        for k, v in routing.items():
            logger.info(f"    {k:8} → {v}")

    out_pt.parent.mkdir(parents=True, exist_ok=True)
    torch.save({
        "state_dict": best_state,
        "in_dim": int(Xtr.shape[1]),
        "dims": DIMS,
        "arch": "Linear(in,128)-ReLU-Dropout-Linear(128,64)-ReLU-Linear(64,3)-Sigmoid",
        "embedder": EE_INPUT_EMBEDDER,
        "heldout_loss": best,
        "report": report,
        "labels": args.labels,
        "neg_weight": neg_w,
    }, out_pt)
    logger.info(f"saved → {out_pt}")
    logger.info("다음(S3-②): NeutroEERouter 어댑터 + Compass 라우팅 연결 → S4 평가")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
