# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 10:24:54 (UTC 2026-10-16 01:24:54), 시도 11, 비컨 #71 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 7c18c7d station: 임무 실행 중
- 현재 단계: train (8.7분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 26877 MiB, 32607 MiB, 71 %, 57
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T011422Z-rerun rerun (대기 끝, 재시도, 2026-10-16 01:14:47 UTC)
- 남은 단계: train; thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, supplement, audit, unload-1, features, split, supp-check

## 마지막 로그

```
    energy epoch 3 val AUROC 0.9784
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4182.81it/s]
    head epoch 1 batch 0 loss 1.0556
    head epoch 1 batch 200 loss 0.6862
    head epoch 1 batch 400 loss 0.2688
    head epoch 1 val loss 0.3114
    head epoch 2 batch 0 loss 0.3738
    head epoch 2 batch 200 loss 0.6827
    head epoch 2 batch 400 loss 0.2112
    head epoch 2 val loss 0.2879
    head epoch 3 batch 0 loss 0.3412
    head epoch 3 batch 200 loss 0.6228
    head epoch 3 batch 400 loss 0.2164
    head epoch 3 val loss 0.2813
== A0ftL: A0ft with the energy encoder at CPEG's size (DeBERTa-v3-large, DESIGN.md 14)
Loading weights:   0%|          | 0/390 [00:00<?, ?it/s]Loading weights: 100%|██████████| 390/390 [00:00<00:00, 4571.18it/s]
[transformers] [1mDebertaV2Model LOAD REPORT[0m from: microsoft/deberta-v3-large
Key                                     | Status     |  | 
----------------------------------------+------------+--+-
mask_predictions.dense.bias             | UNEXPECTED |  | 
lm_predictions.lm_head.LayerNorm.bias   | UNEXPECTED |  | 
lm_predictions.lm_head.bias             | UNEXPECTED |  | 
mask_predictions.classifier.weight      | UNEXPECTED |  | 
mask_predictions.LayerNorm.bias         | UNEXPECTED |  | 
mask_predictions.dense.weight           | UNEXPECTED |  | 
lm_predictions.lm_head.LayerNorm.weight | UNEXPECTED |  | 
lm_predictions.lm_head.dense.weight     | UNEXPECTED |  | 
lm_predictions.lm_head.dense.bias       | UNEXPECTED |  | 
mask_predictions.classifier.bias        | UNEXPECTED |  | 
mask_predictions.LayerNorm.weight       | UNEXPECTED |  | 

Notes:
- UNEXPECTED:	can be ignored when loading from different task/architecture; not ok if you expect identical arch.
    energy epoch 1 batch 0 loss 0.2616
    energy epoch 1 batch 200 loss 0.1549
    energy epoch 1 batch 400 loss 0.0576
    energy epoch 1 batch 600 loss 0.0279
    energy epoch 1 batch 800 loss 0.0601
    energy epoch 1 batch 1000 loss 0.0170
    energy epoch 1 batch 1200 loss 0.1190
```
