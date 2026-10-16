# v2.1 심사 대응 무인 실행 상태: 명령 처리

- 시각 2026-10-16 15:11:14 (UTC 2026-10-16 06:11:14), 시도 25, 비컨 #118 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 3be4d45 v21r T: variants A0-A7 trained on the isolated corpus (seed 42)
- 현재 단계: thresholds (0.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1568 MiB, 32607 MiB, 0 %, 44
- 다음 동작: 끌어온 코드로 다시 실행
- 사유: 명령 20261016T060500Z-update (update, 단계 경계)
- 마지막으로 처리한 명령: 20261016T060500Z-update update (수신, 다음 단계 경계에서 적용, 2026-10-16 05:51:21 UTC)
- 남은 단계: thresholds; routes; gate-diag-check; gate-diag; preview-check; preview; gate-review; main-check; matrix-zephyr-check; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train

## 마지막 로그

```
    epoch  50  val 0.3141
    epoch  60  val 0.3323
== A1: T/F head (no I)
    epoch   1  val 0.4027
    epoch  10  val 0.3247
    epoch  20  val 0.3316
    epoch  30  val 0.3494
    epoch  40  val 0.3545
    epoch  50  val 0.3658
    epoch  60  val 0.3761
== A2: softmax safe / ambiguous / harmful
    epoch   1  val 0.4558
    epoch  10  val 0.3554
    epoch  20  val 0.3874
    epoch  30  val 0.4176
    epoch  40  val 0.4193
    epoch  50  val 0.4499
    epoch  60  val 0.4400
== A3: binary harm classifier (F >= 0.5)
    epoch   1  val 0.4089
    epoch  10  val 0.3126
    epoch  20  val 0.3330
    epoch  30  val 0.3632
    epoch  40  val 0.3587
    epoch  50  val 0.3804
    epoch  60  val 0.3862
== A7: fine-tuned MiniLM (T/I/F, same loss)
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 5441.52it/s]
D:\Projects\PEINN\revision\aai_r1\v21r\models.py:282: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
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
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  34%|███▎      | 67/199 [00:00<00:00, 661.83it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1305.44it/s]
    energy epoch 1 batch 0 loss 0.2560
    energy epoch 1 batch 200 loss 0.0568
    energy epoch 1 batch 400 loss 0.0154
    energy epoch 1 batch 600 loss 0.0446
    energy epoch 1 batch 800 loss 0.0283
    energy epoch 1 batch 1000 loss 0.0558
    energy epoch 1 batch 1200 loss 0.0661
    energy epoch 1 batch 1400 loss 0.0253
    energy epoch 1 batch 1600 loss 0.0927
    energy epoch 1 val AUROC 0.9899
    energy epoch 2 batch 0 loss 0.0404
    energy epoch 2 batch 200 loss 0.0203
    energy epoch 2 batch 400 loss 0.0108
    energy epoch 2 batch 600 loss 0.0240
    energy epoch 2 batch 800 loss 0.0017
    energy epoch 2 batch 1000 loss 0.0223
    energy epoch 2 batch 1200 loss 0.0050
    energy epoch 2 batch 1400 loss 0.0118
    energy epoch 2 batch 1600 loss 0.1950
    energy epoch 2 val AUROC 0.9925
    energy epoch 3 batch 0 loss 0.0115
    energy epoch 3 batch 200 loss 0.0387
    energy epoch 3 batch 400 loss 0.0043
    energy epoch 3 batch 600 loss 0.0007
    energy epoch 3 batch 800 loss 0.0008
    energy epoch 3 batch 1000 loss 0.0028
    energy epoch 3 batch 1200 loss 0.0006
    energy epoch 3 batch 1400 loss 0.0004
    energy epoch 3 batch 1600 loss 0.0114
    energy epoch 3 val AUROC 0.9923
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4590.81it/s]
    head epoch 1 batch 0 loss 1.0666
    head epoch 1 batch 200 loss 0.4600
    head epoch 1 batch 400 loss 0.1702
    head epoch 1 batch 600 loss 0.3834
    head epoch 1 batch 800 loss 0.3045
    head epoch 1 batch 1000 loss 0.2197
    head epoch 1 batch 1200 loss 0.2737
    head epoch 1 batch 1400 loss 0.1622
    head epoch 1 batch 1600 loss 0.3695
    head epoch 1 val loss 0.2318
    head epoch 2 batch 0 loss 0.3284
    head epoch 2 batch 200 loss 0.2660
    head epoch 2 batch 400 loss 0.1638
    head epoch 2 batch 600 loss 0.2083
    head epoch 2 batch 800 loss 0.1547
    head epoch 2 batch 1000 loss 0.1685
    head epoch 2 batch 1200 loss 0.0535
    head epoch 2 batch 1400 loss 0.1485
    head epoch 2 batch 1600 loss 0.3284
    head epoch 2 val loss 0.2322
    head epoch 3 batch 0 loss 0.2947
    head epoch 3 batch 200 loss 0.2445
    head epoch 3 batch 400 loss 0.0903
    head epoch 3 batch 600 loss 0.2505
    head epoch 3 batch 800 loss 0.1654
    head epoch 3 batch 1000 loss 0.0989
    head epoch 3 batch 1200 loss 0.0154
    head epoch 3 batch 1400 loss 0.0826
    head epoch 3 batch 1600 loss 0.2743
    head epoch 3 val loss 0.2425
    head epoch 4 batch 0 loss 0.2405
    head epoch 4 batch 200 loss 0.2639
    head epoch 4 batch 400 loss 0.0612
    head epoch 4 batch 600 loss 0.1602
    head epoch 4 batch 800 loss 0.1220
    head epoch 4 batch 1000 loss 0.0926
    head epoch 4 batch 1200 loss 0.0030
    head epoch 4 batch 1400 loss 0.0737
    head epoch 4 batch 1600 loss 0.1865
    head epoch 4 val loss 0.2704
    head epoch 5 batch 0 loss 0.2103
    head epoch 5 batch 200 loss 0.2371
    head epoch 5 batch 400 loss 0.0012
    head epoch 5 batch 600 loss 0.1773
    head epoch 5 batch 800 loss 0.0726
    head epoch 5 batch 1000 loss 0.0787
    head epoch 5 batch 1200 loss 0.0008
    head epoch 5 batch 1400 loss 0.0770
    head epoch 5 batch 1600 loss 0.2270
    head epoch 5 val loss 0.2782
== A0ftM: A0ft with I raised to 1 for inputs out of the training distribution (DESIGN.md 20)
{"neg_weight": 1.0, "row_weight": "sqrt_inverse_source_frequency", "row_weight_by_source": {"alpaca": 1.829, "beavertails": 1.831, "classical_dilemma": 5.17, "daily_dilemmas": 1.828, "dolly": 1.829, "hh_rlhf_harmless": 1.829, "hh_rlhf_helpful": 1.829, "hh_rlhf_redteam": 1.828, "jailbreak": 2.134, "moralchoice_highamb": 1.983, "narrative": 1.493, "supp:coconot_contrast": 2.743, "supp:falsereject_tr
[git] pushed to main

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
```
