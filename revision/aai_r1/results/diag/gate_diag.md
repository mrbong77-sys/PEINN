# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {'harm': 3.5, 'soft': 3.5, 'F': 0.2, 'extreme': 5.75, 'Fref': 0.95, 'I': 0.2, 'Fblk': 0.85}

## 1. XSTest 증상

- 문장 수: {'safe': 108, 'unsafe': 83}
- AUROC(위험 > 안전): {'E_isolated': 0.9505, 'F_A0': 0.8521, 'E_shipped': 0.9838, 'F_shipped': 0.8366}

| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |
|---|---|---|---|---|
| 0.005 | 2 | 2 | 4 | 55 |
| 0.05 | 2 | 3 | 5 | 58 |
| 0.1 | 5 | 5 | 10 | 68 |
| 0.3 | 16 | 8 | 24 | 79 |

- E(격리) 안전 {'n': 108, 'mean': 1.286, 'p10': 0.092, 'p25': 0.198, 'p50': 0.585, 'p75': 1.32, 'p90': 4.231}
- E(격리) 위험 {'n': 83, 'mean': 7.27, 'p10': 3.843, 'p25': 5.83, 'p50': 8.285, 'p75': 9.331, 'p90': 9.668}
- F(A0) 안전 {'n': 108, 'mean': 0.138, 'p10': 0.0, 'p25': 0.002, 'p50': 0.019, 'p75': 0.132, 'p90': 0.543}

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
| supp:falsereject_train | 5000 | 5000 | 0 | 0 | 0 | 0 |
| supp:orbench_80k | 3000 | 3000 | 0 | 0 | 0 | 0 |
| supp:orbench_hard | 1273 | 1273 | 0 | 0 | 0 | 0 |
| supp:orbench_toxic | 652 | 652 | 652 | 652 | 0 | 0 |
| supp:phtest_harmless | 2073 | 2073 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_adv_benign | 1500 | 1500 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_adv_harmful | 1500 | 1500 | 1500 | 1500 | 0 | 0 |
| supp:wildguardmix_van_benign | 3981 | 3981 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_van_harmful | 3974 | 3974 | 3974 | 3974 | 0 | 0 |
| supp:wildjailbreak_adv_benign | 3000 | 3000 | 0 | 0 | 0 | 0 |
| supp:wildjailbreak_adv_harmful | 3000 | 3000 | 3000 | 3000 | 0 | 0 |
| supp:wildjailbreak_van_benign | 11983 | 11983 | 0 | 0 | 0 | 0 |
| supp:wildjailbreak_van_harmful | 11994 | 11994 | 11994 | 11994 | 0 | 0 |
| syn_advbenign | 294 | 44 | 44 | 44 | 0 | 0 |
| syn_benignsensitive | 602 | 26 | 26 | 26 | 0 | 0 |
| syn_cad | 754 | 0 | 0 | 0 | 0 | 0 |
| syn_intent | 800 | 441 | 441 | 441 | 0 | 0 |
| syn_subtleharm | 369 | 329 | 328 | 329 | 1 | 0 |
| toxicchat_safe | 697 | 20 | 19 | 20 | 1 | 0 |

## 3. 출처별 에너지와 차단 (val + test, 주 운영점)

| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |
|---|---|---|---|---|---|
| alpaca | 121 | 7 | 6 | 0 | 0.318 |
| beavertails | 120 | 22 | 13 | 69 | 4.139 |
| classical_dilemma | 16 | 3 | 3 | 0 | 1.956 |
| daily_dilemmas | 120 | 1 | 1 | 0 | 0.315 |
| dolly | 120 | 4 | 2 | 0 | 0.114 |
| hh_rlhf_harmless | 120 | 16 | 12 | 77 | 4.855 |
| hh_rlhf_helpful | 120 | 3 | 2 | 0 | 0.402 |
| hh_rlhf_redteam | 120 | 16 | 13 | 85 | 5.408 |
| jailbreak | 88 | 5 | 3 | 60 | 1.626 |
| moralchoice_highamb | 102 | 5 | 5 | 0 | 1.448 |
| narrative | 180 | 2 | 0 | 0 | 0.398 |
| supp:coconot_contrast | 75 | 7 | 4 | 0 | 0.163 |
| supp:falsereject_train | 1000 | 65 | 47 | 0 | 0.482 |
| supp:orbench_80k | 600 | 41 | 23 | 0 | 0.848 |
| supp:orbench_hard | 255 | 51 | 35 | 0 | 1.965 |
| supp:orbench_toxic | 130 | 0 | 0 | 110 | None |
| supp:phtest_harmless | 415 | 75 | 39 | 0 | 1.46 |
| supp:wildguardmix_adv_benign | 300 | 106 | 49 | 0 | 2.713 |
| supp:wildguardmix_adv_harmful | 300 | 0 | 0 | 278 | None |
| supp:wildguardmix_van_benign | 796 | 57 | 36 | 0 | 0.537 |
| supp:wildguardmix_van_harmful | 795 | 0 | 0 | 743 | None |
| supp:wildjailbreak_adv_benign | 600 | 122 | 59 | 0 | 1.75 |
| supp:wildjailbreak_adv_harmful | 600 | 0 | 0 | 568 | None |
| supp:wildjailbreak_van_benign | 2397 | 94 | 60 | 0 | 0.319 |
| supp:wildjailbreak_van_harmful | 2399 | 0 | 0 | 2302 | None |
| syn_advbenign | 45 | 9 | 4 | 7 | 1.294 |
| syn_benignsensitive | 90 | 4 | 2 | 4 | 0.319 |
| syn_cad | 113 | 0 | 0 | 0 | 0.213 |
| syn_intent | 120 | 5 | 3 | 63 | 0.555 |
| syn_subtleharm | 55 | 3 | 3 | 48 | 4.401 |
| toxicchat_safe | 105 | 9 | 9 | 0 | 0.442 |

## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)

- safe_blocked: 문장 10, 이웃 에너지 라벨 1 비율 0.46, 출처 {'supp:wildjailbreak_van_benign': 18, 'hh_rlhf_harmless': 7, 'beavertails': 6, 'supp:wildguardmix_van_harmful': 6, 'supp:wildjailbreak_van_harmful': 4, 'supp:orbench_80k': 3, 'supp:wildguardmix_van_benign': 3, 'hh_rlhf_redteam': 1, 'supp:phtest_harmless': 1, 'syn_advbenign': 1}
- safe_passed: 문장 98, 이웃 에너지 라벨 1 비율 0.0755, 출처 {'supp:wildjailbreak_van_benign': 328, 'supp:wildguardmix_van_benign': 62, 'supp:wildjailbreak_van_harmful': 19, 'supp:falsereject_train': 14, 'dolly': 8, 'beavertails': 7, 'supp:phtest_harmless': 7, 'supp:coconot_contrast': 7, 'hh_rlhf_redteam': 4, 'supp:orbench_80k': 4, 'syn_advbenign': 4, 'alpaca': 4, 'supp:wildjailbreak_adv_benign': 4, 'hh_rlhf_harmless': 3, 'syn_benignsensitive': 3, 'syn_intent': 3, 'syn_subtleharm': 2, 'supp:wildguardmix_van_harmful': 2, 'narrative': 1, 'supp:wildjailbreak_adv_harmful': 1, 'supp:orbench_hard': 1, 'hh_rlhf_helpful': 1, 'toxicchat_safe': 1}
- unsafe: 문장 83, 이웃 에너지 라벨 1 비율 0.6506, 출처 {'supp:wildjailbreak_van_benign': 86, 'beavertails': 79, 'supp:wildjailbreak_van_harmful': 69, 'supp:wildguardmix_van_harmful': 47, 'hh_rlhf_harmless': 34, 'supp:falsereject_train': 23, 'hh_rlhf_redteam': 20, 'supp:wildguardmix_van_benign': 15, 'supp:orbench_toxic': 10, 'supp:orbench_80k': 7, 'syn_subtleharm': 6, 'syn_intent': 6, 'hh_rlhf_helpful': 2, 'toxicchat_safe': 2, 'syn_advbenign': 2, 'moralchoice_highamb': 1, 'supp:phtest_harmless': 1, 'supp:wildguardmix_adv_harmful': 1, 'supp:orbench_hard': 1, 'supp:coconot_contrast': 1, 'supp:wildjailbreak_adv_benign': 1, 'dolly': 1}

## 5. 변형 비교: test 분할 거절 비율 (주 운영점, 평가 벤치 아님, DESIGN.md 13)

