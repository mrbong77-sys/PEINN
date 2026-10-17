# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-17 22:53:28 (UTC 2026-10-17 13:53:28), 시도 2, 비컨 #335 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 12c5bca station: 임무 실행 중
- 현재 단계: a8 (115.4분째)
- 마지막 출력 후: 2.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 6684 MiB, 32607 MiB, 91 %, 69
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261017T091200Z-restart restart (자식 종료 후 재실행, 2026-10-17 09:10:54 UTC)
- 남은 단계: a8; analyze-a8; ggb-export-a8; ggb-rescore-a8; bench-export-a8; bench-stats-a8
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768

## 마지막 로그

```
[git] pushed to main

[v21r] ===== a8: A8: LoRA on qwen2.5-7B with the same supervision; benches on the merged model =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r a8
A8 targets: 58775 items ({'safe': 35467, 'harm': 21843, 'dilemma': 1465}), 55902 to do
  no target for 0c63f2d7ad (safe): HTTPError: HTTP Error 500: Internal Server Error
  200/55902
  400/55902
  600/55902
  800/55902
  1000/55902
  1200/55902
  1400/55902
  1600/55902
  1800/55902
  2000/55902
  2200/55902
  2400/55902
  2600/55902
  2800/55902
  3000/55902
  3200/55902
  3400/55902
  3600/55902
  3800/55902
  4000/55902
  4200/55902
  4400/55902
  4600/55902
  4800/55902
  5000/55902
  5200/55902
  5400/55902
  5600/55902
  5800/55902
  6000/55902
  6200/55902
  6400/55902
  6600/55902
  6800/55902
```
