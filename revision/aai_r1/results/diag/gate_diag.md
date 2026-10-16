# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {'harm': 5.44, 'soft': 5.44, 'F': 0.8, 'extreme': 6.517, 'Fref': 0.95, 'I': 0.35, 'Fblk': 0.95}

## 1. XSTest 증상

- 문장 수: {'safe': 108, 'unsafe': 83}
- AUROC(위험 > 안전): {'E_isolated': 0.9253, 'F_A0': 0.7252, 'E_shipped': 0.9838, 'F_shipped': 0.8366}

| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |
|---|---|---|---|---|
| 0.005 | 19 | 19 | 38 | 80 |
| 0.05 | 19 | 19 | 38 | 80 |
| 0.1 | 39 | 13 | 52 | 82 |
| 0.3 | 19 | 65 | 84 | 83 |

- E(격리) 안전 {'n': 108, 'mean': 5.421, 'p10': 2.392, 'p25': 3.733, 'p50': 5.561, 'p75': 7.111, 'p90': 8.168}
- E(격리) 위험 {'n': 83, 'mean': 8.747, 'p10': 7.37, 'p25': 8.354, 'p50': 8.989, 'p75': 9.519, 'p90': 9.706}
- F(A0) 안전 {'n': 108, 'mean': 0.86, 'p10': 0.776, 'p25': 0.817, 'p50': 0.862, 'p75': 0.911, 'p90': 0.949}

## 2. 출처별 라벨

| 출처 | 행 | F 라벨 있음 | 에너지 라벨 1 | polar F | polar F인데 라벨 0 | polar T인데 라벨 1 |
|---|---|---|---|---|---|---|
| alpaca | 800 | 2 | 2 | 2 | 0 | 0 |
| beavertails | 798 | 506 | 499 | 506 | 7 | 0 |
| benign_harm_discuss | 322 | 8 | 8 | 8 | 0 | 0 |
| classical_dilemma | 101 | 4 | 4 | 4 | 0 | 0 |
| daily_dilemmas | 800 | 11 | 11 | 11 | 0 | 0 |
| dolly | 799 | 1 | 1 | 1 | 0 | 0 |
| hh_rlhf_harmless | 799 | 574 | 571 | 574 | 3 | 0 |
| hh_rlhf_helpful | 799 | 1 | 1 | 1 | 0 | 0 |
| hh_rlhf_redteam | 800 | 614 | 611 | 614 | 3 | 0 |
| jailbreak | 587 | 446 | 446 | 446 | 0 | 0 |
| moralchoice_highamb | 680 | 52 | 52 | 52 | 0 | 0 |
| narrative | 1200 | 13 | 13 | 13 | 0 | 0 |
| syn_advbenign | 294 | 44 | 44 | 44 | 0 | 0 |
| syn_benignsensitive | 602 | 26 | 26 | 26 | 0 | 0 |
| syn_cad | 754 | 0 | 0 | 0 | 0 | 0 |
| syn_intent | 800 | 441 | 441 | 441 | 0 | 0 |
| syn_subtleharm | 369 | 329 | 328 | 329 | 1 | 0 |
| toxicchat_safe | 697 | 20 | 19 | 20 | 1 | 0 |
| trick_safe | 509 | 178 | 178 | 178 | 0 | 0 |

## 3. 출처별 에너지와 차단 (val + test, 주 운영점)

| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |
|---|---|---|---|---|---|
| alpaca | 121 | 2 | 1 | 0 | 0.729 |
| beavertails | 120 | 28 | 21 | 71 | 6.389 |
| benign_harm_discuss | 48 | 2 | 0 | 0 | 2.331 |
| classical_dilemma | 16 | 3 | 2 | 0 | 3.835 |
| daily_dilemmas | 120 | 1 | 1 | 1 | 1.504 |
| dolly | 120 | 1 | 1 | 0 | 1.0 |
| hh_rlhf_harmless | 120 | 17 | 15 | 81 | 5.512 |
| hh_rlhf_helpful | 120 | 8 | 5 | 0 | 1.464 |
| hh_rlhf_redteam | 120 | 16 | 12 | 88 | 6.209 |
| jailbreak | 88 | 9 | 4 | 61 | 4.357 |
| moralchoice_highamb | 102 | 13 | 5 | 1 | 4.183 |
| narrative | 180 | 2 | 0 | 0 | 2.689 |
| syn_advbenign | 45 | 11 | 11 | 5 | 4.12 |
| syn_benignsensitive | 90 | 8 | 2 | 4 | 0.95 |
| syn_cad | 113 | 2 | 0 | 0 | 0.921 |
| syn_intent | 120 | 5 | 3 | 66 | 1.311 |
| syn_subtleharm | 55 | 4 | 4 | 47 | 7.945 |
| toxicchat_safe | 105 | 6 | 4 | 1 | 1.649 |
| trick_safe | 77 | 9 | 4 | 24 | 3.389 |

## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)

- safe_blocked: 문장 52, 이웃 에너지 라벨 1 비율 0.6038, 출처 {'trick_safe': 115, 'beavertails': 49, 'hh_rlhf_harmless': 29, 'hh_rlhf_redteam': 16, 'dolly': 9, 'syn_advbenign': 8, 'benign_harm_discuss': 7, 'syn_subtleharm': 6, 'hh_rlhf_helpful': 6, 'syn_benignsensitive': 4, 'syn_intent': 4, 'moralchoice_highamb': 2, 'syn_cad': 2, 'toxicchat_safe': 1, 'narrative': 1, 'jailbreak': 1}
- safe_passed: 문장 56, 이웃 에너지 라벨 1 비율 0.3929, 출처 {'trick_safe': 79, 'beavertails': 29, 'dolly': 27, 'hh_rlhf_helpful': 23, 'hh_rlhf_harmless': 21, 'benign_harm_discuss': 21, 'syn_subtleharm': 14, 'syn_advbenign': 13, 'alpaca': 12, 'hh_rlhf_redteam': 12, 'syn_intent': 9, 'syn_benignsensitive': 6, 'toxicchat_safe': 5, 'syn_cad': 3, 'jailbreak': 3, 'narrative': 1, 'classical_dilemma': 1, 'daily_dilemmas': 1}
- unsafe: 문장 83, 이웃 에너지 라벨 1 비율 0.8723, 출처 {'beavertails': 135, 'trick_safe': 96, 'hh_rlhf_harmless': 71, 'hh_rlhf_redteam': 42, 'benign_harm_discuss': 16, 'syn_intent': 16, 'syn_subtleharm': 13, 'syn_advbenign': 6, 'hh_rlhf_helpful': 5, 'daily_dilemmas': 3, 'syn_benignsensitive': 3, 'toxicchat_safe': 3, 'dolly': 3, 'classical_dilemma': 2, 'syn_cad': 1}
