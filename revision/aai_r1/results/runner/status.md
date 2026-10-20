# v2.1 심사 대응 무인 실행 상태: 완료

- 시각 2026-10-21 03:46:31 (UTC 2026-10-20 18:46:31), 시도 1, 비컨 #468 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: b227dec v21r release 2.2.2: A1ft-A3ft heads and A8 adapters (in parts), corpus split identifiers
- 현재 단계: release-extra (1.6분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 3416 MiB, 32607 MiB, 0 %, 39
- 다음 동작: 없음(모든 단계 끝)
- 사유: –
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: 없음
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8, ethics-diag-check, ethics-diag, finish-check, forced-export, gate-mem, gate-retrain, ftv-check, ftv, release-extra-check, release-extra

## 마지막 로그

```
[v21r] skip record (routing texts of the benches with a mock LLM): finished 2026-10-16 00:34:51
[v21r] skip supp-check (supplement, audit, features, split, train, thresholds, routes on the check cache (pre-test)): finished 2026-10-16 14:50:44
[v21r] skip supplement (public over-refusal and adversarial training sets (DESIGN.md 12)): finished 2026-10-16 13:48:36
[v21r] skip audit (isolation audit of the v4 corpus (guard + recorded texts)): finished 2026-10-16 13:48:41
[v21r] skip unload-1 (free the GPU (any Ollama model)): finished 2026-10-16 09:35:42
[v21r] skip features (frozen v2.1 features of the corpus and the routing texts): finished 2026-10-16 13:58:34
[v21r] skip split (embedding near-duplicates out, train / val / test split): finished 2026-10-16 13:58:38
[v21r] skip train (variants A0-A7 and the energy calibrator on the isolated corpus): finished 2026-10-16 15:11:08
[v21r] skip thresholds (thresholds of every variant on val, pushed before any answer): finished 2026-10-16 15:27:38
[v21r] skip routes (route tables of every variant and operating point): finished 2026-10-16 15:27:40
[v21r] skip nemo (NeMo Guardrails answers three probe prompts on every base): finished 2026-10-16 00:50:22
[v21r] skip approval (the professor's go for the full matrix): finished 2026-10-16 00:50:22
[v21r] skip nemo-doc-early (NeMo rail verdicts on the bases answered so far (CPU)): finished 2026-10-16 09:00:27
[v21r] skip dev-guard-check (Llama Guard input verdicts on 40 check rows (pre-test)): finished 2026-10-16 14:35:29
[v21r] skip dev-guard (Llama Guard input verdicts on the corpus test split (dev reference, DESIGN.md 14)): finished 2026-10-16 14:38:28
[v21r] skip gate-diag-check (gate diagnosis on the check cache first (pre-test, CPU)): finished 2026-10-16 15:27:41
[v21r] skip gate-diag (gate diagnosis: why the isolated gate blocks XSTest safe texts (CPU, counts only)): finished 2026-10-16 15:27:44
[v21r] skip preview-check (the preview on the check cache first (pre-test, CPU)): finished 2026-10-16 15:27:44
[v21r] skip preview (benchmark metrics of the fixed gate on qwen and gemma4, re-scored (CPU, no model call)): finished 2026-10-16 15:28:17
[v21r] skip gate-review (hold until the diagnosis is reviewed and the direction confirmed): finished 2026-10-16 15:28:17
[v21r] skip main-check (A0ftM@0.03 still meets UCR < 5 % and gate ORR < 5 % after the saved retrain (DESIGN.md 24)): finished 2026-10-16 15:28:18
[v21r] skip matrix-zephyr-check (zephyr with R2D2, NeMo and Llama Guard on the check benches first (pre-test; R2D2 has not run yet)): finished 2026-10-16 15:44:15
[v21r] skip r2d2-probe (R2D2 served as now vs its own template and Q8_0 on 30 non-benchmark prompts (DESIGN.md 25)): finished 2026-10-16 16:05:46
[v21r] skip ollama-list (the models Ollama holds and the R2D2 / zephyr builds (Eugene 17:51 KST, DESIGN.md 25)): finished 2026-10-16 17:53:51
[v21r] skip matrix-gemma3 (the matrix on gemma3 first (does not depend on the zephyr review, DESIGN.md 25)): finished 2026-10-16 23:13:16
[v21r] skip biomon-check (cheap-monitor bioweapons prompt on 3 items per group first (pre-test, DESIGN.md 26)): finished 2026-10-16 23:17:54
[v21r] skip biomon (cheap-monitor bioweapons prompt on PEINN, Vanilla, Llama Guard, NeMo, Shieldstral (outside the paper, Eugene 2026-10-16 16:43 KST: first after gemma3)): finished 2026-10-16 23:36:11
[v21r] skip nemo-orr (which XSTest safe prompts NeMo refuses and by which rail, on the bases answered so far (CPU; Eugene 2026-10-16 18:11 KST)): finished 2026-10-16 23:36:17
[v21r] skip nemo-audit (NeMo arm set-up audit: wrapper parameters, system prompt, answer format vs Vanilla (CPU; Eugene 2026-10-16 18:17 KST)): finished 2026-10-16 23:36:22
[v21r] skip nemo-reset-check (NeMo with the fixed provider: the qwen pre-test's 'others' tag set aside (DESIGN.md 29)): finished 2026-10-16 23:36:22
[v21r] skip matrix-nemo-check (the qwen pre-test's 'others' tag again (NeMo live, other arms from the stores)): finished 2026-10-16 23:40:37
[v21r] skip nemo-fair-review (NeMo calls carry NeMo's parameters; NeMo answered every check bench (DESIGN.md 29)): finished 2026-10-16 23:42:50
[v21r] skip r2d2-cpeg (R2D2 from the canonical checkpoint, unquantized, HarmBench prompt; the zephyr pre-test cache dropped (DESIGN.md 25)): finished 2026-10-17 00:36:42
[v21r] skip r2d2-fingerprint (how close each R2D2 build Ollama holds comes to the submitted H02 answers (12 XSTest safe prompts, greedy; record only)): finished 2026-10-17 00:37:26
[v21r] skip matrix-zephyr-check2 (the zephyr pre-test again with CPEG's R2D2 (check benches)): finished 2026-10-17 00:52:24
[v21r] skip zephyr-review (the zephyr pre-test's answers: every arm and tier, no errors, few empty (DESIGN.md 24)): finished 2026-10-17 00:52:24
[v21r] skip nemo-fair-review-zephyr (the same NeMo checks on the zephyr pre-test (DESIGN.md 29)): finished 2026-10-17 00:52:25
[v21r] skip nemo-reset (the 'others' tag of qwen, gemma4 and gemma3 set aside so NeMo runs again (DESIGN.md 29)): finished 2026-10-17 00:52:25
[v21r] skip matrix (PEINN forced to each tier + Vanilla, R2D2, NeMo, Llama Guard; generate then judge per base): finished 2026-10-17 10:04:06
[v21r] skip repeat-reset (bases with error rows in the 'others' tag: that tag set aside (DESIGN.md 30)): finished 2026-10-17 10:04:19
[v21r] skip matrix-repeat (the 'others' tag again with the Ollama repeat guard; stored answers reused (DESIGN.md 30)): finished 2026-10-17 11:18:09
[v21r] skip repeat-review (error rows before and after, calls the repeat guard answered (DESIGN.md 30)): finished 2026-10-17 11:18:22
[v21r] skip nemo-doc (NeMo rail verdicts per base from the driver's call log (R2)): finished 2026-10-17 10:04:11
[v21r] skip nemo-orr-all (NeMo's XSTest safe refusals by type and rail on every base (CPU)): finished 2026-10-17 11:18:27
[v21r] skip nemo-audit-all (NeMo set-up audit on the final answers of every base (CPU, DESIGN.md 29)): finished 2026-10-17 11:18:33
[v21r] skip cost (route cost per tier (gate time, calls, tokens)): finished 2026-10-17 13:21:39
[v21r] skip analyze (benchmark results, curves, calibration, I construct): finished 2026-10-17 13:22:49
[v21r] skip release (trained heads and calibrator -> results/checkpoints (data availability)): finished 2026-10-17 13:22:54
[v21r] skip repeat-diff ('others' answers and scores before and after the repeat-guard rerun (CPU)): finished 2026-10-17 13:31:59
[v21r] skip cost-gate (gate time again on one CPU thread (the first run used the GPU; DESIGN.md 9)): finished 2026-10-17 13:28:39
[v21r] skip analyze-cost (benchmark results again, with the CPU gate time): finished 2026-10-17 13:29:43
[v21r] skip nemo-orr-final (NeMo's XSTest safe refusals by rail, counted per prompt across runs (CPU)): finished 2026-10-17 13:40:17
[v21r] skip repeat-diff-means (each arm's metrics before and after the repeat-guard rerun (CPU, DESIGN.md 31)): finished 2026-10-17 13:40:21
[v21r] skip nemo-orr-detail (the logged NeMo calls of the XSTest safe prompts no rail event explains (CPU)): finished 2026-10-17 13:44:36
[v21r] skip nemo-orr-dialog (NeMo dialog calls whose user turn matches no XSTest safe prompt: examples (CPU)): finished 2026-10-17 13:46:53
[v21r] skip nemo-orr-totals (NeMo on all XSTest rows: fixed refusals against input blocks and 'ask harmful' dialogs (CPU)): finished 2026-10-17 13:51:12
[v21r] skip a8-check (A8 end to end on a 0.5B model and 24 items (catches path errors before the 7B run)): finished 2026-10-17 14:29:34
[v21r] skip ggb-export (every GGB answer of the reported systems with the pipeline's score (CPU)): finished 2026-10-17 14:47:23
[v21r] skip bench-export (every other bench's reported rows: answers, verdicts, scores (CPU, Eugene 2026-10-17 14:55 KST)): finished 2026-10-17 15:00:09
[v21r] skip bench-stats (every bench's statistics from the records, submitted definitions (CPU, DESIGN.md 34)): finished 2026-10-17 17:24:35
[v21r] skip cap-check (768-token first answers: pre-test on gemma4 MORABLES run 1 (stops the rest if it fails)): finished 2026-10-17 18:17:25
[v21r] skip cap-reset (Ethics, MORABLES and GGB set aside in every tag (answers kept in archive_cap384/)): finished 2026-10-17 18:17:25
[v21r] skip matrix-cap768 (Ethics, MORABLES and GGB again on every base; unchanged calls come from the stores): finished 2026-10-17 20:56:36
[v21r] skip analyze-cap768 (benchmark results again after the 768-token rerun): finished 2026-10-17 20:57:39
[v21r] skip ggb-export-cap768 (GGB answers again (CPU)): finished 2026-10-17 20:57:43
[v21r] skip ggb-rescore-cap768 (GGB re-scored again (CPU)): finished 2026-10-17 20:57:47
[v21r] skip bench-export-cap768 (every other bench's reported rows again (CPU)): finished 2026-10-17 20:57:57
[v21r] skip bench-stats-cap768 (every bench's statistics again (CPU, DESIGN.md 34)): finished 2026-10-17 20:58:03
[v21r] skip a8 (A8: LoRA on qwen2.5-7B with the same supervision; benches on the merged model): finished 2026-10-18 17:54:11
[v21r] skip analyze-a8 (benchmark results again, with the A8 row): finished 2026-10-18 17:55:14
[v21r] skip ggb-export-a8 (GGB answers again, with the A8 rows (CPU, DESIGN.md 32)): finished 2026-10-18 17:55:20
[v21r] skip ggb-rescore-a8 (GGB re-scored from the answer text, with A8 (CPU, DESIGN.md 32)): finished 2026-10-18 17:55:23
[v21r] skip bench-export-a8 (every other bench's reported rows again, with A8 (CPU)): finished 2026-10-18 17:55:34
[v21r] skip bench-stats-a8 (every bench's statistics again, with A8 (CPU, DESIGN.md 34)): finished 2026-10-18 17:55:40
[v21r] skip ethics-diag-check (R2D2 WVS and NeMo MFQ reproduction on 3 items each first (pre-test, DESIGN.md 36)): finished 2026-10-18 18:06:11
[v21r] skip ethics-diag (R2D2 WVS (replay, greedy, HF bf16 checkpoint) and NeMo MFQ self-check (replay, without the answer format): design or harness): finished 2026-10-18 18:16:50
[v21r] skip finish-check (forced export, gate memory and gate retraining on the check cache first (pre-test)): finished 2026-10-18 19:47:19
[v21r] skip forced-export (forced-tag rows, route tables, signals, val/test labels -> results/forced (CPU)): finished 2026-10-18 19:47:34
[v21r] skip gate-mem (A0ftM's whole input gate in one process: time and peak memory, GPU and one CPU thread): finished 2026-10-18 19:48:46
[v21r] skip gate-retrain (A0ftM's gate trained again from the same corpus into a scratch folder: time, memory): finished 2026-10-18 20:03:46
[v21r] skip ftv-check (A1-A3 fine-tuned heads on 64 rows, one epoch (pre-test; nothing pushed)): finished 2026-10-19 12:03:30
[v21r] skip ftv (A1-A3 heads with PEINN's fine-tuned MiniLM, thresholds on val, routes -> results/forced): finished 2026-10-19 12:29:55

[v21r] ===== release-extra-check: A1ft-A3ft heads, A8 adapters and split identifiers checked on a few rows first (pre-test; nothing pushed) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r release-extra --check
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4381.03it/s]
  A1ft: 600 texts, max |signal - published| 2.33e-06
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 3186.20it/s]
  A2ft: 600 texts, max |signal - published| 1.17e-06
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 2961.21it/s]
  A3ft: 600 texts, max |signal - published| 2.50e-06
  base Qwen/Qwen2.5-7B-Instruct@a09a354: index and the shards of 1 tensor(s) (cache first, else download)
  model.layers.23.self_attn.q_proj: {'equal': 1.0, 'changed': 11438595, 'equal_changed': 1.0}
  corpus_split_ids.csv.gz: 64986 rows {'train': 52569, 'test': 6211, 'val': 6206}, columns ['sha', 'split', 'source', 'file_role', 'polar', 'T', 'I', 'F', 'mask_T', 'mask_I', 'mask_F']
release-extra check: 3 heads, A8 adapter (392 tensors) and the identifiers pass

[v21r] ===== release-extra: A1ft-A3ft heads and A8 adapters (in parts), corpus split identifiers -> results =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r release-extra
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4080.99it/s]
  A1ft: 13938 texts, max |signal - published| 4.14e-06
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 3929.29it/s]
  A2ft: 13938 texts, max |signal - published| 1.85e-06
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4067.19it/s]
  A3ft: 13938 texts, max |signal - published| 4.53e-06
  base Qwen/Qwen2.5-7B-Instruct@a09a354: index and the shards of 3 tensor(s) (cache first, else download)
  model.layers.23.self_attn.q_proj: {'equal': 1.0, 'changed': 11438595, 'equal_changed': 1.0}
  model.layers.25.mlp.down_proj: {'equal': 1.0, 'changed': 55756997, 'equal_changed': 1.0}
  model.layers.27.self_attn.o_proj: {'equal': 1.0, 'changed': 11244549, 'equal_changed': 1.0}
  corpus_split_ids.csv.gz: 64986 rows {'train': 52569, 'test': 6211, 'val': 6206}, columns ['sha', 'split', 'source', 'file_role', 'polar', 'T', 'I', 'F', 'mask_T', 'mask_I', 'mask_F']
  A1ft_head.pt: 2 parts in checkpoints/ablation_ft/
  A2ft_head.pt: 2 parts in checkpoints/ablation_ft/
  A3ft_head.pt: 2 parts in checkpoints/ablation_ft/
  adapter.safetensors: 4 parts in checkpoints/a8/
[git] pushed to main

[v21r] all steps finished and pushed in 3.0 min
```
