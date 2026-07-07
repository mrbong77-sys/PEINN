# run_stat_nla.py
"""
PEA-OS NLA Statistical Batch Runner

Captures per-prompt:
  - Full input prompt (system + user, both passes)
  - Full LLM response (Pass 1 intuition + Pass 2 reflection when PEINN triggers)
  - Natural-language NLA interpretation of internal hidden states (Pass 1 + Pass 2)
  - EE intent / energy / pass_type for PEINN gating audit
  - ASR judgement for HarmBench / Taxonomy

Used to ground qualitative analysis of PEINN's effect on internal reasoning.
Reference: Li et al. (2026) — *Training Language Models to Explain Their Own
Computations* (arXiv:2511.08579v3). This script provides the {feature description}
side of that framework over harmful-prompt batches.
"""

import os
# 로컬 캐시 전용 모드
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("HF_DATASETS_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import argparse
import asyncio
import csv
import json
import logging
import random
import time
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from pea_eval.config.settings import (
    load_settings, MODULE_DIR, DATA_DIR, OUTPUT_DIR, FINAL_DIR,
)
from pea_eval.evaluators.harmbench_eval import (
    judge_asr_batch, load_harmbench_behaviors, load_harmbench_arms,
)
from pea_eval.evaluators.ethics_eval import EthicsEvaluator
from pea_eval.evaluators.llm_client import EvalLLMClient
from pea_eval.evaluators.prompt_builder import (
    build_eval_prompt, build_system_prompt, build_reflection_prompt,
)
from pea_eval.evaluators.confucian_mux import get_confucian_features
from pea_eval.backends.hf_backend import HFModelBackend
from pea_eval.nla.nla_interpreter import NLAInterpreter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("peinn.run_stat_nla")


# ═══════════════════════════════════════════════════════════════════════
# Configuration dataclasses
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class NLAArmConfig:
    arm_id: str
    description: str
    llm_backend: str
    llm_model: str
    ee_enabled: bool
    rag_enabled: bool
    nemo_enabled: bool
    reverse_peinn: bool
    thinking_mode: bool
    analysis_group: str
    agent_profile: str = "none"


@dataclass
class NLAHarmBenchResult:
    """Schema mirrors save_harmbench_csv (harmbench_eval.py) + NLA extension."""
    run_id: str
    arm_id: str
    behavior_id: str
    # arm meta
    model: str
    llm_backend: str
    defense_type: str
    ee_enabled: int
    rag_enabled: int
    nemo_enabled: int
    analysis_group: str
    # prompt meta
    category: str
    semantic_category: str
    behavior: str = ""              # full behavior text (no truncation)
    # judge output
    asr_judgment: str = ""
    asr_binary: int = 0
    latency_sec: float = 0.0
    # 2-pass NLA standard columns
    prompt_p1: str = ""
    response_p1: str = ""
    nla_concepts_p1: str = ""
    thought_block_p1: str = ""
    prompt_p2: str = ""
    response_p2: str = ""
    nla_concepts_p2: str = ""
    thought_block_p2: str = ""
    # EE / PEINN gating audit
    ee_intent: str = ""
    ee_energy: float = 0.0
    ee_pass_type: str = "1-pass"
    # legacy / convenience
    response: str = ""              # effective final response = response_p2 if PEINN else response_p1
    nla_concepts: str = ""          # effective final concepts
    nla_layer_count: int = 0
    nla_error: str = ""


@dataclass
class NLATaxonomyResult:
    """Schema mirrors save_taxonomy_csv + NLA extension."""
    run_id: str
    arm_id: str
    scenario_id: str
    model: str
    llm_backend: str
    defense_type: str
    ee_enabled: int
    rag_enabled: int
    nemo_enabled: int
    analysis_group: str
    taxonomy_family: str
    sub_technique: str
    total_turns: int
    turn_prompts: dict = field(default_factory=dict)        # {turn_idx: str}
    turn_responses: dict = field(default_factory=dict)      # {turn_idx: str}
    # final-turn 2-pass NLA standard columns
    prompt_p1: str = ""
    response_p1: str = ""
    nla_concepts_p1: str = ""
    thought_block_p1: str = ""
    prompt_p2: str = ""
    response_p2: str = ""
    nla_concepts_p2: str = ""
    thought_block_p2: str = ""
    ee_intent: str = ""
    ee_energy: float = 0.0
    ee_pass_type: str = "1-pass"
    # judge output
    asr_judgment: str = ""
    asr_binary: int = 0
    latency_sec: float = 0.0
    response: str = ""              # effective final-turn response
    nla_concepts: str = ""
    nla_layer_count: int = 0
    nla_error: str = ""


@dataclass
class NLAEthicsResult:
    """Schema mirrors save_results (ethics_eval.py) + NLA extension."""
    run_id: str
    arm_id: str
    item_id: str
    instrument: str
    category: str
    model: str
    defense_type: str
    score: str = ""
    ground_truth: str = ""
    alignment: float = 0.0
    rqi: str = ""
    ecm: str = ""
    judge_rationale: str = ""
    latency_sec: float = 0.0
    prompt_p1: str = ""
    response_p1: str = ""
    nla_concepts_p1: str = ""
    thought_block_p1: str = ""
    prompt_p2: str = ""
    response_p2: str = ""
    nla_concepts_p2: str = ""
    thought_block_p2: str = ""
    ee_intent: str = ""
    ee_energy: float = 0.0
    ee_pass_type: str = "1-pass"
    response: str = ""
    nla_concepts: str = ""
    nla_layer_count: int = 0
    nla_error: str = ""


# ═══════════════════════════════════════════════════════════════════════
# Arms loading
# ═══════════════════════════════════════════════════════════════════════

def load_nla_arms(yaml_path: Path) -> list[NLAArmConfig]:
    """Load NLA arms from YAML. Falls back to default H05/H07/H11/H13 if missing."""
    if not Path(yaml_path).exists():
        logger.warning(f"Arms YAML not found at {yaml_path} — using built-in NLA defaults.")
        return _builtin_nla_arms()

    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    arms_data = data.get("arms", data)

    arms: list[NLAArmConfig] = []
    for k, v in arms_data.items():
        if not isinstance(v, dict):
            continue
        defense = str(v.get("defense", "vanilla")).lower()
        model_id = v.get("model_id", v.get("llm_model", ""))
        arms.append(NLAArmConfig(
            arm_id=k,
            description=v.get("description", ""),
            llm_backend=v.get("backend", v.get("llm_backend", "hf")),
            llm_model=model_id,
            ee_enabled=("peinn" in defense),
            rag_enabled=("peinn" in defense),  # PEINN uses MUX (RAG) by definition
            nemo_enabled=("nemo" in defense),
            reverse_peinn=("reverse" in defense),
            thinking_mode=("gemma-3" in model_id.lower()),
            analysis_group=v.get("analysis_group", "NLA"),
            agent_profile=v.get("agent_profile", "none"),
        ))
    return arms


def _builtin_nla_arms() -> list[NLAArmConfig]:
    """Per wiki.md §3, the four NLA-target arms."""
    return [
        NLAArmConfig(arm_id="H05", description="Qwen2.5-7B Vanilla (NLA baseline)",
                     llm_backend="hf", llm_model="Qwen/Qwen2.5-7B-Instruct",
                     ee_enabled=False, rag_enabled=False, nemo_enabled=False,
                     reverse_peinn=False, thinking_mode=False, analysis_group="NLA"),
        NLAArmConfig(arm_id="H07", description="Qwen2.5-7B + PEINN (NLA core target)",
                     llm_backend="hf", llm_model="Qwen/Qwen2.5-7B-Instruct",
                     ee_enabled=True, rag_enabled=True, nemo_enabled=False,
                     reverse_peinn=False, thinking_mode=False, analysis_group="NLA"),
        NLAArmConfig(arm_id="H11", description="Gemma-3-12B Vanilla (large baseline)",
                     llm_backend="hf", llm_model="google/gemma-3-12b-it",
                     ee_enabled=False, rag_enabled=False, nemo_enabled=False,
                     reverse_peinn=False, thinking_mode=True, analysis_group="NLA"),
        NLAArmConfig(arm_id="H13", description="Gemma-3-12B + PEINN (large PEINN)",
                     llm_backend="hf", llm_model="google/gemma-3-12b-it",
                     ee_enabled=True, rag_enabled=True, nemo_enabled=False,
                     reverse_peinn=False, thinking_mode=True, analysis_group="NLA"),
    ]


def _defense_type(arm: NLAArmConfig) -> str:
    if arm.ee_enabled:
        return "ReversePEINN" if arm.reverse_peinn else "PEINN"
    if arm.nemo_enabled:
        return "NeMo"
    return "Vanilla"


# ═══════════════════════════════════════════════════════════════════════
# Prompt builders
# ═══════════════════════════════════════════════════════════════════════

class _MockArm:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def build_pass1_prompt(
    raw_user: str,
    arm: NLAArmConfig,
    ee_emotion_text: str = "",
    rag_context: str = "",
    default_system: str = "harmbench",
    persona=None,
) -> tuple[str, str, dict]:
    """Returns (system_prompt, user_prompt, peinn_features)."""
    mock_arm = _MockArm(
        arm_id=arm.arm_id, ee_enabled=arm.ee_enabled,
        reverse_peinn=arm.reverse_peinn, agent_profile=arm.agent_profile,
    )
    peinn_features = {}
    if arm.ee_enabled:
        peinn_features = get_confucian_features(raw_user, ee_emotion_text, rag_context)

    system_prompt = build_system_prompt(
        mock_arm, persona, language="en", peinn_features=peinn_features,
    )
    module_constraints = build_eval_prompt(default_system, mock_arm)
    if module_constraints:
        system_prompt = f"{system_prompt}\n\n{module_constraints}".strip()

    return system_prompt, raw_user, peinn_features


# ═══════════════════════════════════════════════════════════════════════
# EE helper
# ═══════════════════════════════════════════════════════════════════════

def _ee_classify(ee_runner, text: str, agent_profile: str = "A") -> tuple[str, float, str, str]:
    """Returns (intent, weighted_energy, emotion_text, rag_context). Safe on errors."""
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


def _safe_nla(nla, hidden_states) -> tuple[str, int, str]:
    """Returns (concepts, layer_count, error)."""
    if nla is None or hidden_states is None:
        return "", 0, ""
    try:
        concepts = nla.explain(hidden_states)
        n_layers = int(hidden_states.shape[0]) if hasattr(hidden_states, "shape") and len(hidden_states.shape) >= 1 else 0
        return concepts, n_layers, ""
    except Exception as e:
        logger.error(f"NLA explain failed: {e}")
        return "", 0, str(e)


# ═══════════════════════════════════════════════════════════════════════
# HarmBench runner
# ═══════════════════════════════════════════════════════════════════════

async def run_harmbench(
    arms: list[NLAArmConfig], behaviors: list, args, judge_client: EvalLLMClient, settings,
) -> tuple[list[NLAHarmBenchResult], list[NLAArmConfig]]:
    all_results: list[NLAHarmBenchResult] = []

    for arm in sorted(arms, key=lambda a: a.arm_id):
        logger.info(f"[HarmBench/NLA] Arm {arm.arm_id} ({_defense_type(arm)}): {arm.description}")
        try:
            backend = HFModelBackend.get_instance(arm.llm_model, device="cuda")
        except Exception as e:
            logger.error(f"Backend init failed for {arm.arm_id}: {e}")
            continue
        nla = NLAInterpreter.get_instance(arm.llm_model) if not args.no_nla else None

        ee_runner = None
        if arm.ee_enabled:
            try:
                from pea_eval.evaluators.ee_runner import EvalEERunner
                ee_runner = EvalEERunner.get_instance(ee_config=settings.ee)
                ee_runner.initialize()
            except Exception as e:
                logger.error(f"EE init failed: {e}")

        arm_results: list[NLAHarmBenchResult] = []

        for rep in range(args.repeats):
            for idx, bhv in enumerate(behaviors):
                raw_user = bhv.behavior
                if getattr(bhv, "context", ""):
                    raw_user = f"{bhv.behavior}\n\nContext:\n{bhv.context}"

                run_id = f"nla_hb_{arm.arm_id}_r{rep+1:02d}_i{idx+1:04d}"
                result = NLAHarmBenchResult(
                    run_id=run_id, arm_id=arm.arm_id, behavior_id=bhv.behavior_id,
                    model=arm.llm_model, llm_backend="hf", defense_type=_defense_type(arm),
                    ee_enabled=int(arm.ee_enabled), rag_enabled=int(arm.rag_enabled),
                    nemo_enabled=int(arm.nemo_enabled), analysis_group=arm.analysis_group,
                    category=bhv.category, semantic_category=bhv.semantic,
                    behavior=bhv.behavior,
                )

                try:
                    # ── EE (input-side harmfulness classifier) ──
                    agent_key = arm.agent_profile if arm.agent_profile in ("A", "B") else "A"
                    intent, energy, emotion_text, rag_context = _ee_classify(
                        ee_runner, raw_user, agent_key
                    ) if arm.ee_enabled else ("N/A", 0.0, "", "")
                    result.ee_intent = intent
                    result.ee_energy = energy

                    # ── Pass 1 (always for PEINN; baseline arm = single pass) ──
                    sys_p1, user_p1, peinn_features = build_pass1_prompt(
                        raw_user, arm, emotion_text, rag_context, default_system="harmbench",
                    )
                    result.prompt_p1 = f"[System]\n{sys_p1}\n\n[User]\n{user_p1}"

                    gen_p1 = await backend.generate(
                        system_prompt=sys_p1, user_prompt=user_p1,
                        capture_hidden_states=not args.no_nla,
                        thinking_mode=arm.thinking_mode and not args.no_thinking,
                    )
                    result.response_p1 = gen_p1.text
                    result.thought_block_p1 = gen_p1.thought_block or ""
                    nla_p1, n_layers_p1, err_p1 = _safe_nla(nla, gen_p1.hidden_states_pooled)
                    result.nla_concepts_p1 = nla_p1
                    result.nla_layer_count = n_layers_p1
                    result.latency_sec = float(gen_p1.latency_sec or 0.0)
                    if err_p1:
                        result.nla_error = err_p1

                    # ── Pass 2 (PEINN, only if HARMFUL — matches production gating) ──
                    if arm.ee_enabled and intent == "HARMFUL":
                        from pea_eval.config.settings import get_model_tier
                        # NLA는 hidden state 캡처가 핵심이라 stop/max_tokens는 HF backend
                        # 기본값 유지 (사후 검증용 긴 컴플리션 필요). tier·ee_energy는 전달.
                        sys_p2, user_p2, _p2_stop, _p2_max_tokens = build_reflection_prompt(
                            raw_user, gen_p1.text, peinn_features,
                            tier=get_model_tier(arm.llm_model), ee_energy=energy,
                        )
                        result.prompt_p2 = f"[System]\n{sys_p2}\n\n[User]\n{user_p2}"
                        gen_p2 = await backend.generate(
                            system_prompt=sys_p2, user_prompt=user_p2,
                            capture_hidden_states=not args.no_nla,
                            thinking_mode=arm.thinking_mode and not args.no_thinking,
                        )
                        result.response_p2 = gen_p2.text
                        result.thought_block_p2 = gen_p2.thought_block or ""
                        nla_p2, _, err_p2 = _safe_nla(nla, gen_p2.hidden_states_pooled)
                        result.nla_concepts_p2 = nla_p2
                        result.ee_pass_type = "2-pass"
                        result.latency_sec += float(gen_p2.latency_sec or 0.0)
                        if err_p2 and not result.nla_error:
                            result.nla_error = err_p2
                        # effective final
                        result.response = gen_p2.text
                        result.nla_concepts = nla_p2
                    else:
                        # 1-pass: p2 mirrors p1
                        result.prompt_p2 = result.prompt_p1
                        result.response_p2 = result.response_p1
                        result.nla_concepts_p2 = result.nla_concepts_p1
                        result.thought_block_p2 = result.thought_block_p1
                        result.response = result.response_p1
                        result.nla_concepts = result.nla_concepts_p1
                        result.ee_pass_type = "1-pass"

                except Exception as e:
                    logger.error(f"[{arm.arm_id}] item {idx+1} failed: {e}")
                    result.nla_error = f"runtime: {str(e)[:200]}"
                    result.response = result.response or f"[ERROR] {str(e)[:200]}"

                arm_results.append(result)
                if (idx + 1) % 10 == 0:
                    logger.info(f"  [{arm.arm_id}] rep{rep+1} progress {idx+1}/{len(behaviors)}")

        # ── ASR judge ──
        if not args.no_judge:
            logger.info(f"[{arm.arm_id}] Judging ASR ({len(arm_results)} items)...")
            batch_size = 10
            for i in range(0, len(arm_results), batch_size):
                chunk = arm_results[i:i + batch_size]
                items = [(j, r.behavior, r.response) for j, r in enumerate(chunk)]
                try:
                    judgments = await judge_asr_batch(judge_client, items)
                    for j, judgment in judgments.items():
                        chunk[j].asr_judgment = judgment
                        chunk[j].asr_binary = 1 if judgment == "HARMFUL" else 0
                except Exception as e:
                    logger.error(f"Judge batch failed at chunk {i}: {e}")
                    for c in chunk:
                        c.asr_judgment = c.asr_judgment or "ERROR"

        all_results.extend(arm_results)

    return all_results, arms


# ═══════════════════════════════════════════════════════════════════════
# Taxonomy runner (multi-turn; Pass 2 on FINAL turn if PEINN+HARMFUL)
# ═══════════════════════════════════════════════════════════════════════

async def run_taxonomy(
    arms: list[NLAArmConfig], args, judge_client: EvalLLMClient, settings,
) -> tuple[list[NLATaxonomyResult], list[NLAArmConfig]]:
    from pea_eval.evaluators.taxonomy_eval import generate_dynamic_scenarios
    per_cat = args.npilot if args.npilot > 0 else 5
    scenarios = generate_dynamic_scenarios(repeats_per_category=per_cat, seed=42)

    all_results: list[NLATaxonomyResult] = []

    for arm in sorted(arms, key=lambda a: a.arm_id):
        logger.info(f"[Taxonomy/NLA] Arm {arm.arm_id} ({_defense_type(arm)}): {arm.description}")
        try:
            backend = HFModelBackend.get_instance(arm.llm_model, device="cuda")
        except Exception as e:
            logger.error(f"Backend init failed for {arm.arm_id}: {e}")
            continue
        nla = NLAInterpreter.get_instance(arm.llm_model) if not args.no_nla else None

        ee_runner = None
        if arm.ee_enabled:
            try:
                from pea_eval.evaluators.ee_runner import EvalEERunner
                ee_runner = EvalEERunner.get_instance(ee_config=settings.ee)
                ee_runner.initialize()
            except Exception as e:
                logger.error(f"EE init failed: {e}")

        arm_results: list[NLATaxonomyResult] = []
        agent_key = arm.agent_profile if arm.agent_profile in ("A", "B") else "A"

        for rep in range(args.repeats):
            for scenario in scenarios:
                run_id = f"nla_tax_{arm.arm_id}_r{rep+1:02d}_s{scenario.scenario_id}"
                result = NLATaxonomyResult(
                    run_id=run_id, arm_id=arm.arm_id, scenario_id=scenario.scenario_id,
                    model=arm.llm_model, llm_backend="hf", defense_type=_defense_type(arm),
                    ee_enabled=int(arm.ee_enabled), rag_enabled=int(arm.rag_enabled),
                    nemo_enabled=int(arm.nemo_enabled), analysis_group=arm.analysis_group,
                    taxonomy_family=scenario.taxonomy_family, sub_technique=scenario.sub_technique,
                    total_turns=len(scenario.prompts),
                )

                try:
                    history_lines: list[str] = []
                    total_latency = 0.0
                    final_text = ""

                    for turn_idx, p_text in enumerate(scenario.prompts, 1):
                        is_final = (turn_idx == len(scenario.prompts))

                        # EE on the per-turn context for PEINN arms
                        context_for_ee = p_text
                        if history_lines:
                            context_for_ee = "\n".join(history_lines) + f"\n[Current]\n{p_text}"
                        intent, energy, emotion_text, rag_context = _ee_classify(
                            ee_runner, context_for_ee, agent_key,
                        ) if arm.ee_enabled else ("N/A", 0.0, "", "")

                        sys_p1, user_p1, peinn_features = build_pass1_prompt(
                            p_text, arm, emotion_text, rag_context, default_system="taxonomy",
                        )
                        if history_lines:
                            user_p1 = (
                                "[Conversation History]\n"
                                + "\n".join(history_lines)
                                + f"\n\n[Current Turn]\n{user_p1}"
                            )
                        full_prompt_log = f"[System]\n{sys_p1}\n\n[User]\n{user_p1}"

                        gen = await backend.generate(
                            system_prompt=sys_p1, user_prompt=user_p1,
                            capture_hidden_states=(not args.no_nla) and is_final,
                            thinking_mode=arm.thinking_mode and not args.no_thinking,
                        )
                        total_latency += float(gen.latency_sec or 0.0)
                        result.turn_prompts[turn_idx] = full_prompt_log
                        result.turn_responses[turn_idx] = gen.text
                        history_lines.append(f"U: {p_text}\nA: {gen.text}")

                        if is_final:
                            result.ee_intent = intent
                            result.ee_energy = energy
                            result.prompt_p1 = full_prompt_log
                            result.response_p1 = gen.text
                            result.thought_block_p1 = gen.thought_block or ""
                            nla_p1, n_layers, err_p1 = _safe_nla(nla, gen.hidden_states_pooled)
                            result.nla_concepts_p1 = nla_p1
                            result.nla_layer_count = n_layers
                            if err_p1:
                                result.nla_error = err_p1
                            final_text = gen.text

                            # Pass 2 (PEINN + HARMFUL only) on the final turn
                            if arm.ee_enabled and intent == "HARMFUL":
                                from pea_eval.config.settings import get_model_tier
                                sys_p2, user_p2, _p2_stop, _p2_max_tokens = build_reflection_prompt(
                                    p_text, gen.text, peinn_features,
                                    tier=get_model_tier(arm.llm_model), ee_energy=energy,
                                )
                                result.prompt_p2 = f"[System]\n{sys_p2}\n\n[User]\n{user_p2}"
                                gen2 = await backend.generate(
                                    system_prompt=sys_p2, user_prompt=user_p2,
                                    capture_hidden_states=not args.no_nla,
                                    thinking_mode=arm.thinking_mode and not args.no_thinking,
                                )
                                total_latency += float(gen2.latency_sec or 0.0)
                                result.response_p2 = gen2.text
                                result.thought_block_p2 = gen2.thought_block or ""
                                nla_p2, _, err_p2 = _safe_nla(nla, gen2.hidden_states_pooled)
                                result.nla_concepts_p2 = nla_p2
                                result.ee_pass_type = "2-pass"
                                if err_p2 and not result.nla_error:
                                    result.nla_error = err_p2
                                final_text = gen2.text
                                result.response = gen2.text
                                result.nla_concepts = nla_p2
                            else:
                                result.prompt_p2 = result.prompt_p1
                                result.response_p2 = result.response_p1
                                result.nla_concepts_p2 = result.nla_concepts_p1
                                result.thought_block_p2 = result.thought_block_p1
                                result.ee_pass_type = "1-pass"
                                result.response = result.response_p1
                                result.nla_concepts = result.nla_concepts_p1

                    result.latency_sec = round(total_latency, 2)

                except Exception as e:
                    logger.error(f"[{arm.arm_id}] scenario {scenario.scenario_id} failed: {e}")
                    result.nla_error = f"runtime: {str(e)[:200]}"
                    result.response = result.response or f"[ERROR] {str(e)[:200]}"

                arm_results.append(result)

        # ── ASR judge on the effective final response ──
        if not args.no_judge:
            logger.info(f"[{arm.arm_id}] Judging Taxonomy ASR ({len(arm_results)} items)...")
            batch_size = 10
            for i in range(0, len(arm_results), batch_size):
                chunk = arm_results[i:i + batch_size]
                final_turn_prompt = lambda r: r.turn_prompts.get(r.total_turns, "") or r.prompt_p1
                items = [
                    (j, scenario_text_for_judge(r, final_turn_prompt(r)), r.response)
                    for j, r in enumerate(chunk)
                ]
                try:
                    judgments = await judge_asr_batch(judge_client, items)
                    for j, judgment in judgments.items():
                        chunk[j].asr_judgment = judgment
                        chunk[j].asr_binary = 1 if judgment == "HARMFUL" else 0
                except Exception as e:
                    logger.error(f"Judge batch failed at chunk {i}: {e}")
                    for c in chunk:
                        c.asr_judgment = c.asr_judgment or "ERROR"

        all_results.extend(arm_results)

    return all_results, arms


def scenario_text_for_judge(r: NLATaxonomyResult, fallback: str) -> str:
    """Compact rendering of multi-turn scenario for the ASR judge prompt."""
    parts = []
    for i in sorted(r.turn_prompts.keys()):
        parts.append(f"[Turn {i} prompt]\n{r.turn_prompts[i][:600]}")
    return "\n\n".join(parts) if parts else fallback[:1200]


# ═══════════════════════════════════════════════════════════════════════
# CSV writers
# ═══════════════════════════════════════════════════════════════════════

_TRUNC_TB = 4000
_TRUNC_PROMPT = 12000
_TRUNC_NLA = 1500


def _safe_truncate(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[:n] + "...[truncated]"


def write_harmbench_csv(results: list[NLAHarmBenchResult], csv_path: Path) -> Path:
    """Mirrors save_harmbench_csv columns + NLA p1/p2 extension."""
    fieldnames = [
        # identifiers
        "run_id", "arm_id", "behavior_id",
        # arm meta
        "model", "llm_backend", "defense_type",
        "ee_enabled", "rag_enabled", "nemo_enabled", "analysis_group",
        # prompt meta
        "category", "semantic_category",
        # judge
        "asr_judgment", "asr_binary", "latency_sec",
        # effective (legacy)
        "behavior", "response", "nla_concepts",
        # 2-pass NLA standard
        "prompt_p1", "response_p1", "nla_concepts_p1", "thought_block_p1",
        "prompt_p2", "response_p2", "nla_concepts_p2", "thought_block_p2",
        # EE audit
        "ee_intent", "ee_energy", "ee_pass_type",
        # NLA meta
        "nla_layer_count", "nla_error",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in results:
            row = {fn: getattr(r, fn, "") for fn in fieldnames}
            for col in ("prompt_p1", "prompt_p2"):
                row[col] = _safe_truncate(row.get(col, ""), _TRUNC_PROMPT)
            for col in ("thought_block_p1", "thought_block_p2"):
                row[col] = _safe_truncate(row.get(col, ""), _TRUNC_TB)
            for col in ("nla_concepts", "nla_concepts_p1", "nla_concepts_p2"):
                row[col] = _safe_truncate(row.get(col, ""), _TRUNC_NLA)
            w.writerow(row)
    logger.info(f"HarmBench/NLA CSV saved: {csv_path} ({len(results)} rows, {len(fieldnames)} cols)")
    return csv_path


def write_taxonomy_csv(results: list[NLATaxonomyResult], csv_path: Path) -> Path:
    """Mirrors save_taxonomy_csv columns + NLA p1/p2 + per-turn prompts/responses."""
    if not results:
        logger.warning("No taxonomy results to save.")
        return csv_path
    max_turns = max((r.total_turns for r in results), default=1)

    fieldnames = [
        "run_id", "arm_id", "defense_type", "model", "scenario_id",
        "taxonomy_family", "sub_technique", "total_turns",
    ]
    for i in range(1, max_turns + 1):
        fieldnames.extend([f"turn_{i}_prompt", f"turn_{i}_response"])
    fieldnames.extend([
        "asr_judgment", "asr_binary", "latency_sec",
        "response", "nla_concepts",
        "prompt_p1", "response_p1", "nla_concepts_p1", "thought_block_p1",
        "prompt_p2", "response_p2", "nla_concepts_p2", "thought_block_p2",
        "ee_intent", "ee_energy", "ee_pass_type",
        "nla_layer_count", "nla_error",
    ])

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in results:
            row = {fn: getattr(r, fn, "") for fn in fieldnames if not fn.startswith("turn_")}
            for i in range(1, max_turns + 1):
                row[f"turn_{i}_prompt"] = _safe_truncate(r.turn_prompts.get(i, ""), _TRUNC_PROMPT)
                row[f"turn_{i}_response"] = r.turn_responses.get(i, "")
            for col in ("prompt_p1", "prompt_p2"):
                row[col] = _safe_truncate(row.get(col, ""), _TRUNC_PROMPT)
            for col in ("thought_block_p1", "thought_block_p2"):
                row[col] = _safe_truncate(row.get(col, ""), _TRUNC_TB)
            for col in ("nla_concepts", "nla_concepts_p1", "nla_concepts_p2"):
                row[col] = _safe_truncate(row.get(col, ""), _TRUNC_NLA)
            w.writerow(row)
    logger.info(f"Taxonomy/NLA CSV saved: {csv_path} ({len(results)} rows, {len(fieldnames)} cols)")
    return csv_path


# ═══════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════

async def main():
    parser = argparse.ArgumentParser(description="PEA-OS NLA Statistical Batch Runner")
    parser.add_argument("module", choices=["harmbench", "taxonomy"],
                        help="Evaluation module to run (PEINN-effect target)")
    parser.add_argument("runs", nargs="?", type=int, default=10,
                        help="Repetitions per arm (default 10)")
    parser.add_argument("--arms", nargs="+", default=None,
                        help="Arm IDs (comma or space). Defaults to H05,H07,H11,H13")
    parser.add_argument("--npilot", type=int, default=10,
                        help="HarmBench: # behaviors; Taxonomy: per-category scenarios. 0=all")
    parser.add_argument("--no-nla", action="store_true",
                        help="Skip NLA interpreter (much faster, no internal-reasoning column)")
    parser.add_argument("--no-thinking", action="store_true",
                        help="Disable Gemma <think> parsing")
    parser.add_argument("--no-judge", action="store_true",
                        help="Skip ASR judge (records asr_judgment as empty)")
    parser.add_argument("--config", type=str, default=None,
                        help="Path to arms YAML (default: config/arms_nla.yaml)")
    args = parser.parse_args()
    args.repeats = int(args.runs or 10)

    yaml_path = Path(args.config) if args.config else (MODULE_DIR / "config" / "arms_nla.yaml")
    arms = load_nla_arms(yaml_path)

    if args.arms:
        raw_arms = ",".join(args.arms)
        target_arms = {a.strip() for a in raw_arms.split(",") if a.strip()}
        arms = [a for a in arms if a.arm_id in target_arms]
    if not arms:
        logger.error("No arms selected. Aborting.")
        return

    settings = load_settings(mode="real")
    judge_client = EvalLLMClient(
        ollama_config=settings.ollama,
        gemini_config=settings.gemini,
        lmstudio_config=settings.lmstudio,
    )

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    out_dir = FINAL_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── dispatch ──
    if args.module == "harmbench":
        csv_path = DATA_DIR / "harmbench_behaviors_text_val.csv"
        behaviors = load_harmbench_behaviors(csv_path, n_pilot=args.npilot)
        results, arms = await run_harmbench(arms, behaviors, args, judge_client, settings)
        out_csv = out_dir / f"nla_harmbench_{args.repeats}runs_{timestamp}.csv"
        write_harmbench_csv(results, out_csv)
    else:  # taxonomy
        results, arms = await run_taxonomy(arms, args, judge_client, settings)
        out_csv = out_dir / f"nla_taxonomy_{args.repeats}runs_{timestamp}.csv"
        write_taxonomy_csv(results, out_csv)

    # ── thinking JSONL (Gemma) ──
    jsonl_path = out_dir / f"nla_{args.module}_thinking_{timestamp}.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as f:
        for r in results:
            tb1 = getattr(r, "thought_block_p1", "") or ""
            tb2 = getattr(r, "thought_block_p2", "") or ""
            if not (tb1 or tb2):
                continue
            payload = {
                "run_id": r.run_id, "arm_id": r.arm_id,
                "thought_block_p1": tb1, "thought_block_p2": tb2,
                "nla_concepts_p1": r.nla_concepts_p1,
                "nla_concepts_p2": r.nla_concepts_p2,
                "response_p1": r.response_p1, "response_p2": r.response_p2,
                "ee_intent": r.ee_intent, "ee_energy": r.ee_energy,
                "ee_pass_type": r.ee_pass_type,
                "asr_judgment": r.asr_judgment,
            }
            if args.module == "harmbench":
                payload.update({"behavior_id": r.behavior_id, "behavior": r.behavior})
            else:
                payload.update({
                    "scenario_id": r.scenario_id,
                    "taxonomy_family": r.taxonomy_family,
                    "sub_technique": r.sub_technique,
                })
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    # ── summary MD ──
    md_path = out_dir / f"nla_{args.module}_summary_{timestamp}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# NLA {args.module.capitalize()} Summary ({timestamp})\n\n")
        f.write("| Arm | Defense | n | ASR% (HARMFUL) | 2-pass triggered | NLA errors |\n")
        f.write("|---|---|---|---|---|---|\n")
        for arm in arms:
            arm_res = [r for r in results if r.arm_id == arm.arm_id]
            n = len(arm_res)
            harmful = sum(1 for r in arm_res if r.asr_judgment == "HARMFUL")
            two_pass = sum(1 for r in arm_res if getattr(r, "ee_pass_type", "") == "2-pass")
            nla_err = sum(1 for r in arm_res if getattr(r, "nla_error", ""))
            asr_pct = (harmful / n * 100) if n else 0.0
            f.write(f"| {arm.arm_id} | {_defense_type(arm)} | {n} | {asr_pct:.1f}% ({harmful}) | {two_pass} | {nla_err} |\n")

    logger.info(f"Done. CSV={out_csv.name}  JSONL={jsonl_path.name}  Summary={md_path.name}")


if __name__ == "__main__":
    asyncio.run(main())
