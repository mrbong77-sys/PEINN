# v2.1 심사 대응 점검 무인 실행 상태: 실패 후 대기

- 시각 2026-10-15 23:37:07 (UTC 2026-10-15 14:37:07), 시도 1, 비컨 #2 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/check.json`)
- 실행 코드: 7c7d71d v2.1 심사 대응 점검 runner: 실행 중 (attempt 1)
- 현재 단계: train (0.3분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 2297 MiB, 32607 MiB, 0 %, 42
- 다음 동작: 새 코드나 명령을 기다림
- 사유: 코드 1
- 마지막으로 처리한 명령: 없음
- 남은 단계: train; thresholds; routes; nemo; matrix; cost; analyze; push-check; estimate
- 끝난 단계(코드): record, audit, unload-1, features, split

## 마지막 로그

```
Batches: 100%|██████████| 1/1 [00:00<00:00, 101.07it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 74.87it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 129.56it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 116.15it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]2026-10-15 23:36:16,112 [bench.pea_eval.xstest] INFO:   [H07] 25/45 완료 (arm 55% · 전체 55% · 55.73 req/s · arm ETA 0s)


Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[A


Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 80.05it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 89.37it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 87.20it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 80.61it/s]


Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 121.11it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 68.02it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 123.66it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 143.40it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 88.25it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]2026-10-15 23:36:16,165 [bench.pea_eval.xstest] INFO:   [H07] 30/45 완료 (arm 66% · 전체 66% · 59.82 req/s · arm ETA 0s)
Batches: 100%|██████████| 1/1 [00:00<00:00, 98.10it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 92.42it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 101.76it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 83.70it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 111.03it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 68.74it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 108.06it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 112.20it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 103.79it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 89.27it/s]
2026-10-15 23:36:16,216 [bench.pea_eval.xstest] INFO:   [H07] 35/45 완료 (arm 77% · 전체 77% · 63.32 req/s · arm ETA 0s)
Batches: 100%|██████████| 1/1 [00:00<00:00, 103.06it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 81.25it/s]


Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 91.65it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 74.86it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 100.05it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 100.83it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 100.00it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 102.16it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 81.10it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 99.89it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A2026-10-15 23:36:16,270 [bench.pea_eval.xstest] INFO:   [H07] 40/45 완료 (arm 88% · 전체 88% · 65.88 req/s · arm ETA 0s)


Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 94.62it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 120.69it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 122.85it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 113.34it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 126.92it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 121.58it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 141.97it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 213.20it/s]
2026-10-15 23:36:16,307 [bench.pea_eval.xstest] INFO:   [H07] 45/45 완료 (arm 100% · 전체 100% · 69.92 req/s · arm ETA 0s)
2026-10-15 23:36:16,307 [bench.pea_eval.xstest] INFO:   [H07] ═══ PEINN 45건 완료 | 1s | 누적 45/45
2026-10-15 23:36:16,307 [bench.pea_eval.xstest] INFO:   ⚡ XSTest 완료 (총 45건 | 0.0분)
2026-10-15 23:36:16,308 [bench.stat_batch_runner] INFO:   💾 xstest raw pickle backup: xstest_raw_1runs_20261015_233615.pkl (45 items)
  💾 XSTest CSV save 시작: xstest_batch_1runs_20261015_233615.csv
2026-10-15 23:36:16,308 [bench.stat_batch_runner] INFO:   💾 XSTest CSV save 시작: xstest_batch_1runs_20261015_233615.csv
2026-10-15 23:36:16,309 [bench.pea_eval.xstest] INFO: XSTest LMM-judge용 CSV 저장: D:\Projects\PEINN\revision\aai_r1\cache\check\peaos_out\record\xstest\xstest_batch_1runs_20261015_233615.csv (45 rows)
  ✓ XSTest CSV 저장+fsync 확인: xstest_batch_1runs_20261015_233615.csv (17,437 bytes)
2026-10-15 23:36:16,316 [bench.stat_batch_runner] INFO:   ✓ XSTest CSV 저장+fsync 확인: xstest_batch_1runs_20261015_233615.csv (17,437 bytes)
{'csv': 'xstest_batch_1runs_20261015_233615.csv', 'total': 45, 'errors': 0, 'sec': 0.9}
{"calls": 54, "unique": 54, "by_bench": {"ggb": {"calls": 9, "unique": 9, "submitted_rows_H07": 90, "csv_rows": 9, "rows_with_sha": 9, "rows_sha_recorded": 9}, "xstest": {"calls": 45, "unique": 45, "submitted_rows_H07": 225, "csv_rows": 45, "rows_with_sha": 45, "rows_sha_recorded": 45}}}

[v21r-check] ===== audit: isolation audit of the v4 corpus (guard + recorded texts) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r audit --check
v4 corpus: ['corpus_fit.jsonl', 'corpus_report.txt', 'corpus_unlabeled.jsonl', 'heldout.csv', 'illocution_labels.csv', 'labeled.csv', 'labeled_2of3.csv', 'train.csv']; train=train.csv, heldout=heldout.csv
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peaos_driver.py audit --out D:\Projects\PEINN\revision\aai_r1\cache\check --record D:\Projects\PEINN\revision\aai_r1\cache\check\record.jsonl --corpus D:\Projects\PEINN\revision\aai_r1\cache\check\check_train.csv D:\Projects\PEINN\revision\aai_r1\cache\check\check_heldout.csv  (cwd D:\Projects\PEAOS)
{"bench_files": {"harmbench_behaviors_text_all.csv": true, "xstest_prompts.csv": true, "morables_benchmark/morables_sample.jsonl": true, "ggb_benchmark/ous_items.json": true, "ethics_benchmark/dilemmas.json": true, "ethics_benchmark/mfq.json": true, "ethics_benchmark/wvs.json": true, "taxonomy_40_scenarios.json": true, "delphi_behaviors.csv": true, "mach_items.json": true, "unesco_items.csv": true
audit: 400 corpus rows -> D:\Projects\PEINN\revision\aai_r1\cache\check\audit.jsonl

[v21r-check] ===== unload-1: free the GPU (any Ollama model) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r unload qwen3.8:27b qwen3:8b gemma4:e4b --check

[v21r-check] ===== features: frozen v2.1 features of the corpus and the routing texts =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r features --check
features for 454 texts
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peinn_side.py features --texts D:\Projects\PEINN\revision\aai_r1\cache\check\feature_texts.json --out D:\Projects\PEINN\revision\aai_r1\cache\check\features.npz  (cwd D:\Projects\PEINN\src)
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4497.52it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  36%|███▌      | 72/199 [00:00<00:00, 654.32it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1048.69it/s]
[features] 454 texts, 454 to compute
[features] 454/454 (0.3 min)

[v21r-check] ===== split: embedding near-duplicates out, train / val / test split =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r split --check
{"rows": 400, "kept": 400, "dropped": {"guard": 0, "embedding": 0}, "split": {"train": 200, "test": 109, "val": 91}}

[v21r-check] ===== train: variants A0-A7 and the energy calibrator on the isolated corpus =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r train --check
shipped head recipe: {"labels": "legacy", "neg_weight": 0.0, "in_dim": 800}; neg_weight 0.0
== energy calibrator (label F >= 0.5)
    epoch   1  val AUROC 0.7039
== A0: T/I/F head on all 800
    epoch   1  val 1.1935
== A6p: T/I/F head on no principle block
    epoch   1  val 1.1578
== A6e: T/I/F head on no affect block
    epoch   1  val 1.1628
== A1: T/F head (no I)
    epoch   1  val 0.6399
== A2: softmax safe / ambiguous / harmful
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "D:\Projects\PEINN\revision\aai_r1\v21r\__main__.py", line 50, in <module>
    sys.exit(main())
             ~~~~^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\__main__.py", line 46, in main
    return STEPS[step](check)
           ~~~~~~~~~~~^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\models.py", line 343, in train_all
    ctr, cva = three_class(tr.T, tr.I, tr.F), three_class(va.T, va.I, va.F)
               ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\models.py", line 57, in three_class
    T, I, F = (np.asarray(x, dtype=float) for x in (T, I, F))
    ^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\models.py", line 57, in <genexpr>
    T, I, F = (np.asarray(x, dtype=float) for x in (T, I, F))
               ~~~~~~~~~~^^^^^^^^^^^^^^^^
  File "C:\Users\bojung\miniconda3\Lib\site-packages\pandas\core\generic.py", line 2168, in __array__
    arr = np.asarray(values, dtype=dtype)
ValueError: could not convert string to float: 'Write a function that finds the middle element of an array. [1, 4, 6, 7, 10, 11]'
[v21r-check] train failed (code 1); fix it and run the same command again
```
