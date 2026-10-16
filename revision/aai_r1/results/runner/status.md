# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 11:42:14 (UTC 2026-10-16 02:42:14), 시도 17, 비컨 #87 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 94de278 v21r G: AUROC of E and F per test-split pair, XSTest block conditions per operating point (error analysis)
- 현재 단계: 없음
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1586 MiB, 32607 MiB, 1 %, 45
- 다음 동작: 단계 진행
- 사유: 시작
- 마지막으로 처리한 명령: 20261016T024105Z-rerun rerun (대기 끝, 재시도, 2026-10-16 02:42:13 UTC)
- 남은 단계: gate-diag-check; gate-diag; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split, train, thresholds, routes, dev-guard-check, dev-guard, preview-check, preview

## 마지막 로그

```
[v21r] skip record (routing texts of the benches with a mock LLM): finished 2026-10-16 00:34:51
[v21r] skip supp-check (supplement, audit, features, split, train, thresholds, routes on the check cache (pre-test)): finished 2026-10-16 11:15:10
[v21r] skip supplement (public over-refusal and adversarial training sets (DESIGN.md 12)): finished 2026-10-16 11:16:00
[v21r] skip audit (isolation audit of the v4 corpus (guard + recorded texts)): finished 2026-10-16 11:16:03
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 09:35:42
[v21r] skip features (frozen v2.1 features of the corpus and the routing texts): finished 2026-10-16 11:20:29
[v21r] skip split (embedding near-duplicates out, train / val / test split): finished 2026-10-16 11:20:33
[v21r] skip train (variants A0-A7 and the energy calibrator on the isolated corpus): finished 2026-10-16 11:30:13
[v21r] skip thresholds (thresholds of every variant on val, pushed before any answer): finished 2026-10-16 11:36:11
[v21r] skip routes (route tables of every variant and operating point): finished 2026-10-16 11:36:15
[v21r] skip nemo (NeMo Guardrails answers three probe prompts on every base): finished 2026-10-16 00:50:22
[v21r] skip approval (the professor's go for the full matrix): finished 2026-10-16 00:50:22
[v21r] skip nemo-doc-early (NeMo rail verdicts on the bases answered so far (CPU)): finished 2026-10-16 09:00:27
[v21r] skip dev-guard-check (Llama Guard input verdicts on 40 check rows (pre-test)): finished 2026-10-16 11:36:15
[v21r] skip dev-guard (Llama Guard input verdicts on the corpus test split (dev reference, DESIGN.md 14)): finished 2026-10-16 11:37:36

[v21r] ===== gate-diag-check: gate diagnosis on the check cache first (pre-test, CPU) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r gate-diag --check
```
