# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 13:16:04 (UTC 2026-10-16 04:16:04), 시도 21, 비컨 #101 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 462ab84 v21r Θ: finer curve points 0.015, 0.025, 0.035 (DESIGN.md 21)
- 현재 단계: 없음
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1586 MiB, 32607 MiB, 2 %, 43
- 다음 동작: 단계 진행
- 사유: 시작
- 마지막으로 처리한 명령: 20261016T041600Z-rerun rerun (대기 끝, 재시도, 2026-10-16 04:16:03 UTC)
- 남은 단계: thresholds; routes; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train

## 마지막 로그

```
[v21r] skip record (routing texts of the benches with a mock LLM): finished 2026-10-16 00:34:51
[v21r] skip supp-check (supplement, audit, features, split, train, thresholds, routes on the check cache (pre-test)): finished 2026-10-16 12:48:14
[v21r] skip supplement (public over-refusal and adversarial training sets (DESIGN.md 12)): finished 2026-10-16 12:11:02
[v21r] skip audit (isolation audit of the v4 corpus (guard + recorded texts)): finished 2026-10-16 12:11:06
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 09:35:42
[v21r] skip features (frozen v2.1 features of the corpus and the routing texts): finished 2026-10-16 12:18:07
[v21r] skip split (embedding near-duplicates out, train / val / test split): finished 2026-10-16 12:18:11
[v21r] skip train (variants A0-A7 and the energy calibrator on the isolated corpus): finished 2026-10-16 13:04:19

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
```
