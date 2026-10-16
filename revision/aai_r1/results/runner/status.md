# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 13:26:09 (UTC 2026-10-16 04:26:09), 시도 21, 비컨 #102 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: ecef267 station: 임무 실행 중
- 현재 단계: thresholds (10.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1563 MiB, 32607 MiB, 0 %, 41
- 다음 동작: 단계 진행
- 사유: 정기 보고
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
A0: {"harm": 1.28, "soft": 1.28, "F": 0.5, "extreme": 5.373, "Fref": 0.95, "I": 0.25, "Fblk": 0.55} stage1 {'harm_hb': 0.916030534351145, 'safe_hb': 0.09929577464788733, 'met': True} cost 0.0938
A1: {"harm": 2.445, "soft": 2.445, "F": 0.3, "extreme": 5.373, "Fref": 0.95, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9118667591950035, 'safe_hb': 0.09964788732394367, 'met': True} cost 0.1096
A2: {"harm": 2.445, "soft": 2.445, "F": 0.35, "extreme": 5.373, "Fref": 0.85, "I": 0.2, "Fblk": 0.6} stage1 {'harm_hb': 0.9118667591950035, 'safe_hb': 0.0982394366197183, 'met': True} cost 0.0944
A3: {"harm": 1.28, "soft": 1.28, "F": 0.55, "extreme": 5.373, "Fref": 0.95, "I": 0.2, "Fblk": 0.05} stage1 {'harm_hb': 0.9125607217210271, 'safe_hb': 0.09894366197183098, 'met': True} cost 0.1098
A5: {"Fhb": 0.5, "Fref": 0.5, "I": 0.2, "Fblk": 0.6} stage1 {'harm_hb': 0.8008327550312283, 'safe_hb': 0.09014084507042254, 'met': False} cost 0.1244
A6p: {"harm": 1.28, "soft": 1.28, "F": 0.35, "extreme": 6.45, "Fref": 0.95, "I": 0.2, "Fblk": 0.55} stage1 {'harm_hb': 0.9188063844552394, 'safe_hb': 0.09859154929577464, 'met': True} cost 0.0917
A6e: {"harm": 0.501, "soft": 0.501, "F": 0.6, "extreme": 5.373, "Fref": 0.85, "I": 0.2, "Fblk": 0.7} stage1 {'harm_hb': 0.9174184594031922, 'safe_hb': 0.09718309859154929, 'met': True} cost 0.0921
A7: {"harm": 0.735, "soft": 0.735, "F": 0.2, "extreme": 7.099, "Fref": 0.95, "I": 0.2, "Fblk": 0.4} stage1 {'harm_hb': 0.9424011103400416, 'safe_hb': 0.09964788732394367, 'met': True} cost 0.0841
A0ft: {"harm": 0.823, "soft": 0.823, "F": 0.3, "extreme": 1.489, "Fref": 0.95, "I": 0.3, "Fblk": 0.65} stage1 {'harm_hb': 0.9757113115891742, 'safe_hb': 0.09859154929577464, 'met': True} cost 0.0757
```
