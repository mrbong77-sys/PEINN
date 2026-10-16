# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 15:21:23 (UTC 2026-10-16 06:21:23), 시도 25, 비컨 #120 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 1957272 station: 임무 실행 중
- 현재 단계: thresholds (10.1분째)
- 마지막 출력 후: 1.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1568 MiB, 32607 MiB, 0 %, 40
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T060500Z-update update (수신, 다음 단계 경계에서 적용, 2026-10-16 05:51:21 UTC)
- 남은 단계: thresholds; routes; gate-diag-check; gate-diag; preview-check; preview; gate-review; main-check; matrix-zephyr-check; zephyr-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train

## 마지막 로그

```
[v21r] skip record (routing texts of the benches with a mock LLM): finished 2026-10-16 00:34:51
[v21r] skip supp-check (supplement, audit, features, split, train, thresholds, routes on the check cache (pre-test)): finished 2026-10-16 14:50:44
[v21r] skip supplement (public over-refusal and adversarial training sets (DESIGN.md 12)): finished 2026-10-16 13:48:36
[v21r] skip audit (isolation audit of the v4 corpus (guard + recorded texts)): finished 2026-10-16 13:48:41
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 09:35:42
[v21r] skip features (frozen v2.1 features of the corpus and the routing texts): finished 2026-10-16 13:58:34
[v21r] skip split (embedding near-duplicates out, train / val / test split): finished 2026-10-16 13:58:38
[v21r] skip train (variants A0-A7 and the energy calibrator on the isolated corpus): finished 2026-10-16 15:11:08

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
A0: {"harm": 3.5, "soft": 3.5, "F": 0.2, "extreme": 5.75, "Fref": 0.95, "I": 0.2, "Fblk": 0.85} stage1 {'harm_hb': 0.9384615384615385, 'safe_hb': 0.09954508964409954, 'met': True} cost 0.0829
A1: {"harm": 3.5, "soft": 3.5, "F": 0.3, "extreme": 5.25, "Fref": 0.95, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9393162393162393, 'safe_hb': 0.09874230666309874, 'met': True} cost 0.0935
A2: {"harm": 4.0, "soft": 4.0, "F": 0.15, "extreme": 5.25, "Fref": 0.95, "I": 0.2, "Fblk": 0.35} stage1 {'harm_hb': 0.9371794871794872, 'safe_hb': 0.09927749531709927, 'met': True} cost 0.0849
A3: {"harm": 3.75, "soft": 3.75, "F": 0.2, "extreme": 5.25, "Fref": 0.95, "I": 0.85, "Fblk": 0.45} stage1 {'harm_hb': 0.9384615384615385, 'safe_hb': 0.09874230666309874, 'met': True} cost 0.0933
A5: {"Fhb": 0.45, "Fref": 0.45, "I": 0.35, "Fblk": 0.7} stage1 {'harm_hb': 0.8688034188034188, 'safe_hb': 0.09793952368209793, 'met': True} cost 0.1094
A6p: {"harm": 3.5, "soft": 3.5, "F": 0.15, "extreme": 5.75, "Fref": 0.9, "I": 0.2, "Fblk": 0.65} stage1 {'harm_hb': 0.941025641025641, 'safe_hb': 0.0982071180090982, 'met': True} cost 0.0810
```
