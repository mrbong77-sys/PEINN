# v2.1 심사 대응 무인 실행 상태: 실패 후 대기

- 시각 2026-10-16 00:42:44 (UTC 2026-10-15 15:42:44), 시도 1, 비컨 #2 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 123ad15 v21r R: routing texts of the submitted benches recorded with a mock LLM (counts)
- 현재 단계: split (0.1분째)
- 마지막 출력 후: 0.1분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1693 MiB, 32607 MiB, 0 %, 35
- 다음 동작: 새 코드나 명령을 기다림
- 사유: 코드 1
- 마지막으로 처리한 명령: 없음
- 남은 단계: split; train; thresholds; routes; nemo; approval; matrix; cost; analyze
- 끝난 단계(코드): record, audit, unload-1, features

## 마지막 로그

```
Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 77.93it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 74.86it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 111.46it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 82.59it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 124.56it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 77.30it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 67.37it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 83.34it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 77.29it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 77.20it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 99.00it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 94.11it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 95.07it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 107.87it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 109.67it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 82.87it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 95.89it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 112.56it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 91.47it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 78.57it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 109.10it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 82.12it/s]

Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 83.21it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 86.02it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 87.47it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 90.16it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 96.15it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 67.16it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 122.24it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][A

Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[A


Batches:   0%|          | 0/1 [00:00<?, ?it/s][A[A[ABatches: 100%|██████████| 1/1 [00:00<00:00, 98.06it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 87.50it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 99.92it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 70.53it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 142.48it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]Batches: 100%|██████████| 1/1 [00:00<00:00, 161.03it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s]
Batches:   0%|          | 0/1 [00:00<?, ?it/s][ABatches: 100%|██████████| 1/1 [00:00<00:00, 194.86it/s]
Batches: 100%|██████████| 1/1 [00:00<00:00, 203.36it/s]
2026-10-16 00:34:47,415 [bench.pea_eval.morables] INFO:   [Morables] PEINN/qwen2.5: acc_clean=0.0 acc_adv=0.0 RG=0.0 SCR=0.0
2026-10-16 00:34:47,419 [bench.stat_batch_runner] INFO:   💾 morables raw pickle backup: morables_raw_5runs_20261016_003436.pkl (900 items)
  💾 Morables CSV save 시작: morables_batch_5runs_20261016_003436.csv
2026-10-16 00:34:47,419 [bench.stat_batch_runner] INFO:   💾 Morables CSV save 시작: morables_batch_5runs_20261016_003436.csv
2026-10-16 00:34:47,434 [bench.pea_eval.morables] INFO: Morables 결과 저장: D:\Projects\PEINN\revision\aai_r1\cache\full\peaos_out\record\morables\morables_batch_5runs_20261016_003436.csv (900 rows)
  ✓ Morables CSV 저장+fsync 확인: morables_batch_5runs_20261016_003436.csv (2,328,392 bytes)
2026-10-16 00:34:47,450 [bench.stat_batch_runner] INFO:   ✓ Morables CSV 저장+fsync 확인: morables_batch_5runs_20261016_003436.csv (2,328,392 bytes)
{'csv': 'morables_batch_5runs_20261016_003436.csv', 'total': 900, 'errors': 0, 'sec': 10.5}
{"calls": 2315, "unique": 1521, "by_bench": {"harmbench": {"calls": 500, "unique": 245, "submitted_rows_H07": 500, "csv_rows": 500, "rows_with_sha": 500, "rows_sha_recorded": 500}, "ggb": {"calls": 90, "unique": 9, "submitted_rows_H07": 90, "csv_rows": 90, "rows_with_sha": 90, "rows_sha_recorded": 90}, "xstest": {"calls": 225, "unique": 191, "submitted_rows_H07": 225, "csv_rows": 225, "rows_with_s
[git] pushed to main

[v21r] ===== audit: isolation audit of the v4 corpus (guard + recorded texts) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r audit
v4 corpus: ['corpus_fit.jsonl', 'corpus_report.txt', 'corpus_unlabeled.jsonl', 'heldout.csv', 'illocution_labels.csv', 'labeled.csv', 'labeled_2of3.csv', 'train.csv']; train=train.csv, heldout=heldout.csv
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peaos_driver.py audit --out D:\Projects\PEINN\revision\aai_r1\cache\full --record D:\Projects\PEINN\revision\aai_r1\cache\full\record.jsonl --corpus D:\Projects\PEAOS\pea_eval\data\ee_3class\v4\train.csv D:\Projects\PEAOS\pea_eval\data\ee_3class\v4\heldout.csv  (cwd D:\Projects\PEAOS)
{"bench_files": {"harmbench_behaviors_text_all.csv": true, "xstest_prompts.csv": true, "morables_benchmark/morables_sample.jsonl": true, "ggb_benchmark/ous_items.json": true, "ethics_benchmark/dilemmas.json": true, "ethics_benchmark/mfq.json": true, "ethics_benchmark/wvs.json": true, "taxonomy_40_scenarios.json": true, "delphi_behaviors.csv": true, "mach_items.json": true, "unesco_items.csv": true
audit: 12511 corpus rows -> D:\Projects\PEINN\revision\aai_r1\cache\full\audit.jsonl

[v21r] ===== unload-1: free the GPU (any Ollama model) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r unload qwen3.8:27b qwen3:8b gemma4:e4b

[v21r] ===== features: frozen v2.1 features of the corpus and the routing texts =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r features
features for 14032 texts
[v21r] $ C:\Users\bojung\miniconda3\python.exe D:\Projects\PEINN\revision\aai_r1\v21r\peinn_side.py features --texts D:\Projects\PEINN\revision\aai_r1\cache\full\feature_texts.json --out D:\Projects\PEINN\revision\aai_r1\cache\full\features.npz  (cwd D:\Projects\PEINN\src)
No sentence-transformers model found with name sentence-transformers/all-MiniLM-L6-v2. Creating a new one with mean pooling.
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4276.13it/s]
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  32%|███▏      | 64/199 [00:00<00:00, 587.16it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1309.09it/s]
[features] 14032 texts, 14032 to compute
[features] 500/14032 (0.3 min)
[features] 1000/14032 (0.6 min)
[features] 1500/14032 (0.8 min)
[features] 2000/14032 (1.1 min)
[features] 2500/14032 (1.3 min)
[features] 3000/14032 (1.6 min)
[features] 3500/14032 (1.8 min)
[features] 4000/14032 (2.1 min)
[features] 4500/14032 (2.4 min)
[features] 5000/14032 (2.6 min)
[features] 5500/14032 (2.9 min)
[features] 6000/14032 (3.2 min)
[features] 6500/14032 (3.4 min)
[features] 7000/14032 (3.7 min)
[features] 7500/14032 (3.9 min)
[features] 8000/14032 (4.2 min)
[features] 8500/14032 (4.5 min)
[features] 9000/14032 (4.7 min)
[features] 9500/14032 (5.0 min)
[features] 10000/14032 (5.3 min)
[features] 10500/14032 (5.6 min)
[features] 11000/14032 (5.9 min)
[features] 11500/14032 (6.1 min)
[features] 12000/14032 (6.4 min)
[features] 12500/14032 (6.7 min)
[features] 13000/14032 (6.9 min)
[features] 13500/14032 (7.2 min)
[features] 14000/14032 (7.5 min)
[features] 14032/14032 (7.5 min)

[v21r] ===== split: embedding near-duplicates out, train / val / test split =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r split
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "D:\Projects\PEINN\revision\aai_r1\v21r\__main__.py", line 50, in <module>
    sys.exit(main())
             ~~~~^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\__main__.py", line 46, in main
    return STEPS[step](check)
           ~~~~~~~~~~~^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\data.py", line 259, in split
    C.jdump(st, o / "corpus_audit.json")
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Projects\PEINN\revision\aai_r1\v21r\common.py", line 88, in jdump
    f.write_text(json.dumps(obj, indent=1, ensure_ascii=False, default=_np) + "\n", encoding="utf-8")
                 ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\bojung\miniconda3\Lib\json\__init__.py", line 238, in dumps
    **kw).encode(obj)
          ~~~~~~^^^^^
  File "C:\Users\bojung\miniconda3\Lib\json\encoder.py", line 200, in encode
    chunks = self.iterencode(o, _one_shot=True)
  File "C:\Users\bojung\miniconda3\Lib\json\encoder.py", line 261, in iterencode
    return _iterencode(o, 0)
TypeError: keys must be str, int, float, bool or None, not tuple
[v21r] split failed (code 1); fix it and run the same command again
```
