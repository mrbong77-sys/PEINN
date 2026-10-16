# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {'harm': 3.159, 'soft': 3.159, 'F': 0.45, 'extreme': 5.205, 'Fref': 0.85, 'I': 0.2, 'Fblk': 0.6}

## 1. XSTest 증상

- 문장 수: {'safe': 108, 'unsafe': 83}
- AUROC(위험 > 안전): {'E_isolated': 0.8726, 'F_A0': 0.8169, 'E_shipped': 0.9838, 'F_shipped': 0.8366}

| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |
|---|---|---|---|---|
| 0.005 | 15 | 17 | 32 | 65 |
| 0.05 | 19 | 15 | 34 | 67 |
| 0.1 | 51 | 4 | 55 | 76 |
| 0.3 | 74 | 4 | 78 | 81 |

- E(격리) 안전 {'n': 108, 'mean': 4.87, 'p10': 1.614, 'p25': 2.92, 'p50': 5.08, 'p75': 6.52, 'p90': 8.073}
- E(격리) 위험 {'n': 83, 'mean': 8.189, 'p10': 5.524, 'p25': 7.415, 'p50': 8.851, 'p75': 9.487, 'p90': 9.697}
- F(A0) 안전 {'n': 108, 'mean': 0.289, 'p10': 0.001, 'p25': 0.01, 'p50': 0.106, 'p75': 0.573, 'p90': 0.83}

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
| syn_advbenign | 294 | 44 | 44 | 44 | 0 | 0 |
| syn_benignsensitive | 602 | 26 | 26 | 26 | 0 | 0 |
| syn_cad | 754 | 0 | 0 | 0 | 0 | 0 |
| syn_intent | 800 | 441 | 441 | 441 | 0 | 0 |
| syn_subtleharm | 369 | 329 | 328 | 329 | 1 | 0 |
| toxicchat_safe | 697 | 20 | 19 | 20 | 1 | 0 |

## 3. 출처별 에너지와 차단 (val + test, 주 운영점)

| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |
|---|---|---|---|---|---|
| alpaca | 121 | 3 | 3 | 0 | 0.485 |
| beavertails | 120 | 25 | 24 | 71 | 5.725 |
| classical_dilemma | 16 | 2 | 2 | 1 | 3.074 |
| daily_dilemmas | 120 | 1 | 1 | 1 | 0.839 |
| dolly | 120 | 1 | 1 | 0 | 0.631 |
| hh_rlhf_harmless | 120 | 19 | 17 | 82 | 5.224 |
| hh_rlhf_helpful | 120 | 11 | 9 | 0 | 0.89 |
| hh_rlhf_redteam | 120 | 20 | 17 | 89 | 6.004 |
| jailbreak | 88 | 10 | 9 | 64 | 3.968 |
| moralchoice_highamb | 102 | 16 | 16 | 1 | 2.297 |
| narrative | 180 | 2 | 2 | 0 | 1.978 |
| syn_advbenign | 45 | 14 | 13 | 6 | 3.471 |
| syn_benignsensitive | 90 | 6 | 5 | 4 | 0.669 |
| syn_cad | 113 | 0 | 0 | 0 | 0.736 |
| syn_intent | 120 | 5 | 5 | 65 | 0.99 |
| syn_subtleharm | 55 | 4 | 4 | 48 | 6.716 |
| toxicchat_safe | 105 | 7 | 6 | 2 | 1.227 |

## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)

- safe_blocked: 문장 55, 이웃 에너지 라벨 1 비율 0.6727, 출처 {'beavertails': 90, 'hh_rlhf_harmless': 58, 'hh_rlhf_redteam': 40, 'dolly': 18, 'syn_subtleharm': 14, 'syn_advbenign': 12, 'hh_rlhf_helpful': 11, 'syn_intent': 8, 'syn_benignsensitive': 6, 'syn_cad': 6, 'toxicchat_safe': 4, 'alpaca': 3, 'jailbreak': 2, 'narrative': 1, 'daily_dilemmas': 1, 'moralchoice_highamb': 1}
- safe_passed: 문장 53, 이웃 에너지 라벨 1 비율 0.3509, 출처 {'beavertails': 50, 'dolly': 40, 'hh_rlhf_harmless': 31, 'hh_rlhf_redteam': 29, 'hh_rlhf_helpful': 29, 'alpaca': 15, 'syn_advbenign': 14, 'syn_intent': 12, 'toxicchat_safe': 10, 'syn_subtleharm': 9, 'syn_benignsensitive': 6, 'moralchoice_highamb': 4, 'daily_dilemmas': 4, 'syn_cad': 3, 'classical_dilemma': 3, 'narrative': 3, 'jailbreak': 3}
- unsafe: 문장 83, 이웃 에너지 라벨 1 비율 0.8313, 출처 {'beavertails': 165, 'hh_rlhf_harmless': 89, 'hh_rlhf_redteam': 56, 'syn_subtleharm': 30, 'syn_intent': 25, 'daily_dilemmas': 9, 'dolly': 8, 'syn_advbenign': 7, 'syn_benignsensitive': 6, 'hh_rlhf_helpful': 5, 'toxicchat_safe': 5, 'classical_dilemma': 4, 'moralchoice_highamb': 2, 'alpaca': 2, 'jailbreak': 1, 'syn_cad': 1}
