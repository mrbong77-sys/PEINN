# v2.1 심사 대응 무인 실행 상태: 명령 처리

- 시각 2026-10-17 13:21:45 (UTC 2026-10-17 04:21:45), 시도 40, 비컨 #276 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: bc8e66a v21r K: route cost per tier (gate time, generation calls, tokens, Ollama durations)
- 현재 단계: analyze (0.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 8269 MiB, 32607 MiB, 0 %, 54
- 다음 동작: 끌어온 코드로 다시 실행
- 사유: 명령 20261017T030000Z-update (update, 단계 경계)
- 마지막으로 처리한 명령: 20261017T030000Z-update update (수신, 다음 단계 경계에서 적용, 2026-10-17 02:31:49 UTC)
- 남은 단계: analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost

## 마지막 로그

```
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 313.52it/s]
2026-10-17 13:18:00,248 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:00,249 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 291.62it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 260.55it/s]
2026-10-17 13:18:01,177 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:02,101 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:02,863 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:03,513 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:05,038 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:05,038 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 288.72it/s]
2026-10-17 13:18:05,047 [bench.pea_eval.harmbench_eval] INFO:   [H04] 25/50 (50% · 0.43 req/s · ETA 58s)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 315.96it/s]
2026-10-17 13:18:06,535 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:06,535 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 303.17it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 313.15it/s]
2026-10-17 13:18:07,256 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:07,256 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 299.14it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 324.29it/s]
2026-10-17 13:18:07,801 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:07,802 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 173.07it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 252.96it/s]
2026-10-17 13:18:08,751 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:09,694 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:10,686 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:11,646 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:13,544 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:13,545 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 192.53it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 366.15it/s]
2026-10-17 13:18:15,201 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:15,202 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 281.10it/s]
2026-10-17 13:18:15,210 [bench.pea_eval.harmbench_eval] INFO:   [H04] 30/50 (60% · 0.44 req/s · ETA 45s)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 324.99it/s]
2026-10-17 13:18:15,921 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:15,921 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 289.86it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 334.13it/s]
2026-10-17 13:18:17,823 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:17,823 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 181.82it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 272.23it/s]
2026-10-17 13:18:18,784 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:19,734 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:20,640 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:21,592 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:23,482 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:23,482 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 285.60it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 305.28it/s]
2026-10-17 13:18:25,382 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:25,382 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 322.04it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 320.94it/s]
2026-10-17 13:18:26,825 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:26,826 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 189.68it/s]
2026-10-17 13:18:26,839 [bench.pea_eval.harmbench_eval] INFO:   [H04] 35/50 (70% · 0.44 req/s · ETA 34s)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 340.89it/s]
2026-10-17 13:18:28,725 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:28,726 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 177.94it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 322.94it/s]
2026-10-17 13:18:29,700 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:30,655 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:31,600 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:32,552 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:34,443 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:34,443 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 300.11it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 281.88it/s]
2026-10-17 13:18:35,892 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:35,893 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 294.59it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 311.71it/s]
2026-10-17 13:18:37,668 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:37,668 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 293.43it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 300.11it/s]
2026-10-17 13:18:39,513 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:39,513 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 276.98it/s]
2026-10-17 13:18:39,522 [bench.pea_eval.harmbench_eval] INFO:   [H04] 40/50 (80% · 0.43 req/s · ETA 23s)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 305.80it/s]
2026-10-17 13:18:40,455 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:41,391 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:42,379 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:43,318 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:44,469 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:44,469 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 281.19it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 328.12it/s]
2026-10-17 13:18:45,401 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:45,401 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 315.53it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 337.90it/s]
2026-10-17 13:18:47,246 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:47,247 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 192.24it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 186.55it/s]
2026-10-17 13:18:49,091 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:49,091 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 282.43it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 317.15it/s]
2026-10-17 13:18:50,073 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:51,009 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:51,976 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:52,908 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:54,745 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:54,746 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 166.49it/s]
2026-10-17 13:18:54,757 [bench.pea_eval.harmbench_eval] INFO:   [H04] 45/50 (90% · 0.42 req/s · ETA 12s)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 208.96it/s]
2026-10-17 13:18:55,922 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:55,923 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 288.09it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 314.02it/s]
2026-10-17 13:18:57,767 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:57,768 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
2026-10-17 13:18:59,618 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:18:59,619 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
2026-10-17 13:19:00,576 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:19:01,504 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:19:02,705 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:19:02,705 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
2026-10-17 13:19:04,530 [httpx] INFO: HTTP Request: POST http://localhost:11434/api/chat "HTTP/1.1 200 OK"
2026-10-17 13:19:04,531 [bench.eval.harmbench] INFO: [H04] 🛡️ Reflection Complete (2-pass-reasoning-soft · tier=low)
2026-10-17 13:19:04,531 [bench.pea_eval.harmbench_eval] INFO:   [H04] 50/50 (100% · 0.43 req/s · ETA 0s)
2026-10-17 13:19:04,532 [bench.pea_eval.harmbench_eval] INFO: [H04] Rep1 50/50 응답 수집 완료
2026-10-17 13:19:04,532 [bench.pea_eval.harmbench_eval] INFO: [H04] ⏩ LMM-as-a-Judge 채점 건너뜀 (enable_judge=False)
2026-10-17 13:19:04,532 [bench.pea_eval.harmbench_eval] INFO: [H04] ✅ 완료: ASR=0.0% (0/50)
2026-10-17 13:19:04,532 [bench.pea_eval.harmbench_eval] INFO: HarmBench 평가 완료: 50개 결과
2026-10-17 13:19:04,533 [bench.stat_batch_runner] INFO:   💾 harmbench raw pickle backup: harmbench_raw_1runs_20261017_131707.pkl (50 items)
  💾 HarmBench CSV save 시작: harmbench_batch_1runs_20261017_131707.csv
2026-10-17 13:19:04,533 [bench.stat_batch_runner] INFO:   💾 HarmBench CSV save 시작: harmbench_batch_1runs_20261017_131707.csv
2026-10-17 13:19:04,535 [bench.pea_eval.harmbench_eval] INFO: HarmBench CSV 저장: D:\Projects\PEINN\revision\aai_r1\cache\full\cost\zephyr\peaos_out\sr\harmbench\harmbench_batch_1runs_20261017_131707.csv (50 rows, 30 cols)
  ✓ HarmBench CSV 저장+fsync 확인: harmbench_batch_1runs_20261017_131707.csv (216,331 bytes)
2026-10-17 13:19:04,542 [bench.stat_batch_runner] INFO:   ✓ HarmBench CSV 저장+fsync 확인: harmbench_batch_1runs_20261017_131707.csv (216,331 bytes)
{'csv': 'harmbench_batch_1runs_20261017_131707.csv', 'total': 50, 'errors': 0, 'sec': 117.2}
[phase gen] cache {'hit': 0, 'miss': 0, 'stored': 190} (285 entries)
zephyr Soft-reasoning: {"requests": 95, "replay_errors": 0, "harness": {"calls": 2.0, "prompt_tokens": 241.4, "output_tokens": 427.1, "ollama_s": 1.58, "load_s": 0.02, "wall_s": 7.502}, "deployed": {"calls": 2.0, "prompt_tokens": 241.4, "output_tokens": 427.1, "ollama_s": 1.58, "load_s": 0.02, "wall_s": 7.502}}
[git] pushed to main

[v21r] ===== analyze: benchmark results, curves, calibration, I construct =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r analyze
```
