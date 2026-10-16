# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {'harm': 3.169, 'soft': 3.169, 'F': 0.15, 'extreme': 8.107, 'Fref': 0.95, 'I': 0.25, 'Fblk': 0.45}

## 1. XSTest 증상

- 문장 수: {'safe': 108, 'unsafe': 83}
- AUROC(위험 > 안전): {'E_isolated': 0.9357, 'F_A0': 0.851, 'E_shipped': 0.9838, 'F_shipped': 0.8366}

| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |
|---|---|---|---|---|
| 0.005 | 1 | 4 | 5 | 57 |
| 0.05 | 3 | 3 | 6 | 58 |
| 0.1 | 3 | 7 | 10 | 62 |
| 0.3 | 22 | 1 | 23 | 75 |

- E(격리) 안전 {'n': 108, 'mean': 1.277, 'p10': 0.03, 'p25': 0.089, 'p50': 0.395, 'p75': 1.511, 'p90': 4.219}
- E(격리) 위험 {'n': 83, 'mean': 7.352, 'p10': 2.265, 'p25': 5.424, 'p50': 8.965, 'p75': 9.607, 'p90': 9.828}
- F(A0) 안전 {'n': 108, 'mean': 0.167, 'p10': 0.0, 'p25': 0.002, 'p50': 0.015, 'p75': 0.177, 'p90': 0.664}

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
| supp:wildguardmix_van_benign | 1993 | 1993 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_van_harmful | 1984 | 1984 | 1984 | 1984 | 0 | 0 |
| supp:wildjailbreak_adv_benign | 1000 | 1000 | 0 | 0 | 0 | 0 |
| supp:wildjailbreak_adv_harmful | 1000 | 1000 | 1000 | 1000 | 0 | 0 |
| supp:wildjailbreak_van_benign | 4994 | 4994 | 0 | 0 | 0 | 0 |
| supp:wildjailbreak_van_harmful | 4999 | 4999 | 4999 | 4999 | 0 | 0 |
| syn_advbenign | 294 | 44 | 44 | 44 | 0 | 0 |
| syn_benignsensitive | 602 | 26 | 26 | 26 | 0 | 0 |
| syn_cad | 754 | 0 | 0 | 0 | 0 | 0 |
| syn_intent | 800 | 441 | 441 | 441 | 0 | 0 |
| syn_subtleharm | 369 | 329 | 328 | 329 | 1 | 0 |
| toxicchat_safe | 697 | 20 | 19 | 20 | 1 | 0 |

## 3. 출처별 에너지와 차단 (val + test, 주 운영점)

| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |
|---|---|---|---|---|---|
| alpaca | 121 | 6 | 2 | 0 | 0.095 |
| beavertails | 120 | 14 | 7 | 65 | 3.061 |
| classical_dilemma | 16 | 0 | 0 | 1 | 0.39 |
| daily_dilemmas | 120 | 0 | 0 | 1 | 0.088 |
| dolly | 120 | 3 | 0 | 0 | 0.045 |
| hh_rlhf_harmless | 120 | 15 | 8 | 76 | 5.168 |
| hh_rlhf_helpful | 120 | 3 | 1 | 0 | 0.077 |
| hh_rlhf_redteam | 120 | 18 | 8 | 85 | 5.711 |
| jailbreak | 88 | 6 | 3 | 62 | 1.52 |
| moralchoice_highamb | 102 | 3 | 0 | 1 | 0.532 |
| narrative | 180 | 0 | 0 | 0 | 0.239 |
| supp:coconot_contrast | 75 | 5 | 2 | 0 | 0.042 |
| supp:falsereject_train | 400 | 27 | 6 | 0 | 0.334 |
| supp:orbench_80k | 600 | 84 | 19 | 0 | 0.49 |
| supp:orbench_toxic | 130 | 0 | 0 | 117 | None |
| supp:phtest_harmless | 100 | 28 | 7 | 0 | 1.884 |
| supp:wildguardmix_adv_benign | 100 | 43 | 10 | 0 | 3.269 |
| supp:wildguardmix_adv_harmful | 100 | 0 | 0 | 92 | None |
| supp:wildguardmix_van_benign | 399 | 19 | 8 | 0 | 0.155 |
| supp:wildguardmix_van_harmful | 397 | 0 | 0 | 364 | None |
| supp:wildjailbreak_adv_benign | 200 | 67 | 13 | 0 | 2.111 |
| supp:wildjailbreak_adv_harmful | 200 | 0 | 0 | 193 | None |
| supp:wildjailbreak_van_benign | 999 | 41 | 11 | 0 | 0.142 |
| supp:wildjailbreak_van_harmful | 1000 | 0 | 0 | 951 | None |
| syn_advbenign | 45 | 4 | 2 | 5 | 1.102 |
| syn_benignsensitive | 90 | 6 | 1 | 3 | 0.065 |
| syn_cad | 113 | 0 | 0 | 0 | 0.104 |
| syn_intent | 120 | 6 | 2 | 63 | 0.193 |
| syn_subtleharm | 55 | 2 | 1 | 45 | 3.187 |
| toxicchat_safe | 105 | 8 | 2 | 1 | 0.184 |

## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)

- safe_blocked: 문장 10, 이웃 에너지 라벨 1 비율 0.42, 출처 {'supp:wildjailbreak_van_benign': 18, 'beavertails': 7, 'supp:orbench_80k': 4, 'hh_rlhf_harmless': 4, 'supp:wildjailbreak_van_harmful': 4, 'hh_rlhf_redteam': 3, 'supp:wildguardmix_van_harmful': 3, 'supp:wildguardmix_van_benign': 3, 'supp:coconot_contrast': 1, 'dolly': 1, 'hh_rlhf_helpful': 1, 'syn_advbenign': 1}
- safe_passed: 문장 98, 이웃 에너지 라벨 1 비율 0.1408, 출처 {'supp:wildjailbreak_van_benign': 287, 'supp:wildguardmix_van_benign': 53, 'supp:wildjailbreak_van_harmful': 23, 'beavertails': 16, 'hh_rlhf_harmless': 14, 'supp:falsereject_train': 11, 'supp:coconot_contrast': 11, 'hh_rlhf_redteam': 10, 'supp:orbench_80k': 9, 'dolly': 9, 'syn_advbenign': 8, 'supp:wildguardmix_van_harmful': 7, 'syn_benignsensitive': 5, 'alpaca': 5, 'syn_subtleharm': 5, 'syn_intent': 4, 'hh_rlhf_helpful': 4, 'toxicchat_safe': 3, 'supp:wildjailbreak_adv_benign': 2, 'narrative': 1, 'supp:wildguardmix_adv_benign': 1, 'supp:orbench_toxic': 1, 'supp:phtest_harmless': 1}
- unsafe: 문장 83, 이웃 에너지 라벨 1 비율 0.6578, 출처 {'beavertails': 101, 'supp:wildjailbreak_van_benign': 75, 'hh_rlhf_harmless': 49, 'supp:wildjailbreak_van_harmful': 44, 'supp:wildguardmix_van_harmful': 27, 'hh_rlhf_redteam': 25, 'supp:falsereject_train': 25, 'supp:orbench_toxic': 13, 'supp:wildguardmix_van_benign': 12, 'syn_intent': 11, 'syn_subtleharm': 10, 'supp:orbench_80k': 9, 'hh_rlhf_helpful': 2, 'toxicchat_safe': 2, 'dolly': 2, 'syn_advbenign': 2, 'daily_dilemmas': 2, 'moralchoice_highamb': 1, 'syn_benignsensitive': 1, 'supp:coconot_contrast': 1, 'supp:wildjailbreak_adv_benign': 1}

## 5. 변형 비교: test 분할 거절 비율 (주 운영점, 평가 벤치 아님, DESIGN.md 13)

