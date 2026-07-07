"""
PEINN — Statistical Batch Runner for the six canonical benchmarks (run_stat_batch.py)

Runs the paper's six benchmarks × N independent repeats and writes one aggregated CSV
per benchmark (for statistical / LLM-judge analysis).

Benchmarks:
  1. HarmBench  — attack-success rate (do-no-harm axis)
  2. XSTest     — over-refusal vs. unsafe-compliance
  3. Taxonomy   — jailbreak-taxonomy resistance
  4. Ethics     — Jiao et al. moral-reasoning suite (MFA/WVS/RQI)
  5. MORABLES   — narrative moral-judgement robustness
  6. GGB        — Greatest Good Benchmark (Oxford Utilitarianism Scale)

For the v2.1 PEINN arms specifically, prefer `scripts/run_v21_bench.py`, which also sets
the routing engine + head env for you.

Usage:
    python run_stat_batch.py                                 → all six benchmarks
    python run_stat_batch.py harmbench,xstest 1              → a subset, 1 repeat
    python run_stat_batch.py harmbench 1 --arms H04,H07,H10  → specific arms
    python run_stat_batch.py harmbench 1 --gpt-oss           → optional gpt-oss:120b arms (H18-H21)
"""
import asyncio
import csv
import hashlib
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

# 프로젝트 루트 경로 자동 감지
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("peinn.stat_batch_runner")

from pea_eval.config.settings import load_settings, FINAL_DIR, EvalSettings


# ═══════════════════════════════════════════
# 통제 변인 (Controlled Variables)
# ═══════════════════════════════════════════
# Temperature: 0.3 고정 (모든 평가 run 동일)
# Top-P: 0.95 고정
# Seed: run마다 고유 시드 부여 (자연스러운 분산 확보)
# 시스템 프롬프트, 모델 버전: 변경 금지
EVAL_TEMPERATURE = 0.3


def _make_run_seed(eval_type: str, run_idx: int) -> int:
    """
    eval_type + run_idx 조합으로 고유 난수 시드를 생성합니다.
    재현 가능하지만 run마다 다른 값 → 자연스러운 분산 확보.

    예) unesco_01 → 12345, unesco_02 → 67890 (매번 다름)
         unesco_01 재실행 → 12345 (동일 = 재현 가능)
    """
    key = f"{eval_type}_run{run_idx:03d}"
    h = hashlib.sha256(key.encode()).hexdigest()
    return int(h[:8], 16)  # 32-bit 정수 시드


import re as _re

_RUN_TOKEN_RE = _re.compile(r"^r(\d+)$")


def _run_from_run_id(run_id) -> int | None:
    """run_id의 회차 토큰(`_rNN_`)에서 rep 번호를 추출.

    통합 run_id 규칙 f"{prefix}_{arm}_r{rep:02d}_{item}" 에서 arm 바로 뒤의
    첫 `rNN` 토큰이 회차다(item 쪽에 우연히 r숫자가 있어도 첫 토큰만 사용).
    토큰이 없으면(레거시 단일 run_id) None.
    """
    if not run_id:
        return None
    for tok in str(run_id).split("_"):
        m = _RUN_TOKEN_RE.match(tok)
        if m:
            return int(m.group(1))
    return None


# ═══════════════════════════════════════════
# 배치 구성
# ═══════════════════════════════════════════

DEFAULT_RUNS = 10  # p<0.05 확보를 위한 최소 시행 (7-Arm ANOVA)

# Default plan = the six canonical benchmarks reported in the paper (all reproducible
# from this repo). The PEA-OS-specific evals (unesco/flip/mach/delphi) are still
# runnable by naming them explicitly, but are not part of the default reproduction
# set; `tci` is excluded entirely because it needs the PEA-OS orchestrator, which is
# not shipped here.
BATCH_PLAN = [
    ("harmbench", DEFAULT_RUNS),
    ("xstest",    DEFAULT_RUNS),
    ("taxonomy",  DEFAULT_RUNS),
    ("ethics",    DEFAULT_RUNS),
    ("morables",  DEFAULT_RUNS),
    ("ggb",       DEFAULT_RUNS),
]

TYPE_LABELS = {
    "harmbench": "HarmBench",
    "xstest":    "XSTest",
    "taxonomy":  "Taxonomy Eval",
    "ethics":    "LMM Ethics Benchmark",
    "morables":  "Morables (moral robustness)",
    "ggb":       "Greatest Good Bench (OUS)",
}


