# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 14:06:32 (UTC 2026-10-16 05:06:32), 시도 23, 비컨 #109 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: f3d91bf v21r C: isolation audit of the v4 head corpus and the train/val/test split
- 현재 단계: train (7.9분째)
- 마지막 출력 후: 0.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 14523 MiB, 32607 MiB, 97 %, 70
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T044500Z-rerun rerun (대기 끝, 재시도, 2026-10-16 04:46:20 UTC)
- 남은 단계: train; thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split

## 마지막 로그

```
Consider using tensor.detach() first. (Triggered internally at C:\actions-runner\_work\pytorch\pytorch\pytorch\torch\csrc\autograd\generated\python_variable_methods.cpp:837.)
  log(f"    epoch {ep + 1} batch {i} loss {float(l_):.4f}")
    epoch 1 batch 0 loss 1.0418
    epoch 1 batch 200 loss 0.3003
    epoch 1 batch 400 loss 0.1965
    epoch 1 batch 600 loss 0.3323
    epoch 1 batch 800 loss 0.2865
    epoch 1 batch 1000 loss 0.2785
    epoch 1 batch 1200 loss 0.2144
    epoch 1 batch 1400 loss 0.1811
    epoch 1 batch 1600 loss 0.3633
    epoch 1 val 0.2332
    epoch 2 batch 0 loss 0.3617
    epoch 2 batch 200 loss 0.1950
    epoch 2 batch 400 loss 0.1224
    epoch 2 batch 600 loss 0.2744
    epoch 2 batch 800 loss 0.1740
    epoch 2 batch 1000 loss 0.2115
    epoch 2 batch 1200 loss 0.1010
    epoch 2 batch 1400 loss 0.2193
    epoch 2 batch 1600 loss 0.3615
    epoch 2 val 0.2401
    epoch 3 batch 0 loss 0.3038
    epoch 3 batch 200 loss 0.1565
    epoch 3 batch 400 loss 0.0404
    epoch 3 batch 600 loss 0.2252
    epoch 3 batch 800 loss 0.1369
    epoch 3 batch 1000 loss 0.1806
    epoch 3 batch 1200 loss 0.0253
    epoch 3 batch 1400 loss 0.1284
    epoch 3 batch 1600 loss 0.2698
    epoch 3 val 0.2293
== A0ft: PEINN with the calibrator's mpnet and the head's MiniLM fine-tuned (DESIGN.md 13)
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  38%|███▊      | 76/199 [00:00<00:00, 728.38it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1347.66it/s]
    energy epoch 1 batch 0 loss 0.2560
    energy epoch 1 batch 200 loss 0.0568
    energy epoch 1 batch 400 loss 0.0154
    energy epoch 1 batch 600 loss 0.0446
    energy epoch 1 batch 800 loss 0.0283
    energy epoch 1 batch 1000 loss 0.0558
```
