# 코퍼스 격리 검사 (DESIGN.md 3)

- 대상 행 12,511, 남긴 행 11,679
- 가드 탈락 1 (정확 일치·5-gram 포함률 > 0.5), 임베딩 탈락 0 (MiniLM 코사인 ≥ 0.92), XSTest 유형 합성 출처 탈락 831 (trick_safe, benign_harm_discuss, DESIGN.md 11)
- 분할: {'train': 9924, 'test': 882, 'val': 873}

## 출처별 탈락

- beavertails|guard: 1
- benign_harm_discuss|xstest_type: 322
- trick_safe|xstest_type: 509
