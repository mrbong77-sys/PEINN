# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-17 17:54:44 (UTC 2026-10-17 08:54:44), 시도 1, 비컨 #304 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: a1f8cdd station: 임무 실행 중
- 현재 단계: a8 (30.1분째)
- 마지막 출력 후: 1.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 7187 MiB, 32607 MiB, 92 %, 68
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261017T071000Z-update update (대기 끝, 재시도, 2026-10-17 04:51:04 UTC)
- 남은 단계: a8; analyze-a8; ggb-export-a8; ggb-rescore-a8; bench-export-a8; bench-stats-a8; cap-check; cap-reset; matrix-cap768; analyze-cap768; ggb-export-cap768; ggb-rescore-cap768; bench-export-cap768; bench-stats-cap768
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats

## 마지막 로그

```
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

[v21r] ===== bench-stats: every bench's statistics from the records, submitted definitions (CPU, DESIGN.md 34) =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r bench-stats
  qwen: LlamaGuard UCR 4.1 ORR 6.4, NeMo UCR 5.17 ORR 24.0, PEINN UCR 3.5 ORR 6.4, Vanilla UCR 20.03 ORR 2.4
  gemma4: LlamaGuard UCR 3.3 ORR 13.6, NeMo UCR 0.4 ORR 43.2, PEINN UCR 1.33 ORR 12.0, Vanilla UCR 13.33 ORR 10.4
  gemma3: LlamaGuard UCR 3.57 ORR 12.0, NeMo UCR 2.23 ORR 49.6, PEINN UCR 2.87 ORR 10.4, Vanilla UCR 24.87 ORR 4.8
  zephyr: LlamaGuard UCR 6.33 ORR 5.6, NeMo UCR 8.73 ORR 33.6, PEINN UCR 3.07 ORR 4.8, R2D2 UCR 12.63 ORR 23.2, Vanilla UCR 60.1 ORR 0.8
[git] pushed to main

[v21r] ===== a8: A8: LoRA on qwen2.5-7B with the same supervision; benches on the merged model =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r a8
A8 targets: 58775 items ({'safe': 35467, 'harm': 21843, 'dilemma': 1465}), 58775 to do
  200/58775
  400/58775
  600/58775
  800/58775
  1000/58775
  1200/58775
  1400/58775
  1600/58775
  1800/58775
```