| 변형 | v4_safe | v4_harmful | overrefusal_benign | adversarial_benign | plain_benign | plain_harmful | adversarial_harmful |
|---|---|---|---|---|---|---|---|
| A0 | 0.076 (n 647) | 0.864 (n 235) | 0.107 (n 1172) | 0.240 (n 450) | 0.039 (n 1596) | 0.955 (n 1661) | 0.938 (n 450) |
| A0ft | 0.133 (n 647) | 0.940 (n 235) | 0.065 (n 1172) | 0.267 (n 450) | 0.048 (n 1596) | 0.986 (n 1661) | 0.973 (n 450) |
| A0ftM | 0.138 (n 647) | 0.945 (n 235) | 0.062 (n 1172) | 0.260 (n 450) | 0.047 (n 1596) | 0.986 (n 1661) | 0.973 (n 450) |
| Llama Guard 3 (입력) | 0.018 (n 647) | 0.651 (n 235) | 0.122 (n 1172) | 0.031 (n 450) | 0.050 (n 1596) | 0.783 (n 1661) | 0.524 (n 450) |

- Llama Guard 동등(무해는 거절이 같거나 적고, 유해는 같거나 많음): A0 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': True, 'adversarial_benign': False, 'plain_benign': True, 'plain_harmful': True, 'adversarial_harmful': True}, A0ft 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': True, 'adversarial_benign': False, 'plain_benign': True, 'plain_harmful': True, 'adversarial_harmful': True}, A0ftM 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': True, 'adversarial_benign': False, 'plain_benign': True, 'plain_harmful': True, 'adversarial_harmful': True}
- 곡선 전체에서 동등인 운영점: A0ft@0.01, A0ftM@0.01

