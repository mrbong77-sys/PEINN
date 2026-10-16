# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 09:17:30 (UTC 2026-10-16 00:17:30), 시도 6, 비컨 #58 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 094626d v21r: preview step re-scores the finished bases with the fixed gate before any more GPU work
- 현재 단계: 없음
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1630 MiB, 32607 MiB, 0 %, 45
- 다음 동작: 단계 진행
- 사유: 시작
- 마지막으로 처리한 명령: 20261016T000838Z-rerun rerun (대기 끝, 재시도, 2026-10-16 00:10:41 UTC)
- 남은 단계: preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, audit, unload-1, features, nemo, approval, nemo-doc-early, split, train, thresholds, routes, gate-diag-check, gate-diag

## 마지막 로그

```
[v21r] skip record (routing texts of the benches with a mock LLM): finished 2026-10-16 00:34:51
[v21r] skip audit (isolation audit of the v4 corpus (guard + recorded texts)): finished 2026-10-16 00:34:52
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 00:34:53
[v21r] skip features (frozen v2.1 features of the corpus and the routing texts): finished 2026-10-16 00:42:35
[v21r] skip split (embedding near-duplicates out, train / val / test split): finished 2026-10-16 09:10:47
[v21r] skip train (variants A0-A7 and the energy calibrator on the isolated corpus): finished 2026-10-16 09:12:02
[v21r] skip thresholds (thresholds of every variant on val, pushed before any answer): finished 2026-10-16 09:13:13
[v21r] skip routes (route tables of every variant and operating point): finished 2026-10-16 09:13:17
[v21r] skip nemo (NeMo Guardrails answers three probe prompts on every base): finished 2026-10-16 00:50:22
[v21r] skip approval (the professor's go for the full matrix): finished 2026-10-16 00:50:22
[v21r] skip nemo-doc-early (NeMo rail verdicts on the bases answered so far (CPU)): finished 2026-10-16 09:00:27
[v21r] skip gate-diag-check (gate diagnosis on the check cache first (pre-test, CPU)): finished 2026-10-16 09:13:17
[v21r] skip gate-diag (gate diagnosis: why the isolated gate blocks XSTest safe texts (CPU, counts only)): finished 2026-10-16 09:13:21

[v21r] ===== preview-check: the preview on the check cache first (pre-test, CPU) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r preview --check
```
