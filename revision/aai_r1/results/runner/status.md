# v2.1 심사 대응 무인 실행 상태: 실행 중

- 시각 2026-10-16 11:33:55 (UTC 2026-10-16 02:33:55), 시도 16, 비컨 #85 (주기 10분, 명령 확인 2분마다, 명령 파일 `revision/aai_r1/commands/run.json`)
- 실행 코드: 2569576 v21r T: variants A0-A7 trained on the isolated corpus (seed 42)
- 현재 단계: thresholds (3.7분째)
- 마지막 출력 후: 0.0분
- GPU(사용 MiB, 전체 MiB, 사용률, 온도): 1597 MiB, 32607 MiB, 1 %, 41
- 다음 동작: 단계 진행
- 사유: 정기 보고
- 마지막으로 처리한 명령: 20261016T021319Z-rerun rerun (대기 끝, 재시도, 2026-10-16 02:13:44 UTC)
- 남은 단계: thresholds; routes; dev-guard-check; dev-guard; gate-diag-check; gate-diag; preview-check; preview; gate-review; matrix; nemo-doc; a8-check; a8; cost; analyze; release
- 끝난 단계(코드): record, nemo, approval, nemo-doc-early, unload-1, supp-check, supplement, audit, features, split, train

## 마지막 로그

```
    energy epoch 2 batch 400 loss 0.0069
    energy epoch 2 batch 600 loss 0.0065
    energy epoch 2 batch 800 loss 0.0280
    energy epoch 2 val AUROC 0.9849
    energy epoch 3 batch 0 loss 0.0351
    energy epoch 3 batch 200 loss 0.0049
    energy epoch 3 batch 400 loss 0.0010
    energy epoch 3 batch 600 loss 0.0012
    energy epoch 3 batch 800 loss 0.0184
    energy epoch 3 val AUROC 0.9854
Loading weights:   0%|          | 0/103 [00:00<?, ?it/s]Loading weights: 100%|██████████| 103/103 [00:00<00:00, 4908.74it/s]
    head epoch 1 batch 0 loss 1.0577
    head epoch 1 batch 200 loss 0.4437
    head epoch 1 batch 400 loss 0.2991
    head epoch 1 batch 600 loss 0.2367
    head epoch 1 batch 800 loss 0.3345
    head epoch 1 val loss 0.2694
    head epoch 2 batch 0 loss 0.3144
    head epoch 2 batch 200 loss 0.2700
    head epoch 2 batch 400 loss 0.2402
    head epoch 2 batch 600 loss 0.1603
    head epoch 2 batch 800 loss 0.3477
    head epoch 2 val loss 0.2445
    head epoch 3 batch 0 loss 0.2417
    head epoch 3 batch 200 loss 0.2432
    head epoch 3 batch 400 loss 0.2052
    head epoch 3 batch 600 loss 0.1378
    head epoch 3 batch 800 loss 0.2892
    head epoch 3 val loss 0.2460
{"neg_weight": 1.0, "row_weight": "sqrt_inverse_source_frequency", "row_weight_by_source": {"alpaca": 1.291, "beavertails": 1.292, "classical_dilemma": 3.649, "daily_dilemmas": 1.29, "dolly": 1.291, "hh_rlhf_harmless": 1.291, "hh_rlhf_helpful": 1.291, "hh_rlhf_redteam": 1.29, "jailbreak": 1.506, "moralchoice_highamb": 1.399, "narrative": 1.053, "supp:coconot_contrast": 1.936, "supp:falsereject_tra
[git] pushed to main

[v21r] ===== thresholds: thresholds of every variant on val, pushed before any answer =====
[ops] $ C:\Users\bojung\miniconda3\python.exe -u -m v21r thresholds
A0: {"harm": 3.169, "soft": 3.169, "F": 0.15, "extreme": 8.107, "Fref": 0.95, "I": 0.25, "Fblk": 0.45} stage1 {'harm_hb': 0.9316389132340053, 'safe_hb': 0.09979529170931423, 'met': True} cost 0.0885
A1: {"harm": 2.168, "soft": 2.168, "F": 0.35, "extreme": 6.175, "Fref": 0.9, "I": 2.0, "Fblk": 1.0} stage1 {'harm_hb': 0.9272567922874672, 'safe_hb': 0.09979529170931423, 'met': True} cost 0.1094
A2: {"harm": 3.733, "soft": 3.733, "F": 0.2, "extreme": 6.175, "Fref": 0.95, "I": 0.45, "Fblk": 0.5} stage1 {'harm_hb': 0.9255039439088519, 'safe_hb': 0.0977482088024565, 'met': True} cost 0.0894
A3: {"harm": 3.169, "soft": 3.169, "F": 0.25, "extreme": 6.175, "Fref": 0.9, "I": 0.45, "Fblk": 0.8} stage1 {'harm_hb': 0.9263803680981595, 'safe_hb': 0.0992835209825998, 'met': True} cost 0.1046
A5: {"Fhb": 0.5, "Fref": 0.5, "I": 0.3, "Fblk": 0.5} stage1 {'harm_hb': 0.8483786152497809, 'safe_hb': 0.08700102354145343, 'met': False} cost 0.1090
A6p: {"harm": 4.458, "soft": 4.458, "F": 0.05, "extreme": 5.174, "Fref": 0.95, "I": 0.25, "Fblk": 0.75} stage1 {'harm_hb': 0.9263803680981595, 'safe_hb': 0.09979529170931423, 'met': True} cost 0.0899
```
