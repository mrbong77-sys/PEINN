# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-19 12:15:28 (UTC 2026-10-19 03:15:28), 시도 1, 비컨 #463 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 514a4f9 v2.1 심사 대응 runner: 실행 중 (attempt 2)
- 현재 단계: ftv (10.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 7899 MiB, 32607 MiB, 97 %, 68
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: ftv
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain, ftv-check

## 마지막 로그

```
    head epoch 5 batch 800 loss 0.0492
    head epoch 5 batch 1000 loss 0.0396
    head epoch 5 batch 1200 loss 0.0042
    head epoch 5 batch 1400 loss 0.0514
    head epoch 5 batch 1600 loss 0.0740
    head epoch 5 val loss 0.2986
{"out": "tf", "val_loss": 0.224218, "epochs": [{"epoch": 1, "val": 0.2412, "val_F_auroc": 0.9785}, {"epoch": 2, "val": 0.2242, "val_F_auroc": 0.9851}, {"epoch": 3, "val": 0.2533, "val_F_auroc": 0.9858}, {"epoch": 4, "val": 0.3079, "val_F_auroc": 0.9847}, {"epoch": 5, "val": 0.2986, "val_F_auroc": 0.9862}], "sec": 367.2, "gpu_peak_GB": 1.697}
== A2ft: fine-tuned MiniLM head, out 'softmax'
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4259.06it/s]
    head epoch 1 batch 0 loss 1.0987
    head epoch 1 batch 200 loss 0.4241
    head epoch 1 batch 400 loss 0.1841
    head epoch 1 batch 600 loss 0.6325
    head epoch 1 batch 800 loss 0.2664
    head epoch 1 batch 1000 loss 0.2275
    head epoch 1 batch 1200 loss 0.4403
    head epoch 1 batch 1400 loss 0.1235
    head epoch 1 batch 1600 loss 0.3268
    head epoch 1 val loss 0.2516
    head epoch 2 batch 0 loss 0.1916
    head epoch 2 batch 200 loss 0.2817
    head epoch 2 batch 400 loss 0.2387
    head epoch 2 batch 600 loss 0.2596
    head epoch 2 batch 800 loss 0.0575
    head epoch 2 batch 1000 loss 0.0715
    head epoch 2 batch 1200 loss 0.0322
    head epoch 2 batch 1400 loss 0.0360
    head epoch 2 batch 1600 loss 0.1811
    head epoch 2 val loss 0.2569
    head epoch 3 batch 0 loss 0.1005
    head epoch 3 batch 200 loss 0.2652
    head epoch 3 batch 400 loss 0.1648
    head epoch 3 batch 600 loss 0.3188
    head epoch 3 batch 800 loss 0.0204
    head epoch 3 batch 1000 loss 0.0220
    head epoch 3 batch 1200 loss 0.0096
    head epoch 3 batch 1400 loss 0.0179
    head epoch 3 batch 1600 loss 0.1507
    head epoch 3 val loss 0.3420
    head epoch 4 batch 0 loss 0.0689
```
