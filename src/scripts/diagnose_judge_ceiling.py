#!/usr/bin/env python3
"""
Judge ceiling 진단 — 기존 ethics_batch CSV에서 판정 실패 패턴 분석.

확인 항목:
  1. Dilemma judge_rationale 빈/default 비율 (parsing 실패 추정)
  2. score / rqi / ecm 분포 (정확히 3.0에 몰려있는지)
  3. arm × judge_rationale 패턴 (특정 arm이 더 실패하는지)
  4. judge 응답 sample 출력 (실제로 뭘 반환했는지)

사용:
  python scripts/diagnose_judge_ceiling.py
  python scripts/diagnose_judge_ceiling.py --csv path/to/ethics_batch.csv
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def fnum(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def find_latest_ethics_csv() -> Path | None:
    out = REPO_ROOT / "pea_eval" / "output" / "final"
    if not out.exists():
        out = REPO_ROOT / "pea_eval" / "output"
    csvs = list(out.rglob("ethics_batch_*.csv"))
    if not csvs:
        return None
    return max(csvs, key=lambda p: p.stat().st_mtime)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", type=Path, help="ethics_batch CSV 경로 (미지정 시 가장 최근 파일)")
    ap.add_argument("--show-rationale", type=int, default=5,
                    help="arm별 판정 사유 sample 출력 개수 (default 5)")
    args = ap.parse_args()

    path = args.csv or find_latest_ethics_csv()
    if path is None or not path.exists():
        print("FAIL: ethics_batch CSV를 찾을 수 없습니다. --csv로 직접 지정하세요.")
        return 1
    print(f"=== {path.name} ===\n")

    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    dilemma = [r for r in rows if r.get("instrument") == "Dilemma"]
    if not dilemma:
        print("Dilemma rows 없음.")
        return 1

    arms = sorted(set(r["arm_id"] for r in dilemma))
    print(f"arms: {arms},  Dilemma 총 {len(dilemma)}행\n")

    # ── 1. judge_rationale 분석 ──
    print("─" * 60)
    print("1. judge_rationale (parsing 실패 / 기본값 추정)")
    print("─" * 60)
    for arm in arms:
        sub = [r for r in dilemma if r["arm_id"] == arm]
        rats = [(r.get("judge_rationale") or "").strip() for r in sub]
        empty = sum(1 for x in rats if not x)
        short = sum(1 for x in rats if x and len(x) < 20)
        unique_short = len(set(x for x in rats if x and len(x) < 80))
        lens = [len(x) for x in rats if x]
        print(f"  {arm}  n={len(sub)}  empty_rationale={empty}  short(<20)={short}  "
              f"unique_rationales={len(set(rats))}/{len(sub)}  "
              f"median_len={statistics.median(lens) if lens else 0:.0f}")

    # ── 2. score 분포 ──
    print()
    print("─" * 60)
    print("2. score / rqi / ecm 분포 (3.0에 정확히 몰려있는지)")
    print("─" * 60)
    for arm in arms:
        sub = [r for r in dilemma if r["arm_id"] == arm]
        for field in ("score", "rqi", "ecm"):
            vals = [fnum(r.get(field)) for r in sub if fnum(r.get(field)) is not None]
            if not vals:
                continue
            mn, mx = min(vals), max(vals)
            sd = statistics.stdev(vals) if len(vals) > 1 else 0
            distinct = len(set(round(v, 3) for v in vals))
            print(f"  {arm} {field:6s}  n={len(vals):3d}  min={mn:.2f}  max={mx:.2f}  "
                  f"mean={sum(vals)/len(vals):.3f}  sd={sd:.4f}  distinct={distinct}")

    # ── 3. judge_rationale sample ──
    print()
    print("─" * 60)
    print(f"3. judge_rationale sample (arm별 {args.show_rationale}건)")
    print("─" * 60)
    for arm in arms:
        sub = [r for r in dilemma if r["arm_id"] == arm]
        print(f"\n  [{arm}]")
        for r in sub[:args.show_rationale]:
            rat = (r.get("judge_rationale") or "").strip()
            rqi = r.get("rqi", "")
            score = r.get("score", "")
            iid = r.get("item_id", "")
            print(f"    {iid}  rqi={rqi}  score={score}")
            print(f"      rationale: {rat[:200] if rat else '[EMPTY]'}")

    # ── 4. 진단 요약 ──
    print()
    print("─" * 60)
    print("진단 요약")
    print("─" * 60)
    all_rats = [(r.get("judge_rationale") or "").strip() for r in dilemma]
    empty_pct = 100 * sum(1 for x in all_rats if not x) / len(all_rats)
    unique_pct = 100 * len(set(all_rats)) / len(all_rats)
    all_rqi = [fnum(r.get("rqi")) for r in dilemma if fnum(r.get("rqi")) is not None]
    rqi_three = sum(1 for v in all_rqi if abs(v - 3.0) < 0.01)
    rqi_three_pct = 100 * rqi_three / len(all_rqi) if all_rqi else 0

    print(f"  judge_rationale empty: {empty_pct:.0f}%")
    print(f"  unique rationales: {unique_pct:.0f}%")
    print(f"  rqi == 3.00 (정확): {rqi_three_pct:.0f}%")

    print()
    if empty_pct > 30:
        print("  → 가설 1 (parsing 실패): 강함. judge 응답이 JSON으로 안 떨어지고 있을 가능성.")
        print("     ethics_eval.judge_dilemmas_batch의 try/except에서 무엇이 잡히는지 로깅 추가 필요.")
    elif rqi_three_pct > 80 and unique_pct > 50:
        print("  → 가설 2 (judge 중간값 편향): 강함. rationale은 다양한데 점수만 3에 몰림.")
        print("     judge가 rubric의 1-5 범위에서 확신 없이 안전한 3을 default로 선택.")
        print("     rubric 변경(behavioral extraction) 또는 stronger judge 필요.")
    elif rqi_three_pct < 20:
        print("  → 가설 3 (실제 ceiling 아님): 점수가 분산됨. ceiling 의심이 잘못된 것.")
    else:
        print("  → 혼합 패턴: empty와 score-3 둘 다 부분적. 두 원인 모두 작용 중.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
