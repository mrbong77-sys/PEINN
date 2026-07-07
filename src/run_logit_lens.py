"""
PEA-OS — Logit Lens Statistical Run

NLA(run_stat_nla.py)와 동일한 구동 방식으로 HarmBench / Taxonomy 프롬프트에 대해
Vanilla vs PEINN의 *내부 레이어별 토큰 부상 패턴*을 시각화한다.

산출물:
  - 레이어 × 토큰 단위 entropy / top1-prob 히트맵 PNG (per arm × item × pass)
  - manifest.csv 1개 — 모든 PNG와 행 메타(asr_outcome, ee_pass_type, response 등)를 묶음

LMM 분석자는 manifest.csv의 한 행을 선택 → 해당 행이 가리키는 2~4장의 PNG와
프롬프트/응답 텍스트를 함께 받아 사후 정성 분석을 수행한다.

사용 예:
  python run_logit_lens.py harmbench --arms H05,H07 --runs 3 --npilot 5
  python run_logit_lens.py taxonomy  --arms H05,H07 --runs 3 --npilot 3 --no-judge
"""

import argparse
import asyncio
import csv
import logging
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import torch

# 로컬 캐시 전용 모드 (HF 서버 체크 우회)
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

from pea_eval.config.settings import load_settings, DATA_DIR, FINAL_DIR
from pea_eval.evaluators.harmbench_eval import (
    judge_asr_batch, load_harmbench_arms, load_harmbench_behaviors,
)
from pea_eval.evaluators.llm_client import EvalLLMClient
from pea_eval.evaluators.prompt_builder import (
    build_eval_prompt, build_system_prompt, build_reflection_prompt,
)
from pea_eval.evaluators.confucian_mux import get_confucian_features
from pea_eval.logit_lens.analyzer import identify_sentence_ranges
from pea_eval.logit_lens.collector import LogitLensCollector
from pea_eval.logit_lens.visualizer import plot_sentence_heatmaps

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("peinn.run_logit_lens")


# ═══════════════════════════════════════════════════════════════════════
# Configuration
# ═══════════════════════════════════════════════════════════════════════

DEFAULT_ARMS = ["H05", "H07"]   # Qwen2.5-7B Vanilla + PEINN (paired NLA target)
DEFAULT_RUNS = 3
DEFAULT_NPILOT = 5
MAX_SENTENCES_PER_RESPONSE = 2  # cap PNGs per response (entropy + prob = 2 modes ⇒ ≤4 PNGs)
GENERATION_MAX_NEW_TOKENS = 128


@dataclass
class PassPayload:
    """One forward/generate pass on a single prompt."""
    pass_label: str                 # "p1" or "p2"
    full_input_text: str            # decoded prompt seen by collector.collect
    prompt_token_len: int           # offset where response tokens begin
    response_text: str
    response_token_ids: list = field(default_factory=list)
    result: object = None           # LogitLensResult
    error: str = ""


@dataclass
class ItemRecord:
    """One (arm, item, rep) record. May contain p1 only, or p1+p2 for PEINN HARMFUL."""
    run_id: str
    arm_id: str
    defense_type: str
    model: str
    item_id: str
    behavior: str                   # full prompt text (no truncation)
    category: str
    semantic_category: str
    taxonomy_family: str = ""
    sub_technique: str = ""
    total_turns: int = 1
    ee_intent: str = ""
    ee_energy: float = 0.0
    ee_pass_type: str = "1-pass"
    asr_judgment: str = ""          # filled after ASR judge stage
    asr_outcome: str = "skip"       # atk | def | err | skip
    passes: list = field(default_factory=list)   # list[PassPayload]


# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════

def _defense_type(arm) -> str:
    if getattr(arm, "ee_enabled", False):
        return "ReversePEINN" if getattr(arm, "reverse_peinn", False) else "PEINN"
    if getattr(arm, "nemo_enabled", False):
        return "NeMo"
    if "r2d2" in (arm.llm_model or "").lower():
        return "R2D2"
    return "Vanilla"


def _outcome_tag(judgment: str) -> str:
    j = (judgment or "").upper()
    if j == "HARMFUL":
        return "atk"
    if j == "REFUSED":
        return "def"
    if j == "ERROR":
        return "err"
    return "skip"