# ═══════════════════════════════════════════
# 개별 모듈 실행 함수
# ═══════════════════════════════════════════

def _save_results_pickle(results, pkl_path: Path, label: str) -> None:
    """raw results를 pickle로 즉시 백업 — CSV save 실패해도 데이터 손실 방지.

    2026-06-02 다회차 배치(harmbench→xstest 전환) 시 첫 결과 미저장 케이스 진단 도구.
    pickle은 모듈/dataclass 의존하나 동일 PEINN 빌드에서 항상 재로드 가능 — 충분.
    """
    import pickle
    try:
        pkl_path.parent.mkdir(parents=True, exist_ok=True)
        with open(pkl_path, "wb") as f:
            pickle.dump(results, f)
        logger.info(f"  💾 {label} raw pickle backup: {pkl_path.name} ({len(results)} items)")
    except Exception as e:  # noqa: BLE001
        logger.warning(f"  ⚠ {label} pickle backup 실패: {type(e).__name__}: {str(e)[:120]}")


def _save_csv_durable(save_fn, results, csv_path: Path, label: str, *save_fn_args) -> bool:
    """CSV save + fsync + verify. 실패 시 pickle에서 1회 재시도. 결과를 stdout에도 명시.

    2026-06-03 다회차 배치(특히 harmbench)에서 결과지 미저장 케이스 재발 진단·방어:
      - logger.info 출력이 콘솔 어디론가 묻혔을 가능성 → print()로 stdout 직접 출력
      - file buffer가 fsync 안 된 상태에서 다음 bench로 넘어가는 race 의심 → 명시 fsync
      - 검증 후 실패 시 pickle backup으로 1회 재시도 (raw results는 메모리에 있음)

    Returns: 최종 성공 여부 (True/False)
    """
    import os
    import sys

    def _emit(msg):
        # stdout 직접 + logger 동시 — 둘 중 어느 하나라도 콘솔에 도달
        sys.stdout.write(msg + "\n"); sys.stdout.flush()
        logger.info(msg)

    def _attempt_save():
        try:
            save_fn(results, csv_path, *save_fn_args)
            # 명시 fsync — OS write buffer가 디스크에 동기되기 전 race 회피
            with open(csv_path, "rb") as f:
                os.fsync(f.fileno())
            return True, None
        except Exception as e:  # noqa: BLE001
            import traceback
            return False, traceback.format_exc()

    _emit(f"  💾 {label} CSV save 시작: {csv_path.name}")
    ok, err = _attempt_save()
    if ok and csv_path.exists():
        sz = csv_path.stat().st_size
        if sz > 200:
            _emit(f"  ✓ {label} CSV 저장+fsync 확인: {csv_path.name} ({sz:,} bytes)")
            return True
        else:
            _emit(f"  ⚠ {label} CSV 크기 비정상 ({sz} bytes) — 재시도")
            ok = False
    if not ok:
        _emit(f"  ❌ {label} 1차 save 실패 — pickle backup 유지, 재시도")
        if err:
            sys.stderr.write(err + "\n"); sys.stderr.flush()
        # 부분 쓰기 정리
        if csv_path.exists() and csv_path.stat().st_size < 200:
            try:
                csv_path.unlink(missing_ok=True)
            except Exception:  # noqa: BLE001
                pass
        # 2차 시도 (현 results 그대로)
        ok2, err2 = _attempt_save()
        if ok2 and csv_path.exists() and csv_path.stat().st_size > 200:
            sz = csv_path.stat().st_size
            _emit(f"  ✓ {label} CSV 저장+fsync 확인 (재시도): {csv_path.name} ({sz:,} bytes)")
            return True
        _emit(f"  ❌ {label} CSV 최종 실패 — pickle backup 사용으로 사후 복구 필요")
        if err2:
            sys.stderr.write(err2 + "\n"); sys.stderr.flush()
        return False
    return False

