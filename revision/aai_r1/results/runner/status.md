# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-19 12:22:48 (UTC 2026-10-19 03:22:48), 시도 2, 비컨 #463 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 0fd92b5 v2.1 심사 대응 runner: 실행 중 (attempt 1)
- 현재 단계: ftv (19.3분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 7811 MiB, 32607 MiB, 97 %, 68
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: ftv
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain, ftv-check

## 마지막 로그

```
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
    head epoch 3 batch 800 loss 0.0626
    head epoch 3 batch 1000 loss 0.0166
    head epoch 3 batch 1200 loss 0.0136
    head epoch 3 batch 1400 loss 0.0288
    head epoch 3 batch 1600 loss 0.0195
    head epoch 3 val loss 0.2723
    head epoch 4 batch 0 loss 0.1660
    head epoch 4 batch 200 loss 0.2091
    head epoch 4 batch 400 loss 0.0406
    head epoch 4 batch 600 loss 0.0064
    head epoch 4 batch 800 loss 0.0018
    head epoch 4 batch 1000 loss 0.1526
    head epoch 4 batch 1200 loss 0.0020
    head epoch 4 batch 1400 loss 0.0016
    head epoch 4 batch 1600 loss 0.0673
    head epoch 4 val loss 0.3394
    head epoch 5 batch 0 loss 0.0471
    head epoch 5 batch 200 loss 0.0027
    head epoch 5 batch 400 loss 0.0052
    head epoch 5 batch 600 loss 0.0013
    head epoch 5 batch 800 loss 0.0015
    head epoch 5 batch 1000 loss 0.0009
    head epoch 5 batch 1200 loss 0.0022
```