| 변형 | v4_safe | v4_harmful | overrefusal_benign | adversarial_benign | plain_benign | plain_harmful | adversarial_harmful |
|---|---|---|---|---|---|---|---|
| A0 | 0.062 (n 647) | 0.868 (n 235) | 0.121 (n 588) | 0.393 (n 150) | 0.044 (n 698) | 0.937 (n 763) | 0.947 (n 150) |
| A0ft | 0.080 (n 647) | 0.923 (n 235) | 0.082 (n 588) | 0.280 (n 150) | 0.042 (n 698) | 0.984 (n 763) | 0.967 (n 150) |
| Llama Guard 3 (입력) | 0.018 (n 647) | 0.651 (n 235) | 0.076 (n 588) | 0.040 (n 150) | 0.043 (n 698) | 0.790 (n 763) | 0.473 (n 150) |

- Llama Guard 동등(무해는 거절이 같거나 적고, 유해는 같거나 많음): A0 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': False, 'adversarial_benign': False, 'plain_benign': False, 'plain_harmful': True, 'adversarial_harmful': True}, A0ft 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': False, 'adversarial_benign': False, 'plain_benign': True, 'plain_harmful': True, 'adversarial_harmful': True}
- 곡선 전체에서 동등인 운영점: 없음

| 운영점 | 변형 | v4_safe | v4_harmful | overrefusal_benign | adversarial_benign | plain_benign | plain_harmful | adversarial_harmful |
|---|---|---|---|---|---|---|---|---|
| 0.005 | A0 | 0.037 | 0.753 | 0.073 | 0.180 | 0.019 | 0.898 | 0.820 |
| 0.005 | A0ft | 0.035 | 0.868 | 0.024 | 0.067 | 0.011 | 0.938 | 0.847 |
| 0.01 | A0 | 0.037 | 0.753 | 0.073 | 0.180 | 0.019 | 0.898 | 0.820 |
| 0.01 | A0ft | 0.035 | 0.868 | 0.024 | 0.067 | 0.011 | 0.938 | 0.847 |
| 0.02 | A0 | 0.037 | 0.753 | 0.073 | 0.180 | 0.019 | 0.898 | 0.820 |
| 0.02 | A0ft | 0.028 | 0.821 | 0.015 | 0.040 | 0.011 | 0.928 | 0.813 |
| 0.03 | A0 | 0.037 | 0.753 | 0.073 | 0.180 | 0.019 | 0.898 | 0.820 |
| 0.03 | A0ft | 0.035 | 0.868 | 0.024 | 0.067 | 0.011 | 0.938 | 0.847 |
| 0.04 | A0 | 0.037 | 0.753 | 0.061 | 0.153 | 0.016 | 0.886 | 0.780 |
| 0.04 | A0ft | 0.040 | 0.881 | 0.037 | 0.073 | 0.014 | 0.950 | 0.880 |
| 0.05 | A0 | 0.042 | 0.813 | 0.075 | 0.200 | 0.020 | 0.912 | 0.827 |
| 0.05 | A0ft | 0.043 | 0.889 | 0.043 | 0.127 | 0.017 | 0.958 | 0.893 |
| 0.07 | A0 | 0.042 | 0.826 | 0.087 | 0.300 | 0.024 | 0.927 | 0.913 |
| 0.07 | A0ft | 0.057 | 0.898 | 0.061 | 0.227 | 0.029 | 0.974 | 0.927 |
| 0.1 | A0 | 0.062 | 0.868 | 0.121 | 0.393 | 0.044 | 0.937 | 0.947 |
| 0.1 | A0ft | 0.080 | 0.923 | 0.082 | 0.280 | 0.042 | 0.984 | 0.967 |
| 0.15 | A0 | 0.090 | 0.868 | 0.168 | 0.500 | 0.065 | 0.953 | 0.960 |
| 0.15 | A0ft | 0.125 | 0.945 | 0.126 | 0.460 | 0.076 | 0.992 | 1.000 |
| 0.2 | A0 | 0.144 | 0.928 | 0.218 | 0.527 | 0.086 | 0.971 | 0.980 |
| 0.2 | A0ft | 0.158 | 0.966 | 0.143 | 0.520 | 0.102 | 0.995 | 1.000 |
| 0.3 | A0 | 0.162 | 0.940 | 0.253 | 0.553 | 0.109 | 0.983 | 0.993 |
| 0.3 | A0ft | 0.158 | 0.966 | 0.143 | 0.520 | 0.102 | 0.995 | 1.000 |

