# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {'harm': 2.243, 'soft': 2.243, 'F': 0.55, 'extreme': 6.041, 'Fref': 0.9, 'I': 0.3, 'Fblk': 0.45}

## 1. XSTest 증상

- 문장 수: {'safe': 108, 'unsafe': 83}
- AUROC(위험 > 안전): {'E_isolated': 0.8893, 'F_A0': 0.8191, 'E_shipped': 0.9838, 'F_shipped': 0.8366}

| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |
|---|---|---|---|---|
| 0.005 | 6 | 9 | 15 | 61 |
| 0.05 | 6 | 9 | 15 | 61 |
| 0.1 | 16 | 7 | 23 | 66 |
| 0.3 | 55 | 6 | 61 | 77 |

- E(격리) 안전 {'n': 108, 'mean': 2.434, 'p10': 0.013, 'p25': 0.12, 'p50': 1.426, 'p75': 3.564, 'p90': 6.87}
- E(격리) 위험 {'n': 83, 'mean': 7.918, 'p10': 3.084, 'p25': 6.361, 'p50': 9.707, 'p75': 9.887, 'p90': 9.966}
- F(A0) 안전 {'n': 108, 'mean': 0.213, 'p10': 0.0, 'p25': 0.003, 'p50': 0.024, 'p75': 0.373, 'p90': 0.81}

## 2. 출처별 라벨

| 출처 | 행 | F 라벨 있음 | 에너지 라벨 1 | polar F | polar F인데 라벨 0 | polar T인데 라벨 1 |
|---|---|---|---|---|---|---|
| alpaca | 800 | 2 | 2 | 2 | 0 | 0 |
| beavertails | 798 | 506 | 499 | 506 | 7 | 0 |
| classical_dilemma | 101 | 4 | 4 | 4 | 0 | 0 |
| daily_dilemmas | 800 | 11 | 11 | 11 | 0 | 0 |
| dolly | 799 | 1 | 1 | 1 | 0 | 0 |
| hh_rlhf_harmless | 799 | 574 | 571 | 574 | 3 | 0 |
| hh_rlhf_helpful | 799 | 1 | 1 | 1 | 0 | 0 |
| hh_rlhf_redteam | 800 | 614 | 611 | 614 | 3 | 0 |
| jailbreak | 587 | 446 | 446 | 446 | 0 | 0 |
| moralchoice_highamb | 680 | 52 | 52 | 52 | 0 | 0 |
| narrative | 1200 | 13 | 13 | 13 | 0 | 0 |
| supp:coconot_contrast | 377 | 377 | 0 | 0 | 0 | 0 |
| supp:falsereject_train | 2000 | 2000 | 0 | 0 | 0 | 0 |
| supp:orbench_80k | 3000 | 3000 | 0 | 0 | 0 | 0 |
| supp:orbench_toxic | 652 | 652 | 652 | 652 | 0 | 0 |
| supp:phtest_harmless | 500 | 500 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_adv_benign | 500 | 500 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_adv_harmful | 500 | 500 | 500 | 500 | 0 | 0 |
| supp:wildjailbreak_adv_benign | 1000 | 1000 | 0 | 0 | 0 | 0 |
| supp:wildjailbreak_adv_harmful | 1000 | 1000 | 1000 | 1000 | 0 | 0 |
| syn_advbenign | 294 | 44 | 44 | 44 | 0 | 0 |
| syn_benignsensitive | 602 | 26 | 26 | 26 | 0 | 0 |
| syn_cad | 754 | 0 | 0 | 0 | 0 | 0 |
| syn_intent | 800 | 441 | 441 | 441 | 0 | 0 |
| syn_subtleharm | 369 | 329 | 328 | 329 | 1 | 0 |
| toxicchat_safe | 697 | 20 | 19 | 20 | 1 | 0 |

## 3. 출처별 에너지와 차단 (val + test, 주 운영점)

| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |
|---|---|---|---|---|---|
| alpaca | 121 | 2 | 2 | 0 | 0.002 |
| beavertails | 120 | 19 | 18 | 63 | 4.389 |
| classical_dilemma | 16 | 0 | 0 | 0 | 0.11 |
| daily_dilemmas | 120 | 0 | 0 | 1 | 0.016 |
| dolly | 120 | 1 | 1 | 0 | 0.002 |
| hh_rlhf_harmless | 120 | 13 | 12 | 76 | 3.476 |
| hh_rlhf_helpful | 120 | 3 | 3 | 0 | 0.022 |
| hh_rlhf_redteam | 120 | 12 | 12 | 85 | 5.612 |
| jailbreak | 88 | 4 | 3 | 59 | 1.15 |
| moralchoice_highamb | 102 | 9 | 9 | 0 | 0.298 |
| narrative | 180 | 0 | 0 | 0 | 0.038 |
| supp:coconot_contrast | 75 | 7 | 7 | 0 | 0.016 |
| supp:falsereject_train | 400 | 21 | 20 | 0 | 0.023 |
| supp:orbench_80k | 600 | 41 | 34 | 0 | 0.065 |
| supp:orbench_toxic | 130 | 0 | 0 | 118 | None |
| supp:phtest_harmless | 100 | 11 | 9 | 0 | 0.213 |
| supp:wildguardmix_adv_benign | 100 | 44 | 38 | 0 | 3.173 |
| supp:wildguardmix_adv_harmful | 100 | 0 | 0 | 93 | None |
| supp:wildjailbreak_adv_benign | 200 | 46 | 39 | 0 | 1.129 |
| supp:wildjailbreak_adv_harmful | 200 | 0 | 0 | 179 | None |
| syn_advbenign | 45 | 7 | 5 | 6 | 0.134 |
| syn_benignsensitive | 90 | 2 | 2 | 4 | 0.008 |
| syn_cad | 113 | 0 | 0 | 0 | 0.002 |
| syn_intent | 120 | 1 | 1 | 63 | 0.036 |
| syn_subtleharm | 55 | 2 | 2 | 44 | 2.92 |
| toxicchat_safe | 105 | 3 | 2 | 1 | 0.03 |

## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)

- safe_blocked: 문장 23, 이웃 에너지 라벨 1 비율 0.5304, 출처 {'beavertails': 26, 'hh_rlhf_harmless': 16, 'hh_rlhf_redteam': 13, 'supp:falsereject_train': 9, 'supp:orbench_80k': 9, 'supp:wildjailbreak_adv_benign': 8, 'supp:coconot_contrast': 8, 'dolly': 6, 'syn_advbenign': 5, 'supp:wildjailbreak_adv_harmful': 4, 'hh_rlhf_helpful': 4, 'syn_benignsensitive': 3, 'syn_subtleharm': 1, 'syn_intent': 1, 'supp:wildguardmix_adv_harmful': 1, 'supp:wildguardmix_adv_benign': 1}
- safe_passed: 문장 85, 이웃 에너지 라벨 1 비율 0.2753, 출처 {'beavertails': 55, 'supp:coconot_contrast': 53, 'supp:falsereject_train': 41, 'hh_rlhf_harmless': 41, 'supp:wildjailbreak_adv_benign': 32, 'dolly': 31, 'supp:orbench_80k': 31, 'hh_rlhf_redteam': 29, 'hh_rlhf_helpful': 18, 'syn_advbenign': 12, 'syn_subtleharm': 12, 'supp:phtest_harmless': 12, 'alpaca': 11, 'toxicchat_safe': 10, 'supp:wildguardmix_adv_benign': 10, 'syn_benignsensitive': 6, 'syn_intent': 5, 'supp:orbench_toxic': 5, 'syn_cad': 4, 'classical_dilemma': 2, 'jailbreak': 2, 'daily_dilemmas': 1, 'narrative': 1, 'supp:wildjailbreak_adv_harmful': 1}
- unsafe: 문장 83, 이웃 에너지 라벨 1 비율 0.7205, 출처 {'beavertails': 134, 'hh_rlhf_harmless': 67, 'supp:falsereject_train': 46, 'hh_rlhf_redteam': 43, 'supp:orbench_toxic': 25, 'supp:orbench_80k': 20, 'syn_intent': 18, 'syn_subtleharm': 17, 'supp:wildjailbreak_adv_benign': 7, 'supp:wildjailbreak_adv_harmful': 6, 'daily_dilemmas': 5, 'dolly': 5, 'toxicchat_safe': 5, 'supp:coconot_contrast': 5, 'syn_advbenign': 4, 'syn_benignsensitive': 3, 'hh_rlhf_helpful': 2, 'moralchoice_highamb': 1, 'supp:wildguardmix_adv_harmful': 1, 'classical_dilemma': 1}
