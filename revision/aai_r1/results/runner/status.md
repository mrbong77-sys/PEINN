# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 13:40:22 (UTC 2026-10-16 04:40:22), 시도 22, 비컨 #105 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: a03626f station: 임무 실행 중
- 현재 단계: thresholds (10.1분째)
- 마지막 출력 후: 0.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1563 MiB, 32607 MiB, 0 %, 39
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T042942Z-rerun rerun (대기 끝, 재시도, 2026-10-16 04:30:16 UTC)
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
A0: {"harm": 0.953, "soft": 0.953, "F": 0.5, "extreme": 5.5, "Fref": 0.95, "I": 0.25, "Fblk": 0.55} stage1 {'harm_hb': 0.9181124219292158, 'safe_hb': 0.09929577464788733, 'met': True} cost 0.0932
A1: {"harm": 2.25, "soft": 2.25, "F": 0.25, "extreme": 6.25, "Fref": 0.85, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9139486467730743, 'safe_hb': 0.09929577464788733, 'met': True} cost 0.1087
A2: {"harm": 1.5, "soft": 1.5, "F": 0.35, "extreme": 6.45, "Fref": 0.9, "I": 0.25, "Fblk": 0.6} stage1 {'harm_hb': 0.9146426092990978, 'safe_hb': 0.09894366197183098, 'met': True} cost 0.0938
A3: {"harm": 2.25, "soft": 2.25, "F": 0.35, "extreme": 5.75, "Fref": 0.95, "I": 0.7, "Fblk": 0.65} stage1 {'harm_hb': 0.9153365718251214, 'safe_hb': 0.09964788732394367, 'met': True} cost 0.1066
A5: {"Fhb": 0.5, "Fref": 0.5, "I": 0.2, "Fblk": 0.6} stage1 {'harm_hb': 0.8008327550312283, 'safe_hb': 0.09014084507042254, 'met': False} cost 0.1244
A6p: {"harm": 1.28, "soft": 1.28, "F": 0.35, "extreme": 6.25, "Fref": 0.95, "I": 0.2, "Fblk": 0.55} stage1 {'harm_hb': 0.919500346981263, 'safe_hb': 0.09964788732394367, 'met': True} cost 0.0920
A6e: {"harm": 0.75, "soft": 0.75, "F": 0.55, "extreme": 5.5, "Fref": 0.9, "I": 0.2, "Fblk": 0.7} stage1 {'harm_hb': 0.9201943095072866, 'safe_hb': 0.09718309859154929, 'met': True} cost 0.0910
A7: {"harm": 0.75, "soft": 0.75, "F": 0.15, "extreme": 8.0, "Fref": 0.95, "I": 0.2, "Fblk": 0.4} stage1 {'harm_hb': 0.9430950728660652, 'safe_hb': 0.09894366197183098, 'met': True} cost 0.0828
A0ft: {"harm": 0.75, "soft": 0.75, "F": 0.15, "extreme": 2.0, "Fref": 0.95, "I": 0.25, "Fblk": 0.65} stage1 {'harm_hb': 0.9764052741151977, 'safe_hb': 0.09753521126760563, 'met': True} cost 0.0736
```
