# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 13:56:26 (UTC 2026-10-16 04:56:26), 시도 23, 비컨 #108 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: d22ee23 v21r S: public over-refusal and adversarial training sets added to the corpus (counts)
- 현재 단계: features (7.7분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 2847 MiB, 32607 MiB, 15 %, 37
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T044500Z-rerun rerun (대기 끝, 재시도, 2026-10-16 04:46:20 UTC)
- 남은 단계: features; split; train; thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit

## 마지막 로그

```
{"bench_files": {"harmbench_behaviors_text_all.csv": true, "xstest_prompts.csv": true, "morables_benchmark/morables_sample.jsonl": true, "ggb_benchmark/ous_items.json": true, "ethics_benchmark/dilemmas.json": true, "ethics_benchmark/mfq.json": true, "ethics_benchmark/wvs.json": true, "taxonomy_40_scenarios.json": true, "delphi_behaviors.csv": true, "mach_items.json": true, "unesco_items.csv": true
audit: 65891 corpus rows -> D:\Projects\PEINN\revision\aai_r1\cache\full\audit.jsonl
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 09:35:42

[v21r] ===== features: frozen v2.1 features of the corpus and the routing texts =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r features
features for 67369 texts
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peinn_side.py features --texts D:\Projects\PEINN\revision\aai_r1\cache\full\feature_texts.json --out D:\Projects\PEINN\revision\aai_r1\cache\full\features.npz  (cwd D:\Projects\PEINN\src)
No sentence-transformers model found with name sentence-transformers/all-MiniLM-L6-v2. Creating a new one with mean pooling.
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4711.31it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  25%|██▍       | 49/199 [00:00<00:00, 475.12it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1321.53it/s]
[features] 67369 texts, 17978 to compute
[features] 500/17978 (0.3 min)
[features] 1000/17978 (0.5 min)
[features] 1500/17978 (0.8 min)
[features] 2000/17978 (1.1 min)
[features] 2500/17978 (1.3 min)
[features] 3000/17978 (1.6 min)
[features] 3500/17978 (1.9 min)
[features] 4000/17978 (2.1 min)
[features] 4500/17978 (2.4 min)
[features] 5000/17978 (2.7 min)
[features] 5500/17978 (2.9 min)
[features] 6000/17978 (3.2 min)
[features] 6500/17978 (3.5 min)
[features] 7000/17978 (3.8 min)
[features] 7500/17978 (4.1 min)
[features] 8000/17978 (4.3 min)
[features] 8500/17978 (4.6 min)
[features] 9000/17978 (4.8 min)
[features] 9500/17978 (5.1 min)
[features] 10000/17978 (5.4 min)
[features] 10500/17978 (5.6 min)
[features] 11000/17978 (5.9 min)
[features] 11500/17978 (6.2 min)
[features] 12000/17978 (6.5 min)
[features] 12500/17978 (6.7 min)
[features] 13000/17978 (7.0 min)
[features] 13500/17978 (7.3 min)
[features] 14000/17978 (7.6 min)
```
