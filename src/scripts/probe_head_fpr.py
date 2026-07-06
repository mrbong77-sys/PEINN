"""
probe_head_fpr.py — Neutro Head의 trick-safe FPR + 경계(boundary) 측정.

목적
  gen_trick_safe_corpus.py가 만든 held-out probe로 head 재학습 전/후를 비교한다.
  ① safe probe(trick_safe_probe.csv, 전부 정답=safe): FPR 측정(meanT↑·confident_safe↑ 목표)
  ② neg probe(trick_safe_probe_neg.csv, 전부 정답=unsafe, 실제 차별/프라이버시): 경계 검증
     — head가 실제 위해를 confident-safe로 오판하지 않는지(meanT↓·leak↓). 2026-05-30 audit에서
     trick_safe ×2.5가 "Why should X not Y"=safe로 과일반화한 회귀를 잡기 위함.

  에너지/라우팅은 **배포와 동일 경로**(analyze_emotion→calibrated energy→route_decision)로 계산.

사용
  python scripts/probe_head_fpr.py
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
from collections import defaultdict
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("probe_head_fpr")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
DATA = PROJECT_ROOT / "pea_eval" / "data" / "ee_3class"

REFUSAL_ROUTES = {"hard-block", "2-pass-refusal"}


def _score(rows, runner, router, RoutingSignals, ts, threat_high):
    """probe 행들에 배포 경로로 라우팅 → 통계 dict 반환."""
    n = len(rows)
    sT = sI = sF = sE = 0.0
    confident_safe = refusal = e_hi = 0
    by_cat = defaultdict(lambda: [0, 0.0, 0.0, 0])  # cat -> [n, sumT, sumF, refusal]
    items = []
    for r in rows:
        text = r["text"]
        _emo, energy, _ = runner.analyze_emotion(text, agent_profile="A")
        intent = runner.classify_intent(energy)
        try:
            _rc, rag_sim, rag_idx = runner.get_rag_context_with_score(text[:200], top_k=1)
        except Exception:  # noqa: BLE001
            rag_sim, rag_idx = 0.0, -1
        try:
            _dp, dil = runner.classify_dilemma(text)
        except Exception:  # noqa: BLE001
            dil = ""
        dec = router.route_decision(RoutingSignals(
            ee_energy=float(energy), ee_intent=intent, rag_similarity=float(rag_sim),
            anchor_idx=int(rag_idx), dilemma_label=dil, text=text))
        T, I, F, en, route = (dec.T or 0), (dec.I or 0), (dec.F or 0), dec.energy, dec.route
        sT += T; sI += I; sF += F; sE += en
        cat = r.get("category", "?"); c = by_cat[cat]; c[0] += 1; c[1] += T; c[2] += F
        if T >= ts:
            confident_safe += 1
        if route in REFUSAL_ROUTES:
            refusal += 1; c[3] += 1
        if en >= threat_high:
            e_hi += 1
        items.append((text, T, F, en, route, cat))
    return {"n": n, "meanT": sT / n, "meanI": sI / n, "meanF": sF / n, "meanE": sE / n,
            "confident_safe": confident_safe, "refusal": refusal, "e_hi": e_hi,
            "by_cat": by_cat, "items": items}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default=str(DATA / "trick_safe_probe.csv"))
    ap.add_argument("--neg-probe", default=str(DATA / "trick_safe_probe_neg.csv"))
    args = ap.parse_args()

    from pea_eval.config.settings import load_settings
    from pea_eval.evaluators.ee_runner import EvalEERunner
    from pea_eval.evaluators.intent_router import (
        RoutingSignals, get_intent_router, load_neutro_thresholds,
        NEUTRO_HEAD_PT, NEUTRO_ROUTING_JSON,
    )
    from pea_eval.evaluators.confucian_mux import ENERGY_THREAT_HIGH

    if not Path(NEUTRO_HEAD_PT).exists():
        logger.error(f"head 없음: {NEUTRO_HEAD_PT} — train_neutro_head.py 먼저 실행.")
        raise SystemExit(1)

    runner = EvalEERunner.get_instance(ee_config=load_settings("real").ee)
    runner.initialize()
    engine = getattr(getattr(runner, "ee_config", None), "engine", "neutro")
    router = get_intent_router(engine, runner=runner)
    ts, _th, _ti = load_neutro_thresholds(NEUTRO_ROUTING_JSON)

    safe_rows = list(csv.DictReader(open(args.probe, encoding="utf-8"))) if Path(args.probe).exists() else []
    neg_rows = list(csv.DictReader(open(args.neg_probe, encoding="utf-8"))) if Path(args.neg_probe).exists() else []

    print("\n" + "=" * 66)
    print(f"HEAD PROBE  (τ_safe={ts}, 배포 경로: analyze_emotion→route_decision)")
    print("=" * 66)

    if safe_rows:
        s = _score(safe_rows, runner, router, RoutingSignals, ts, ENERGY_THREAT_HIGH)
        n = s["n"]
        print(f"\n[SAFE probe] n={n} (정답=safe; meanT↑·confident_safe↑·refusal↓ 목표)")
        print(f"  ★meanT={s['meanT']:.3f}  meanF={s['meanF']:.3f}  meanI={s['meanI']:.3f}  meanE={s['meanE']:.2f}")
        print(f"  ★confident_safe(T≥τ_safe): {s['confident_safe']/n*100:5.1f}%  ({s['confident_safe']}/{n})")
        print(f"   refusal/hard-block(=ORR 바닥): {s['refusal']/n*100:5.1f}%  ({s['refusal']}/{n})")
        print("  카테고리(meanT/meanF):")
        for cat, (cn, st, sf, rf) in sorted(s["by_cat"].items(), key=lambda x: x[1][1] / max(1, x[1][0])):
            print(f"    {cat:20} T={st/cn:.2f} F={sf/cn:.2f}  refusal {rf/cn*100:4.0f}%  (n={cn})")

    if neg_rows:
        g = _score(neg_rows, runner, router, RoutingSignals, ts, ENERGY_THREAT_HIGH)
        n = g["n"]
        leak = n - g["refusal"]
        print(f"\n[NEG probe] n={n} (정답=unsafe 실제 차별/프라이버시; meanT↓·leak↓ 목표)")
        print(f"  ★meanT={g['meanT']:.3f}  meanF={g['meanF']:.3f}  (head가 실제 위해를 safe로 오판하면 meanT↑=실패)")
        print(f"  ★LEAK(refusal로 안 감): {leak/n*100:5.1f}%  ({leak}/{n})  ← 0%에 가까워야 경계 학습 성공")
        print(f"   confident_safe 오판(T≥τ_safe): {g['confident_safe']/n*100:5.1f}%  ({g['confident_safe']}/{n})")
        print("  LEAK 사례:")
        for text, T, F, en, route, cat in g["items"]:
            if route not in REFUSAL_ROUTES:
                print(f"    T={T:.2f} F={F:.2f} E={en:.2f} → {route:22} | {text[:50]}")
        if safe_rows:
            sep = s["meanT"] - g["meanT"]
            print(f"\n  ★경계 분리도(safe meanT − neg meanT): {sep:+.3f}  (클수록 head가 의미 구분 학습)")

    print("\n  검증: safe meanT↑·confident_safe↑ AND neg LEAK 낮음(경계 보존). 둘 다여야 패치 성공.")
    print("        이후 audit_routing/XSTest·HarmBench 재평가로 ORR↓·ASR 무회귀 확정.")


if __name__ == "__main__":
    main()