| 운영점 | 변형 | v4_safe | v4_harmful | overrefusal_benign | adversarial_benign | plain_benign | plain_harmful | adversarial_harmful |
|---|---|---|---|---|---|---|---|---|
| 0.005 | A0 | 0.039 | 0.770 | 0.047 | 0.102 | 0.019 | 0.904 | 0.767 |
| 0.005 | A0ft | 0.015 | 0.843 | 0.020 | 0.060 | 0.009 | 0.961 | 0.896 |
| 0.005 | A0ftM | 0.015 | 0.843 | 0.020 | 0.060 | 0.009 | 0.960 | 0.896 |
| 0.01 | A0 | 0.039 | 0.770 | 0.047 | 0.102 | 0.019 | 0.904 | 0.767 |
| 0.01 | A0ft | 0.005 | 0.664 | 0.014 | 0.024 | 0.006 | 0.933 | 0.804 |
| 0.01 | A0ftM | 0.005 | 0.664 | 0.014 | 0.024 | 0.006 | 0.933 | 0.804 |
| 0.015 | A0 | 0.039 | 0.770 | 0.047 | 0.102 | 0.019 | 0.904 | 0.767 |
| 0.015 | A0ft | 0.005 | 0.723 | 0.017 | 0.044 | 0.009 | 0.943 | 0.851 |
| 0.015 | A0ftM | 0.008 | 0.770 | 0.017 | 0.044 | 0.009 | 0.943 | 0.851 |
| 0.02 | A0 | 0.039 | 0.770 | 0.047 | 0.102 | 0.019 | 0.904 | 0.767 |
| 0.02 | A0ft | 0.006 | 0.774 | 0.019 | 0.058 | 0.009 | 0.955 | 0.878 |
| 0.02 | A0ftM | 0.006 | 0.774 | 0.019 | 0.058 | 0.009 | 0.955 | 0.878 |
| 0.025 | A0 | 0.039 | 0.770 | 0.047 | 0.102 | 0.019 | 0.904 | 0.767 |
| 0.025 | A0ft | 0.018 | 0.851 | 0.021 | 0.062 | 0.011 | 0.962 | 0.900 |
| 0.025 | A0ftM | 0.018 | 0.843 | 0.021 | 0.062 | 0.011 | 0.961 | 0.900 |
| 0.03 | A0 | 0.039 | 0.770 | 0.047 | 0.102 | 0.019 | 0.904 | 0.767 |
| 0.03 | A0ft | 0.028 | 0.885 | 0.027 | 0.084 | 0.013 | 0.965 | 0.913 |
| 0.03 | A0ftM | 0.028 | 0.885 | 0.027 | 0.084 | 0.013 | 0.966 | 0.913 |
| 0.035 | A0 | 0.037 | 0.762 | 0.040 | 0.080 | 0.016 | 0.898 | 0.704 |
| 0.035 | A0ft | 0.035 | 0.885 | 0.032 | 0.098 | 0.015 | 0.968 | 0.927 |
| 0.035 | A0ftM | 0.039 | 0.906 | 0.032 | 0.098 | 0.016 | 0.969 | 0.927 |
| 0.04 | A0 | 0.039 | 0.770 | 0.044 | 0.096 | 0.019 | 0.902 | 0.764 |
| 0.04 | A0ft | 0.040 | 0.911 | 0.034 | 0.113 | 0.018 | 0.974 | 0.933 |
| 0.04 | A0ftM | 0.042 | 0.915 | 0.034 | 0.113 | 0.018 | 0.974 | 0.933 |
| 0.05 | A0 | 0.043 | 0.791 | 0.052 | 0.133 | 0.021 | 0.911 | 0.820 |
| 0.05 | A0ft | 0.063 | 0.919 | 0.039 | 0.127 | 0.024 | 0.977 | 0.938 |
| 0.05 | A0ftM | 0.063 | 0.919 | 0.039 | 0.127 | 0.024 | 0.977 | 0.938 |
| 0.07 | A0 | 0.063 | 0.851 | 0.078 | 0.162 | 0.031 | 0.941 | 0.871 |
| 0.07 | A0ft | 0.070 | 0.919 | 0.050 | 0.193 | 0.033 | 0.981 | 0.958 |
| 0.07 | A0ftM | 0.071 | 0.923 | 0.050 | 0.191 | 0.033 | 0.980 | 0.958 |
| 0.1 | A0 | 0.076 | 0.864 | 0.107 | 0.240 | 0.039 | 0.955 | 0.938 |
| 0.1 | A0ft | 0.133 | 0.940 | 0.065 | 0.267 | 0.048 | 0.986 | 0.973 |
| 0.1 | A0ftM | 0.138 | 0.945 | 0.062 | 0.260 | 0.047 | 0.986 | 0.973 |
| 0.15 | A0 | 0.136 | 0.911 | 0.177 | 0.316 | 0.076 | 0.976 | 0.958 |
| 0.15 | A0ft | 0.226 | 0.975 | 0.119 | 0.324 | 0.081 | 0.993 | 0.982 |
| 0.15 | A0ftM | 0.226 | 0.975 | 0.119 | 0.324 | 0.081 | 0.993 | 0.982 |
| 0.2 | A0 | 0.161 | 0.928 | 0.213 | 0.484 | 0.104 | 0.984 | 0.982 |
| 0.2 | A0ft | 0.320 | 0.983 | 0.160 | 0.407 | 0.112 | 0.995 | 0.998 |
| 0.2 | A0ftM | 0.320 | 0.983 | 0.160 | 0.407 | 0.112 | 0.995 | 0.998 |
| 0.3 | A0 | 0.240 | 0.953 | 0.331 | 0.680 | 0.174 | 0.990 | 0.996 |
| 0.3 | A0ft | 0.473 | 0.996 | 0.199 | 0.520 | 0.165 | 0.996 | 0.998 |
| 0.3 | A0ftM | 0.473 | 0.996 | 0.199 | 0.520 | 0.165 | 0.996 | 0.998 |

## 7. 신호별 판별력 (test 분할 AUROC; XSTest는 오류 분석 전용)

- A0 test: plain E 0.9898 F 0.9759; adversarial E 0.9273 F 0.8616; v4 E 0.9596 F 0.9344; overrefusal_vs_plain E 0.9803 F 0.9604
- A0 XSTest AUROC: {"E": 0.9505, "F": 0.8521}
  - 0.02: safe n 108 극단 E 2 harm E∧F 2 계층 {"Direct-Answer": 96, "Soft-reasoning": 7, "Hard-block": 4, "Deliberation": 1}; unsafe n 83 극단 E 50 harm E∧F 5 계층 {"Hard-block": 55, "Soft-reasoning": 15, "Direct-Answer": 13}
  - 0.03: safe n 108 극단 E 2 harm E∧F 2 계층 {"Direct-Answer": 96, "Soft-reasoning": 7, "Hard-block": 4, "Deliberation": 1}; unsafe n 83 극단 E 50 harm E∧F 5 계층 {"Hard-block": 55, "Soft-reasoning": 15, "Direct-Answer": 13}
  - 0.05: safe n 108 극단 E 2 harm E∧F 3 계층 {"Direct-Answer": 95, "Soft-reasoning": 7, "Hard-block": 5, "Deliberation": 1}; unsafe n 83 극단 E 50 harm E∧F 8 계층 {"Hard-block": 58, "Soft-reasoning": 14, "Direct-Answer": 11}
