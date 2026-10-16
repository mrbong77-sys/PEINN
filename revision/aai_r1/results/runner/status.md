# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 13:07:05 (UTC 2026-10-16 04:07:05), 시도 20, 비컨 #99 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 3ef5333 v21r T: variants A0-A7 trained on the isolated corpus (seed 42)
- 현재 단계: thresholds (2.8분째)
- 마지막 출력 후: 0.7분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1567 MiB, 32607 MiB, 0 %, 41
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T034603Z-rerun rerun (대기 끝, 재시도, 2026-10-16 03:46:53 UTC)
- 남은 단계: thresholds; routes; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supplement, audit, features, split, dev-guard-check, dev-guard, supp-check, train

## 마지막 로그

```
    head epoch 1 batch 800 loss 0.4311
    head epoch 1 batch 1000 loss 0.1454
    head epoch 1 val loss 0.2489
    head epoch 2 batch 0 loss 0.2414
    head epoch 2 batch 200 loss 0.2155
    head epoch 2 batch 400 loss 0.2585
    head epoch 2 batch 600 loss 0.3652
    head epoch 2 batch 800 loss 0.2637
    head epoch 2 batch 1000 loss 0.1327
    head epoch 2 val loss 0.2413
    head epoch 3 batch 0 loss 0.1636
    head epoch 3 batch 200 loss 0.1449
    head epoch 3 batch 400 loss 0.2017
    head epoch 3 batch 600 loss 0.3070
    head epoch 3 batch 800 loss 0.2442
    head epoch 3 batch 1000 loss 0.0915
    head epoch 3 val loss 0.2563
    head epoch 4 batch 0 loss 0.1402
    head epoch 4 batch 200 loss 0.0950
    head epoch 4 batch 400 loss 0.1044
    head epoch 4 batch 600 loss 0.2877
    head epoch 4 batch 800 loss 0.2253
    head epoch 4 batch 1000 loss 0.0559
    head epoch 4 val loss 0.2889
    head epoch 5 batch 0 loss 0.1299
    head epoch 5 batch 200 loss 0.1101
    head epoch 5 batch 400 loss 0.1022
    head epoch 5 batch 600 loss 0.1872
    head epoch 5 batch 800 loss 0.2177
    head epoch 5 batch 1000 loss 0.0324
    head epoch 5 val loss 0.3041
== A0ftM: A0ft with I raised to 1 for inputs out of the training distribution (DESIGN.md 20)
{"neg_weight": 1.0, "row_weight": "sqrt_inverse_source_frequency", "row_weight_by_source": {"alpaca": 1.465, "beavertails": 1.466, "classical_dilemma": 4.142, "daily_dilemmas": 1.464, "dolly": 1.465, "hh_rlhf_harmless": 1.465, "hh_rlhf_helpful": 1.465, "hh_rlhf_redteam": 1.464, "jailbreak": 1.709, "moralchoice_highamb": 1.588, "narrative": 1.196, "supp:coconot_contrast": 2.197, "supp:falsereject_t
[git] pushed to main

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
A0: {"harm": 1.28, "soft": 1.28, "F": 0.5, "extreme": 5.373, "Fref": 0.95, "I": 0.25, "Fblk": 0.55} stage1 {'harm_hb': 0.916030534351145, 'safe_hb': 0.09929577464788733, 'met': True} cost 0.0938
A1: {"harm": 2.445, "soft": 2.445, "F": 0.3, "extreme": 5.373, "Fref": 0.95, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9118667591950035, 'safe_hb': 0.09964788732394367, 'met': True} cost 0.1096
A2: {"harm": 2.445, "soft": 2.445, "F": 0.35, "extreme": 5.373, "Fref": 0.85, "I": 0.2, "Fblk": 0.6} stage1 {'harm_hb': 0.9118667591950035, 'safe_hb': 0.0982394366197183, 'met': True} cost 0.0944
```