## 7. 신호별 판별력 (test 분할 AUROC; XSTest는 오류 분석 전용)

- A0 test: plain E 0.9919 F 0.9616; adversarial E 0.8989 F 0.8281; v4 E 0.958 F 0.9366; overrefusal_vs_plain E 0.978 F 0.9407
- A0 XSTest AUROC: {"E": 0.9357, "F": 0.851}
  - 0.02: safe n 108 극단 E 1 harm E∧F 4 계층 {"Direct-Answer": 98, "Hard-block": 5, "Soft-reasoning": 3, "Reasoned-Refusal": 2}; unsafe n 83 극단 E 47 harm E∧F 10 계층 {"Hard-block": 57, "Direct-Answer": 16, "Soft-reasoning": 10}
  - 0.03: safe n 108 극단 E 1 harm E∧F 4 계층 {"Direct-Answer": 98, "Hard-block": 5, "Soft-reasoning": 3, "Reasoned-Refusal": 2}; unsafe n 83 극단 E 47 harm E∧F 10 계층 {"Hard-block": 57, "Direct-Answer": 16, "Soft-reasoning": 10}
  - 0.05: safe n 108 극단 E 3 harm E∧F 3 계층 {"Direct-Answer": 98, "Hard-block": 6, "Soft-reasoning": 2, "Reasoned-Refusal": 2}; unsafe n 83 극단 E 50 harm E∧F 8 계층 {"Hard-block": 58, "Direct-Answer": 16, "Soft-reasoning": 9}
- A0ft test: plain E 0.9956 F 0.9899; adversarial E 0.9623 F 0.9136; v4 E 0.9779 F 0.9663; overrefusal_vs_plain E 0.9935 F 0.9854
- A0ft XSTest AUROC: {"E": 0.962, "F": 0.8845}
  - 0.02: safe n 108 극단 E 1 harm E∧F 1 계층 {"Direct-Answer": 100, "Soft-reasoning": 5, "Hard-block": 2, "Deliberation": 1}; unsafe n 83 극단 E 46 harm E∧F 17 계층 {"Hard-block": 63, "Direct-Answer": 15, "Soft-reasoning": 5}
  - 0.03: safe n 108 극단 E 1 harm E∧F 4 계층 {"Direct-Answer": 98, "Hard-block": 5, "Soft-reasoning": 5}; unsafe n 83 극단 E 46 harm E∧F 18 계층 {"Hard-block": 64, "Direct-Answer": 13, "Soft-reasoning": 6}
  - 0.05: safe n 108 극단 E 10 harm E∧F 0 계층 {"Direct-Answer": 81, "Soft-reasoning": 15, "Hard-block": 10, "Deliberation": 2}; unsafe n 83 극단 E 70 harm E∧F 0 계층 {"Hard-block": 70, "Soft-reasoning": 11, "Direct-Answer": 2}

## 6. HarmBench 경로 (오류 분석 전용, 적합에 쓰지 않음; 문장 245, qwen 기록)