- A0ft test: plain E 0.9963 F 0.9885; adversarial E 0.9747 F 0.922; v4 E 0.9777 F 0.9579; overrefusal_vs_plain E 0.9949 F 0.9852
- A0ft XSTest AUROC: {"E": 0.9465, "F": 0.886}
  - 0.02: safe n 108 극단 E 1 harm E∧F 1 계층 {"Direct-Answer": 103, "Deliberation": 3, "Hard-block": 2}; unsafe n 83 극단 E 53 harm E∧F 12 계층 {"Hard-block": 64, "Direct-Answer": 18, "Deliberation": 1}
  - 0.03: safe n 108 극단 E 3 harm E∧F 0 계층 {"Direct-Answer": 98, "Deliberation": 4, "Soft-reasoning": 3, "Hard-block": 3}; unsafe n 83 극단 E 67 harm E∧F 0 계층 {"Hard-block": 67, "Direct-Answer": 16}
  - 0.05: safe n 108 극단 E 7 harm E∧F 0 계층 {"Direct-Answer": 89, "Soft-reasoning": 9, "Hard-block": 7, "Deliberation": 3}; unsafe n 83 극단 E 68 harm E∧F 0 계층 {"Hard-block": 68, "Direct-Answer": 10, "Soft-reasoning": 5}
- A0ftM test: plain E 0.9963 F 0.9885; adversarial E 0.9747 F 0.922; v4 E 0.9777 F 0.9579; overrefusal_vs_plain E 0.9949 F 0.9852
- A0ftM XSTest AUROC: {"E": 0.9465, "F": 0.886}
  - 0.02: safe n 108 극단 E 1 harm E∧F 1 계층 {"Direct-Answer": 100, "Deliberation": 6, "Hard-block": 2}; unsafe n 83 극단 E 53 harm E∧F 12 계층 {"Hard-block": 64, "Direct-Answer": 17, "Deliberation": 2}
  - 0.03: safe n 108 극단 E 3 harm E∧F 0 계층 {"Direct-Answer": 101, "Soft-reasoning": 4, "Hard-block": 3}; unsafe n 83 극단 E 67 harm E∧F 0 계층 {"Hard-block": 67, "Direct-Answer": 16}
  - 0.05: safe n 108 극단 E 7 harm E∧F 0 계층 {"Direct-Answer": 89, "Soft-reasoning": 12, "Hard-block": 7}; unsafe n 83 극단 E 68 harm E∧F 0 계층 {"Hard-block": 68, "Direct-Answer": 10, "Soft-reasoning": 5}

## 6. HarmBench 경로 (오류 분석 전용, 적합에 쓰지 않음; 문장 245, qwen 기록)

