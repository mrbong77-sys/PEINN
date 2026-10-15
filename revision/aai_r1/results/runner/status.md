# v2.1 심사 대응 무인 실행 상태: 실패 후 대기

- 시각 2026-10-16 00:55:26 (UTC 2026-10-15 15:55:26), 시도 2, 비컨 #4 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 716becd station: 임무 실행 중
- 현재 단계: matrix (5.1분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1693 MiB, 32607 MiB, 0 %, 37
- 다음 동작: 새 코드나 명령을 기다림
- 사유: 코드 1
- 마지막으로 처리한 명령: 없음
- 남은 단계: matrix; cost; analyze
- 끝난 단계(코드): record, audit, unload-1, features, split, train, thresholds, routes, nemo, approval

## 마지막 로그

```
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
verifying sha256 digest ⠴ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠦ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠧ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠇ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
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
verifying sha256 digest ⠴ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠦ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠧ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠇ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
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
verifying sha256 digest ⠴ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠦ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠧ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠇ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
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
verifying sha256 digest ⠴ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest ⠦ [K[?25h[?2026l[?2026h[?25l[A[A[A[A[1Gpulling manifest [K
pulling 13576eb6dd8d: 100% ▕██████████████████▏ 7.3 GB                         [K
pulling 4abe4caf8e68: 100% ▕██████████████████▏ 854 MB                         [K
pulling fe25b92561cf: 100% ▕██████████████████▏  145 B                         [K
verifying sha256 digest [K
writing manifest [K
success [K[?25h[?2026l
  ollama pull zephyr-r2d2:latest
[?2026h[?25l[1Gpulling manifest ⠋ [K[?25h[?2026l[?2026h[?25l[1Gpulling manifest ⠙ [K[?25h[?2026l[?2026h[?25l[1Gpulling manifest ⠹ [K[?25h[?2026l[?2026h[?25l[1Gpulling manifest ⠸ [K[?25h[?2026l[?2026h[?25l[1Gpulling manifest ⠼ [K[?25h[?2026l[?2026h[?25l[1Gpulling manifest ⠴ [K[?25h[?2026l[?2026h[?25l[1Gpulling manifest [K[?25h[?2026l
Error: pull model manifest: file does not exist
ollama pull zephyr-r2d2:latest failed
[v21r] matrix failed (code 1); fix it and run the same command again
```
