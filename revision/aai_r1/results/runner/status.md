# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 12:39:05 (UTC 2026-10-16 03:39:05), 시도 19, 비컨 #95 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 99cbca3 station: 임무 실행 중
- 현재 단계: thresholds (5.7분째)
- 마지막 출력 후: 0.9분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1563 MiB, 32607 MiB, 0 %, 42
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T030740Z-rerun rerun (대기 끝, 재시도, 2026-10-16 03:08:48 UTC)
- 남은 단계: thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split, train

## 마지막 로그

```
    head epoch 1 val loss 0.2488
    head epoch 2 batch 0 loss 0.2389
    head epoch 2 batch 200 loss 0.2110
    head epoch 2 batch 400 loss 0.2546
    head epoch 2 batch 600 loss 0.3629
    head epoch 2 batch 800 loss 0.2660
    head epoch 2 batch 1000 loss 0.1320
    head epoch 2 val loss 0.2402
    head epoch 3 batch 0 loss 0.1620
    head epoch 3 batch 200 loss 0.1501
    head epoch 3 batch 400 loss 0.2073
    head epoch 3 batch 600 loss 0.3066
    head epoch 3 batch 800 loss 0.2472
    head epoch 3 batch 1000 loss 0.0866
    head epoch 3 val loss 0.2581
    head epoch 4 batch 0 loss 0.1435
    head epoch 4 batch 200 loss 0.1019
    head epoch 4 batch 400 loss 0.1038
    head epoch 4 batch 600 loss 0.2806
    head epoch 4 batch 800 loss 0.2230
    head epoch 4 batch 1000 loss 0.0484
    head epoch 4 val loss 0.2933
    head epoch 5 batch 0 loss 0.1301
    head epoch 5 batch 200 loss 0.1102
    head epoch 5 batch 400 loss 0.0968
    head epoch 5 batch 600 loss 0.1867
    head epoch 5 batch 800 loss 0.2222
    head epoch 5 batch 1000 loss 0.0322
    head epoch 5 val loss 0.3056
{"neg_weight": 1.0, "row_weight": "sqrt_inverse_source_frequency", "row_weight_by_source": {"alpaca": 1.465, "beavertails": 1.466, "classical_dilemma": 4.142, "daily_dilemmas": 1.464, "dolly": 1.465, "hh_rlhf_harmless": 1.465, "hh_rlhf_helpful": 1.465, "hh_rlhf_redteam": 1.464, "jailbreak": 1.709, "moralchoice_highamb": 1.588, "narrative": 1.196, "supp:coconot_contrast": 2.197, "supp:falsereject_t
[git] pushed to main

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
A0: {"harm": 1.28, "soft": 1.28, "F": 0.5, "extreme": 5.373, "Fref": 0.95, "I": 0.25, "Fblk": 0.55} stage1 {'harm_hb': 0.916030534351145, 'safe_hb': 0.09929577464788733, 'met': True} cost 0.0938
A1: {"harm": 2.445, "soft": 2.445, "F": 0.3, "extreme": 5.373, "Fref": 0.95, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9118667591950035, 'safe_hb': 0.09964788732394367, 'met': True} cost 0.1096
A2: {"harm": 2.445, "soft": 2.445, "F": 0.35, "extreme": 5.373, "Fref": 0.85, "I": 0.2, "Fblk": 0.6} stage1 {'harm_hb': 0.9118667591950035, 'safe_hb': 0.0982394366197183, 'met': True} cost 0.0944
A3: {"harm": 1.28, "soft": 1.28, "F": 0.55, "extreme": 5.373, "Fref": 0.95, "I": 0.2, "Fblk": 0.05} stage1 {'harm_hb': 0.9125607217210271, 'safe_hb': 0.09894366197183098, 'met': True} cost 0.1098
A5: {"Fhb": 0.5, "Fref": 0.5, "I": 0.2, "Fblk": 0.6} stage1 {'harm_hb': 0.8008327550312283, 'safe_hb': 0.09014084507042254, 'met': False} cost 0.1244
A6p: {"harm": 1.28, "soft": 1.28, "F": 0.35, "extreme": 6.45, "Fref": 0.95, "I": 0.2, "Fblk": 0.55} stage1 {'harm_hb': 0.9188063844552394, 'safe_hb': 0.09859154929577464, 'met': True} cost 0.0917
```
