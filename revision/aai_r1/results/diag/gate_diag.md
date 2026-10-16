# 게이트 진단 (DESIGN.md 11)

주 운영점 0.1 문턱: {'harm': 1.28, 'soft': 1.28, 'F': 0.5, 'extreme': 5.373, 'Fref': 0.95, 'I': 0.25, 'Fblk': 0.55}

## 1. XSTest 증상

- 문장 수: {'safe': 108, 'unsafe': 83}
- AUROC(위험 > 안전): {'E_isolated': 0.9383, 'F_A0': 0.8594, 'E_shipped': 0.9838, 'F_shipped': 0.8366}

| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |
|---|---|---|---|---|
| 0.005 | 2 | 3 | 5 | 58 |
| 0.05 | 2 | 3 | 5 | 58 |
| 0.1 | 6 | 5 | 11 | 68 |
| 0.3 | 29 | 0 | 29 | 79 |

- E(격리) 안전 {'n': 108, 'mean': 1.008, 'p10': 0.002, 'p25': 0.014, 'p50': 0.125, 'p75': 0.767, 'p90': 3.532}
- E(격리) 위험 {'n': 83, 'mean': 7.529, 'p10': 1.275, 'p25': 6.451, 'p50': 9.12, 'p75': 9.769, 'p90': 9.926}
- F(A0) 안전 {'n': 108, 'mean': 0.153, 'p10': 0.0, 'p25': 0.003, 'p50': 0.012, 'p75': 0.165, 'p90': 0.641}

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
| supp:wildguardmix_van_benign | 1993 | 1993 | 0 | 0 | 0 | 0 |
| supp:wildguardmix_van_harmful | 1984 | 1984 | 1984 | 1984 | 0 | 0 |
| supp:wildjailbreak_adv_benign | 3000 | 3000 | 0 | 0 | 0 | 0 |
| supp:wildjailbreak_adv_harmful | 3000 | 3000 | 3000 | 3000 | 0 | 0 |
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
| alpaca | 121 | 8 | 8 | 0 | 0.007 |
| beavertails | 120 | 18 | 16 | 65 | 3.011 |
| classical_dilemma | 16 | 3 | 3 | 0 | 0.405 |
| daily_dilemmas | 120 | 1 | 1 | 1 | 0.005 |
| dolly | 120 | 2 | 0 | 0 | 0.002 |
| hh_rlhf_harmless | 120 | 18 | 16 | 75 | 4.859 |
| hh_rlhf_helpful | 120 | 3 | 2 | 0 | 0.01 |
| hh_rlhf_redteam | 120 | 18 | 15 | 82 | 5.954 |
| jailbreak | 88 | 4 | 3 | 63 | 1.065 |
| moralchoice_highamb | 102 | 5 | 5 | 0 | 0.123 |
| narrative | 180 | 1 | 1 | 0 | 0.028 |
| supp:coconot_contrast | 75 | 4 | 2 | 0 | 0.006 |
| supp:falsereject_train | 1000 | 49 | 41 | 0 | 0.013 |
| supp:orbench_80k | 600 | 32 | 23 | 0 | 0.048 |
| supp:orbench_hard | 255 | 42 | 36 | 0 | 0.364 |
| supp:orbench_toxic | 130 | 0 | 0 | 107 | None |
| supp:phtest_harmless | 415 | 59 | 39 | 0 | 0.269 |
| supp:wildguardmix_adv_benign | 300 | 99 | 73 | 0 | 1.591 |
| supp:wildguardmix_adv_harmful | 300 | 0 | 0 | 276 | None |
| supp:wildguardmix_van_benign | 399 | 34 | 31 | 0 | 0.047 |
| supp:wildguardmix_van_harmful | 397 | 0 | 0 | 368 | None |
| supp:wildjailbreak_adv_benign | 600 | 121 | 76 | 0 | 0.547 |
| supp:wildjailbreak_adv_harmful | 600 | 0 | 0 | 552 | None |
| supp:wildjailbreak_van_benign | 999 | 47 | 37 | 0 | 0.013 |
| supp:wildjailbreak_van_harmful | 1000 | 0 | 0 | 948 | None |
| syn_advbenign | 45 | 10 | 8 | 6 | 0.125 |
| syn_benignsensitive | 90 | 5 | 4 | 4 | 0.014 |
| syn_cad | 113 | 0 | 0 | 0 | 0.004 |
| syn_intent | 120 | 2 | 1 | 62 | 0.047 |
| syn_subtleharm | 55 | 4 | 3 | 42 | 6.558 |
| toxicchat_safe | 105 | 11 | 9 | 2 | 0.06 |

## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)

- safe_blocked: 문장 11, 이웃 에너지 라벨 1 비율 0.2909, 출처 {'supp:wildjailbreak_van_benign': 25, 'beavertails': 6, 'hh_rlhf_harmless': 5, 'supp:wildguardmix_van_harmful': 3, 'supp:orbench_80k': 2, 'syn_benignsensitive': 2, 'syn_advbenign': 2, 'hh_rlhf_redteam': 2, 'supp:wildjailbreak_van_harmful': 2, 'supp:falsereject_train': 1, 'alpaca': 1, 'supp:coconot_contrast': 1, 'supp:wildguardmix_van_benign': 1, 'dolly': 1, 'hh_rlhf_helpful': 1}
- safe_passed: 문장 97, 이웃 에너지 라벨 1 비율 0.1216, 출처 {'supp:wildjailbreak_van_benign': 269, 'supp:wildguardmix_van_benign': 56, 'supp:falsereject_train': 20, 'beavertails': 16, 'supp:phtest_harmless': 15, 'supp:wildjailbreak_van_harmful': 14, 'hh_rlhf_harmless': 11, 'dolly': 10, 'supp:coconot_contrast': 10, 'hh_rlhf_redteam': 8, 'syn_advbenign': 8, 'supp:wildguardmix_van_harmful': 8, 'supp:wildjailbreak_adv_benign': 7, 'supp:orbench_80k': 6, 'alpaca': 4, 'syn_intent': 4, 'syn_subtleharm': 3, 'syn_benignsensitive': 3, 'toxicchat_safe': 3, 'hh_rlhf_helpful': 3, 'supp:orbench_hard': 3, 'supp:wildguardmix_adv_benign': 1, 'narrative': 1, 'supp:wildjailbreak_adv_harmful': 1, 'supp:orbench_toxic': 1}
- unsafe: 문장 83, 이웃 에너지 라벨 1 비율 0.6506, 출처 {'beavertails': 97, 'supp:wildjailbreak_van_benign': 66, 'hh_rlhf_harmless': 44, 'supp:wildjailbreak_van_harmful': 43, 'supp:falsereject_train': 38, 'supp:wildguardmix_van_harmful': 30, 'hh_rlhf_redteam': 24, 'supp:orbench_toxic': 15, 'supp:wildguardmix_van_benign': 10, 'syn_intent': 10, 'supp:orbench_80k': 9, 'syn_subtleharm': 9, 'hh_rlhf_helpful': 2, 'supp:wildjailbreak_adv_benign': 2, 'toxicchat_safe': 2, 'supp:orbench_hard': 2, 'supp:wildjailbreak_adv_harmful': 2, 'syn_advbenign': 2, 'daily_dilemmas': 2, 'moralchoice_highamb': 1, 'supp:phtest_harmless': 1, 'supp:wildguardmix_adv_harmful': 1, 'syn_benignsensitive': 1, 'supp:coconot_contrast': 1, 'dolly': 1}

## 5. 변형 비교: test 분할 거절 비율 (주 운영점, 평가 벤치 아님, DESIGN.md 13)

| 변형 | v4_safe | v4_harmful | overrefusal_benign | adversarial_benign | plain_benign | plain_harmful | adversarial_harmful |
|---|---|---|---|---|---|---|---|
| A0 | 0.076 (n 647) | 0.860 (n 235) | 0.074 (n 1172) | 0.260 (n 450) | 0.073 (n 698) | 0.941 (n 763) | 0.920 (n 450) |
| A0ft | 0.124 (n 647) | 0.936 (n 235) | 0.044 (n 1172) | 0.238 (n 450) | 0.062 (n 698) | 0.983 (n 763) | 0.984 (n 450) |
| A0ftM | 0.124 (n 647) | 0.936 (n 235) | 0.043 (n 1172) | 0.238 (n 450) | 0.059 (n 698) | 0.983 (n 763) | 0.984 (n 450) |
| Llama Guard 3 (입력) | 0.018 (n 647) | 0.651 (n 235) | 0.122 (n 1172) | 0.020 (n 450) | 0.057 (n 698) | 0.780 (n 763) | 0.498 (n 450) |

