# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 12:18:54 (UTC 2026-10-16 03:18:54), 시도 19, 비컨 #93 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 4c653b4 v21r C: isolation audit of the v4 head corpus and the train/val/test split
- 현재 단계: train (0.7분째)
- 마지막 출력 후: 0.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 2186 MiB, 32607 MiB, 15 %, 37
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T030740Z-rerun rerun (대기 끝, 재시도, 2026-10-16 03:08:48 UTC)
- 남은 단계: train; thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split

## 마지막 로그

```
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4645.50it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  33%|███▎      | 65/199 [00:00<00:00, 648.41it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1234.18it/s]
[features] 49391 texts, 11846 to compute
[features] 500/11846 (0.3 min)
[features] 1000/11846 (0.5 min)
[features] 1500/11846 (0.8 min)
[features] 2000/11846 (1.1 min)
[features] 2500/11846 (1.4 min)
[features] 3000/11846 (1.7 min)
[features] 3500/11846 (1.9 min)
[features] 4000/11846 (2.2 min)
[features] 4500/11846 (2.5 min)
[features] 5000/11846 (2.8 min)
[features] 5500/11846 (3.1 min)
[features] 6000/11846 (3.4 min)
[features] 6500/11846 (3.7 min)
[features] 7000/11846 (4.0 min)
[features] 7500/11846 (4.2 min)
[features] 8000/11846 (4.5 min)
[features] 8500/11846 (4.8 min)
[features] 9000/11846 (5.1 min)
[features] 9500/11846 (5.4 min)
[features] 10000/11846 (5.8 min)
[features] 10500/11846 (6.1 min)
[features] 11000/11846 (6.4 min)
[features] 11500/11846 (6.6 min)
[features] 11846/11846 (6.8 min)

[v21r] ===== split: embedding near-duplicates out, train / val / test split =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r split
{"rows": 47870, "kept": 47024, "dropped": {"guard": 12, "embedding": 3, "xstest_type": 831}, "split": {"train": 38199, "test": 4415, "val": 4410}}
[git] pushed to main

[v21r] ===== train: variants A0-A7 and the energy calibrator on the isolated corpus =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r train
shipped head recipe: {"labels": "legacy", "neg_weight": 0.0, "in_dim": 800}; trained on every axis (neg_weight 1.0, DESIGN.md 4)
== energy calibrator (label F >= 0.5)
    epoch   1  val AUROC 0.8975
    epoch  10  val AUROC 0.9591
    epoch  20  val AUROC 0.9618
```
