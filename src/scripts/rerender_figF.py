"""
rerender_figF.py — FigF (T/I/F by gt) 단독 재생성 (sharex 버그 수정 적용).

기존 emotion_routing_data.csv가 있으면 즉시 재생성. 본 평가 전체 재실행 불필요.

Usage:
  python scripts/rerender_figF.py /path/to/emotion_routing_data.csv
  python scripts/rerender_figF.py /path/to/emotion_routing_data.csv --out figures/

본 스크립트는 run_xai_capture.py의 render_tif_by_gt 함수를 그대로 호출 — 코드 중복 회피.
"""
from __future__ import annotations
import argparse
import sys
from pathlib import Path

if __name__ == "__main__":
    PROJ = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(PROJ))

    ap = argparse.ArgumentParser()
    ap.add_argument("csv", help="emotion_routing_data.csv 경로")
    ap.add_argument("--out", default="FigF_tif_by_gt_fixed.png", help="출력 PNG 경로")
    args = ap.parse_args()

    import pandas as pd
    from run_xai_capture import render_tif_by_gt

    df = pd.read_csv(args.csv)
    print(f"loaded {len(df)} rows, columns={list(df.columns)[:10]}...")
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    render_tif_by_gt(df, str(out))
    print(f"✓ saved: {out}")