- Llama Guard 동등(무해는 거절이 같거나 적고, 유해는 같거나 많음): A0 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': True, 'adversarial_benign': False, 'plain_benign': False, 'plain_harmful': True, 'adversarial_harmful': True}, A0ft 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': True, 'adversarial_benign': False, 'plain_benign': False, 'plain_harmful': True, 'adversarial_harmful': True}, A0ftM 아니오 {'v4_safe': False, 'v4_harmful': True, 'overrefusal_benign': True, 'adversarial_benign': False, 'plain_benign': False, 'plain_harmful': True, 'adversarial_harmful': True}
- 곡선 전체에서 동등인 운영점: 없음

| 운영점 | 변형 | v4_safe | v4_harmful | overrefusal_benign | adversarial_benign | plain_benign | plain_harmful | adversarial_harmful |
|---|---|---|---|---|---|---|---|---|
| 0.005 | A0 | 0.037 | 0.770 | 0.041 | 0.153 | 0.039 | 0.885 | 0.856 |
| 0.005 | A0ft | 0.025 | 0.877 | 0.026 | 0.084 | 0.020 | 0.958 | 0.936 |
| 0.005 | A0ftM | 0.025 | 0.877 | 0.026 | 0.084 | 0.020 | 0.958 | 0.936 |
| 0.01 | A0 | 0.037 | 0.770 | 0.041 | 0.153 | 0.039 | 0.885 | 0.856 |
| 0.01 | A0ft | 0.025 | 0.877 | 0.026 | 0.084 | 0.020 | 0.958 | 0.936 |
| 0.01 | A0ftM | 0.025 | 0.877 | 0.026 | 0.084 | 0.020 | 0.958 | 0.936 |
| 0.02 | A0 | 0.037 | 0.770 | 0.041 | 0.153 | 0.039 | 0.885 | 0.856 |
| 0.02 | A0ft | 0.017 | 0.817 | 0.017 | 0.064 | 0.016 | 0.937 | 0.907 |
| 0.02 | A0ftM | 0.015 | 0.817 | 0.017 | 0.064 | 0.016 | 0.937 | 0.907 |
| 0.03 | A0 | 0.037 | 0.770 | 0.041 | 0.153 | 0.039 | 0.885 | 0.856 |
| 0.03 | A0ft | 0.025 | 0.877 | 0.026 | 0.080 | 0.020 | 0.958 | 0.927 |
| 0.03 | A0ftM | 0.025 | 0.877 | 0.026 | 0.080 | 0.020 | 0.958 | 0.927 |
| 0.04 | A0 | 0.037 | 0.770 | 0.041 | 0.153 | 0.039 | 0.885 | 0.856 |
| 0.04 | A0ft | 0.029 | 0.881 | 0.027 | 0.107 | 0.021 | 0.963 | 0.951 |
| 0.04 | A0ftM | 0.029 | 0.877 | 0.026 | 0.102 | 0.020 | 0.963 | 0.951 |
| 0.05 | A0 | 0.037 | 0.770 | 0.041 | 0.153 | 0.039 | 0.885 | 0.856 |
| 0.05 | A0ft | 0.046 | 0.894 | 0.032 | 0.129 | 0.029 | 0.975 | 0.956 |
| 0.05 | A0ftM | 0.046 | 0.894 | 0.032 | 0.127 | 0.029 | 0.975 | 0.956 |
| 0.07 | A0 | 0.057 | 0.821 | 0.055 | 0.180 | 0.057 | 0.920 | 0.847 |
| 0.07 | A0ft | 0.091 | 0.932 | 0.036 | 0.156 | 0.036 | 0.979 | 0.964 |
| 0.07 | A0ftM | 0.090 | 0.928 | 0.036 | 0.156 | 0.036 | 0.979 | 0.964 |
| 0.1 | A0 | 0.076 | 0.860 | 0.074 | 0.260 | 0.073 | 0.941 | 0.920 |
| 0.1 | A0ft | 0.124 | 0.936 | 0.044 | 0.238 | 0.062 | 0.983 | 0.984 |
| 0.1 | A0ftM | 0.124 | 0.936 | 0.043 | 0.238 | 0.059 | 0.983 | 0.984 |
| 0.15 | A0 | 0.101 | 0.915 | 0.114 | 0.398 | 0.105 | 0.954 | 0.962 |
| 0.15 | A0ft | 0.198 | 0.953 | 0.065 | 0.340 | 0.106 | 0.988 | 0.993 |
| 0.15 | A0ftM | 0.198 | 0.953 | 0.065 | 0.340 | 0.106 | 0.988 | 0.993 |
| 0.2 | A0 | 0.130 | 0.915 | 0.159 | 0.467 | 0.128 | 0.966 | 0.973 |
| 0.2 | A0ft | 0.295 | 0.966 | 0.083 | 0.400 | 0.145 | 0.990 | 0.996 |
| 0.2 | A0ftM | 0.295 | 0.966 | 0.083 | 0.400 | 0.145 | 0.990 | 0.996 |
| 0.3 | A0 | 0.229 | 0.953 | 0.259 | 0.536 | 0.218 | 0.980 | 0.978 |
| 0.3 | A0ft | 0.391 | 0.983 | 0.106 | 0.498 | 0.205 | 0.991 | 1.000 |
| 0.3 | A0ftM | 0.391 | 0.983 | 0.106 | 0.498 | 0.205 | 0.991 | 1.000 |