async def _run_harmbench_batch(settings, n_runs: int, arm_filter: list[str] | None = None) -> dict:
    """HarmBench N회 시행 → 통합 CSV 경로 반환"""
    from pea_eval.evaluators.harmbench_eval import (
        run_harmbench_eval, save_harmbench_csv, load_harmbench_arms,
    )

    arms, _ = load_harmbench_arms()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = await run_harmbench_eval(
        settings=settings, n_pilot=50, repeats=n_runs, target_arms=arm_filter,
    )

    csv_path = FINAL_DIR / f"harmbench_batch_{n_runs}runs_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _save_results_pickle(results, FINAL_DIR / f"harmbench_raw_{n_runs}runs_{ts}.pkl", "harmbench")
    _save_csv_durable(save_harmbench_csv, results, csv_path, "HarmBench", arms)

    errors = sum(1 for r in results if r.error)
    return {
        "csv_path": str(csv_path),
        "total": len(results),
        "errors": errors,
    }


async def _run_xstest_batch(settings, n_runs: int, arm_filter: list[str] | None = None) -> dict:
    """XSTest N회 시행 → 통합 CSV 경로 반환"""
    from pea_eval.evaluators.xstest_eval import (
        run_xstest_eval, save_xstest_csv,
    )
    from pea_eval.evaluators.harmbench_eval import load_harmbench_arms

    arms, _ = load_harmbench_arms()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = await run_xstest_eval(settings=settings, target_arms=arm_filter, repeats=n_runs)

    csv_path = FINAL_DIR / f"xstest_batch_{n_runs}runs_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _save_results_pickle(results, FINAL_DIR / f"xstest_raw_{n_runs}runs_{ts}.pkl", "xstest")
    _save_csv_durable(save_xstest_csv, results, csv_path, "XSTest", arms)

    errors = sum(1 for r in results if r.error)
    return {
        "csv_path": str(csv_path),
        "total": len(results),
        "errors": errors,
    }


async def _run_taxonomy_batch(settings, n_runs: int, arm_filter: list[str] | None = None) -> dict:
    """Taxonomy N회 시행 → 통합 CSV 경로 반환"""
    from pea_eval.evaluators.taxonomy_eval import (
        run_taxonomy_eval, save_taxonomy_csv,
    )

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    results = await run_taxonomy_eval(settings=settings, repeats=n_runs, target_arms=arm_filter)

    csv_path = FINAL_DIR / f"taxonomy_batch_{n_runs}runs_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _save_results_pickle(results, FINAL_DIR / f"taxonomy_raw_{n_runs}runs_{ts}.pkl", "taxonomy")
    _save_csv_durable(save_taxonomy_csv, results, csv_path, "Taxonomy")

    errors = sum(1 for r in results if r.error)
    return {
        "csv_path": str(csv_path),
        "total": len(results),
        "errors": errors,
    }

async def _run_ethics_batch(settings, n_runs: int, arm_filter: list[str] | None = None) -> dict:
    """LMM Ethics Benchmark N회 시행 → 통합 CSV 경로 반환"""
    from pea_eval.evaluators.ethics_eval import get_evaluator
    from pea_eval.evaluators.llm_client import EvalLLMClient
    from pea_eval.evaluators.harmbench_eval import load_harmbench_arms

    # 클라이언트 초기화 (settings 기반)
    client = EvalLLMClient(
        ollama_config=settings.ollama,
        gemini_config=settings.gemini,
        lmstudio_config=settings.lmstudio
    )
    
    # EE Runner 초기화
    ee_runner = None
    from pea_eval.evaluators.ee_runner import EvalEERunner
    try:
        ee_runner = EvalEERunner.get_instance(ee_config=settings.ee)
        ee_runner.initialize()
    except Exception as e:
        logger.warning(f"Ethics EE 초기화 실패: {e}")

    evaluator = get_evaluator(client, ee_runner)
    arms, _ = load_harmbench_arms()
    
    # Arm 필터링
    target_arm_ids = arm_filter if arm_filter else list(arms.keys())
    
    all_results = []
    for arm_id in target_arm_ids:
        if arm_id not in arms: continue
        arm_cfg = arms[arm_id]
        
        # Arm별 평가 수행 (intra-module repetition)
        results = await evaluator.evaluate_arm(
            arm_id=arm_id,
            arm_config=arm_cfg,
            repeats=n_runs
        )
        all_results.extend(results)

    # ── Dilemma 일괄 채점 (전체 생성 후 1회 — harmbench/taxonomy와 동일 형태) ──
    # 기존: evaluate_arm이 rep마다 judge → judge(26B) 모델을 arm×rep회 로드(시간 주범).
    # 변경: 모든 arm·rep 생성이 끝난 뒤 Dilemma만 모아 1회 채점 → judge 모델 1회 로드.
    dilemmas = [r for r in all_results if r.get("instrument") == "Dilemma"]
    if dilemmas:
        last_model = ""
        for aid in reversed(target_arm_ids):
            if aid in arms:
                last_model = arms[aid].llm_model or ""
                break
        logger.info(f"Ethics: 전체 생성 완료 → Dilemma {len(dilemmas)}건 일괄 채점(judge 1회 로드)")
        await evaluator.judge_dilemmas_batch(dilemmas, unload_model=last_model)  # in-place 채점
    
    # ── 최종 결과 파일 이동 및 경로 반환 ──
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    final_csv = FINAL_DIR / f"ethics_batch_{n_runs}runs_{ts}.csv"
    FINAL_DIR.mkdir(parents=True, exist_ok=True)
    
    evaluator.save_results(arm_id="batch", run_id=f"{n_runs}runs", results=all_results)
    actual_path = evaluator.output_dir / f"results_batch_{n_runs}runs.csv"
    if actual_path.exists():
        import shutil
        shutil.copy2(actual_path, final_csv)
    
    await client.close()
    
    errors = sum(1 for r in all_results if r.get("error"))
    return {
        "csv_path": str(final_csv),
        "total": len(all_results),
        "errors": errors,
    }


