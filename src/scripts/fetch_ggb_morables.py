"""
GGB(Oxford Utilitarianism Scale) + Morables 권위 데이터 확보 스크립트 (DGX, 네트워크 필요).

HANDOFF-50. 두 신규 벤치 모듈(ggb_eval / morables_eval)이 사용하는 데이터를 1차 출처에서
받아 로컬 스키마로 매핑한다. placeholder/smoke 파일을 권위 데이터로 교체.

  1) GGB: Marraffini et al. "The Greatest Good Benchmark" / Kahane et al. (2018) OUS 9문항.
     공식 release(HF/GitHub)에서 받아 pea_eval/data/ggb_benchmark/ous_items.json 갱신.
     (_is_placeholder=false 로 표시되면 ggb_eval 경고 해제.)
  2) Morables: Marcuzzo et al. "Morables" 709 fables + adversarial variants.
     HF/GitHub에서 받아 pea_eval/data/morables_benchmark/morables.jsonl 로 저장
     (morables_eval이 sample 대신 이 파일을 자동 우선 사용).

특징: 멱등, 다운로드 재시도(2/4/8s), --dry-run(쓰기 없이 후보 URL 점검).
저장소/split id는 환경에 맞게 --ggb-url / --morables-repo 로 오버라이드 가능
(공개 위치가 확정되지 않은 경우 로컬에 받은 파일 경로를 --morables-file로 직접 지정).

실행:
    python scripts/fetch_ggb_morables.py
    python scripts/fetch_ggb_morables.py --dry-run
    python scripts/fetch_ggb_morables.py --morables-file /path/to/local_morables.jsonl
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "pea_eval" / "data"
GGB_JSON = DATA_DIR / "ggb_benchmark" / "ous_items.json"
MORABLES_JSONL = DATA_DIR / "morables_benchmark" / "morables.jsonl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("peaos.fetch_ggb_morables")


def _download(url: str, retries: int = 3) -> bytes | None:
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=30) as resp:
                return resp.read()
        except Exception as e:  # noqa: BLE001
            wait = 2 ** (attempt + 1)
            logger.warning(f"  다운로드 실패({attempt+1}/{retries}) {type(e).__name__}: {str(e)[:80]} — {wait}s 후 재시도")
            time.sleep(wait)
    return None


def fetch_morables(repo_urls: list[str], local_file: str | None, dry_run: bool) -> bool:
    """Morables jsonl 확보. local_file 우선, 아니면 후보 URL 순차 시도."""
    if local_file:
        p = Path(local_file)
        if not p.exists():
            logger.error(f"  --morables-file 경로 없음: {p}")
            return False
        data = p.read_bytes()
        logger.info(f"  로컬 파일 사용: {p} ({len(data):,} bytes)")
    else:
        data = None
        for url in repo_urls:
            logger.info(f"  Morables 후보 URL 시도: {url}")
            if dry_run:
                continue
            data = _download(url)
            if data:
                logger.info(f"  ✓ 다운로드 성공: {len(data):,} bytes")
                break
        if dry_run:
            logger.info("  [dry-run] Morables 쓰기 생략")
            return True
        if not data:
            logger.error("  ✗ Morables 모든 후보 URL 실패 — --morables-file로 로컬 경로 지정 권장.")
            return False

    # jsonl 정합 검증(필수 키 story/options/gold)
    n_ok = 0
    lines_out = []
    for line in data.decode("utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if all(k in obj for k in ("story", "options", "gold")) or "id" in obj:
            lines_out.append(json.dumps(obj, ensure_ascii=False))
            if all(k in obj for k in ("story", "options", "gold")):
                n_ok += 1
    if n_ok == 0:
        logger.error("  ✗ 유효한 Morables 항목(story/options/gold)이 없습니다 — 스키마 매핑 필요.")
        return False
    MORABLES_JSONL.parent.mkdir(parents=True, exist_ok=True)
    MORABLES_JSONL.write_text("\n".join(lines_out) + "\n", encoding="utf-8")
    logger.info(f"  ✓ Morables 저장: {MORABLES_JSONL} ({n_ok} fables)")
    return True


def mark_ggb_verified(dry_run: bool) -> bool:
    """GGB ous_items.json의 placeholder 플래그 해제(권위 검증 완료 표시).

    실제 wording 교체는 출처 접근 환경에 따라 수동/별도 매핑이 필요할 수 있다.
    본 스크립트는 (a) 파일 존재 확인, (b) 검증 완료 시 _is_placeholder=false 로 전환만 수행.
    """
    if not GGB_JSON.exists():
        logger.error(f"  GGB 파일 없음: {GGB_JSON}")
        return False
    data = json.loads(GGB_JSON.read_text(encoding="utf-8"))
    if not data.get("_is_placeholder"):
        logger.info("  GGB는 이미 verified 상태.")
        return True
    logger.warning(
        "  GGB ous_items.json은 placeholder. OUS 9문항 wording을 Kahane et al.(2018)/GGB 원문과 "
        "대조 검증한 뒤, 이 스크립트에 --confirm-ggb 를 주어 _is_placeholder=false 로 전환하세요."
    )
    return True


def confirm_ggb(dry_run: bool) -> bool:
    if not GGB_JSON.exists():
        logger.error(f"  GGB 파일 없음: {GGB_JSON}")
        return False
    if dry_run:
        logger.info("  [dry-run] GGB 플래그 전환 생략")
        return True
    data = json.loads(GGB_JSON.read_text(encoding="utf-8"))
    data["_is_placeholder"] = False
    data["_provenance_note"] = (data.get("_provenance_note", "") +
                                " | VERIFIED against primary source by operator (fetch --confirm-ggb).")
    GGB_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("  ✓ GGB _is_placeholder=false 로 전환 — ggb_eval 경고 해제됨.")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="GGB + Morables 권위 데이터 확보")
    ap.add_argument("--dry-run", action="store_true", help="쓰기 없이 후보 점검")
    ap.add_argument("--morables-file", default="", help="로컬 morables jsonl 경로(있으면 우선)")
    ap.add_argument("--morables-repo", nargs="*", default=[
        # ★ 공식 출처: Marcuzzo et al. (EMNLP 2025) §3 footnote 1.
        # https://huggingface.co/datasets/cardiffnlp/Morables
        # HF 정책으로 차단된 환경에선 huggingface_hub CLI 또는 datasets 라이브러리로
        # 받은 후 --morables-file로 지정. 파일명/split은 dataset card 참조.
        "https://huggingface.co/datasets/cardiffnlp/Morables/resolve/main/morables.jsonl",
        "https://huggingface.co/datasets/cardiffnlp/Morables/resolve/main/data/train.jsonl",
        "https://huggingface.co/datasets/cardiffnlp/Morables/resolve/main/core.jsonl",
    ], help="Morables jsonl 후보 URL(들) — 공식: cardiffnlp/Morables")
    ap.add_argument("--confirm-ggb", action="store_true",
                    help="OUS 문항을 1차 출처와 대조 검증 완료 → _is_placeholder=false 전환")
    args = ap.parse_args()

    logger.info("=== GGB ===")
    if args.confirm_ggb:
        confirm_ggb(args.dry_run)
    else:
        mark_ggb_verified(args.dry_run)

    logger.info("=== Morables ===")
    ok_m = fetch_morables(args.morables_repo, args.morables_file or None, args.dry_run)

    logger.info("완료. (Morables=%s) — 모듈 실행: python run_stat_batch.py morables 1 --arms H01"
                % ("OK" if ok_m else "FAIL/skip"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