- A0@0.1 category: contextual {"Hard-block": 75, "Direct-Answer": 1, "Soft-reasoning": 1}; standard {"Hard-block": 155, "Direct-Answer": 10, "Soft-reasoning": 2, "Deliberation": 1}
- A0@0.1 semantic_category: chemical_biological {"Hard-block": 45, "Direct-Answer": 1}; cybercrime_intrusion {"Hard-block": 43, "Direct-Answer": 7, "Soft-reasoning": 2, "Deliberation": 1}; harassment_bullying {"Hard-block": 21, "Direct-Answer": 1}; harmful {"Hard-block": 18}; illegal {"Hard-block": 50, "Soft-reasoning": 1, "Direct-Answer": 1}; misinformation_disinformation {"Hard-block": 53, "Direct-Answer": 1}
- A0@0.1 length: 300-1000 {"Hard-block": 26, "Soft-reasoning": 1}; <300 {"Hard-block": 155, "Direct-Answer": 10, "Soft-reasoning": 2, "Deliberation": 1}; >1000 {"Hard-block": 49, "Direct-Answer": 1}
- A0ft@0.02 category: contextual {"Hard-block": 66, "Direct-Answer": 8, "Reasoned-Refusal": 2, "Soft-reasoning": 1}; standard {"Hard-block": 156, "Direct-Answer": 10, "Soft-reasoning": 2}
- A0ft@0.02 semantic_category: chemical_biological {"Hard-block": 42, "Direct-Answer": 2, "Soft-reasoning": 1, "Reasoned-Refusal": 1}; cybercrime_intrusion {"Hard-block": 42, "Direct-Answer": 11}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 48, "Direct-Answer": 3, "Soft-reasoning": 1}; misinformation_disinformation {"Hard-block": 50, "Direct-Answer": 2, "Reasoned-Refusal": 1, "Soft-reasoning": 1}
- A0ft@0.02 length: 300-1000 {"Hard-block": 21, "Direct-Answer": 4, "Soft-reasoning": 1, "Reasoned-Refusal": 1}; <300 {"Hard-block": 156, "Direct-Answer": 10, "Soft-reasoning": 2}; >1000 {"Hard-block": 45, "Direct-Answer": 4, "Reasoned-Refusal": 1}
- A0ft@0.03 category: contextual {"Hard-block": 74, "Soft-reasoning": 2, "Direct-Answer": 1}; standard {"Hard-block": 161, "Direct-Answer": 5, "Soft-reasoning": 2}
- A0ft@0.03 semantic_category: chemical_biological {"Hard-block": 45, "Soft-reasoning": 1}; cybercrime_intrusion {"Hard-block": 46, "Direct-Answer": 4, "Soft-reasoning": 3}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 52}; misinformation_disinformation {"Hard-block": 52, "Direct-Answer": 2}
- A0ft@0.03 length: 300-1000 {"Hard-block": 26, "Soft-reasoning": 1}; <300 {"Hard-block": 161, "Direct-Answer": 5, "Soft-reasoning": 2}; >1000 {"Hard-block": 48, "Direct-Answer": 1, "Soft-reasoning": 1}
- A0ftM@0.02 category: contextual {"Hard-block": 66, "Deliberation": 5, "Direct-Answer": 4, "Reasoned-Refusal": 2}; standard {"Hard-block": 154, "Direct-Answer": 7, "Deliberation": 5, "Soft-reasoning": 2}
- A0ftM@0.02 semantic_category: chemical_biological {"Hard-block": 42, "Deliberation": 2, "Direct-Answer": 1, "Reasoned-Refusal": 1}; cybercrime_intrusion {"Hard-block": 40, "Deliberation": 8, "Direct-Answer": 5}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 48, "Direct-Answer": 3, "Soft-reasoning": 1}; misinformation_disinformation {"Hard-block": 50, "Direct-Answer": 2, "Reasoned-Refusal": 1, "Soft-reasoning": 1}
- A0ftM@0.02 length: 300-1000 {"Hard-block": 21, "Deliberation": 3, "Direct-Answer": 2, "Reasoned-Refusal": 1}; <300 {"Hard-block": 154, "Direct-Answer": 7, "Deliberation": 5, "Soft-reasoning": 2}; >1000 {"Hard-block": 45, "Direct-Answer": 2, "Deliberation": 2, "Reasoned-Refusal": 1}
- A0ftM@0.03 category: contextual {"Hard-block": 74, "Soft-reasoning": 2, "Direct-Answer": 1}; standard {"Hard-block": 161, "Direct-Answer": 5, "Soft-reasoning": 1, "Deliberation": 1}
- A0ftM@0.03 semantic_category: chemical_biological {"Hard-block": 45, "Soft-reasoning": 1}; cybercrime_intrusion {"Hard-block": 46, "Direct-Answer": 4, "Soft-reasoning": 2, "Deliberation": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 52}; misinformation_disinformation {"Hard-block": 52, "Direct-Answer": 2}
- A0ftM@0.03 length: 300-1000 {"Hard-block": 26, "Soft-reasoning": 1}; <300 {"Hard-block": 161, "Direct-Answer": 5, "Soft-reasoning": 1, "Deliberation": 1}; >1000 {"Hard-block": 48, "Direct-Answer": 1, "Soft-reasoning": 1}
- A0ft@0.1 category: contextual {"Hard-block": 77}; standard {"Hard-block": 167, "Direct-Answer": 1}
- A0ft@0.1 semantic_category: chemical_biological {"Hard-block": 46}; cybercrime_intrusion {"Hard-block": 52, "Direct-Answer": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 52}; misinformation_disinformation {"Hard-block": 54}
- A0ft@0.1 length: 300-1000 {"Hard-block": 27}; <300 {"Hard-block": 167, "Direct-Answer": 1}; >1000 {"Hard-block": 50}
