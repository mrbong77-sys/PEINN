#!/usr/bin/env python3
"""
NeMo Guardrails용 fastembed 모델 prefetch.

문제:
  NeMo Guardrails는 user-message 유사도 인덱스에 fastembed(ONNX)의
  all-MiniLM-L6-v2를 사용한다. 평가 파이프라인은 pea_eval/backends/
  hf_backend.py import 시점에 HF_HUB_OFFLINE=1 / TRANSFORMERS_OFFLINE=1
  을 강제하므로, fastembed 캐시(/tmp/fastembed_cache)가 비어 있으면
  NeMo 초기화가 실패한다:
     ValueError: Could not load model sentence-transformers/all-MiniLM-L6-v2
  → NeMo arm (H03/H06/H09/H12) 이 전부 collapse.

해결:
  네트워크가 살아있는 상태에서 이 스크립트를 1회 실행해 fastembed
  캐시를 채운다. 이후 오프라인 평가에서 NeMo가 캐시된 모델을 로드한다.

  ⚠ 이 스크립트는 hf_backend를 import하지 않는다 (offline env가 켜지면
    안 되므로). 평가 실행 전에 별도 프로세스로 먼저 돌린다.

사용:
  python scripts/prefetch_fastembed.py
  # 기본 캐시: /tmp/fastembed_cache (fastembed default)
  # 다른 경로: FASTEMBED_CACHE_PATH=/path python scripts/prefetch_fastembed.py
"""
from __future__ import annotations

import os
import sys

# offline env가 켜져 있으면 다운로드 불가 — 명시적으로 해제
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)

# NeMo Guardrails fastembed 기본 모델 + 캐시 경로
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = os.environ.get("FASTEMBED_CACHE_PATH", "/tmp/fastembed_cache")


def main() -> int:
    try:
        from fastembed import TextEmbedding
    except ImportError:
        print("FAIL: fastembed 미설치. pip install fastembed", file=sys.stderr)
        return 1

    print(f"Downloading fastembed model: {MODEL_NAME}")
    print(f"  cache_dir: {CACHE_DIR}")
    os.makedirs(CACHE_DIR, exist_ok=True)

    try:
        emb = TextEmbedding(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
        # forward 1회 — 모델 파일이 실제 사용 가능한지 확인
        vecs = list(emb.embed(["prefetch verification sentence"]))
        dim = len(vecs[0]) if vecs else 0
        print(f"  ✓ 다운로드 + 임베딩 검증 완료 (dim={dim})")
    except Exception as e:
        print(f"FAIL: fastembed 다운로드 실패: {type(e).__name__}: {e}", file=sys.stderr)
        return 1

    # 오프라인 재로드 검증 — 평가 환경과 동일한 조건으로 한번 더 확인
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    try:
        from fastembed import TextEmbedding as TE2
        emb2 = TE2(model_name=MODEL_NAME, cache_dir=CACHE_DIR)
        list(emb2.embed(["offline reload check"]))
        print("  ✓ 오프라인(HF_HUB_OFFLINE=1) 재로드 성공 — NeMo arm 정상 초기화 가능")
    except Exception as e:
        print(
            f"WARN: 오프라인 재로드 실패: {e}\n"
            f"  캐시는 받았으나 평가 시 offline 로드가 안 될 수 있음. "
            f"FASTEMBED_CACHE_PATH 환경변수가 평가 프로세스와 동일한지 확인.",
            file=sys.stderr,
        )
        return 2

    print(f"\n완료. 평가 실행 시 동일 캐시({CACHE_DIR})가 쓰이도록 보장하세요.")
    print("  (fastembed 기본 캐시가 /tmp 라 재부팅 시 사라질 수 있음 — "
          "그 경우 이 스크립트를 다시 실행)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
