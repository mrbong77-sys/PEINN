# v2.1 심사 대응 무인 실행 상태: 완료

- 시각 2026-10-21 05:46:15 (UTC 2026-10-20 20:46:15), 시도 1, 비컨 #470 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 0842e65 v21r peaos-diff: the PEAOS harness the runs called against its copy in src/
- 현재 단계: peaos-diff (0.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 3542 MiB, 32607 MiB, 1 %, 43
- 다음 동작: 없음(모든 단계 끝)
- 사유: –
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: 없음
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain, ftv-check, ftv, release-extra-check, release-extra, peaos-diff-check, peaos-diff

## 마지막 로그

```
[v21r] skip analyze-a8 (benchmark results again, with the A8 row): finished 2026-10-18 17:55:14
[v21r] skip ggb-export-a8 (GGB answers again, with the A8 rows (CPU)): finished 2026-10-18 17:55:20
[v21r] skip ggb-rescore-a8 (GGB re-scored from the answer text, with A8 (CPU)): finished 2026-10-18 17:55:23
[v21r] skip bench-export-a8 (every other bench's reported rows again, with A8 (CPU)): finished 2026-10-18 17:55:34
[v21r] skip bench-stats-a8 (every bench's statistics again, with A8 (CPU)): finished 2026-10-18 17:55:40
[v21r] skip ethics-diag-check (R2D2 WVS and NeMo MFQ reproduction on 3 items each first (pre-test)): finished 2026-10-18 18:06:11
[v21r] skip ethics-diag (R2D2 WVS (replay, greedy, HF bf16 checkpoint) and NeMo MFQ self-check (replay, without the answer format): design or harness): finished 2026-10-18 18:16:50
[v21r] skip finish-check (forced export, gate memory and gate retraining on the check cache first (pre-test)): finished 2026-10-18 19:47:19
[v21r] skip forced-export (forced-tag rows, route tables, signals, val/test labels -> results/forced (CPU)): finished 2026-10-18 19:47:34
[v21r] skip gate-mem (A0ftM's whole input gate in one process: time and peak memory, GPU and one CPU thread): finished 2026-10-18 19:48:46
[v21r] skip gate-retrain (A0ftM's gate trained again from the same corpus into a scratch folder: time, memory): finished 2026-10-18 20:03:46
[v21r] skip ftv-check (A1-A3 fine-tuned heads on 64 rows, one epoch (pre-test; nothing pushed)): finished 2026-10-19 12:03:30
[v21r] skip ftv (A1-A3 heads with PEINN's fine-tuned MiniLM, thresholds on val, routes -> results/forced): finished 2026-10-19 12:29:55
[v21r] skip release-extra-check (A1ft-A3ft heads, A8 adapters and split identifiers checked on a few rows first (pre-test; nothing pushed)): finished 2026-10-21 03:44:57
[v21r] skip release-extra (A1ft-A3ft heads and A8 adapters (in parts), corpus split identifiers -> results): finished 2026-10-21 03:46:30

[v21r] ===== peaos-diff-check: PEAOS harness against src/ (pre-test; nothing pushed) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r peaos-diff --check
environment: {'python': '3.13.2', 'os': 'Windows-11-10.0.26300-SP0', 'packages': {'torch': '2.10.0+cu128', 'transformers': '5.17.0', 'sentence-transformers': '5.3.0', 'safetensors': '0.8.0', 'huggingface-hub': '1.7.1', 'peft': '0.21.0', 'accelerate': '1.15.0', 'nemoguardrails': '0.21.0', 'langchain': '1.2.15', 'langchain-core': '1.2.26', 'langchain-community': '0.4.1', 'fastembed': '0.8.0', 'opena
PEAOS 2c7c850e055d (dirty files 0): {'same': 13, 'differs': 31, 'only_peaos': 30, 'only_src': 0}
  only_peaos used config/__init__.py 
  only_peaos used config/default_config.yaml secret-like string at line 25
  only_peaos used config/settings.py 
  differs    used config/user_config.yaml secret-like string at line 114
  differs    used core/__init__.py 
  differs    used core/emotion_engine.py 
  differs    used core/golden_anchors.py 
  differs    used core/golden_anchors_reverse.py 
  only_peaos used core/memory_bank.py 
  differs    used core/peinn.py 
  differs    used core/utils.py 
  only_peaos used integrations/__init__.py 
  only_peaos used integrations/gemini_api.py 
  only_peaos used integrations/ollama_client.py 
  only_peaos used integrations/vllm_openai_client.py 
  only_peaos used orchestrator/__init__.py 
  only_peaos used orchestrator/tci_module.py 
  differs    used pea_eval/backends/hf_backend.py 
  only_peaos used pea_eval/config/arms.yaml 
  only_peaos used pea_eval/config/arms_shieldstral.yaml 
  differs    used pea_eval/config/settings.py 
  only_peaos used pea_eval/config/unesco_rubric.yaml 
  differs    used pea_eval/evaluators/anchor_category_runner.py 
  only_peaos used pea_eval/evaluators/arm_runner.py 
  differs    used pea_eval/evaluators/benign_detector.py 
  only_peaos used pea_eval/evaluators/decision_flip_eval.py 
  only_peaos used pea_eval/evaluators/delphi_eval.py 
  differs    used pea_eval/evaluators/dilemma_runner.py 
  differs    used pea_eval/evaluators/ee_runner.py 
  differs    used pea_eval/evaluators/ethics_eval.py 
  differs    used pea_eval/evaluators/ggb_eval.py 
  differs    used pea_eval/evaluators/harmbench_eval.py 
  differs    used pea_eval/evaluators/intent_router.py 
  only_peaos used pea_eval/evaluators/ksafe_mm_eval.py 
  differs    used pea_eval/evaluators/llm_client.py 
  only_peaos used pea_eval/evaluators/mach_eval.py 
  differs    used pea_eval/evaluators/morables_eval.py 
  only_peaos used pea_eval/evaluators/or_bench_eval.py 
  differs    used pea_eval/evaluators/prompt_builder.py 
  only_peaos used pea_eval/evaluators/refusal_classifier.py 
  differs    used pea_eval/evaluators/taxonomy_eval.py 
  only_peaos used pea_eval/evaluators/unesco_eval.py 
  differs    used pea_eval/evaluators/xstest_eval.py 
  differs    used pea_eval/pge/__init__.py 
  only_peaos used pea_eval/pge/build_corpus.py 
  only_peaos used pea_eval/pge/combiner.py 
  only_peaos used pea_eval/pge/construction_vector_gate.py 
  only_peaos used pea_eval/pge/energy_resolution.py 
  only_peaos used pea_eval/pge/label_corpus_llm.py 
  differs    used pea_eval/pge/provenance_guard.py 
  only_peaos used pea_eval/pge/readout.py 
  only_peaos used pea_eval/pge/route_dryrun.py 
  only_peaos used pea_eval/pge/upsampler.py 
  differs    used peinn_v2/__init__.py 
  differs    used peinn_v2/energy.py 
  differs    used peinn_v2/train/data.py 
  differs    used run_stat_batch.py 
  differs    used scripts/build_morables_dataset.py 
  differs    used scripts/fetch_benchmark_data.py 
  differs    used scripts/fetch_ggb_morables.py 
  only_peaos used scripts/run_shieldstral_bench.py 

[v21r] ===== peaos-diff: PEAOS harness against its copy in src/ -> results/peaos_diff.json =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r peaos-diff
environment: {'python': '3.13.2', 'os': 'Windows-11-10.0.26300-SP0', 'packages': {'torch': '2.10.0+cu128', 'transformers': '5.17.0', 'sentence-transformers': '5.3.0', 'safetensors': '0.8.0', 'huggingface-hub': '1.7.1', 'peft': '0.21.0', 'accelerate': '1.15.0', 'nemoguardrails': '0.21.0', 'langchain': '1.2.15', 'langchain-core': '1.2.26', 'langchain-community': '0.4.1', 'fastembed': '0.8.0', 'opena
PEAOS 2c7c850e055d (dirty files 0): {'same': 13, 'differs': 31, 'only_peaos': 30, 'only_src': 0}
  only_peaos used config/__init__.py 
  only_peaos used config/default_config.yaml secret-like string at line 25
  only_peaos used config/settings.py 
  differs    used config/user_config.yaml secret-like string at line 114
  differs    used core/__init__.py 
  differs    used core/emotion_engine.py 
  differs    used core/golden_anchors.py 
  differs    used core/golden_anchors_reverse.py 
  only_peaos used core/memory_bank.py 
  differs    used core/peinn.py 
  differs    used core/utils.py 
  only_peaos used integrations/__init__.py 
  only_peaos used integrations/gemini_api.py 
  only_peaos used integrations/ollama_client.py 
  only_peaos used integrations/vllm_openai_client.py 
  only_peaos used orchestrator/__init__.py 
  only_peaos used orchestrator/tci_module.py 
  differs    used pea_eval/backends/hf_backend.py 
  only_peaos used pea_eval/config/arms.yaml 
  only_peaos used pea_eval/config/arms_shieldstral.yaml 
  differs    used pea_eval/config/settings.py 
  only_peaos used pea_eval/config/unesco_rubric.yaml 
  differs    used pea_eval/evaluators/anchor_category_runner.py 
  only_peaos used pea_eval/evaluators/arm_runner.py 
  differs    used pea_eval/evaluators/benign_detector.py 
  only_peaos used pea_eval/evaluators/decision_flip_eval.py 
  only_peaos used pea_eval/evaluators/delphi_eval.py 
  differs    used pea_eval/evaluators/dilemma_runner.py 
  differs    used pea_eval/evaluators/ee_runner.py 
  differs    used pea_eval/evaluators/ethics_eval.py 
  differs    used pea_eval/evaluators/ggb_eval.py 
  differs    used pea_eval/evaluators/harmbench_eval.py 
  differs    used pea_eval/evaluators/intent_router.py 
  only_peaos used pea_eval/evaluators/ksafe_mm_eval.py 
  differs    used pea_eval/evaluators/llm_client.py 
  only_peaos used pea_eval/evaluators/mach_eval.py 
  differs    used pea_eval/evaluators/morables_eval.py 
  only_peaos used pea_eval/evaluators/or_bench_eval.py 
  differs    used pea_eval/evaluators/prompt_builder.py 
  only_peaos used pea_eval/evaluators/refusal_classifier.py 
  differs    used pea_eval/evaluators/taxonomy_eval.py 
  only_peaos used pea_eval/evaluators/unesco_eval.py 
  differs    used pea_eval/evaluators/xstest_eval.py 
  differs    used pea_eval/pge/__init__.py 
  only_peaos used pea_eval/pge/build_corpus.py 
  only_peaos used pea_eval/pge/combiner.py 
  only_peaos used pea_eval/pge/construction_vector_gate.py 
  only_peaos used pea_eval/pge/energy_resolution.py 
  only_peaos used pea_eval/pge/label_corpus_llm.py 
  differs    used pea_eval/pge/provenance_guard.py 
  only_peaos used pea_eval/pge/readout.py 
  only_peaos used pea_eval/pge/route_dryrun.py 
  only_peaos used pea_eval/pge/upsampler.py 
  differs    used peinn_v2/__init__.py 
  differs    used peinn_v2/energy.py 
  differs    used peinn_v2/train/data.py 
  differs    used run_stat_batch.py 
  differs    used scripts/build_morables_dataset.py 
  differs    used scripts/fetch_benchmark_data.py 
  differs    used scripts/fetch_ggb_morables.py 
  only_peaos used scripts/run_shieldstral_bench.py 
[git] pushed to main

[v21r] all steps finished and pushed in 0.1 min
```