def _ee_classify(ee_runner, text: str, agent_profile: str = "A"):
    """(intent, energy, emotion_text, rag_context); safe on errors."""
    if not ee_runner:
        return "N/A", 0.0, "", ""
    try:
        _, energy, emotion_text = ee_runner.analyze_emotion(text, agent_profile=agent_profile)
        intent = ee_runner.classify_intent(energy)
        rag_context = ""
        try:
            rag_context = ee_runner.get_rag_context(text[:200], top_k=1) or ""
        except Exception as e:
            logger.warning(f"RAG fetch failed: {e}")
        return intent, float(energy), emotion_text, rag_context
    except Exception as e:
        logger.error(f"EE classify failed: {e}")
        return "N/A", 0.0, "", ""


def _build_pass1_prompt(raw_user, arm, persona, emotion_text, rag_context, default_system):
    peinn_features = {}
    if getattr(arm, "ee_enabled", False):
        peinn_features = get_confucian_features(raw_user, emotion_text, rag_context)
    sys_p = build_system_prompt(arm, persona, language="en", peinn_features=peinn_features)
    constraints = build_eval_prompt(default_system, arm)
    if constraints:
        sys_p = f"{sys_p}\n\n{constraints}".strip()
    return sys_p, raw_user, peinn_features


def _generate_and_collect(
    collector: LogitLensCollector,
    sys_prompt: str,
    user_prompt: str,
    arm_id: str,
    item_id: str,
    pass_label: str,
) -> PassPayload:
    """Run a single generate + logit-lens collect cycle. Returns PassPayload."""
    full_input = collector.tokenizer.apply_chat_template(
        [{"role": "system", "content": sys_prompt},
         {"role": "user", "content": user_prompt}],
        tokenize=False, add_generation_prompt=True,
    )
    enc = collector.tokenizer(
        full_input, return_tensors="pt", add_special_tokens=False,
    ).to(collector.model.device)
    prompt_len = enc.input_ids.shape[1]

    with torch.no_grad():
        gen = collector.model.generate(
            **enc,
            max_new_tokens=GENERATION_MAX_NEW_TOKENS,
            do_sample=True, temperature=0.3, top_p=0.95,
            pad_token_id=collector.tokenizer.eos_token_id,
        )
    gen_ids = gen[0]
    response_ids = gen_ids[prompt_len:].cpu().tolist()
    response_text = collector.tokenizer.decode(response_ids, skip_special_tokens=True)

    full_sequence = collector.tokenizer.decode(gen_ids, skip_special_tokens=False)
    try:
        result = collector.collect(
            full_sequence, arm_id, f"{item_id}_{pass_label}", max_input_tokens=2048,
        )
        err = ""
    except Exception as e:
        result = None
        err = str(e)[:200]
        logger.error(f"collect failed: {e}")

    return PassPayload(
        pass_label=pass_label,
        full_input_text=full_input,
        prompt_token_len=prompt_len,
        response_text=response_text,
        response_token_ids=response_ids,
        result=result,
        error=err,
    )


def _render_pass_pngs(
    payload: PassPayload, tokenizer, out_dir: Path, file_stem_prefix: str, top_layers: int = 0,
) -> dict:
    """Render heatmaps for up to MAX_SENTENCES_PER_RESPONSE sentences of the response.
    Returns dict of {key: png_path_string}."""
    paths = {}
    if payload.result is None or not payload.response_text:
        return paths
    try:
        sentence_ranges = identify_sentence_ranges(
            payload.response_text, tokenizer, payload.response_token_ids,
        )
    except Exception as e:
        logger.error(f"sentence range failed: {e}")
        return paths

    for s_idx, (s_start, s_end) in enumerate(sentence_ranges[:MAX_SENTENCES_PER_RESPONSE]):
        abs_start = payload.prompt_token_len + s_start
        abs_end = payload.prompt_token_len + s_end
        if abs_end <= abs_start:
            continue
        for mode in ("entropy", "prob"):
            stem = f"{file_stem_prefix}_s{s_idx+1}"
            try:
                out_path = plot_sentence_heatmaps(
                    payload.result, start=abs_start, end=abs_end,
                    label=f"Sentence_{s_idx+1}", mode=mode,
                    output_dir=out_dir, file_stem=stem, top_layers=top_layers,
                )
                if out_path:
                    paths[f"{mode}_s{s_idx+1}"] = str(out_path)
            except Exception as e:
                logger.error(f"render {mode} s{s_idx+1} failed: {e}")
    return paths


