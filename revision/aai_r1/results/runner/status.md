# v2.1 심사 대응 무인 실행 상태: 완료

- 시각 2026-10-19 12:27:06 (UTC 2026-10-19 03:27:06), 시도 1, 비컨 #465 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 4c12ce3 v21r ftv: A1-A3 with the fine-tuned encoders, thresholds and routes (DESIGN.md 42)
- 현재 단계: ftv (21.7분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 4786 MiB, 32607 MiB, 0 %, 43
- 다음 동작: 없음(모든 단계 끝)
- 사유: –
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: 없음
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain, ftv-check, ftv

## 마지막 로그

```
    head epoch 2 batch 600 loss 0.1259
    head epoch 2 batch 800 loss 0.0970
    head epoch 2 batch 1000 loss 0.1220
    head epoch 2 batch 1200 loss 0.1505
    head epoch 2 batch 1400 loss 0.1359
    head epoch 2 batch 1600 loss 0.1462
    head epoch 2 val loss 0.2242
    head epoch 3 batch 0 loss 0.1990
    head epoch 3 batch 200 loss 0.1730
    head epoch 3 batch 400 loss 0.1059
    head epoch 3 batch 600 loss 0.1732
    head epoch 3 batch 800 loss 0.0850
    head epoch 3 batch 1000 loss 0.0511
    head epoch 3 batch 1200 loss 0.0560
    head epoch 3 batch 1400 loss 0.0563
    head epoch 3 batch 1600 loss 0.2148
    head epoch 3 val loss 0.2533
    head epoch 4 batch 0 loss 0.1382
    head epoch 4 batch 200 loss 0.1065
    head epoch 4 batch 400 loss 0.0028
    head epoch 4 batch 600 loss 0.1092
    head epoch 4 batch 800 loss 0.0574
    head epoch 4 batch 1000 loss 0.2243
    head epoch 4 batch 1200 loss 0.0037
    head epoch 4 batch 1400 loss 0.0500
    head epoch 4 batch 1600 loss 0.0710
    head epoch 4 val loss 0.3079
    head epoch 5 batch 0 loss 0.1015
    head epoch 5 batch 200 loss 0.0776
    head epoch 5 batch 400 loss 0.0018
    head epoch 5 batch 600 loss 0.1602
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
    head epoch 4 batch 200 loss 0.2163
    head epoch 4 batch 400 loss 0.0181
    head epoch 4 batch 600 loss 0.0821
    head epoch 4 batch 800 loss 0.0070
    head epoch 4 batch 1000 loss 0.0502
    head epoch 4 batch 1200 loss 0.0090
    head epoch 4 batch 1400 loss 0.0008
    head epoch 4 batch 1600 loss 0.0548
    head epoch 4 val loss 0.3734
    head epoch 5 batch 0 loss 0.0309
    head epoch 5 batch 200 loss 0.0720
    head epoch 5 batch 400 loss 0.0062
    head epoch 5 batch 600 loss 0.0605
    head epoch 5 batch 800 loss 0.0025
    head epoch 5 batch 1000 loss 0.0034
    head epoch 5 batch 1200 loss 0.0017
    head epoch 5 batch 1400 loss 0.0006
    head epoch 5 batch 1600 loss 0.0781
    head epoch 5 val loss 0.3792
{"out": "softmax", "val_loss": 0.251635, "epochs": [{"epoch": 1, "val": 0.2516, "val_F_auroc": 0.9784}, {"epoch": 2, "val": 0.2569, "val_F_auroc": 0.9845}, {"epoch": 3, "val": 0.342, "val_F_auroc": 0.9853}, {"epoch": 4, "val": 0.3734, "val_F_auroc": 0.9857}, {"epoch": 5, "val": 0.3792, "val_F_auroc": 0.9859}], "sec": 363.2, "gpu_peak_GB": 1.787}
== A3ft: fine-tuned MiniLM head, out 'binary'
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4197.48it/s]
    head epoch 1 batch 0 loss 0.6909
    head epoch 1 batch 200 loss 0.3609
    head epoch 1 batch 400 loss 0.2071
    head epoch 1 batch 600 loss 0.3675
    head epoch 1 batch 800 loss 0.3209
    head epoch 1 batch 1000 loss 0.1520
    head epoch 1 batch 1200 loss 0.2834
    head epoch 1 batch 1400 loss 0.1822
    head epoch 1 batch 1600 loss 0.3571
    head epoch 1 val loss 0.2326
    head epoch 2 batch 0 loss 0.2431
    head epoch 2 batch 200 loss 0.1575
    head epoch 2 batch 400 loss 0.1712
    head epoch 2 batch 600 loss 0.1016
    head epoch 2 batch 800 loss 0.0430
    head epoch 2 batch 1000 loss 0.0795
    head epoch 2 batch 1200 loss 0.0313
    head epoch 2 batch 1400 loss 0.1136
    head epoch 2 batch 1600 loss 0.1613
    head epoch 2 val loss 0.2235
    head epoch 3 batch 0 loss 0.1285
    head epoch 3 batch 200 loss 0.0585
    head epoch 3 batch 400 loss 0.0066
    head epoch 3 batch 600 loss 0.0930
    head epoch 3 batch 800 loss 0.0624
    head epoch 3 batch 1000 loss 0.0165
    head epoch 3 batch 1200 loss 0.0134
    head epoch 3 batch 1400 loss 0.0294
    head epoch 3 batch 1600 loss 0.0194
    head epoch 3 val loss 0.2718
    head epoch 4 batch 0 loss 0.1638
    head epoch 4 batch 200 loss 0.2140
    head epoch 4 batch 400 loss 0.0421
    head epoch 4 batch 600 loss 0.0066
    head epoch 4 batch 800 loss 0.0023
    head epoch 4 batch 1000 loss 0.1695
    head epoch 4 batch 1200 loss 0.0024
    head epoch 4 batch 1400 loss 0.0020
    head epoch 4 batch 1600 loss 0.0722
    head epoch 4 val loss 0.3439
    head epoch 5 batch 0 loss 0.0464
    head epoch 5 batch 200 loss 0.0026
    head epoch 5 batch 400 loss 0.0066
    head epoch 5 batch 600 loss 0.0011
    head epoch 5 batch 800 loss 0.0017
    head epoch 5 batch 1000 loss 0.0009
    head epoch 5 batch 1200 loss 0.0023
    head epoch 5 batch 1400 loss 0.0002
    head epoch 5 batch 1600 loss 0.0007
    head epoch 5 val loss 0.3580
{"out": "binary", "val_loss": 0.22345, "epochs": [{"epoch": 1, "val": 0.2326, "val_F_auroc": 0.9785}, {"epoch": 2, "val": 0.2235, "val_F_auroc": 0.985}, {"epoch": 3, "val": 0.2718, "val_F_auroc": 0.9858}, {"epoch": 4, "val": 0.3439, "val_F_auroc": 0.986}, {"epoch": 5, "val": 0.358, "val_F_auroc": 0.9866}], "sec": 347.4, "gpu_peak_GB": 1.787}
A1ft@0.03: {"harm": 1.5, "soft": 1.5, "F": 0.95, "extreme": 6.25, "Fref": 0.95, "I": 2.0, "Fblk": 1.0}
A2ft@0.03: {"harm": 1.25, "soft": 1.25, "F": 0.9, "extreme": 6.25, "Fref": 0.95, "I": 0.2, "Fblk": 0.05}
A3ft@0.03: {"harm": 2.941, "soft": 2.941, "F": 0.95, "extreme": 6.25, "Fref": 0.95, "I": 0.4, "Fblk": 0.25}
[git] pushed to main

[v21r] all steps finished and pushed in 21.7 min
```
