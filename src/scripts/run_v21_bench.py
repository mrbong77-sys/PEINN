#!/usr/bin/env python3
"""run_v21_bench.py — PEINN v2.1 evaluation harness (6 benches × 17 arms), separate + auto-push.

PEINN v2.1 = v4 NeutroEE head (ee_neutro_head_v4.pt) + the head⊗energy gated 5-tier router
(NeutroEERouterV21, engine="neutro_v21", LOCKED θ F=0.15). A SEPARATE batch script — the v1.0
run_stat_batch.py and arms are untouched; it only sets PEAOS_EE_ENGINE=neutro_v21 (PEINN arms
route via v2.1) + PEINN_NEUTRO_HEAD=v4 head, reuses run_stat_batch's bench runners (RUN_FUNCS)
with output redirected to pea_eval/output/v21/, and auto-pushes ONCE per invocation.

MIRRORS run_stat_batch's CLI (same options): positional `modules runs`, --arms (comma/range),
--gpt-oss, --no-judge; plus v2.1's --no-push. Vanilla/NeMo/Llama-Guard arms are unchanged
comparators; only PEINN arms (H04/07/10/13[/21]) route via v2.1.

RUN ON DGX (Ollama + bench data + the v4 head).
  python scripts/run_v21_bench.py                          # all 6 benches, 1 run, auto-push
  python scripts/run_v21_bench.py harmbench,xstest 1 --arms H01,H04
  python scripts/run_v21_bench.py harmbench:10,ggb:10,xstest:5,taxonomy:5,ethics:5,morables:5 --arms H01-H13
  python scripts/run_v21_bench.py 10                       # all benches, 10 runs (digit shortcut)
  python scripts/run_v21_bench.py --gpt-oss --no-judge --no-push
"""
from __future__ import annotations

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

V21_DIR = PROJECT_ROOT / "pea_eval" / "output" / "v21"
V4_HEAD = PROJECT_ROOT / "pea_eval" / "data" / "ee_neutro_head_v4.pt"
BENCHES = ["harmbench", "xstest", "taxonomy", "ethics", "morables", "ggb"]
ARMS_17 = [f"H{i:02d}" for i in range(1, 18)]   # H01–H17 (gpt-oss H18–21 via --gpt-oss)


# 라우팅 정식 최종 명칭(기록지용). 레거시 route 문자열(하위 pass 로직이 사용)은
# 그대로 두고, v21 기록 CSV의 neutro_route 컬럼만 이 명칭으로 정규화한다.
ROUTE_OFFICIAL = {
    "hard-block": "Hard-block",
    "2-pass-refusal": "Reasoned-Refusal",
    "2-pass-reasoning": "Deliberation",
    "2-pass-reasoning-soft": "Soft-reasoning",
    "1-pass": "Direct-Answer",
}


def _canonicalize_v21_routes() -> None:
    """v21 출력 CSV의 neutro_route 컬럼을 정식 최종 명칭으로 재기록 (idempotent).
    이미 정식명칭이면 그대로 통과 → 재실행해도 변경 없음(불필요한 커밋 방지)."""
    import csv
    for p in sorted(V21_DIR.glob("*.csv")):
        with p.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None or "neutro_route" not in reader.fieldnames:
                continue
            fields = reader.fieldnames
            rows = list(reader)
        if not any(r.get("neutro_route") in ROUTE_OFFICIAL for r in rows):
            continue  # 이미 정식명칭(or 빈 값)뿐 — skip
        for r in rows:
            r["neutro_route"] = ROUTE_OFFICIAL.get(r.get("neutro_route", ""), r.get("neutro_route", ""))
        with p.open("w", encoding="utf-8", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=fields)
            w.writeheader()
            w.writerows(rows)
        print(f"[route-name] 정규화: {p.name}")


def _git(*args, check=False):
    return subprocess.run(["git", *args], cwd=str(PROJECT_ROOT),
                          capture_output=True, text=True, check=check)


def auto_push(label: str) -> None:
    rel = "pea_eval/output/v21"
    _git("add", rel)
    if not _git("status", "--porcelain", rel).stdout.strip():
        print("[auto-push] v21에 변경 없음 — skip")
        return
    _git("commit", "-m", f"PEINN v2.1 bench: {label} (DGX)")
    for i in range(4):
        r = _git("push", "-u", "origin", "main")
        if r.returncode == 0:
            print(f"[auto-push] pushed: {label}")
            return
        print(f"[auto-push] push 실패(retry {i+1}): {r.stderr.strip()[:120]}")
        time.sleep(2 ** (i + 1))
    print("[auto-push] push 4회 실패 — 수동 푸시 필요")


