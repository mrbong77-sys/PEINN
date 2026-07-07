"""
핵심 벤치 데이터 확보 + 로더 정합 스크립트 (DGX 실행, 네트워크 필요).

목적 (EXP-24 후속, 4 핵심 벤치 question-set 완성):
  1) HarmBench: validation split(부분) → 공개 **전체 text 셋**(harmbench_behaviors_text_all.csv)
     다운로드. 헤더가 로더와 동일하므로 drop-in. 벤치 경로는 harmbench_eval/taxonomy가
     이 파일을 보도록 이미 교체됨(코드). EE 학습측(ee_threshold_finder 등)은 val 유지.
  2) Ethics: 선행연구 LLM_Ethics_Benchmark(The-Responsible-AI-Initiative)의 instruments를
     받아 **로컬 스키마로 매핑 + id-union(부족분만 채움)**. blind 교체가 아니라 병합이라
     로더 키(wvs=core_pool, dilemma related_to 옵션)를 보존한다.

특징: 멱등(여러 번 실행 안전), 로컬 ethics 파일 .bak 백업, --dry-run(쓰기 없이 비교 보고),
      다운로드 재시도(2/4/8s), 끝에 로더 호환 검증.

실행:
    python scripts/fetch_benchmark_data.py            # 다운로드+병합 수행
    python scripts/fetch_benchmark_data.py --dry-run  # 개수 비교만(쓰기 X)
"""
from __future__ import annotations

import argparse
import json
import logging
import shutil
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "pea_eval" / "data"
ETHICS_DIR = DATA_DIR / "ethics_benchmark"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peinn.fetch_benchmark_data")

HARMBENCH_ALL_URL = (
    "https://raw.githubusercontent.com/centerforaisafety/HarmBench/main/"
    "data/behavior_datasets/harmbench_behaviors_text_all.csv"
)
HARMBENCH_ALL_PATH = DATA_DIR / "harmbench_behaviors_text_all.csv"
HARMBENCH_HEADER = "Behavior,FunctionalCategory,SemanticCategory,Tags,ContextString,BehaviorID"

ETHICS_BASE = (
    "https://raw.githubusercontent.com/The-Responsible-AI-Initiative/"
    "LLM_Ethics_Benchmark/main/data/instruments/"
)


def _download(url: str, retries: int = 4) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "peaos-fetch"})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            last = e
            wait = 2 ** (attempt + 1)
            logger.warning(f"  다운로드 실패({attempt+1}/{retries}) {type(e).__name__}: {str(e)[:120]} → {wait}s 후 재시도")
            time.sleep(wait)
    raise RuntimeError(f"다운로드 최종 실패: {url}\n{last}")


# ─────────────────────────────────────────────────────────────────────
# 1) HarmBench 전체 text 셋
# ─────────────────────────────────────────────────────────────────────

def fetch_harmbench(dry_run: bool) -> None:
    logger.info("[HarmBench] 전체 text 셋 다운로드…")
    raw = _download(HARMBENCH_ALL_URL).decode("utf-8")
    lines = raw.splitlines()
    header = lines[0].strip().lstrip("﻿")
    if header != HARMBENCH_HEADER:
        raise SystemExit(
            f"[HarmBench] 헤더 불일치 — 로더와 정합 안 됨.\n  기대: {HARMBENCH_HEADER}\n  실제: {header}"
        )
    # 카테고리별 개수 (로더는 standard+contextual만 사용, copyright 제외)
    import csv
    import io
    rows = list(csv.DictReader(io.StringIO(raw)))
    by_cat: dict[str, int] = {}
    for r in rows:
        by_cat[r.get("FunctionalCategory", "").strip().lower()] = by_cat.get(
            r.get("FunctionalCategory", "").strip().lower(), 0
        ) + 1
    usable = by_cat.get("standard", 0) + by_cat.get("contextual", 0)
    logger.info(f"[HarmBench] 총 {len(rows)}행, 카테고리별 {by_cat}")
    logger.info(f"[HarmBench] 로더 사용분(standard+contextual) = {usable}  (copyright {by_cat.get('copyright',0)} 제외)")
    if dry_run:
        logger.info(f"[HarmBench] (dry-run) 저장 생략 → {HARMBENCH_ALL_PATH}")
        return
    HARMBENCH_ALL_PATH.write_text(raw, encoding="utf-8")
    logger.info(f"[HarmBench] 저장 → {HARMBENCH_ALL_PATH}")


# ─────────────────────────────────────────────────────────────────────
# 2) Ethics — 로컬 스키마로 매핑 + id-union
# ─────────────────────────────────────────────────────────────────────

def _backup(path: Path) -> None:
    bak = path.with_suffix(path.suffix + ".bak")
    if path.exists() and not bak.exists():
        shutil.copy2(path, bak)
        logger.info(f"  백업 생성 → {bak.name}")


def _wvs_questions(obj: dict) -> list[dict]:
    """상류/로컬 어디든 domains.*.questions에서 question 리스트를 모은다."""
    out: list[dict] = []
    for dom in obj.get("domains", {}).values():
        if isinstance(dom, dict):
            out.extend(dom.get("questions", []) or [])
    return out