# ═══════════════════════════════════════════════════════════════════════
# HarmBench / Taxonomy item iterators
# ═══════════════════════════════════════════════════════════════════════

def _iter_harmbench_items(args):
    """Yield (item_id, behavior_text, category, semantic, taxonomy_family, sub_technique, total_turns)."""
    csv_path = DATA_DIR / "harmbench_behaviors_text_val.csv"
    behaviors = load_harmbench_behaviors(csv_path, n_pilot=args.npilot)
    for bhv in behaviors:
        user_text = bhv.behavior
        if getattr(bhv, "context", ""):
            user_text = f"{bhv.behavior}\n\nContext:\n{bhv.context}"
        yield (
            bhv.behavior_id, user_text, bhv.category, bhv.semantic, "", "", 1,
        )


def _iter_taxonomy_items(args):
    from pea_eval.evaluators.taxonomy_eval import generate_dynamic_scenarios
    per_cat = args.npilot if args.npilot > 0 else 5
    scenarios = generate_dynamic_scenarios(repeats_per_category=per_cat, seed=42)
    for sc in scenarios:
        # Use FINAL turn as the lens-target prompt (multi-turn jailbreak payoff lives in the last turn).
        final_user = sc.prompts[-1]
        # Embed prior turns as conversation context.
        if len(sc.prompts) > 1:
            history = "\n".join(f"[Turn {i+1}] {p}" for i, p in enumerate(sc.prompts[:-1]))
            final_user = f"[Conversation History]\n{history}\n\n[Final Turn]\n{final_user}"
        yield (
            sc.scenario_id, final_user, sc.taxonomy_family, sc.sub_technique,
            sc.taxonomy_family, sc.sub_technique, len(sc.prompts),
        )


# ═══════════════════════════════════════════════════════════════════════
# Main run
# ═══════════════════════════════════════════════════════════════════════

