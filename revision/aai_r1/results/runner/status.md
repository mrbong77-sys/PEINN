# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 11:23:50 (UTC 2026-10-16 02:23:50), 시도 16, 비컨 #84 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: d238903 v21r C: isolation audit of the v4 head corpus and the train/val/test split
- 현재 단계: train (3.3분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 4382 MiB, 32607 MiB, 91 %, 56
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T021319Z-rerun rerun (대기 끝, 재시도, 2026-10-16 02:13:44 UTC)
- 남은 단계: train; thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split

## 마지막 로그

```
    epoch  40  val 0.4222
    epoch  50  val 0.4269
    epoch  60  val 0.4448
== A2: softmax safe / ambiguous / harmful
    epoch   1  val 0.4692
    epoch  10  val 0.3795
    epoch  20  val 0.4206
    epoch  30  val 0.4663
    epoch  40  val 0.5330
    epoch  50  val 0.5753
    epoch  60  val 0.5559
== A3: binary harm classifier (F >= 0.5)
    epoch   1  val 0.4111
    epoch  10  val 0.3290
    epoch  20  val 0.3753
    epoch  30  val 0.4382
    epoch  40  val 0.4407
    epoch  50  val 0.5045
    epoch  60  val 0.5409
== A7: fine-tuned MiniLM (T/I/F, same loss)
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 5106.12it/s]
D:\Projects\PEINN\revision\aai_r1\v21r\models.py:282: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
Consider using tensor.detach() first. (Triggered internally at C:\actions-runner\_work\pytorch\pytorch\pytorch\torch\csrc\autograd\generated\python_variable_methods.cpp:837.)
  log(f"    epoch {ep + 1} batch {i} loss {float(l_):.4f}")
    epoch 1 batch 0 loss 1.0361
    epoch 1 batch 200 loss 0.4074
    epoch 1 batch 400 loss 0.3159
    epoch 1 batch 600 loss 0.2307
    epoch 1 batch 800 loss 0.3372
    epoch 1 val 0.2735
    epoch 2 batch 0 loss 0.2933
    epoch 2 batch 200 loss 0.3149
    epoch 2 batch 400 loss 0.2872
    epoch 2 batch 600 loss 0.1667
    epoch 2 batch 800 loss 0.3404
    epoch 2 val 0.2609
    epoch 3 batch 0 loss 0.2628
    epoch 3 batch 200 loss 0.2902
    epoch 3 batch 400 loss 0.2451
    epoch 3 batch 600 loss 0.1487
```