## 7. 신호별 판별력 (test 분할 AUROC; XSTest는 오류 분석 전용)

- A0 test: plain E 0.9769 F 0.9583; adversarial E 0.9214 F 0.8534; v4 E 0.9537 F 0.9386; overrefusal_vs_plain E 0.9768 F 0.9526
- A0 XSTest AUROC: {"E": 0.9383, "F": 0.8594}
  - 0.02: safe n 108 극단 E 2 harm E∧F 3 계층 {"Direct-Answer": 102, "Hard-block": 5, "Soft-reasoning": 1}; unsafe n 83 극단 E 49 harm E∧F 9 계층 {"Hard-block": 58, "Direct-Answer": 18, "Soft-reasoning": 7}
  - 0.03: safe n 108 극단 E 2 harm E∧F 3 계층 {"Direct-Answer": 102, "Hard-block": 5, "Soft-reasoning": 1}; unsafe n 83 극단 E 49 harm E∧F 9 계층 {"Hard-block": 58, "Direct-Answer": 18, "Soft-reasoning": 7}
  - 0.05: safe n 108 극단 E 2 harm E∧F 3 계층 {"Direct-Answer": 102, "Hard-block": 5, "Soft-reasoning": 1}; unsafe n 83 극단 E 49 harm E∧F 9 계층 {"Hard-block": 58, "Direct-Answer": 18, "Soft-reasoning": 7}
- A0ft test: plain E 0.9911 F 0.9862; adversarial E 0.9799 F 0.9386; v4 E 0.9721 F 0.9659; overrefusal_vs_plain E 0.9938 F 0.9873
- A0ft XSTest AUROC: {"E": 0.9575, "F": 0.8546}
  - 0.02: safe n 108 극단 E 1 harm E∧F 1 계층 {"Direct-Answer": 103, "Soft-reasoning": 3, "Hard-block": 2}; unsafe n 83 극단 E 53 harm E∧F 9 계층 {"Hard-block": 62, "Direct-Answer": 15, "Soft-reasoning": 6}
  - 0.03: safe n 108 극단 E 5 harm E∧F 0 계층 {"Direct-Answer": 88, "Soft-reasoning": 13, "Hard-block": 5, "Deliberation": 2}; unsafe n 83 극단 E 68 harm E∧F 0 계층 {"Hard-block": 68, "Direct-Answer": 8, "Soft-reasoning": 7}
  - 0.05: safe n 108 극단 E 5 harm E∧F 0 계층 {"Direct-Answer": 88, "Soft-reasoning": 13, "Hard-block": 5, "Deliberation": 2}; unsafe n 83 극단 E 72 harm E∧F 0 계층 {"Hard-block": 72, "Direct-Answer": 8, "Soft-reasoning": 3}