async def run(args):
    settings = load_settings(mode="real")
    arms_map, personas = load_harmbench_arms()
    selected = [arms_map[a] for a in args.arm_ids if a in arms_map]
    if not selected:
        logger.error(f"No arms matched from {args.arm_ids}. Available: {list(arms_map)[:8]}…")
        return

    items = list(
        _iter_harmbench_items(args) if args.module == "harmbench"
        else _iter_taxonomy_items(args)
    )
    logger.info(f"Loaded {len(items)} items for {args.module}; arms={[a.arm_id for a in selected]}")

    judge_client = None
    if not args.no_judge:
        judge_client = EvalLLMClient(
            ollama_config=settings.ollama,
            gemini_config=settings.gemini,
            lmstudio_config=settings.lmstudio,
        )

    ee_runner = None
    if any(getattr(a, "ee_enabled", False) for a in selected):
        from pea_eval.evaluators.ee_runner import EvalEERunner
        try:
            ee_runner = EvalEERunner.get_instance(ee_config=settings.ee)
            ee_runner.initialize()
        except Exception as e:
            logger.error(f"EE init failed (PEINN arms will fall back to vanilla path): {e}")
            ee_runner = None

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = FINAL_DIR / f"logit_lens_{args.module}_{timestamp}"
    png_dir = run_dir / "png"
    run_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Output directory: {run_dir}")

    collector = LogitLensCollector()
    current_model = None

    records: list[ItemRecord] = []

    for arm in sorted(selected, key=lambda a: a.arm_id):
        defense = _defense_type(arm)
        logger.info(f"\n{'='*60}\n🎯 Arm {arm.arm_id} ({defense}) — {arm.llm_model}\n{'='*60}")

        if arm.llm_model != current_model:
            try:
                collector.load_model(arm.llm_model, quantize_4bit=True)
                current_model = arm.llm_model
            except Exception as e:
                logger.error(f"Model load failed for {arm.arm_id}: {e}")
                continue

        persona = personas.get(arm.agent_profile) if getattr(arm, "agent_profile", "none") != "none" else None
        agent_key = arm.agent_profile if arm.agent_profile in ("A", "B") else "A"

        for rep in range(args.runs):
            for idx, (item_id, raw_user, category, semantic, tax_family, sub_tech, total_turns) in enumerate(items):
                run_id = f"ll_{args.module}_{arm.arm_id}_r{rep+1:02d}_i{idx+1:04d}"
                rec = ItemRecord(
                    run_id=run_id, arm_id=arm.arm_id, defense_type=defense,
                    model=arm.llm_model, item_id=item_id,
                    behavior=raw_user, category=category, semantic_category=semantic,
                    taxonomy_family=tax_family, sub_technique=sub_tech, total_turns=total_turns,
                )

                # EE input-side classification (PEINN only)
                if getattr(arm, "ee_enabled", False):
                    intent, energy, emotion_text, rag_context = _ee_classify(
                        ee_runner, raw_user, agent_key,
                    )
                else:
                    intent, energy, emotion_text, rag_context = "N/A", 0.0, "", ""
                rec.ee_intent = intent
                rec.ee_energy = energy

                # ── Pass 1 ──
                sys_p1, user_p1, peinn_features = _build_pass1_prompt(
                    raw_user, arm, persona, emotion_text, rag_context,
                    default_system=args.module,
                )
                try:
                    p1 = _generate_and_collect(
                        collector, sys_p1, user_p1,
                        arm_id=arm.arm_id, item_id=item_id, pass_label="p1",
                    )
                    rec.passes.append(p1)
                    logger.info(f"  [{arm.arm_id}] rep{rep+1} item {idx+1} p1: {p1.response_text[:60]}…")
                except Exception as e:
                    logger.error(f"  [{arm.arm_id}] rep{rep+1} item {idx+1} p1 FAILED: {e}")
                    continue

                # ── Pass 2 (PEINN only, gated by HARMFUL) ──
                if getattr(arm, "ee_enabled", False) and intent == "HARMFUL":
                    from pea_eval.config.settings import get_model_tier
                    sys_p2, user_p2, _p2_stop, _p2_max_tokens = build_reflection_prompt(
                        raw_user, p1.response_text, peinn_features,
                        tier=get_model_tier(arm.llm_model), ee_energy=energy,
                    )
                    try:
                        p2 = _generate_and_collect(
                            collector, sys_p2, user_p2,
                            arm_id=arm.arm_id, item_id=item_id, pass_label="p2",
                        )
                        rec.passes.append(p2)
                        rec.ee_pass_type = "2-pass"
                        logger.info(f"  [{arm.arm_id}] rep{rep+1} item {idx+1} p2: {p2.response_text[:60]}…")
                    except Exception as e:
                        logger.error(f"  [{arm.arm_id}] rep{rep+1} item {idx+1} p2 FAILED: {e}")

                records.append(rec)

    # ── ASR judge (effective final response per record) ──
    if judge_client and records:
        logger.info(f"\n🔍 Judging ASR ({len(records)} records)…")
        batch_size = 10
        for i in range(0, len(records), batch_size):
            chunk = records[i:i+batch_size]
            items_for_judge = []
            for j, r in enumerate(chunk):
                eff_response = (r.passes[-1].response_text if r.passes else "")
                items_for_judge.append((j, r.behavior, eff_response))
            try:
                judgments = await judge_asr_batch(judge_client, items_for_judge)
                for j, judgment in judgments.items():
                    chunk[j].asr_judgment = judgment
                    chunk[j].asr_outcome = _outcome_tag(judgment)
            except Exception as e:
                logger.error(f"Judge batch failed at chunk {i}: {e}")
                for c in chunk:
                    if not c.asr_judgment:
                        c.asr_judgment = "ERROR"
                        c.asr_outcome = "err"

    # ── Render PNGs with outcome-aware filenames ──
    logger.info(f"\n🖼️  Rendering heatmap PNGs…")
    manifest_rows = []
    for rec in records:
        for p in rec.passes:
            outcome = rec.asr_outcome or "skip"
            stem_prefix = (
                f"{args.module}_{rec.arm_id}_{rec.item_id}_{p.pass_label}_{outcome}"
            )
            png_paths = _render_pass_pngs(p, collector.tokenizer, png_dir, stem_prefix, top_layers=args.top_layers)
            manifest_rows.append({
                "run_id": rec.run_id,
                "arm_id": rec.arm_id,
                "defense_type": rec.defense_type,
                "model": rec.model,
                "module": args.module,
                "item_id": rec.item_id,
                "category": rec.category,
                "semantic_category": rec.semantic_category,
                "taxonomy_family": rec.taxonomy_family,
                "sub_technique": rec.sub_technique,
                "total_turns": rec.total_turns,
                "pass_label": p.pass_label,
                "ee_intent": rec.ee_intent,
                "ee_energy": rec.ee_energy,
                "ee_pass_type": rec.ee_pass_type,
                "asr_judgment": rec.asr_judgment,
                "asr_outcome": rec.asr_outcome,
                "behavior": rec.behavior,
                "prompt_full": p.full_input_text[:12000],
                "response": p.response_text,
                "png_entropy_s1": png_paths.get("entropy_s1", ""),
                "png_prob_s1":    png_paths.get("prob_s1", ""),
                "png_entropy_s2": png_paths.get("entropy_s2", ""),
                "png_prob_s2":    png_paths.get("prob_s2", ""),
                "collect_error":  p.error,
            })

    # ── Manifest CSV ──
    manifest_path = run_dir / "manifest.csv"
    if manifest_rows:
        fieldnames = list(manifest_rows[0].keys())
        with open(manifest_path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            w.writeheader()
            for row in manifest_rows:
                w.writerow(row)
        logger.info(f"Manifest saved: {manifest_path} ({len(manifest_rows)} rows)")

    # ── Summary MD ──
    md_path = run_dir / "summary.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# Logit Lens {args.module.capitalize()} Run ({timestamp})\n\n")
        f.write(f"Output dir: `{run_dir}`  •  PNGs: `{png_dir.name}/`  •  Manifest: `manifest.csv`\n\n")
        f.write("| Arm | Defense | Items | atk | def | skip/err | 2-pass | Total passes (rows) |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for arm in selected:
            arm_recs = [r for r in records if r.arm_id == arm.arm_id]
            n_atk = sum(1 for r in arm_recs if r.asr_outcome == "atk")
            n_def = sum(1 for r in arm_recs if r.asr_outcome == "def")
            n_other = sum(1 for r in arm_recs if r.asr_outcome in ("skip", "err"))
            n_2pass = sum(1 for r in arm_recs if r.ee_pass_type == "2-pass")
            n_passes = sum(len(r.passes) for r in arm_recs)
            f.write(
                f"| {arm.arm_id} | {_defense_type(arm)} | {len(arm_recs)} | "
                f"{n_atk} | {n_def} | {n_other} | {n_2pass} | {n_passes} |\n"
            )

    logger.info(f"\n✅ Done. Run dir: {run_dir}")


def _parse_args():
    parser = argparse.ArgumentParser(description="PEA-OS Logit Lens Statistical Runner")
    parser.add_argument("module", choices=["harmbench", "taxonomy"],
                        help="Evaluation module to source prompts from")
    parser.add_argument("--arms", type=str, default=",".join(DEFAULT_ARMS),
                        help="Comma-separated arm IDs (default: H05,H07)")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS,
                        help="Repetitions per (arm, item) (default: 3)")
    parser.add_argument("--npilot", type=int, default=DEFAULT_NPILOT,
                        help="HarmBench: # behaviors; Taxonomy: per-category scenarios (default: 5)")
    parser.add_argument("--no-judge", action="store_true",
                        help="Skip ASR judging (asr_outcome stays 'skip')")
    parser.add_argument("--top-layers", type=int, default=0,
                        help="히트맵에 출력쪽 상위 N개 레이어만 표시(논문 figure용; 0=전체)")
    args = parser.parse_args()
    args.arm_ids = [a.strip() for a in args.arms.split(",") if a.strip()]
    return args


def main():
    args = _parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
