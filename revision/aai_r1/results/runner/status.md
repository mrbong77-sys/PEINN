# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 14:26:43 (UTC 2026-10-16 05:26:43), 시도 23, 비컨 #111 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 25cb8b7 v21r T: variants A0-A7 trained on the isolated corpus (seed 42)
- 현재 단계: thresholds (7.7분째)
- 마지막 출력 후: 0.7분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1563 MiB, 32607 MiB, 0 %, 40
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T044500Z-rerun rerun (대기 끝, 재시도, 2026-10-16 04:46:20 UTC)
- 남은 단계: thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split, train

## 마지막 로그

```
    head epoch 3 batch 200 loss 0.2386
    head epoch 3 batch 400 loss 0.0931
    head epoch 3 batch 600 loss 0.2396
    head epoch 3 batch 800 loss 0.1661
    head epoch 3 batch 1000 loss 0.0953
    head epoch 3 batch 1200 loss 0.0149
    head epoch 3 batch 1400 loss 0.0815
    head epoch 3 batch 1600 loss 0.2796
    head epoch 3 val loss 0.2402
    head epoch 4 batch 0 loss 0.2417
    head epoch 4 batch 200 loss 0.2627
    head epoch 4 batch 400 loss 0.0761
    head epoch 4 batch 600 loss 0.1644
    head epoch 4 batch 800 loss 0.1265
    head epoch 4 batch 1000 loss 0.0904
    head epoch 4 batch 1200 loss 0.0032
    head epoch 4 batch 1400 loss 0.0741
    head epoch 4 batch 1600 loss 0.1843
    head epoch 4 val loss 0.2703
    head epoch 5 batch 0 loss 0.2088
    head epoch 5 batch 200 loss 0.2106
    head epoch 5 batch 400 loss 0.0011
    head epoch 5 batch 600 loss 0.1737
    head epoch 5 batch 800 loss 0.0689
    head epoch 5 batch 1000 loss 0.0793
    head epoch 5 batch 1200 loss 0.0008
    head epoch 5 batch 1400 loss 0.0758
    head epoch 5 batch 1600 loss 0.2225
    head epoch 5 val loss 0.2778
== A0ftM: A0ft with I raised to 1 for inputs out of the training distribution (DESIGN.md 20)
{"neg_weight": 1.0, "row_weight": "sqrt_inverse_source_frequency", "row_weight_by_source": {"alpaca": 1.829, "beavertails": 1.831, "classical_dilemma": 5.17, "daily_dilemmas": 1.828, "dolly": 1.829, "hh_rlhf_harmless": 1.829, "hh_rlhf_helpful": 1.829, "hh_rlhf_redteam": 1.828, "jailbreak": 2.134, "moralchoice_highamb": 1.983, "narrative": 1.493, "supp:coconot_contrast": 2.743, "supp:falsereject_tr
[git] pushed to main

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
A0: {"harm": 3.5, "soft": 3.5, "F": 0.2, "extreme": 5.75, "Fref": 0.95, "I": 0.2, "Fblk": 0.85} stage1 {'harm_hb': 0.9384615384615385, 'safe_hb': 0.09954508964409954, 'met': True} cost 0.0829
A1: {"harm": 3.5, "soft": 3.5, "F": 0.3, "extreme": 5.25, "Fref": 0.95, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9393162393162393, 'safe_hb': 0.09874230666309874, 'met': True} cost 0.0935
A2: {"harm": 4.0, "soft": 4.0, "F": 0.15, "extreme": 5.25, "Fref": 0.95, "I": 0.2, "Fblk": 0.35} stage1 {'harm_hb': 0.9371794871794872, 'safe_hb': 0.09927749531709927, 'met': True} cost 0.0849
A3: {"harm": 3.75, "soft": 3.75, "F": 0.2, "extreme": 5.25, "Fref": 0.95, "I": 0.85, "Fblk": 0.45} stage1 {'harm_hb': 0.9384615384615385, 'safe_hb': 0.09874230666309874, 'met': True} cost 0.0933
A5: {"Fhb": 0.45, "Fref": 0.45, "I": 0.35, "Fblk": 0.7} stage1 {'harm_hb': 0.8688034188034188, 'safe_hb': 0.09793952368209793, 'met': True} cost 0.1094
```
