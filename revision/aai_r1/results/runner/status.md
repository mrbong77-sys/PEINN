# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-17 00:50:50 (UTC 2026-10-16 15:50:50), 시도 36, 비컨 #194 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: fef044c station: 임무 실행 중
- 현재 단계: matrix-zephyr-check2 (13.4분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 25869 MiB, 32607 MiB, 99 %, 65
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T151800Z-rerun rerun (자식 종료 후 재실행, 2026-10-16 15:15:14 UTC)
- 남은 단계: matrix-zephyr-check2; zephyr-review; nemo-fair-review-zephyr; nemo-reset; matrix; nemo-doc; nemo-orr-all; nemo-audit-all; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint

## 마지막 로그

```
2026-10-17 00:50:27,117 [nemoguardrails.actions.action_dispatcher] INFO: Added detect_pii to actions
2026-10-17 00:50:27,117 [nemoguardrails.actions.action_dispatcher] INFO: Added mask_pii to actions
2026-10-17 00:50:27,118 [nemoguardrails.actions.action_dispatcher] INFO: Added protect_text to actions
2026-10-17 00:50:27,118 [nemoguardrails.actions.action_dispatcher] INFO: Added detect_regex_pattern to actions
2026-10-17 00:50:27,119 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_facts to actions
2026-10-17 00:50:27,120 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_input to actions
2026-10-17 00:50:27,120 [nemoguardrails.actions.action_dispatcher] INFO: Added self_check_output to actions
2026-10-17 00:50:27,121 [nemoguardrails.actions.action_dispatcher] INFO: Added detect_sensitive_data to actions
2026-10-17 00:50:27,121 [nemoguardrails.actions.action_dispatcher] INFO: Added mask_sensitive_data to actions
2026-10-17 00:50:27,122 [nemoguardrails.actions.action_dispatcher] INFO: Added topic_safety_check_input to actions
2026-10-17 00:50:27,123 [nemoguardrails.actions.action_dispatcher] INFO: Added trend_ai_guard to actions
2026-10-17 00:50:27,124 [nemoguardrails.actions.action_dispatcher] INFO: Added GetCurrentDateTimeAction to actions
2026-10-17 00:50:27,125 [nemoguardrails.actions.action_dispatcher] INFO: Registered Actions :: ['ClavataCheckAction', 'GetAttentionPercentageAction', 'GetCurrentDateTimeAction', 'UpdateAttentionMaterializedViewAction', 'ai_defense_inspect', 'alignscore request', 'alignscore_check_facts', 'autoalign_factcheck_output_api', 'autoalign_groundedness_output_api', 'autoalign_input_api', 'autoalign_output
2026-10-17 00:50:27,125 [nemoguardrails.actions.action_dispatcher] INFO: Action dispatcher initialized
2026-10-17 00:50:27,127 [bench.pea_eval.harmbench_eval] INFO: NeMo Guardrails 초기화 완료 (Custom HF Backend): zephyr:7b
2026-10-17 00:50:27,127 [bench.pea_eval.xstest] INFO: 🛡️ NeMo Guardrails 초기화 (XSTest): ['zephyr:7b']
2026-10-17 00:50:27,128 [bench.pea_eval.xstest] INFO: 
─── [H01] Vanilla | zephyr:7b ───
2026-10-17 00:50:27,128 [bench.pea_eval.xstest] INFO:   GPU-aware Concurrency: 8 (model=zephyr:7b, nemo=False)
2026-10-17 00:50:27,128 [bench.pea_eval.xstest] INFO:   [H01] 🚀 시작 (총 45건, 동시성 8) — 첫 응답까지 Ollama 큐 대기 시간 있음
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 1/45 완료 (arm 2% · 전체 0% · 921.83 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 5/45 완료 (arm 11% · 전체 2% · 4414.13 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 10/45 완료 (arm 22% · 전체 5% · 8593.12 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 15/45 완료 (arm 33% · 전체 8% · 12436.17 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 20/45 완료 (arm 44% · 전체 11% · 16294.89 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 25/45 완료 (arm 55% · 전체 13% · 20037.76 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 30/45 완료 (arm 66% · 전체 16% · 23647.65 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 35/45 완료 (arm 77% · 전체 19% · 27180.27 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 40/45 완료 (arm 88% · 전체 22% · 30609.77 req/s · arm ETA 0s)
2026-10-17 00:50:27,129 [bench.pea_eval.xstest] INFO:   [H01] 45/45 완료 (arm 100% · 전체 25% · 33934.50 req/s · arm ETA 0s)
[vram] before qwen3:32b: unloaded ['zephyr:7b']
2026-10-17 00:50:27,155 [bench.pea_eval.llm_client] INFO: 🔥 모델 웜업 시작: qwen3:32b
2026-10-17 00:50:27,389 [httpx] INFO: HTTP Request: GET http://localhost:11434/api/tags "HTTP/1.1 200 OK"
2026-10-17 00:50:32,771 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/generate "HTTP/1.1 200 OK"
2026-10-17 00:50:32,772 [bench.pea_eval.llm_client] INFO: 🔥 Ollama 모델 웜업 완료: qwen3:32b
2026-10-17 00:50:32,772 [bench.pea_eval.xstest] INFO: [H01] 🔍 XSTest verdict 채점 시작 (45건)
2026-10-17 00:50:32,773 [bench.pea_eval.llm_client] INFO: Ollama 클라이언트 초기화 (override): 모델=qwen3:32b
2026-10-17 00:50:42,256 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 00:50:46,768 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 00:50:49,860 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
```