- A0ftM test: plain E 0.9911 F 0.9862; adversarial E 0.9799 F 0.9386; v4 E 0.9721 F 0.9659; overrefusal_vs_plain E 0.9938 F 0.9873
- A0ftM XSTest AUROC: {"E": 0.9575, "F": 0.8546}
  - 0.02: safe n 108 극단 E 1 harm E∧F 1 계층 {"Direct-Answer": 101, "Soft-reasoning": 3, "Hard-block": 2, "Deliberation": 2}; unsafe n 83 극단 E 53 harm E∧F 9 계층 {"Hard-block": 62, "Direct-Answer": 14, "Soft-reasoning": 6, "Deliberation": 1}
  - 0.03: safe n 108 극단 E 5 harm E∧F 0 계층 {"Direct-Answer": 88, "Soft-reasoning": 11, "Hard-block": 5, "Deliberation": 4}; unsafe n 83 극단 E 68 harm E∧F 0 계층 {"Hard-block": 68, "Direct-Answer": 7, "Soft-reasoning": 7, "Deliberation": 1}
  - 0.05: safe n 108 극단 E 5 harm E∧F 0 계층 {"Direct-Answer": 85, "Soft-reasoning": 11, "Deliberation": 7, "Hard-block": 5}; unsafe n 83 극단 E 72 harm E∧F 0 계층 {"Hard-block": 72, "Direct-Answer": 7, "Soft-reasoning": 3, "Deliberation": 1}

## 6. HarmBench 경로 (오류 분석 전용, 적합에 쓰지 않음; 문장 245, qwen 기록)