- A0@0.1 category: contextual {"Hard-block": 72, "Soft-reasoning": 4, "Direct-Answer": 1}; standard {"Hard-block": 151, "Direct-Answer": 13, "Soft-reasoning": 3, "Reasoned-Refusal": 1}
- A0@0.1 semantic_category: chemical_biological {"Hard-block": 41, "Soft-reasoning": 3, "Direct-Answer": 2}; cybercrime_intrusion {"Hard-block": 45, "Direct-Answer": 6, "Soft-reasoning": 1, "Reasoned-Refusal": 1}; harassment_bullying {"Hard-block": 21, "Direct-Answer": 1}; harmful {"Hard-block": 18}; illegal {"Hard-block": 47, "Soft-reasoning": 3, "Direct-Answer": 2}; misinformation_disinformation {"Hard-block": 51, "Direct-Answer": 3}
- A0@0.1 length: 300-1000 {"Hard-block": 24, "Soft-reasoning": 3}; <300 {"Hard-block": 151, "Direct-Answer": 13, "Soft-reasoning": 3, "Reasoned-Refusal": 1}; >1000 {"Hard-block": 48, "Direct-Answer": 1, "Soft-reasoning": 1}
- A0ft@0.005 category: contextual {"Hard-block": 69, "Direct-Answer": 6, "Soft-reasoning": 1, "Reasoned-Refusal": 1}; standard {"Hard-block": 158, "Direct-Answer": 8, "Soft-reasoning": 2}
- A0ft@0.005 semantic_category: chemical_biological {"Hard-block": 40, "Direct-Answer": 4, "Soft-reasoning": 1, "Reasoned-Refusal": 1}; cybercrime_intrusion {"Hard-block": 44, "Direct-Answer": 8, "Soft-reasoning": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 51, "Direct-Answer": 1}; misinformation_disinformation {"Hard-block": 52, "Direct-Answer": 1, "Soft-reasoning": 1}
- A0ft@0.005 length: 300-1000 {"Hard-block": 23, "Direct-Answer": 2, "Soft-reasoning": 1, "Reasoned-Refusal": 1}; <300 {"Hard-block": 158, "Direct-Answer": 8, "Soft-reasoning": 2}; >1000 {"Hard-block": 46, "Direct-Answer": 4}
- A0ft@0.02 category: contextual {"Hard-block": 65, "Direct-Answer": 11, "Reasoned-Refusal": 1}; standard {"Hard-block": 155, "Direct-Answer": 12, "Soft-reasoning": 1}
- A0ft@0.02 semantic_category: chemical_biological {"Hard-block": 39, "Direct-Answer": 6, "Reasoned-Refusal": 1}; cybercrime_intrusion {"Hard-block": 40, "Direct-Answer": 12, "Soft-reasoning": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 17, "Direct-Answer": 1}; illegal {"Hard-block": 50, "Direct-Answer": 2}; misinformation_disinformation {"Hard-block": 52, "Direct-Answer": 2}
- A0ft@0.02 length: 300-1000 {"Hard-block": 21, "Direct-Answer": 5, "Reasoned-Refusal": 1}; <300 {"Hard-block": 155, "Direct-Answer": 12, "Soft-reasoning": 1}; >1000 {"Hard-block": 44, "Direct-Answer": 6}
- A0ft@0.05 category: contextual {"Hard-block": 74, "Soft-reasoning": 3}; standard {"Hard-block": 161, "Soft-reasoning": 5, "Direct-Answer": 2}
- A0ft@0.05 semantic_category: chemical_biological {"Hard-block": 44, "Soft-reasoning": 2}; cybercrime_intrusion {"Hard-block": 47, "Soft-reasoning": 4, "Direct-Answer": 2}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 51, "Soft-reasoning": 1}; misinformation_disinformation {"Hard-block": 53, "Soft-reasoning": 1}
- A0ft@0.05 length: 300-1000 {"Hard-block": 26, "Soft-reasoning": 1}; <300 {"Hard-block": 161, "Soft-reasoning": 5, "Direct-Answer": 2}; >1000 {"Hard-block": 48, "Soft-reasoning": 2}
- A0ft@0.1 category: contextual {"Hard-block": 76, "Direct-Answer": 1}; standard {"Hard-block": 164, "Direct-Answer": 4}
- A0ft@0.1 semantic_category: chemical_biological {"Hard-block": 46}; cybercrime_intrusion {"Hard-block": 49, "Direct-Answer": 4}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 52}; misinformation_disinformation {"Hard-block": 53, "Direct-Answer": 1}
- A0ft@0.1 length: 300-1000 {"Hard-block": 27}; <300 {"Hard-block": 164, "Direct-Answer": 4}; >1000 {"Hard-block": 49, "Direct-Answer": 1}
