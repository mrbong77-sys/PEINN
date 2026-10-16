# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 14:51:21 (UTC 2026-10-16 05:51:21), 시도 24, 비컨 #115 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 4c061a8 v2.1 심사 대응 runner: 실행 중 (attempt 24)
- 현재 단계: train (0.6분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 2219 MiB, 32607 MiB, 12 %, 44
- 다음 동작: 다음 단계가 시작되면 멈추고 새 코드로 다시 실행
- 사유: 안전 업데이트 대기
- 마지막으로 처리한 명령: 20261016T060500Z-update update (수신, 다음 단계 경계에서 적용, 2026-10-16 05:51:21 UTC)
- 남은 단계: train; thresholds; routes; gate-diag-check; gate-diag; preview-check; preview; gate-review; main-check; matrix-zephyr-check; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check

## 마지막 로그

```
D:\Projects\PEINN\revision\aai_r1\v21r\models.py:282: UserWarning: Converting a tensor with requires_grad=True to a scalar may lead to unexpected behavior.
Consider using tensor.detach() first. (Triggered internally at C:\actions-runner\_work\pytorch\pytorch\pytorch\torch\csrc\autograd\generated\python_variable_methods.cpp:837.)
  log(f"    epoch {ep + 1} batch {i} loss {float(l_):.4f}")
    epoch 1 batch 0 loss 1.0530
    epoch 1 val 1.0026
== A0ft: PEINN with the calibrator's mpnet and the head's MiniLM fine-tuned (DESIGN.md 13)
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  38%|███▊      | 76/199 [00:00<00:00, 758.80it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1230.61it/s]
    energy epoch 1 batch 0 loss 0.2008
    energy epoch 1 val AUROC 0.7359
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4164.43it/s]
    head epoch 1 batch 0 loss 1.0666
    head epoch 1 val loss 1.0318
== A0ftM: A0ft with I raised to 1 for inputs out of the training distribution (DESIGN.md 20)
{"neg_weight": 1.0, "row_weight": "sqrt_inverse_source_frequency", "row_weight_by_source": {"alpaca": 1.184, "beavertails": 1.001, "daily_dilemmas": 1.129, "dolly": 0.967, "hh_rlhf_harmless": 1.039, "hh_rlhf_helpful": 0.936, "hh_rlhf_redteam": 1.129, "jailbreak": 1.081, "moralchoice_highamb": 1.248, "narrative": 0.837, "supp:coconot_contrast": 0.936, "supp:falsereject_train": 0.936, "supp:orbench_
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds --check
A0: {"harm": 4.893, "soft": 4.893, "F": 0.4, "extreme": 4.909, "Fref": 0.5, "I": 0.2, "Fblk": 0.05} stage1 {'harm_hb': 0.6071428571428571, 'safe_hb': 0.08108108108108109, 'met': False} cost 0.2088
A1: {"harm": 4.893, "soft": 4.893, "F": 0.3, "extreme": 4.909, "Fref": 0.4, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.6428571428571429, 'safe_hb': 0.0945945945945946, 'met': False} cost 0.2088
A2: {"harm": 4.893, "soft": 4.893, "F": 0.3, "extreme": 4.909, "Fref": 0.35, "I": 0.2, "Fblk": 0.05} stage1 {'harm_hb': 0.6428571428571429, 'safe_hb': 0.08108108108108109, 'met': False} cost 0.2000
A3: {"harm": 4.893, "soft": 4.893, "F": 0.35, "extreme": 4.909, "Fref": 0.45, "I": 0.2, "Fblk": 0.3} stage1 {'harm_hb': 0.6071428571428571, 'safe_hb': 0.0945945945945946, 'met': False} cost 0.2105
A5: {"Fhb": 0.5, "Fref": 0.4, "I": 0.2, "Fblk": 0.5} stage1 {'harm_hb': 0.0, 'safe_hb': 0.0, 'met': False} cost 0.2579
A6p: {"harm": 4.893, "soft": 4.893, "F": 0.45, "extreme": 4.898, "Fref": 0.55, "I": 0.25, "Fblk": 0.5} stage1 {'harm_hb': 0.6428571428571429, 'safe_hb': 0.12162162162162163, 'met': False} cost 0.2254
A6e: {"harm": 4.893, "soft": 4.893, "F": 0.45, "extreme": 4.909, "Fref": 0.5, "I": 0.2, "Fblk": 0.45} stage1 {'harm_hb': 0.6071428571428571, 'safe_hb': 0.08108108108108109, 'met': False} cost 0.2044
A7: {"harm": 4.893, "soft": 4.893, "F": 0.45, "extreme": 4.907, "Fref": 0.55, "I": 0.45, "Fblk": 0.45} stage1 {'harm_hb': 0.6071428571428571, 'safe_hb': 0.0945945945945946, 'met': False} cost 0.2167
A0ft: {"harm": 4.613, "soft": 4.613, "F": 0.5, "extreme": 4.616, "Fref": 0.55, "I": 0.2, "Fblk": 0.5} stage1 {'harm_hb': 0.5357142857142857, 'safe_hb': 0.1891891891891892, 'met': False} cost 0.2781
A0ftM: {"harm": 4.613, "soft": 4.613, "F": 0.5, "extreme": 4.616, "Fref": 0.55, "I": 0.2, "Fblk": 0.5} stage1 {'harm_hb': 0.5357142857142857, 'safe_hb': 0.1891891891891892, 'met': False} cost 0.2781
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r routes --check
{"A0paper": 0, "A0@0.1": 0}
[v21r] skip supplement (public over-refusal and adversarial training sets (DESIGN.md 12)): finished 2026-10-16 13:48:36
[v21r] skip audit (isolation audit of the v4 corpus (guard + recorded texts)): finished 2026-10-16 13:48:41
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 09:35:42
[v21r] skip features (frozen v2.1 features of the corpus and the routing texts): finished 2026-10-16 13:58:34
[v21r] skip split (embedding near-duplicates out, train / val / test split): finished 2026-10-16 13:58:38

[v21r] ===== train: variants A0-A7 and the energy calibrator on the isolated corpus =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r train
shipped head recipe: {"labels": "legacy", "neg_weight": 0.0, "in_dim": 800}; trained on every axis (neg_weight 1.0, DESIGN.md 4)
== energy calibrator (label F >= 0.5)
    epoch   1  val AUROC 0.9191
    epoch  10  val AUROC 0.9697
    epoch  20  val AUROC 0.9721
```
