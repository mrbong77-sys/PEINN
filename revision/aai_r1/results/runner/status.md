# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-19 12:12:43 (UTC 2026-10-19 03:12:43), 시도 2, 비컨 #462 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 9533032 v2.1 심사 대응 runner: 실행 중 (attempt 1)
- 현재 단계: ftv (9.2분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 7789 MiB, 32607 MiB, 97 %, 68
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: ftv
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain, ftv-check

## 마지막 로그

```
    head epoch 4 batch 1000 loss 0.2394
    head epoch 4 batch 1200 loss 0.0040
    head epoch 4 batch 1400 loss 0.0501
    head epoch 4 batch 1600 loss 0.0707
    head epoch 4 val loss 0.3056
    head epoch 5 batch 0 loss 0.0988
    head epoch 5 batch 200 loss 0.0709
    head epoch 5 batch 400 loss 0.0017
    head epoch 5 batch 600 loss 0.1630
    head epoch 5 batch 800 loss 0.0490
    head epoch 5 batch 1000 loss 0.0396
    head epoch 5 batch 1200 loss 0.0051
    head epoch 5 batch 1400 loss 0.0515
    head epoch 5 batch 1600 loss 0.0701
    head epoch 5 val loss 0.2984
{"out": "tf", "val_loss": 0.224218, "epochs": [{"epoch": 1, "val": 0.2412, "val_F_auroc": 0.9786}, {"epoch": 2, "val": 0.2242, "val_F_auroc": 0.9851}, {"epoch": 3, "val": 0.2531, "val_F_auroc": 0.9858}, {"epoch": 4, "val": 0.3056, "val_F_auroc": 0.9848}, {"epoch": 5, "val": 0.2984, "val_F_auroc": 0.9861}], "sec": 370.1, "gpu_peak_GB": 1.697}
== A2ft: fine-tuned MiniLM head, out 'softmax'
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 2909.36it/s]
    head epoch 1 batch 0 loss 1.0987
    head epoch 1 batch 200 loss 0.4241
    head epoch 1 batch 400 loss 0.1841
    head epoch 1 batch 600 loss 0.6325
    head epoch 1 batch 800 loss 0.2664
    head epoch 1 batch 1000 loss 0.2227
    head epoch 1 batch 1200 loss 0.4400
    head epoch 1 batch 1400 loss 0.1147
    head epoch 1 batch 1600 loss 0.3341
    head epoch 1 val loss 0.2511
    head epoch 2 batch 0 loss 0.1937
    head epoch 2 batch 200 loss 0.2800
    head epoch 2 batch 400 loss 0.2314
    head epoch 2 batch 600 loss 0.2520
    head epoch 2 batch 800 loss 0.0644
    head epoch 2 batch 1000 loss 0.0596
    head epoch 2 batch 1200 loss 0.0249
    head epoch 2 batch 1400 loss 0.0377
    head epoch 2 batch 1600 loss 0.1851
    head epoch 2 val loss 0.2563
    head epoch 3 batch 0 loss 0.0992
    head epoch 3 batch 200 loss 0.2553
```
