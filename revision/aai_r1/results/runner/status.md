# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-18 15:04:26 (UTC 2026-10-18 06:04:26), 시도 4, 비컨 #435 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 43b7bce station: 임무 실행 중
- 현재 단계: a8 (40.4분째)
- 마지막 출력 후: 1.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 24001 MiB, 32607 MiB, 88 %, 70
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: a8; analyze-a8; ggb-export-a8; ggb-rescore-a8; bench-export-a8; bench-stats-a8; ethics-diag-check; ethics-diag
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768

## 마지막 로그

```

[v21r] ===== a8: A8: LoRA on qwen2.5-7B with the same supervision; benches on the merged model =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r a8
A8 targets: 58775 items ({'safe': 35467, 'harm': 21843, 'dilemma': 1465}), 0 to do
A8 targets: 0 skipped now (Ollama repeat limit), 3 in all
[v21r] $ C:\Users\bojung\miniconda3\python.exe -u D:\Projects\PEINN\revision\aai_r1\v21r\a8_train.py --data D:\Projects\PEINN\revision\aai_r1\cache\full\a8\targets.jsonl --out D:\Projects\PEINN\revision\aai_r1\cache\full\a8\merged --report D:\Projects\PEINN\revision\aai_r1\cache\full\a8\train.json --model Qwen/Qwen2.5-7B-Instruct --hp {} --ckpt D:\Projects\PEINN\revision\aai_r1\cache\full\a8\train
Fetching 11 files:   0%|          | 0/11 [00:00<?, ?it/s]Fetching 11 files: 100%|██████████| 11/11 [00:00<00:00, 23161.32it/s]
[transformers] `torch_dtype` is deprecated! Use `dtype` instead!
Loading weights:   0%|          | 0/339 [00:00<?, ?it/s]Loading weights:   1%|          | 2/339 [00:00<00:35,  9.55it/s]Loading weights:   3%|▎         | 10/339 [00:00<00:11, 28.90it/s]Loading weights:   5%|▌         | 17/339 [00:00<00:12, 24.88it/s]Loading weights:   6%|▋         | 22/339 [00:00<00:10, 29.76it/s]Loading weights:   9%|▊         | 29/339 [00:00<00:08, 35.35it/s]Loading weigh
step 20/3286 loss 1.1068 (60 s, 3.0 s/step, peak reserved 24.4 GiB)
step 40/3286 loss 0.2586 (121 s, 3.0 s/step, peak reserved 24.1 GiB)
step 60/3286 loss 0.2346 (180 s, 2.9 s/step, peak reserved 24.1 GiB)
step 80/3286 loss 0.2859 (242 s, 3.1 s/step, peak reserved 24.1 GiB)
step 100/3286 loss 0.2606 (307 s, 3.3 s/step, peak reserved 24.1 GiB)
step 120/3286 loss 0.3185 (369 s, 3.1 s/step, peak reserved 24.2 GiB)
step 140/3286 loss 0.3179 (430 s, 3.1 s/step, peak reserved 24.3 GiB)
step 160/3286 loss 0.2794 (491 s, 3.1 s/step, peak reserved 24.1 GiB)
step 180/3286 loss 0.2254 (550 s, 3.0 s/step, peak reserved 24.1 GiB)
step 200/3286 loss 0.2631 (611 s, 3.0 s/step, peak reserved 24.5 GiB)
step 220/3286 loss 0.2437 (670 s, 2.9 s/step, peak reserved 24.3 GiB)
step 240/3286 loss 0.2107 (732 s, 3.1 s/step, peak reserved 24.2 GiB)
step 260/3286 loss 0.2657 (794 s, 3.1 s/step, peak reserved 24.2 GiB)
step 280/3286 loss 0.2859 (858 s, 3.2 s/step, peak reserved 24.3 GiB)
step 300/3286 loss 0.2704 (919 s, 3.0 s/step, peak reserved 24.3 GiB)
step 320/3286 loss 0.2763 (980 s, 3.1 s/step, peak reserved 24.2 GiB)
step 340/3286 loss 0.3143 (1040 s, 3.0 s/step, peak reserved 24.2 GiB)
step 360/3286 loss 0.2909 (1101 s, 3.1 s/step, peak reserved 24.4 GiB)
step 380/3286 loss 0.2662 (1176 s, 3.8 s/step, peak reserved 24.2 GiB)
step 400/3286 loss 0.2104 (1258 s, 4.1 s/step, peak reserved 24.1 GiB)
step 420/3286 loss 0.2742 (1341 s, 4.2 s/step, peak reserved 24.2 GiB)
step 440/3286 loss 0.2651 (1414 s, 3.7 s/step, peak reserved 24.2 GiB)
step 460/3286 loss 0.2957 (1476 s, 3.1 s/step, peak reserved 24.2 GiB)
step 480/3286 loss 0.206 (1537 s, 3.0 s/step, peak reserved 24.0 GiB)
step 500/3286 loss 0.2664 (1595 s, 2.9 s/step, peak reserved 24.2 GiB)
step 520/3286 loss 0.2155 (1657 s, 3.1 s/step, peak reserved 24.2 GiB)
step 540/3286 loss 0.3231 (1716 s, 3.0 s/step, peak reserved 24.2 GiB)
step 560/3286 loss 0.2619 (1777 s, 3.0 s/step, peak reserved 24.2 GiB)
step 580/3286 loss 0.2501 (1838 s, 3.0 s/step, peak reserved 24.2 GiB)
step 600/3286 loss 0.2845 (1899 s, 3.0 s/step, peak reserved 24.3 GiB)
step 620/3286 loss 0.1876 (1961 s, 3.1 s/step, peak reserved 24.1 GiB)
```
