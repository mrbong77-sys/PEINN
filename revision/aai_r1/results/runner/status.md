# v2.1 심사 대응 무인 실행 상태: 완료

- 시각 2026-10-18 20:03:50 (UTC 2026-10-18 11:03:50), 시도 1, 비컨 #458 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 8de0ad5 v21r: A0ftM gate retrained from the same corpus, time and memory (DESIGN.md 37)
- 현재 단계: gate-retrain (15.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1704 MiB, 32607 MiB, 5 %, 45
- 다음 동작: 없음(모든 단계 끝)
- 사유: –
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: 없음
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain

## 마지막 로그

```
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 3701.85it/s]
[gate-time] {'device': 'cpu', 'threads': 1, 'n': 20, 'p50_ms': 129.07, 'p95_ms': 157.25, 'mean_ms': 130.39, 'process_peak_GB': 2.571}
gate main cpu1: {'device': 'cpu', 'threads': 1, 'n': 20, 'p50_ms': 129.07, 'p95_ms': 157.25, 'mean_ms': 130.39, 'process_peak_GB': 2.571}
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r gate-retrain --check
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  41%|████      | 82/199 [00:00<00:00, 797.29it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1190.13it/s]
    energy epoch 1 batch 0 loss 0.1699
    energy epoch 1 val AUROC 0.5846
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 3487.13it/s]
    head epoch 1 batch 0 loss 1.0663
    head epoch 1 val loss 1.0281
{"device": "NVIDIA GeForce RTX 5090", "n_train": 64, "n_val": 200, "epochs": {"energy": 1, "head": 1}, "sec": {"energy_mpnet": 23.2, "head_minilm": 2.6, "mahalanobis": 0.3, "thresholds_val": 0.6}, "sec_total": 26.7, "gpu_peak_GB": 9.246, "energy_val_auroc": 0.5846185064935064, "energy_val_auroc_released": 0.9924698555453858, "head_val_loss": 1.0281446154355225, "head_val_loss_released": 0.23177505

[v21r] ===== forced-export: forced-tag rows, route tables, signals, val/test labels -> results/forced (CPU) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r forced-export
  harmbench qwen: 2500 rows, tiers {'Direct-Answer': 500, 'Hard-block': 500, 'Reasoned-Refusal': 500, 'Deliberation': 500, 'Soft-reasoning': 500}, 1.4 MiB
  ggb qwen: 450 rows, tiers {'Direct-Answer': 90, 'Hard-block': 90, 'Reasoned-Refusal': 90, 'Deliberation': 90, 'Soft-reasoning': 90}, 0.0 MiB
  xstest qwen: 1125 rows, tiers {'Direct-Answer': 225, 'Hard-block': 225, 'Reasoned-Refusal': 225, 'Deliberation': 225, 'Soft-reasoning': 225}, 0.5 MiB
  taxonomy qwen: 1000 rows, tiers {'Direct-Answer': 200, 'Hard-block': 200, 'Reasoned-Refusal': 200, 'Deliberation': 200, 'Soft-reasoning': 200}, 0.6 MiB
  ethics qwen: 2000 rows, tiers {'Direct-Answer': 400, 'Hard-block': 400, 'Reasoned-Refusal': 400, 'Deliberation': 400, 'Soft-reasoning': 400}, 0.8 MiB
  morables qwen: 4500 rows, tiers {'Direct-Answer': 900, 'Hard-block': 900, 'Reasoned-Refusal': 900, 'Deliberation': 900, 'Soft-reasoning': 900}, 0.8 MiB
  harmbench gemma4: 2500 rows, tiers {'Direct-Answer': 500, 'Hard-block': 500, 'Reasoned-Refusal': 500, 'Deliberation': 500, 'Soft-reasoning': 500}, 1.1 MiB
  ggb gemma4: 450 rows, tiers {'Direct-Answer': 90, 'Hard-block': 90, 'Reasoned-Refusal': 90, 'Deliberation': 90, 'Soft-reasoning': 90}, 0.0 MiB
  xstest gemma4: 1125 rows, tiers {'Direct-Answer': 225, 'Hard-block': 225, 'Reasoned-Refusal': 225, 'Deliberation': 225, 'Soft-reasoning': 225}, 0.6 MiB
  taxonomy gemma4: 1000 rows, tiers {'Direct-Answer': 200, 'Hard-block': 200, 'Reasoned-Refusal': 200, 'Deliberation': 200, 'Soft-reasoning': 200}, 0.6 MiB
  ethics gemma4: 2000 rows, tiers {'Direct-Answer': 400, 'Hard-block': 400, 'Reasoned-Refusal': 400, 'Deliberation': 400, 'Soft-reasoning': 400}, 1.2 MiB
  morables gemma4: 4500 rows, tiers {'Direct-Answer': 900, 'Hard-block': 900, 'Reasoned-Refusal': 900, 'Deliberation': 900, 'Soft-reasoning': 900}, 3.1 MiB
  harmbench gemma3: 2500 rows, tiers {'Direct-Answer': 500, 'Hard-block': 500, 'Reasoned-Refusal': 500, 'Deliberation': 500, 'Soft-reasoning': 500}, 2.0 MiB
  ggb gemma3: 450 rows, tiers {'Direct-Answer': 90, 'Hard-block': 90, 'Reasoned-Refusal': 90, 'Deliberation': 90, 'Soft-reasoning': 90}, 0.0 MiB
  xstest gemma3: 1125 rows, tiers {'Direct-Answer': 225, 'Hard-block': 225, 'Reasoned-Refusal': 225, 'Deliberation': 225, 'Soft-reasoning': 225}, 0.9 MiB
  taxonomy gemma3: 1000 rows, tiers {'Direct-Answer': 200, 'Hard-block': 200, 'Reasoned-Refusal': 200, 'Deliberation': 200, 'Soft-reasoning': 200}, 0.9 MiB
  ethics gemma3: 2000 rows, tiers {'Direct-Answer': 400, 'Hard-block': 400, 'Reasoned-Refusal': 400, 'Deliberation': 400, 'Soft-reasoning': 400}, 1.4 MiB
  morables gemma3: 4500 rows, tiers {'Direct-Answer': 900, 'Hard-block': 900, 'Reasoned-Refusal': 900, 'Deliberation': 900, 'Soft-reasoning': 900}, 0.8 MiB
  harmbench zephyr: 2500 rows, tiers {'Direct-Answer': 500, 'Hard-block': 500, 'Reasoned-Refusal': 500, 'Deliberation': 500, 'Soft-reasoning': 500}, 2.0 MiB
  ggb zephyr: 450 rows, tiers {'Direct-Answer': 90, 'Hard-block': 90, 'Reasoned-Refusal': 90, 'Deliberation': 90, 'Soft-reasoning': 90}, 0.1 MiB
  xstest zephyr: 1125 rows, tiers {'Direct-Answer': 225, 'Hard-block': 225, 'Reasoned-Refusal': 225, 'Deliberation': 225, 'Soft-reasoning': 225}, 0.6 MiB
  taxonomy zephyr: 1000 rows, tiers {'Direct-Answer': 200, 'Hard-block': 200, 'Reasoned-Refusal': 200, 'Deliberation': 200, 'Soft-reasoning': 200}, 0.9 MiB
  ethics zephyr: 2000 rows, tiers {'Direct-Answer': 400, 'Hard-block': 400, 'Reasoned-Refusal': 400, 'Deliberation': 400, 'Soft-reasoning': 400}, 1.0 MiB
  morables zephyr: 4500 rows, tiers {'Direct-Answer': 900, 'Hard-block': 900, 'Reasoned-Refusal': 900, 'Deliberation': 900, 'Soft-reasoning': 900}, 1.0 MiB
  signals A5: none
  routes (1521, 148), labels 12417, 36 files, 28.8 MiB
[git] pushed to main

[v21r] ===== gate-mem: A0ftM's whole input gate in one process: time and peak memory, GPU and one CPU thread =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r gate-mem
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peinn_side.py gate-time --texts D:\Projects\PEINN\revision\aai_r1\cache\full\cost\gate_texts.json --out D:\Projects\PEINN\revision\aai_r1\cache\full\cost\gate_main_gpu.json --ft-root D:\Projects\PEINN\revision\aai_r1 --ft-models D:\Projects\PEINN\revision\aai_r1\cache\full\models  (cwd D:\Projects\PEINN\src)
No sentence-transformers model found with name sentence-transformers/all-MiniLM-L6-v2. Creating a new one with mean pooling.
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4693.81it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  33%|███▎      | 66/199 [00:00<00:00, 634.96it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1166.89it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  38%|███▊      | 76/199 [00:00<00:00, 716.51it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1160.43it/s]
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4064.17it/s]
[gate-time] {'device': 'cuda', 'threads': 20, 'n': 200, 'p50_ms': 40.23, 'p95_ms': 69.67, 'mean_ms': 46.13, 'gpu_peak_GB': 1.184, 'process_peak_GB': 2.449}
gate main gpu: {'device': 'cuda', 'threads': 20, 'n': 200, 'p50_ms': 40.23, 'p95_ms': 69.67, 'mean_ms': 46.13, 'gpu_peak_GB': 1.184, 'process_peak_GB': 2.449}
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peinn_side.py gate-time --texts D:\Projects\PEINN\revision\aai_r1\cache\full\cost\gate_texts.json --out D:\Projects\PEINN\revision\aai_r1\cache\full\cost\gate_main_cpu1.json --ft-root D:\Projects\PEINN\revision\aai_r1 --ft-models D:\Projects\PEINN\revision\aai_r1\cache\full\models  (cwd D:\Projects\PEINN\src)
No sentence-transformers model found with name sentence-transformers/all-MiniLM-L6-v2. Creating a new one with mean pooling.
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4084.31it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  37%|███▋      | 73/199 [00:00<00:00, 725.91it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1154.39it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  42%|████▏     | 84/199 [00:00<00:00, 822.32it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1161.89it/s]
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 3974.07it/s]
[gate-time] {'device': 'cpu', 'threads': 1, 'n': 200, 'p50_ms': 130.36, 'p95_ms': 169.65, 'mean_ms': 132.24, 'process_peak_GB': 2.575}
gate main cpu1: {'device': 'cpu', 'threads': 1, 'n': 200, 'p50_ms': 130.36, 'p95_ms': 169.65, 'mean_ms': 132.24, 'process_peak_GB': 2.575}
[git] pushed to main

[v21r] ===== gate-retrain: A0ftM's gate trained again from the same corpus into a scratch folder: time, memory =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r gate-retrain
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  45%|████▍     | 89/199 [00:00<00:00, 870.79it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1192.61it/s]
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
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4118.88it/s]
    head epoch 1 batch 0 loss 1.0666
    head epoch 1 batch 200 loss 0.4600
    head epoch 1 batch 400 loss 0.1702
    head epoch 1 batch 600 loss 0.3834
    head epoch 1 batch 800 loss 0.3045
    head epoch 1 batch 1000 loss 0.2197
    head epoch 1 batch 1200 loss 0.2729
    head epoch 1 batch 1400 loss 0.1602
    head epoch 1 batch 1600 loss 0.3712
    head epoch 1 val loss 0.2306
    head epoch 2 batch 0 loss 0.3253
    head epoch 2 batch 200 loss 0.2700
    head epoch 2 batch 400 loss 0.1627
    head epoch 2 batch 600 loss 0.2078
    head epoch 2 batch 800 loss 0.1571
    head epoch 2 batch 1000 loss 0.1621
    head epoch 2 batch 1200 loss 0.0695
    head epoch 2 batch 1400 loss 0.1441
    head epoch 2 batch 1600 loss 0.3248
    head epoch 2 val loss 0.2300
    head epoch 3 batch 0 loss 0.2886
    head epoch 3 batch 200 loss 0.2413
    head epoch 3 batch 400 loss 0.0832
    head epoch 3 batch 600 loss 0.2295
    head epoch 3 batch 800 loss 0.1745
    head epoch 3 batch 1000 loss 0.0987
    head epoch 3 batch 1200 loss 0.0193
    head epoch 3 batch 1400 loss 0.0842
    head epoch 3 batch 1600 loss 0.2703
    head epoch 3 val loss 0.2385
    head epoch 4 batch 0 loss 0.2389
    head epoch 4 batch 200 loss 0.2581
    head epoch 4 batch 400 loss 0.0779
    head epoch 4 batch 600 loss 0.1657
    head epoch 4 batch 800 loss 0.1321
    head epoch 4 batch 1000 loss 0.0897
    head epoch 4 batch 1200 loss 0.0032
    head epoch 4 batch 1400 loss 0.0777
    head epoch 4 batch 1600 loss 0.2008
    head epoch 4 val loss 0.2723
    head epoch 5 batch 0 loss 0.2192
    head epoch 5 batch 200 loss 0.1941
    head epoch 5 batch 400 loss 0.0012
    head epoch 5 batch 600 loss 0.1790
    head epoch 5 batch 800 loss 0.0735
    head epoch 5 batch 1000 loss 0.0822
    head epoch 5 batch 1200 loss 0.0010
    head epoch 5 batch 1400 loss 0.0786
    head epoch 5 batch 1600 loss 0.2476
    head epoch 5 val loss 0.2782
{"device": "NVIDIA GeForce RTX 5090", "n_train": 52569, "n_val": 6206, "epochs": {"energy": 3, "head": 5}, "sec": {"energy_mpnet": 604.5, "head_minilm": 201.2, "mahalanobis": 80.5, "thresholds_val": 7.5}, "sec_total": 893.6, "gpu_peak_GB": 9.273, "energy_val_auroc": 0.9924698555453858, "energy_val_auroc_released": 0.9924698555453858, "head_val_loss": 0.22998625192394212, "head_val_loss_released": 
[git] pushed to main

[v21r] all steps finished and pushed in 17.8 min
```