async def run(bench_runs: list[tuple[str, int]], arms: list[str], no_judge: bool, no_push: bool) -> None:
    import run_stat_batch as R
    R.FINAL_DIR = V21_DIR                            # redirect all batch output → v21
    from pea_eval.config.settings import load_settings
    settings = load_settings("real")
    if no_judge:
        settings.enable_judge = False
        print("  ⚠️ LMM-as-a-Judge 비활성화")
    eng = getattr(settings.ee, "engine", "?")
    if eng != "neutro_v21":
        raise SystemExit(f"engine={eng!r} (PEAOS_EE_ENGINE=neutro_v21 미적용?)")
    print(f"PEINN v2.1: engine={eng}  head={os.environ.get('PEINN_NEUTRO_HEAD')}  out={V21_DIR}")
    print("  계획: " + ", ".join(f"{b}×{r}" for b, r in bench_runs))
    # bench별 완료 즉시 push: 중간 결과 수시 확인 + 돌발 중단 시 기록 보존(연속 런 전체
    # 완료까지 기다리지 않음). bench가 에러나면 해당 bench는 push 건너뜀.
    for b, runs in bench_runs:
        if b not in R.RUN_FUNCS:
            print(f"[skip] 알 수 없는 bench: {b}"); continue
        print(f"\n===== v2.1 bench: {b}  (runs={runs}, arms={len(arms)}: {','.join(arms)}) =====")
        try:
            await R.RUN_FUNCS[b](settings, runs, arms)
        except Exception as e:  # noqa: BLE001
            print(f"[error] {b}: {type(e).__name__}: {str(e)[:200]}")
            continue
        if not no_push:
            _canonicalize_v21_routes()              # neutro_route → 정식 최종 명칭
            auto_push(f"{b} × {len(arms)}arm ×{runs}")


def main() -> int:
    from run_stat_batch import _parse_arm_filter   # reuse the canonical comma/range parser

    ap = argparse.ArgumentParser(description="PEINN v2.1 bench (6×17), auto-push — mirrors run_stat_batch CLI")
    ap.add_argument("modules", nargs="?", default=None,
                    help="benches (comma-sep). bench별 횟수는 'bench:N'으로 지정 가능 "
                         "(콜론 없으면 positional runs/기본 1 적용). "
                         "예: harmbench,xstest  또는  harmbench:10,ggb:10,xstest:5,taxonomy:5. 생략 시 전체 6개")
    ap.add_argument("runs", nargs="?", type=int, default=None,
                    help="콜론 없는 bench에 적용할 기본 반복 수 (default 1). digit-only면 전체벤치+그 횟수")
    ap.add_argument("--arms", nargs="+", default=None,
                    help="arm IDs (comma/range). 예: H01,H04 또는 H08-H13 (default H01–H17)")
    ap.add_argument("--gpt-oss", dest="gpt_oss", action="store_true",
                    help="gpt-oss:120b 4-arm 추가 shortcut (H18–H21; H21=PEINN→v2.1)")
    ap.add_argument("--no-judge", action="store_true", help="LMM-as-a-Judge 채점 건너뛰기")
    ap.add_argument("--no-push", action="store_true", help="auto-push 건너뛰기")
    args = ap.parse_args()

    # digit shortcut: `run_v21_bench.py 10` → all benches, 10 runs
    if args.modules and args.modules.isdigit() and args.runs is None:
        args.runs, args.modules = int(args.modules), None
    default_runs = args.runs or 1

    # bench별 횟수 파싱: 토큰이 'bench:N'이면 N회, 아니면 default_runs.
    if args.modules:
        bench_runs: list[tuple[str, int]] = []
        for tok in args.modules.split(","):
            tok = tok.strip().lower()
            if not tok:
                continue
            name, sep, rs = tok.partition(":")
            name = name.strip()
            if name not in BENCHES:
                print(f"⚠️ 유효 bench 아님: {name!r}  (valid: {','.join(BENCHES)})"); return 1
            if sep:
                if not rs.strip().isdigit() or int(rs) < 1:
                    print(f"⚠️ 횟수 파싱 실패: {tok!r}  (예: harmbench:10)"); return 1
                bench_runs.append((name, int(rs)))
            else:
                bench_runs.append((name, default_runs))
        if not bench_runs:
            print(f"⚠️ 유효 bench 없음: {args.modules}"); return 1
    else:
        bench_runs = [(b, default_runs) for b in BENCHES]

    # arms (mirror run_stat_batch): --arms + --gpt-oss shortcut
    if args.arms:
        arms = _parse_arm_filter(",".join(args.arms))
        if not arms:
            print(f"⚠️ --arms 파싱 실패: {args.arms}  (예: H01,H04 또는 H08-H13)"); return 1
    else:
        arms = list(ARMS_17)
    if args.gpt_oss:
        arms = sorted(set(arms) | {"H18", "H19", "H20", "H21"})
        print(f"[gpt-oss] arms = {arms}")

    if not V4_HEAD.exists():
        print(f"[warn] v4 head 없음: {V4_HEAD} — DGX에서 train_neutro_head.py로 배치 필요")
    os.environ["PEAOS_EE_ENGINE"] = "neutro_v21"     # PEINN arms → v2.1 routing
    os.environ.setdefault("PEINN_NEUTRO_HEAD", str(V4_HEAD))
    V21_DIR.mkdir(parents=True, exist_ok=True)

    # push는 run() 내부에서 bench별로 수행(중간 결과 보존). 마지막에 한 번 더
    # 호출해 혹시 남은 변경(정규화 등)을 회수.
    asyncio.run(run(bench_runs, arms, args.no_judge, args.no_push))

    if not args.no_push:
        _canonicalize_v21_routes()
        auto_push("final sweep (잔여 변경 회수)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