async def _run_morables_batch(settings, n_runs: int, arm_filter: list[str] | None = None) -> dict:
    """Morables (moral robustness) N회 시행 → 통합 CSV 경로 반환"""
    from pea_eval.evaluators.morables_eval import (
        run_morables_eval, save_morables_csv,
    )
    from pea_eval.evaluators.harmbench_eval import load_harmbench_arms

    arms, _ = load_harmbench_arms()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    # 사용자 설계: 709-fable 풀에서 rep당 45개 stratified random sample.
    # rep별 seed=42+r 로 재현 가능, arm 간 같은 rep은 동일 fable 셋(페어링 보존).
    results = await run_morables_eval(
        settings=settings, target_arms=arm_filter, repeats=n_runs,
        sample_size=45, base_seed=42,
    )

    csv_path = FINAL_DIR / f"morables_batch_{n_runs}runs_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _save_results_pickle(results, FINAL_DIR / f"morables_raw_{n_runs}runs_{ts}.pkl", "morables")
    _save_csv_durable(save_morables_csv, results, csv_path, "Morables", arms)

    errors = sum(1 for r in results if getattr(r, "error", ""))
    return {"csv_path": str(csv_path), "total": len(results), "errors": errors}


async def _run_ggb_batch(settings, n_runs: int, arm_filter: list[str] | None = None) -> dict:
    """Greatest Good Benchmark (OUS) N회 시행 → 통합 CSV 경로 반환"""
    from pea_eval.evaluators.ggb_eval import (
        run_ggb_eval, save_ggb_csv,
    )
    from pea_eval.evaluators.harmbench_eval import load_harmbench_arms

    arms, _ = load_harmbench_arms()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    results = await run_ggb_eval(settings=settings, target_arms=arm_filter, repeats=n_runs)

    csv_path = FINAL_DIR / f"ggb_batch_{n_runs}runs_{ts}.csv"
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    _save_results_pickle(results, FINAL_DIR / f"ggb_raw_{n_runs}runs_{ts}.pkl", "ggb")
    _save_csv_durable(save_ggb_csv, results, csv_path, "GGB", arms)

    errors = sum(1 for r in results if getattr(r, "error", ""))
    return {"csv_path": str(csv_path), "total": len(results), "errors": errors}


RUN_FUNCS = {
    "harmbench": _run_harmbench_batch,
    "xstest":    _run_xstest_batch,
    "taxonomy":  _run_taxonomy_batch,
    "ethics":    _run_ethics_batch,
    "morables":  _run_morables_batch,
    "ggb":       _run_ggb_batch,
}


# ═══════════════════════════════════════════
# CSV 통합
# ═══════════════════════════════════════════

