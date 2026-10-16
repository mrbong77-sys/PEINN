# 코퍼스 격리 검사 (DESIGN.md 3)

- 대상 행 28,033, 남긴 행 27,195
- 가드 탈락 7 (정확 일치·5-gram 포함률 > 0.5), 임베딩 탈락 0 (MiniLM 코사인 ≥ 0.92), XSTest 유형 합성 출처 탈락 831 (trick_safe, benign_harm_discuss, DESIGN.md 11)
- 분할: {'train': 22338, 'test': 2434, 'val': 2423}

## 출처별 탈락

- beavertails|guard: 1
- benign_harm_discuss|xstest_type: 322
- supp:coconot_contrast|guard: 2
- supp:orbench_toxic|guard: 3
- supp:wildjailbreak_van_benign|guard: 1
- trick_safe|xstest_type: 509
