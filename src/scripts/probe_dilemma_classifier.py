#!/usr/bin/env python3
"""
DilemmaClassifier 진단 probe — 실제 ethics_benchmark/{mfq,wvs,dilemmas}.json
항목을 분류기에 통과시켜 확률 분포를 출력.

목적: 라우팅이 의도대로 작동하지 않을 때 (예: MFQ를 dilemma로 잡음)
원인이 (a) threshold 미설정 (b) 분류기 자체 분리 실패 중 어느 쪽인지 확정.

사용:
  python scripts/probe_dilemma_classifier.py
  python scripts/probe_dilemma_classifier.py --threshold 0.7   # τ를 바꿔보고 효과 추정
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import torch
from sentence_transformers import SentenceTransformer

from pea_eval.evaluators.dilemma_runner import DilemmaClassifier, MODEL_PATH, _resolve_threshold

DATA = REPO_ROOT / "pea_eval" / "data" / "ethics_benchmark"


def load_mfq() -> list[tuple[str, str]]:
    p = DATA / "mfq.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    out = []
    # mfq.json 실제 구조: foundations.{cat}.{relevance,agreement}_questions
    for f_data in d.get("foundations", {}).values():
        for key in ("relevance_questions", "agreement_questions", "questions"):
            for q in f_data.get(key, []):
                out.append((q["id"], q["prompt"]))
    return out


def load_wvs() -> list[tuple[str, str]]:
    p = DATA / "wvs.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    qs = d.get("domains", {}).get("core_pool", {}).get("questions", [])
    return [(q["id"], q["prompt"]) for q in qs]


def load_dilemmas() -> list[tuple[str, str]]:
    p = DATA / "dilemmas.json"
    d = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for dlm in d.get("dilemmas", []):
        ctx = (dlm.get("description") or "").strip()
        for q in dlm.get("questions", []):
            text = f"Context: {ctx}\n\nQuestion: {q.get('text','')}\n\nTake a single clear stance and briefly explain your reasoning."
            out.append((q["id"], text))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=_resolve_threshold())
    ap.add_argument("--embedder", default=os.environ.get("PEAOS_CALIBRATOR_EMBEDDER", "sentence-transformers/all-mpnet-base-v2"))
    ap.add_argument("--show-each", action="store_true", help="아이템별 개별 확률 출력")
    args = ap.parse_args()

    if not MODEL_PATH.exists():
        print(f"FAIL: 모델 미존재 {MODEL_PATH}")
        return 1
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = DilemmaClassifier().to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    model.eval()
    embedder = SentenceTransformer(args.embedder, device=device)
    print(f"Model: {MODEL_PATH}\nEmbedder: {args.embedder}\nThreshold: {args.threshold}\n")

    groups = [("MFQ", load_mfq()), ("WVS", load_wvs()), ("Dilemma", load_dilemmas())]
    for name, items in groups:
        if not items:
            print(f"[{name}] 데이터 없음")
            continue
        texts = [t for _, t in items]
        with torch.no_grad():
            embs = embedder.encode(texts, convert_to_tensor=True, device=device, show_progress_bar=False)
            probs = model(embs).cpu().numpy().flatten()
        labels = ["DILEMMA" if p >= args.threshold else "NOT" for p in probs]
        d_count = labels.count("DILEMMA")
        print(f"[{name}] n={len(items)}")
        print(f"  prob: min={probs.min():.3f}  median={statistics.median(probs):.3f}  max={probs.max():.3f}  mean={probs.mean():.3f}")
        print(f"  routed DILEMMA: {d_count}/{len(items)} = {100*d_count/len(items):.0f}%   (at τ={args.threshold})")
        # 임계값을 흩뿌려보고 카운트
        print(f"  routed at varying τ:")
        for t in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
            c = sum(1 for p in probs if p >= t)
            print(f"    τ={t:.1f}: {c}/{len(items)} = {100*c/len(items):3.0f}%")
        if args.show_each:
            for (qid, _), p in zip(items, probs):
                mark = "★" if p >= args.threshold else " "
                print(f"    {mark} {p:.3f}  {qid}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
