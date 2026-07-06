"""
merge_aug_into_train.py — 증강 CSV를 train.csv에 *열 이름 정렬*로 안전 병합.

`tail >>` 는 열 순서를 안 맞춰 source 문자열이 T/I/F(숫자) 열에 들어가는 오염을
일으킨다. 본 스크립트는 pandas concat(열 이름 기준 정렬)으로 합치고, train.csv가
요구하는 컬럼(text,T,I,F,source)이 모두 있는지 검증한다.

사용:
  python scripts/merge_aug_into_train.py \
      pea_eval/data/ee_3class/train.csv \
      pea_eval/data/ee_3class/aug_fp_benign.csv

동작:
- aug에서 기존 'aug_fp*'/'hardneg*' source 행이 train에 이미 있으면 먼저 제거(재실행 안전).
- 열 이름으로 정렬해 concat → train.csv 덮어쓰기(.bak 백업 생성).
"""
import sys
from pathlib import Path

import pandas as pd

REQUIRED = ["text", "T", "I", "F", "source"]


def main():
    if len(sys.argv) < 3:
        print("usage: python scripts/merge_aug_into_train.py <train.csv> <aug.csv> [<aug2.csv> ...]")
        sys.exit(1)
    train_path = Path(sys.argv[1])
    aug_paths = sys.argv[2:]

    base = pd.read_csv(train_path)
    print(f"train.csv 로드: {len(base)}행, 열={list(base.columns)}")
    miss = [c for c in REQUIRED if c not in base.columns]
    if miss:
        print(f"❌ train.csv에 필수 열 누락: {miss} — 열 이름을 확인하세요.")
        sys.exit(2)

    # T/I/F가 숫자로 읽히는지(=기존 오염 여부) 점검
    for d in ("T", "I", "F"):
        bad = pd.to_numeric(base[d], errors="coerce").isna() & base[d].notna()
        if bad.any():
            print(f"⚠️ train.csv의 {d} 열에 비숫자 {int(bad.sum())}건 — 오염 의심. "
                  f"먼저 `grep -v aug_fp`로 복구 후 재실행하세요.")
            sys.exit(3)

    aug_frames = []
    for ap in aug_paths:
        a = pd.read_csv(ap)
        am = [c for c in REQUIRED if c not in a.columns]
        if am:
            print(f"❌ {ap} 필수 열 누락: {am}"); sys.exit(2)
        aug_frames.append(a[REQUIRED])
        print(f"aug 로드: {ap} → {len(a)}행")
    aug = pd.concat(aug_frames, ignore_index=True)

    # 재실행 안전: 같은 source 접두(aug_fp/hardneg)가 base에 이미 있으면 제거
    aug_srcs = set(aug["source"].astype(str).unique())
    pre = len(base)
    base = base[~base["source"].astype(str).isin(aug_srcs)]
    if len(base) < pre:
        print(f"  기존 동일 source {pre-len(base)}행 제거(재실행 안전)")

    bak = train_path.with_suffix(".csv.bak")
    bak.write_bytes(train_path.read_bytes())  # 원본 백업

    out = pd.concat([base, aug], ignore_index=True)  # 열 이름 기준 정렬
    out.to_csv(train_path, index=False)
    print(f"✅ 병합 완료: {len(base)} + {len(aug)} = {len(out)}행 → {train_path}")
    print(f"   백업: {bak}  | 열={list(out.columns)}")
    print(f"   source 분포(증강): { {k:int(v) for k,v in aug['source'].value_counts().items()} }")


if __name__ == "__main__":
    main()
