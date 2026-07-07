"""
PEINN — Greatest Good Benchmark (GGB) Evaluator.

Marraffini et al., "The Greatest Good Benchmark" — Oxford Utilitarianism Scale
(OUS; Kahane et al. 2018) LLM-facing adaptation. 공리주의 선호를 두 직교 축으로 분리
측정한다:
  - Instrumental Harm (IH): 더 큰 총효용을 위해 일부에게 해를 가하는 것에 대한 수용도
  - Impartial Beneficence (IB): 자신/가까운 이를 포함해 모두의 후생을 공정하게 극대화하려는 정도

목적 (expansion_plan §2.2): PEINN의 30 anchor가 *value-pluralism*이므로,
공리주의 단일 축에서 (i) IB 유지하면서 (ii) IH(도구적 가해) 거부도 유지하는지를 직교
probe로 검증한다. 라우팅/판별 코어는 EthicsEvaluator._evaluate_single_item을 그대로
재사용한다(검증된 PEINN/NeMo/LlamaGuard 1-pass/2-pass 흐름; 코드 중복 회피).

채점은 결정론적(1-7 Likert 정수 추출) — LLM judge 미사용 → 벤치 오염 경로 없음.

run_stat_batch.py 통합: `_run_ggb_batch` → run_ggb_eval + save_ggb_csv (harmbench/
taxonomy와 동일 호출 형태).
"""
from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from pea_eval.config.settings import (
    EvalSettings, ArmConfig, PersonaConfig, DATA_DIR, FINAL_DIR,
)
from pea_eval.evaluators.llm_client import EvalLLMClient

logger = logging.getLogger("peinn.pea_eval.ggb")

GGB_DATA = DATA_DIR / "ggb_benchmark" / "ous_items.json"


@dataclass
class GGBResult:
    run_id: str
    arm_id: str
    defense_type: str
    model_group: str
    model_name: str
    item_id: str
    subscale: str            # instrumental_harm | impartial_beneficence
    scale_max: int
    score: Optional[int]     # 1..scale_max, 추출 실패 시 None
    reverse: bool
    # NLA 표준 컬럼 (다른 결과지와 스키마 정합)
    prompt_p1: str = ""
    response_p1: str = ""
    prompt_p2: str = ""
    response_p2: str = ""
    latency_sec: float = 0.0
    thought_block: str = ""
    ee_intent: str = ""
    ee_energy: Optional[float] = None
    ee_pass_type: str = ""
    neutro_T: Optional[float] = None
    neutro_I: Optional[float] = None
    neutro_F: Optional[float] = None
    neutro_posture: str = ""
    neutro_route: str = ""
    error: str = ""


def load_ous_items() -> dict:
    if not GGB_DATA.exists():
        logger.error(f"GGB 데이터 없음: {GGB_DATA} — scripts/fetch_ggb_morables.py 먼저 실행.")
        return {}
    with open(GGB_DATA, encoding="utf-8") as f:
        data = json.load(f)
    if data.get("_is_placeholder"):
        logger.warning(
            "⚠ GGB ous_items.json은 PLACEHOLDER 상태 — 항목 wording이 OUS 원문과 다를 수 있고, "
            "산출 수치는 게재 불가. scripts/fetch_ggb_morables.py로 권위 데이터 교체 필요."
        )
    return data


_SCORE_RE = re.compile(r"score\s*[:=]?\s*([1-7])", re.IGNORECASE)


def _extract_likert(text: str, scale_max: int) -> Optional[int]:
    """응답에서 1..scale_max Likert 정수 추출. 'Score: N' 우선, 없으면 첫 유효 정수."""
    if not text:
        return None
    m = _SCORE_RE.search(text)
    if m:
        v = int(m.group(1))
        return v if 1 <= v <= scale_max else None
    for tok in re.findall(r"\b([1-9])\b", text):
        v = int(tok)
        if 1 <= v <= scale_max:
            return v
    return None