def merge_wvs(dry_run: bool) -> None:
    local_path = ETHICS_DIR / "wvs.json"
    local = json.loads(local_path.read_text(encoding="utf-8"))
    local_qs = local["domains"]["core_pool"]["questions"]
    local_ids = {q.get("id") for q in local_qs}

    up = json.loads(_download(ETHICS_BASE + "wvs.json").decode("utf-8"))
    up_qs = _wvs_questions(up)
    add = [q for q in up_qs if q.get("id") not in local_ids]
    logger.info(f"[WVS] 로컬 {len(local_qs)} + 상류 {len(up_qs)} → 신규 {len(add)} 추가 (id-union)")
    if dry_run:
        return
    if add:
        _backup(local_path)
        local_qs.extend(add)
        local_path.write_text(json.dumps(local, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[WVS] 저장 → {local_path} (총 {len(local_qs)} 문항)")


def merge_dilemmas(dry_run: bool) -> None:
    local_path = ETHICS_DIR / "dilemmas.json"
    local = json.loads(local_path.read_text(encoding="utf-8"))
    local_dl = local["dilemmas"]
    by_id = {d.get("id"): d for d in local_dl}

    up = json.loads(_download(ETHICS_BASE + "dilemmas.json").decode("utf-8"))
    up_dl = up.get("dilemmas", [])
    new_d, new_q = 0, 0
    for ud in up_dl:
        did = ud.get("id")
        if did not in by_id:
            local_dl.append(ud)
            by_id[did] = ud
            new_d += 1
            new_q += len(ud.get("questions", []))
        else:
            ld = by_id[did]
            lq_ids = {q.get("id") for q in ld.get("questions", [])}
            for uq in ud.get("questions", []):
                if uq.get("id") not in lq_ids:
                    ld.setdefault("questions", []).append(uq)
                    new_q += 1
    tot_q = sum(len(d.get("questions", [])) for d in local_dl)
    logger.info(f"[Dilemmas] 신규 dilemma {new_d} · 신규 question {new_q} → 총 {len(local_dl)} dilemmas / {tot_q} questions")
    if dry_run:
        return
    if new_d or new_q:
        _backup(local_path)
        local_path.write_text(json.dumps(local, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[Dilemmas] 저장 → {local_path}")


def merge_mfq(dry_run: bool) -> None:
    local_path = ETHICS_DIR / "mfq.json"
    local = json.loads(local_path.read_text(encoding="utf-8"))
    try:
        up = json.loads(_download(ETHICS_BASE + "mfq.json").decode("utf-8"))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[MFQ] 상류 다운로드 실패 → 로컬 유지: {e}")
        return
    lf = local.get("foundations", {})
    uf = up.get("foundations", {})
    new_items = 0
    for fkey, uval in uf.items():
        lval = lf.get(fkey)
        # foundation 내부가 {items:[...]} 또는 [...] 형태일 수 있어 방어적으로 처리
        u_items = uval.get("items") if isinstance(uval, dict) else (uval if isinstance(uval, list) else [])
        if isinstance(lval, dict) and "items" in lval:
            l_ids = {it.get("id") for it in lval["items"]}
            for it in u_items:
                if it.get("id") not in l_ids:
                    lval["items"].append(it); new_items += 1
        elif lval is None:
            lf[fkey] = uval; new_items += len(u_items)
    logger.info(f"[MFQ] foundations {len(lf)} · 신규 item {new_items}")
    if dry_run:
        return
    if new_items:
        _backup(local_path)
        local["foundations"] = lf
        local_path.write_text(json.dumps(local, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"[MFQ] 저장 → {local_path}")


# ─────────────────────────────────────────────────────────────────────
# 검증 — 로더가 읽는 경로/키가 유지되는지
# ─────────────────────────────────────────────────────────────────────

def verify_loaders() -> None:
    logger.info("[검증] 로더 호환성…")
    # WVS
    w = json.loads((ETHICS_DIR / "wvs.json").read_text(encoding="utf-8"))
    nw = len(w["domains"]["core_pool"]["questions"])
    # Dilemmas
    d = json.loads((ETHICS_DIR / "dilemmas.json").read_text(encoding="utf-8"))
    nd = sum(len(x.get("questions", [])) for x in d["dilemmas"])
    # HarmBench (다운로드분이 있으면)
    nh = "n/a"
    if HARMBENCH_ALL_PATH.exists():
        import csv
        with HARMBENCH_ALL_PATH.open(encoding="utf-8") as f:
            rows = [r for r in csv.DictReader(f)
                    if r.get("FunctionalCategory", "").strip().lower() in ("standard", "contextual")]
        nh = len(rows)
    logger.info(f"[검증] WVS core_pool={nw}  Dilemma questions={nd}  HarmBench(usable)={nh}")
    assert nw > 0 and nd > 0, "로더 키 경로가 비었습니다 — 병합 로직 점검 필요"
    logger.info("[검증] OK — 로더 키 경로 유지됨")


def main() -> int:
    ap = argparse.ArgumentParser(description="핵심 벤치 데이터 확보 + 로더 정합")
    ap.add_argument("--dry-run", action="store_true", help="쓰기 없이 개수 비교만 보고")
    ap.add_argument("--skip-harmbench", action="store_true")
    ap.add_argument("--skip-ethics", action="store_true")
    args = ap.parse_args()

    if not args.skip_harmbench:
        fetch_harmbench(args.dry_run)
    if not args.skip_ethics:
        merge_wvs(args.dry_run)
        merge_dilemmas(args.dry_run)
        merge_mfq(args.dry_run)
    if not args.dry_run:
        verify_loaders()
    logger.info("완료. (HarmBench 벤치 경로는 harmbench_eval/taxonomy가 _all.csv를 보도록 코드 반영됨)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
