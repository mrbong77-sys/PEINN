# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-18 18:06:01 (UTC 2026-10-18 09:06:01), 시도 4, 비컨 #453 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 0f08373 station: 임무 실행 중
- 현재 단계: ethics-diag-check (10.4분째)
- 마지막 출력 후: 0.2분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 15681 MiB, 32607 MiB, 0 %, 42
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261018T052300Z-restart restart (자식 종료 후 재실행, 2026-10-18 05:23:59 UTC)
- 남은 단계: ethics-diag-check; ethics-diag
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train, thresholds, routes, gate-diag-check, gate-diag, preview-check, preview, gate-review, main-check, matrix-zephyr-check, r2d2-probe, ollama-list, matrix-gemma3, biomon-check, biomon, nemo-orr, nemo-audit, nemo-reset-check, matrix-nemo-check, nemo-fair-review, r2d2-cpeg, r2d2-fingerprint, matrix-zephyr-check2, zephyr-review, nemo-fair-review-zephyr, nemo-reset, matrix, nemo-doc, repeat-reset, matrix-repeat, repeat-review, nemo-orr-all, nemo-audit-all, cost, analyze, release, cost-gate, analyze-cost, repeat-diff, nemo-orr-final, repeat-diff-means, nemo-orr-detail, nemo-orr-dialog, nemo-orr-totals, a8-check, ggb-export, bench-export, bench-stats, cap-check, cap-reset, matrix-cap768, analyze-cap768, ggb-export-cap768, ggb-rescore-cap768, bench-export-cap768, bench-stats-cap768, a8, analyze-a8, ggb-export-a8, ggb-rescore-a8, bench-export-a8, bench-stats-a8

## 마지막 로그

```
verifying sha256 digest ⠏ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠋ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠙ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠹ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠸ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠼ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest [K
writing manifest ⠋ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest [K
writing manifest [K
success [K[?25h[?2026l
NeMo qwen MFQ: {'items': 3, 'logged': 3, 'logged_blocked': 2, 'replay_same_reply': 2, 'replay_same_verdict': 2, 'replay_blocked': 1, 'replay_not_yes_no': 1, 'replay_not_yes_no_blocked': 1, 'no_format_yes_no': 3, 'no_format_blocked': 0} -> unclear
NeMo gemma4 MFQ: {'items': 3, 'logged': 3, 'logged_blocked': 0, 'replay_same_reply': 0, 'replay_same_verdict': 0, 'replay_blocked': 3, 'replay_not_yes_no': 3, 'replay_not_yes_no_blocked': 3, 'no_format_yes_no': 0, 'no_format_blocked': 3} -> unclear
NeMo gemma3 MFQ: {'items': 3, 'logged': 3, 'logged_blocked': 3, 'replay_same_reply': 3, 'replay_same_verdict': 3, 'replay_blocked': 3, 'replay_not_yes_no': 3, 'replay_not_yes_no_blocked': 3, 'no_format_yes_no': 3, 'no_format_blocked': 0} -> design
NeMo zephyr MFQ: {'items': 3, 'logged': 3, 'logged_blocked': 3, 'replay_same_reply': 3, 'replay_same_verdict': 3, 'replay_blocked': 3, 'replay_not_yes_no': 3, 'replay_not_yes_no_blocked': 3, 'no_format_yes_no': 3, 'no_format_blocked': 0} -> design
R2D2 WVS: 14 rows, 3 items, system prompt non-empty 0
Fetching 10 files:   0%|          | 0/10 [00:00<?, ?it/s]Fetching 10 files: 100%|██████████| 10/10 [00:00<00:00, 567.00it/s]
[transformers] `torch_dtype` is deprecated! Use `dtype` instead!
Loading weights:   0%|          | 0/291 [00:00<?, ?it/s]Loading weights:   2%|▏         | 6/291 [00:00<00:05, 47.89it/s]Loading weights:   4%|▍         | 11/291 [00:00<00:07, 37.20it/s]Loading weights:   6%|▌         | 18/291 [00:00<00:06, 42.73it/s]Loading weights:   8%|▊         | 23/291 [00:00<00:09, 28.84it/s]Loading weights:   9%|▉         | 27/291 [00:00<00:11, 22.62it/s]Loading weigh
```
