# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-17 01:00:55 (UTC 2026-10-16 16:00:55), 시도 36, 비컨 #195 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 91de1c8 station: 임무 실행 중
- 현재 단계: matrix (8.5분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1954 MiB, 32607 MiB, 0 %, 59
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T151800Z-rerun rerun (자식 종료 후 재실행, 2026-10-16 15:15:14 UTC)
- 남은 단계: matrix; nemo-doc; nemo-orr-all; nemo-audit-all; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset

## 마지막 로그

```
2026-10-17 01:00:55,056 [nemoguardrails.actions.action_dispatcher] INFO: Added crowdstrike_aidr_guard to actions
2026-10-17 01:00:55,057 [nemoguardrails.actions.action_dispatcher] INFO: Added alignscore_check_facts to actions
2026-10-17 01:00:55,057 [nemoguardrails.actions.action_dispatcher] INFO: Added alignscore request to actions
2026-10-17 01:00:55,057 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_facts to actions
2026-10-17 01:00:55,058 [nemoguardrails.actions.action_dispatcher] INFO: Added call fiddler faithfulness to actions
2026-10-17 01:00:55,058 [nemoguardrails.actions.action_dispatcher] INFO: Added call fiddler safety on bot message to actions
2026-10-17 01:00:55,058 [nemoguardrails.actions.action_dispatcher] INFO: Added call fiddler safety on user message to actions
2026-10-17 01:00:55,059 [nemoguardrails.actions.action_dispatcher] INFO: Added call gcpnlp api to actions
2026-10-17 01:00:55,059 [nemoguardrails.actions.action_dispatcher] INFO: Added gliner_detect_pii to actions
2026-10-17 01:00:55,059 [nemoguardrails.actions.action_dispatcher] INFO: Added gliner_mask_pii to actions
2026-10-17 01:00:55,060 [nemoguardrails.actions.action_dispatcher] INFO: Added validate_guardrails_ai_input to actions
2026-10-17 01:00:55,060 [nemoguardrails.actions.action_dispatcher] INFO: Added validate_guardrails_ai_output to actions
2026-10-17 01:00:55,061 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_hallucination to actions
2026-10-17 01:00:55,062 [nemoguardrails.actions.action_dispatcher] INFO: Added injection_detection to actions
2026-10-17 01:00:55,063 [nemoguardrails.actions.action_dispatcher] INFO: Added jailbreak_detection_heuristics to actions
2026-10-17 01:00:55,063 [nemoguardrails.actions.action_dispatcher] INFO: Added jailbreak_detection_model to actions
2026-10-17 01:00:55,064 [nemoguardrails.actions.action_dispatcher] INFO: Added llama_guard_check_input to actions
2026-10-17 01:00:55,064 [nemoguardrails.actions.action_dispatcher] INFO: Added llama_guard_check_output to actions
2026-10-17 01:00:55,067 [nemoguardrails.actions.action_dispatcher] INFO: Added pangea_ai_guard to actions
2026-10-17 01:00:55,067 [nemoguardrails.actions.action_dispatcher] INFO: Added patronus_api_check_output to actions
2026-10-17 01:00:55,067 [nemoguardrails.actions.action_dispatcher] INFO: Added patronus_lynx_check_output_hallucination to actions
2026-10-17 01:00:55,068 [nemoguardrails.actions.action_dispatcher] INFO: Added call_policyai_api to actions
2026-10-17 01:00:55,069 [nemoguardrails.actions.action_dispatcher] INFO: Added detect_pii to actions
2026-10-17 01:00:55,069 [nemoguardrails.actions.action_dispatcher] INFO: Added mask_pii to actions
2026-10-17 01:00:55,069 [nemoguardrails.actions.action_dispatcher] INFO: Added protect_text to actions
2026-10-17 01:00:55,070 [nemoguardrails.actions.action_dispatcher] INFO: Added detect_regex_pattern to actions
2026-10-17 01:00:55,071 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_facts to actions
2026-10-17 01:00:55,071 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_input to actions
2026-10-17 01:00:55,072 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_output to actions
2026-10-17 01:00:55,073 [nemoguardrails.actions.action_dispatcher] INFO: Added detect_sensitive_data to actions
2026-10-17 01:00:55,073 [nemoguardrails.actions.action_dispatcher] INFO: Added mask_sensitive_data to actions
2026-10-17 01:00:55,073 [nemoguardrails.actions.action_dispatcher] INFO: Added topic_safety_check_input to actions
2026-10-17 01:00:55,075 [nemoguardrails.actions.action_dispatcher] INFO: Added trend_ai_guard to actions
2026-10-17 01:00:55,076 [nemoguardrails.actions.action_dispatcher] INFO: Added GetCurrentDateTimeAction to actions
2026-10-17 01:00:55,076 [nemoguardrails.actions.action_dispatcher] INFO: Registered Actions :: ['ClavataCheckAction', 'GetAttentionPercentageAction', 'GetCurrentDateTimeAction', 'UpdateAttentionMaterializedViewAction', 'ai_defense_inspect', 'alignscore request', 'alignscore_check_facts', 'autoalign_factcheck_output_api', 'autoalign_groundedness_output_api', 'autoalign_input_api', 'autoalign_output
2026-10-17 01:00:55,076 [nemoguardrails.actions.action_dispatcher] INFO: Action dispatcher initialized
2026-10-17 01:00:55,078 [bench.pea_eval.harmbench_eval] INFO: NeMo Guardrails 초기화 완료 (Custom HF Backend): qwen2.5:7b-instruct
2026-10-17 01:00:55,078 [bench.pea_eval.xstest] INFO: 🛡️ NeMo Guardrails 초기화 (XSTest): ['qwen2.5:7b-instruct']
2026-10-17 01:00:55,096 [bench.pea_eval.llm_client] INFO: 🔥 모델 웜업 시작: qwen2.5:7b-instruct
2026-10-17 01:00:55,325 [httpx] INFO: HTTP Request: GET http://localhost:11434/api/tags "HTTP/1.1 200 OK"
```
