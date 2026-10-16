# 코퍼스 격리 검사 (DESIGN.md 3)

- 대상 행 65,848, 남긴 행 64,986
- 가드 탈락 22 (정확 일치·5-gram 포함률 > 0.5), 임베딩 탈락 9 (MiniLM 코사인 ≥ 0.92), XSTest 유형 합성 출처 탈락 831 (trick_safe, benign_harm_discuss, DESIGN.md 11)
- 분할: {'train': 52569, 'test': 6211, 'val': 6206}

## 출처별 탈락

- beavertails|guard: 1
- benign_harm_discuss|xstest_type: 322
- supp:coconot_contrast|guard: 2
- supp:orbench_toxic|guard: 3
- supp:wildguardmix_van_benign|guard: 2
- supp:wildguardmix_van_harmful|guard: 2
- supp:wildjailbreak_van_benign|embedding: 9
- supp:wildjailbreak_van_benign|guard: 6
- supp:wildjailbreak_van_harmful|guard: 6
- trick_safe|xstest_type: 509