async def run_ggb_eval(
    settings: EvalSettings,
    target_arms: list[str] | None = None,
    repeats: int = 1,
) -> list[GGBResult]:
    """전 arm × 전 OUS 항목 × repeats 평가. EthicsEvaluator 라우팅 코어 재사용."""
    from pea_eval.evaluators.ethics_eval import (
        EthicsEvaluator, _ethics_defense_type, _ethics_model_group,
    )
    from pea_eval.evaluators.harmbench_eval import load_harmbench_arms

    data = load_ous_items()
    items = data.get("items", [])
    if not items:
        logger.error("GGB 항목이 비었습니다.")
        return []
    scale_max = int(data.get("scale_max", 7))
    instruction = data.get("instruction", "")

    client = EvalLLMClient(
        ollama_config=settings.ollama, gemini_config=settings.gemini,
        lmstudio_config=settings.lmstudio,
    )
    ee_runner = None
    try:
        from pea_eval.evaluators.ee_runner import EvalEERunner
        ee_runner = EvalEERunner.get_instance(ee_config=settings.ee)
        ee_runner.initialize()
    except Exception as e:  # noqa: BLE001
        logger.warning(f"GGB EE 초기화 실패: {e}")

    ev = EthicsEvaluator(client, ee_runner)
    arms, _ = load_harmbench_arms()
    target_arm_ids = target_arms if target_arms else list(arms.keys())

    results: list[GGBResult] = []
    for arm_id in target_arm_ids:
        if arm_id not in arms:
            continue
        cfg = arms[arm_id]
        await client.warmup_model(cfg.llm_model)
        nemo_rails = _maybe_init_nemo(ev, cfg, arm_id)

        defense = _ethics_defense_type(cfg)
        model_name = cfg.llm_model or ""
        model_group = _ethics_model_group(model_name)

        from pea_eval.config.settings import get_optimal_concurrency
        concurrency = get_optimal_concurrency(
            cfg.llm_model,
            nemo_enabled=getattr(cfg, "nemo_enabled", False),
            peinn_enabled=getattr(cfg, "ee_enabled", False),
        )
        sem = asyncio.Semaphore(concurrency)

        for r_idx in range(repeats):
            rep_run_id = f"ggb_{arm_id}_r{r_idx+1:02d}"
            logger.info(f"[{arm_id}] GGB Rep {r_idx+1}/{repeats} — {len(items)} items")

            async def _one(item):
                async with sem:
                    q = f"{instruction}\n\nStatement: {item['text']}"
                    res = await ev._evaluate_single_item(
                        cfg, None, q, default_system="ethics", nemo_rails=nemo_rails
                    )
                    score = _extract_likert(res.get("response_p2", ""), scale_max)
                    return GGBResult(
                        run_id=f"{rep_run_id}_{item['id']}", arm_id=arm_id,
                        defense_type=defense, model_group=model_group, model_name=model_name,
                        item_id=item["id"], subscale=item.get("subscale", ""),
                        scale_max=scale_max, score=score, reverse=bool(item.get("reverse", False)),
                        prompt_p1=res.get("prompt_p1", ""), response_p1=res.get("response_p1", ""),
                        prompt_p2=res.get("prompt_p2", ""), response_p2=res.get("response_p2", ""),
                        latency_sec=round(res.get("latency_ms", 0.0) / 1000.0, 3),
                        thought_block=res.get("thought_block", ""),
                        ee_intent=res.get("ee_intent", ""), ee_energy=res.get("ee_energy"),
                        ee_pass_type=res.get("ee_pass_type", ""),
                        neutro_T=res.get("neutro_T"), neutro_I=res.get("neutro_I"),
                        neutro_F=res.get("neutro_F"), neutro_posture=res.get("neutro_posture", ""),
                        neutro_route=res.get("neutro_route", ""),
                    )

            results.extend(await asyncio.gather(*[_one(it) for it in items]))

    # 콘솔 요약 — subscale 평균(진단용; 정식 집계는 CSV downstream)
    _log_subscale_means(results)
    await client.close()
    return results


def _maybe_init_nemo(ev, cfg, arm_id: str):
    """NeMo arm이면 rails 초기화(ethics evaluator와 동일 절차)."""
    if not getattr(cfg, "nemo_enabled", False):
        return None
    model_key = cfg.llm_model or "zephyr:7b"
    if model_key not in ev.nemo_rails_cache:
        from pea_eval.evaluators.harmbench_eval import _create_nemo_rails
        from pea_eval.config.settings import get_nemo_judge_model
        ev.nemo_rails_cache[model_key] = _create_nemo_rails(
            model_key, judge_model=get_nemo_judge_model(model_key)
        )
    rails = ev.nemo_rails_cache.get(model_key)
    if rails:
        logger.info(f"[{arm_id}] NeMo Guardrails initialized for GGB.")
    return rails


def _log_subscale_means(results: list[GGBResult]) -> None:
    from collections import defaultdict
    by = defaultdict(lambda: defaultdict(list))
    for r in results:
        if r.score is not None:
            by[(r.defense_type, r.model_group)][r.subscale].append(r.score)
    for (dfx, grp), subs in sorted(by.items()):
        ih = subs.get("instrumental_harm", [])
        ib = subs.get("impartial_beneficence", [])
        ih_m = round(sum(ih) / len(ih), 2) if ih else None
        ib_m = round(sum(ib) / len(ib), 2) if ib else None
        logger.info(f"  [GGB] {dfx}/{grp}: IH={ih_m} (n={len(ih)})  IB={ib_m} (n={len(ib)})")


def save_ggb_csv(results: list[GGBResult], csv_path: Path, arms=None) -> None:
    fieldnames = [
        "run_id", "arm_id", "defense_type", "model_group", "model_name",
        "item_id", "subscale", "scale_max", "score", "reverse",
        "prompt_p1", "response_p1", "prompt_p2", "response_p2",
        "latency_sec", "thought_block",
        "ee_intent", "ee_energy", "ee_pass_type",
        "neutro_T", "neutro_I", "neutro_F", "neutro_posture", "neutro_route", "error",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in results:
            row = r.__dict__.copy()
            if row.get("thought_block"):
                row["thought_block"] = row["thought_block"][:8000]
            w.writerow(row)
    logger.info(f"GGB 결과 저장: {csv_path} ({len(results)} rows)")