def consolidate_csvs(
    eval_type: str,
    csv_paths: list[str],
    n_runs: int,
) -> Path:
    """
    N회 시행의 개별 CSV를 하나의 통합 CSV로 병합합니다.
    run 컬럼을 추가하여 SPSS/R에서 바로 분석 가능.

    Returns:
        통합 CSV 파일 경로
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    label = TYPE_LABELS.get(eval_type, eval_type)
    out_path = FINAL_DIR / f"consolidated_{eval_type}_{n_runs}runs_{ts}.csv"
    FINAL_DIR.mkdir(parents=True, exist_ok=True)

    valid_paths = [p for p in csv_paths if p and Path(p).exists()]
    if not valid_paths:
        logger.warning(f"{label}: 통합할 CSV 파일이 없습니다.")
        return out_path

    # 첫 파일에서 헤더 읽기
    with open(valid_paths[0], "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        original_fields = reader.fieldnames or []

    # run, seed, temperature 컬럼을 맨 앞에 추가 (원본에 이미 있으면 중복 제거)
    _orig = [c for c in original_fields if c not in ("run", "seed", "temperature")]
    out_fields = ["run", "seed", "temperature"] + _orig

    with open(out_path, "w", encoding="utf-8-sig", newline="") as out_f:
        writer = csv.DictWriter(out_f, fieldnames=out_fields, extrasaction="ignore")
        writer.writeheader()

        for run_idx, csv_path in enumerate(valid_paths, 1):
            try:
                with open(csv_path, "r", encoding="utf-8-sig") as in_f:
                    reader = csv.DictReader(in_f)
                    for row in reader:
                        # 회차는 run_id 토큰에서 우선 도출(모듈이 내부 rep 루프로
                        # 단일 CSV를 내므로 파일 인덱스만으론 run이 1로 고정됨).
                        # 토큰이 없으면 파일 순번(run_idx)으로 fallback.
                        rep = _run_from_run_id(row.get("run_id")) or run_idx
                        row["run"] = rep
                        row["seed"] = _make_run_seed(eval_type, rep)
                        row["temperature"] = EVAL_TEMPERATURE
                        writer.writerow(row)
            except Exception as e:
                logger.error(f"{label} run {run_idx} CSV 읽기 실패: {e}")

    total_rows = sum(
        1 for _ in open(out_path, encoding="utf-8")
    ) - 1  # 헤더 제외

    logger.info(
        f"📊 {label} 통합 CSV 생성: {out_path.name} "
        f"({len(valid_paths)}회 × {total_rows} rows)"
    )
    return out_path


# ═══════════════════════════════════════════
# GPU 메모리 해제
# ═══════════════════════════════════════════

def _release_gpu_memory():
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
    except Exception:
        pass
    try:
        import gc
        gc.collect()
    except Exception:
        pass


# ═══════════════════════════════════════════
# 메인 배치 실행
# ═══════════════════════════════════════════

async def run_full_stat_batch(
    plan: list[tuple[str, int]],
    progress_fn=None,
    arm_filter: list[str] | None = None,
    settings: EvalSettings | None = None,
) -> dict:
    """
    통계 배치 실행 → 모듈별 통합 CSV 생성.

    Args:
        plan: [(eval_type, n_runs), ...]
        progress_fn: async (msg) 콜백 (텔레그램 등)
        arm_filter: 실행할 Arm ID 목록 (None=전체)
        settings: 평가 설정 객체 (None 시 새로 로드)

    Returns:
        {"consolidated_csvs": [path, ...], "summary": str, ...}
    """
    if settings is None:
        settings = load_settings(mode="real")
    total_runs = sum(n for _, n in plan)
    completed = 0
    errors_total = 0
    results_by_type: dict[str, list[str]] = {t: [] for t, _ in plan}

    async def _send(msg: str):
        if progress_fn:
            try:
                await progress_fn(msg)
            except Exception:
                pass
        print(msg)

    plan_str = " | ".join(f"{TYPE_LABELS[t]} {n}회" for t, n in plan)
    await _send(
        f"📊 통계 배치 시작\n\n"
        f"{plan_str}\n"
        f"총 {total_runs}회 순차 시행"
    )

    batch_start = time.time()

    for plan_idx, (eval_type, n_runs) in enumerate(plan):
        label = TYPE_LABELS[eval_type]
        run_func = RUN_FUNCS.get(eval_type)
        if not run_func:
            await _send(f"⚠️ {label}: 실행 함수 없음 — 건너뜀")
            continue

        # 테스트 전환 시 GPU 해제
        if plan_idx > 0:
            _release_gpu_memory()
            await asyncio.sleep(3.0)

        await _send(
            f"\n{'='*30}\n"
            f"▶ {label} 배치 시작 ({n_runs}회 반복)\n"
            f"{'='*30}"
        )

        run_start = time.time()
        try:
            # Batch call to minimize VRAM load cycles
            result = await run_func(settings, n_runs=n_runs, arm_filter=arm_filter)
            csv_path = result.get("csv_path", "")
            if csv_path:
                results_by_type[eval_type].append(csv_path)
                # 2026-06-02 다회차 배치 진단(harmbench → xstest 전환 시 첫 결과 미저장 케이스):
                # csv_path는 함수가 반환했더라도 파일이 실제 디스크에 있는지 확인.
                # exists()=False면 save 단계에서 silent 실패 가능성 — 명시 경고.
                _p = Path(csv_path)
                if _p.exists():
                    sz = _p.stat().st_size
                    logger.info(f"  ✓ {label} CSV 저장 확인: {_p.name} ({sz:,} bytes)")
                else:
                    logger.error(f"  ⚠ {label} csv_path 반환됐으나 파일 부재: {csv_path}")
            else:
                logger.warning(f"  ⚠ {label} csv_path 반환 없음 — save 단계 누락 추정")
            run_errors = result.get("errors", 0)
            errors_total += run_errors
        except Exception as e:
            logger.error(f"배치 실패: {eval_type}: {e}")
            import traceback
            logger.error(f"  traceback:\n{traceback.format_exc()}")
            errors_total += 1

        completed += n_runs # Mark all runs as completed
        run_elapsed = time.time() - run_start
        total_elapsed = time.time() - batch_start
        pct = completed / total_runs * 100

        await _send(
            f"✅ {label} ({n_runs}회) 완료 "
            f"({run_elapsed:.0f}초)\n"
            f"전체: {completed}/{total_runs} ({pct:.0f}%)"
        )

        # Rate limit + GPU 안정화
        _release_gpu_memory()
        await asyncio.sleep(5.0)

    # ── 통합 CSV 생성 ──
    total_elapsed = time.time() - batch_start
    await _send(
        f"\n{'='*30}\n"
        f"📝 통합 CSV 생성 중...\n"
        f"{'='*30}"
    )

    consolidated_paths = []
    for eval_type, n_runs in plan:
        csv_list = results_by_type.get(eval_type, [])
        if not csv_list:
            continue
        try:
            path = consolidate_csvs(eval_type, csv_list, len(csv_list))
            consolidated_paths.append(str(path))
            await _send(
                f"📄 {TYPE_LABELS[eval_type]} 통합 CSV: {path.name} "
                f"({len(csv_list)}회 병합)"
            )
        except Exception as e:
            logger.error(f"통합 CSV 생성 실패 ({eval_type}): {e}")
            await _send(f"❌ {TYPE_LABELS[eval_type]} 통합 CSV 실패: {e}")

    if total_elapsed >= 3600:
        time_str = f"{total_elapsed/3600:.1f}시간"
    else:
        time_str = f"{total_elapsed/60:.1f}분"

    await _send(
        f"\n{'='*30}\n"
        f"🎉 통계 배치 전체 완료!\n"
        f"총 {completed}회 시행 | {time_str}\n"
        f"에러: {errors_total}건\n"
        f"통합 CSV: {len(consolidated_paths)}개\n"
        f"{'='*30}"
    )

    summary = (
        f"통계 배치 완료: {completed}회 시행 ({time_str})\n"
        f"에러: {errors_total}건\n"
        f"통합 CSV: {len(consolidated_paths)}개"
    )

    return {
        "summary": summary,
        "consolidated_csvs": consolidated_paths,
        "consolidated_reports": consolidated_paths,  # 텔레그램 호환
        "completed": completed,
        "errors": errors_total,
        "elapsed_seconds": total_elapsed,
    }


# ═══════════════════════════════════════════
# CLI 엔트리포인트
# ═══════════════════════════════════════════

def _parse_arm_filter(raw: str) -> list[str] | None:
    """
    Arms 필터 문자열을 파싱합니다.

    지원 형식:
        - 쉼표 구분: "H08,H09,H10"
        - 범위: "H08-H13"
        - 혼합: "H01,H08-H13"

    Returns:
        Arm ID 리스트 (예: ["H08", "H09", "H10"]) 또는 파싱 실패 시 None
    """
    import re
    result = []
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    for part in parts:
        # 범위 패턴: H08-H13
        range_match = re.match(r'^([A-Z])(\d+)-\1(\d+)$', part, re.IGNORECASE)
        if range_match:
            prefix = range_match.group(1).upper()
            start = int(range_match.group(2))
            end = int(range_match.group(3))
            for i in range(start, end + 1):
                result.append(f"{prefix}{i:02d}")
        elif re.match(r'^[A-Z]\d+$', part, re.IGNORECASE):
            result.append(part.upper())
        else:
            return None  # 잘못된 형식
    return result if result else None

async def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="PEINN 5-Module Statistical Batch"
    )
    parser.add_argument(
        "modules", nargs="?", default=None,
        help="실행할 모듈 (쉼표 구분). 예: mach,tci. 생략 시 전체.",
    )
    parser.add_argument(
        "runs", nargs="?", type=int, default=None,
        help="시행 횟수 오버라이드. 예: 15",
    )
    parser.add_argument(
        "--arms", nargs="+", default=None,
        help="실행할 Arm ID (쉼표 또는 공백 구분). 예: H08,H09 H10 또는 H08-H13. "
             "gpt-oss:120b side-experiment shortcut: --arms H18-H21 (Vanilla/NeMo/LlamaGuard/PEINN)",
    )
    parser.add_argument(
        "--gpt-oss", dest="gpt_oss", action="store_true",
        help="번외 gpt-oss:120b 4-arm 실험 shortcut: --arms H18-H21. "
             "기존 --arms 와 함께 쓰면 H18-H21 이 추가된다.",
    )
    parser.add_argument(
        "--no-judge", action="store_true",
        help="LMM-as-a-Judge 채점 건너뛰기 (추후 별도 채점)",
    )
    args = parser.parse_args()

    # ─ gpt-oss:120b shortcut ─
    if args.gpt_oss:
        gpt_arms = ["H18", "H19", "H20", "H21"]
        if args.arms:
            args.arms = list(args.arms) + gpt_arms
        else:
            args.arms = gpt_arms
        print(f"[gpt-oss shortcut] arm filter = {args.arms}")

    # Settings 로드
    from pea_eval.config.settings import load_settings
    settings = load_settings(mode="real")
    if args.no_judge:
        settings.enable_judge = False
        print("  ⚠️ LMM-as-a-Judge 채점이 비활성화되었습니다.")

    if args.modules and args.modules.isdigit() and args.runs is None:
        args.runs = int(args.modules)
        args.modules = None

    # ── Arms 필터 파싱 ──
    arm_filter = None
    if args.arms:
        # nargs="+" 로 인해 리스트로 들어오므로 하나로 합침
        raw_arms = ",".join(args.arms)
        arm_filter = _parse_arm_filter(raw_arms)
        if not arm_filter:
            print(f"⚠️ --arms 파싱 실패: {args.arms}")
            print("  예: H08,H09,H10 또는 H08-H13")
            return

    # 실행 계획 결정
    valid_types = {"harmbench", "xstest", "taxonomy", "ethics", "morables", "ggb"}

    if args.modules:
        target_types = [
            t.strip().lower()
            for t in args.modules.split(",")
            if t.strip().lower() in valid_types
        ]
    else:
        target_types = None

    if target_types:
        n = args.runs or DEFAULT_RUNS
        plan = [(t, n) for t in target_types]
    elif args.runs:
        plan = [(t, args.runs) for t, _ in BATCH_PLAN]
    else:
        plan = list(BATCH_PLAN)

    total = sum(n for _, n in plan)
    plan_str = " + ".join(f"{TYPE_LABELS[t]} {n}회" for t, n in plan)

    print("=" * 70)
    print("  PEA OS 5-Module Statistical Batch")
    print("  p<0.05 확보를 위한 다회차 독립시행")
    print("=" * 70)
    print(f"\n  {plan_str}")
    print(f"  총 {total}회 순차 시행")
    if arm_filter:
        print(f"  🎯 Arms 필터: {', '.join(arm_filter)}")
    print(f"\n  통제 변인:")
    print(f"    Temperature: {EVAL_TEMPERATURE} (고정)")
    print(f"    Top-P: 0.95 (고정)")
    print(f"    Seed: run별 고유 (SHA-256 해시 기반)")
    print(f"    프롬프트/모델: 고정")
    print(f"\n{'=' * 70}\n")

    result = await run_full_stat_batch(plan, arm_filter=arm_filter, settings=settings)

    # 결과 출력
    print(f"\n{'=' * 70}")
    print("  통합 CSV 목록:")
    for p in result.get("consolidated_csvs", []):
        print(f"    📊 {Path(p).name}")
    print(f"\n  {result['summary']}")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    asyncio.run(main())