- A0@0.1 category: contextual {"Hard-block": 70, "Direct-Answer": 5, "Reasoned-Refusal": 1, "Soft-reasoning": 1}; standard {"Hard-block": 149, "Direct-Answer": 10, "Soft-reasoning": 8, "Reasoned-Refusal": 1}
- A0@0.1 semantic_category: chemical_biological {"Hard-block": 38, "Direct-Answer": 5, "Reasoned-Refusal": 2, "Soft-reasoning": 1}; cybercrime_intrusion {"Hard-block": 44, "Direct-Answer": 6, "Soft-reasoning": 3}; harassment_bullying {"Hard-block": 21, "Soft-reasoning": 1}; harmful {"Hard-block": 17, "Soft-reasoning": 1}; illegal {"Hard-block": 48, "Direct-Answer": 3, "Soft-reasoning": 1}; misinformation_disinformation {"Hard-block": 51, "Soft-reasoning": 2, "Direct-Answer": 1}
- A0@0.1 length: 300-1000 {"Hard-block": 24, "Direct-Answer": 2, "Reasoned-Refusal": 1}; <300 {"Hard-block": 149, "Direct-Answer": 10, "Soft-reasoning": 8, "Reasoned-Refusal": 1}; >1000 {"Hard-block": 46, "Direct-Answer": 3, "Soft-reasoning": 1}
- A0ft@0.02 category: contextual {"Hard-block": 60, "Direct-Answer": 10, "Soft-reasoning": 4, "Reasoned-Refusal": 3}; standard {"Hard-block": 149, "Direct-Answer": 14, "Soft-reasoning": 5}
- A0ft@0.02 semantic_category: chemical_biological {"Hard-block": 39, "Direct-Answer": 6, "Reasoned-Refusal": 1}; cybercrime_intrusion {"Hard-block": 35, "Direct-Answer": 13, "Soft-reasoning": 4, "Reasoned-Refusal": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 16, "Soft-reasoning": 2}; illegal {"Hard-block": 47, "Direct-Answer": 3, "Soft-reasoning": 2}; misinformation_disinformation {"Hard-block": 50, "Direct-Answer": 2, "Reasoned-Refusal": 1, "Soft-reasoning": 1}
- A0ft@0.02 length: 300-1000 {"Hard-block": 18, "Direct-Answer": 5, "Soft-reasoning": 3, "Reasoned-Refusal": 1}; <300 {"Hard-block": 149, "Direct-Answer": 14, "Soft-reasoning": 5}; >1000 {"Hard-block": 42, "Direct-Answer": 5, "Reasoned-Refusal": 2, "Soft-reasoning": 1}
- A0ft@0.03 category: contextual {"Hard-block": 68, "Soft-reasoning": 5, "Direct-Answer": 4}; standard {"Hard-block": 154, "Soft-reasoning": 7, "Direct-Answer": 7}
- A0ft@0.03 semantic_category: chemical_biological {"Hard-block": 41, "Direct-Answer": 3, "Soft-reasoning": 2}; cybercrime_intrusion {"Hard-block": 40, "Soft-reasoning": 8, "Direct-Answer": 5}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 49, "Direct-Answer": 3}; misinformation_disinformation {"Hard-block": 52, "Soft-reasoning": 2}
- A0ft@0.03 length: 300-1000 {"Hard-block": 22, "Soft-reasoning": 4, "Direct-Answer": 1}; <300 {"Hard-block": 154, "Soft-reasoning": 7, "Direct-Answer": 7}; >1000 {"Hard-block": 46, "Direct-Answer": 3, "Soft-reasoning": 1}
- A0ftM@0.02 category: contextual {"Hard-block": 60, "Direct-Answer": 7, "Soft-reasoning": 4, "Deliberation": 3, "Reasoned-Refusal": 3}; standard {"Hard-block": 149, "Direct-Answer": 10, "Soft-reasoning": 5, "Deliberation": 4}
- A0ftM@0.02 semantic_category: chemical_biological {"Hard-block": 39, "Direct-Answer": 3, "Deliberation": 3, "Reasoned-Refusal": 1}; cybercrime_intrusion {"Hard-block": 35, "Direct-Answer": 9, "Deliberation": 4, "Soft-reasoning": 4, "Reasoned-Refusal": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 16, "Soft-reasoning": 2}; illegal {"Hard-block": 47, "Direct-Answer": 3, "Soft-reasoning": 2}; misinformation_disinformation {"Hard-block": 50, "Direct-Answer": 2, "Reasoned-Refusal": 1, "Soft-reasoning": 1}
- A0ftM@0.02 length: 300-1000 {"Hard-block": 18, "Direct-Answer": 3, "Soft-reasoning": 3, "Deliberation": 2, "Reasoned-Refusal": 1}; <300 {"Hard-block": 149, "Direct-Answer": 10, "Soft-reasoning": 5, "Deliberation": 4}; >1000 {"Hard-block": 42, "Direct-Answer": 4, "Reasoned-Refusal": 2, "Deliberation": 1, "Soft-reasoning": 1}
- A0ftM@0.03 category: contextual {"Hard-block": 68, "Soft-reasoning": 4, "Deliberation": 3, "Direct-Answer": 2}; standard {"Hard-block": 154, "Direct-Answer": 6, "Soft-reasoning": 4, "Deliberation": 4}
- A0ftM@0.03 semantic_category: chemical_biological {"Hard-block": 41, "Deliberation": 3, "Soft-reasoning": 1, "Direct-Answer": 1}; cybercrime_intrusion {"Hard-block": 40, "Soft-reasoning": 5, "Deliberation": 4, "Direct-Answer": 4}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 49, "Direct-Answer": 3}; misinformation_disinformation {"Hard-block": 52, "Soft-reasoning": 2}
- A0ftM@0.03 length: 300-1000 {"Hard-block": 22, "Soft-reasoning": 3, "Deliberation": 2}; <300 {"Hard-block": 154, "Direct-Answer": 6, "Soft-reasoning": 4, "Deliberation": 4}; >1000 {"Hard-block": 46, "Direct-Answer": 2, "Soft-reasoning": 1, "Deliberation": 1}
- A0ft@0.1 category: contextual {"Hard-block": 75, "Soft-reasoning": 2}; standard {"Hard-block": 162, "Soft-reasoning": 3, "Direct-Answer": 3}
- A0ft@0.1 semantic_category: chemical_biological {"Hard-block": 44, "Soft-reasoning": 2}; cybercrime_intrusion {"Hard-block": 50, "Soft-reasoning": 2, "Direct-Answer": 1}; harassment_bullying {"Hard-block": 22}; harmful {"Hard-block": 18}; illegal {"Hard-block": 49, "Direct-Answer": 2, "Soft-reasoning": 1}; misinformation_disinformation {"Hard-block": 54}
- A0ft@0.1 length: 300-1000 {"Hard-block": 26, "Soft-reasoning": 1}; <300 {"Hard-block": 162, "Soft-reasoning": 3, "Direct-Answer": 3}; >1000 {"Hard-block": 49, "Soft-reasoning": 1}
