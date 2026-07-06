"""
UNESCO Ethics of AI CSV에서 평가용 시나리오를 선별합니다.

원칙당 2~3개 (총 25개) 선별 기준:
  - 시나리오 길이 다양성 (짧은/중간/긴)
  - 원칙별 독립적인 주제 커버리지
  - PoC 수준에서 통계적 유의성 검증 가능한 최소 수량

사용법:
    python -m pea_eval.data.select_scenarios
"""
import csv
import hashlib
import os
import random
from collections import defaultdict
from pathlib import Path

# 상위 모듈에서 경로 가져오기
try:
    from pea_eval.config.settings import (
        UNESCO_CSV_PATH, DATA_DIR, normalize_principle
    )
except ImportError:
    # 직접 실행 시 경로 설정
    _this = Path(__file__).resolve()
    _module_dir = _this.parent.parent
    _project_root = _module_dir.parent
    UNESCO_CSV_PATH = _project_root / "unesco_ethics_of_artificial_intelligence.csv"
    DATA_DIR = _this.parent

    PRINCIPLE_NORMALIZATION = {
        "Awareness & Literacy": "Awareness and Literacy",
        "Multi-stakeholder and Adaptive Governance and Collaboration":
            "Multi-stakeholder and Adaptive Governance & Collaboration",
        "Safety and Security & Fairness and Non-Discrimination":
            "Safety and Security",
        "Safety and Security, Responsibility and Accountability, "
        "and Human Oversight and Determination":
            "Safety and Security",
        "Human Dignity and Autonomy":
            "Proportionality and Do No Harm",
    }

    def normalize_principle(raw: str) -> str:
        stripped = raw.strip()
        return PRINCIPLE_NORMALIZATION.get(stripped, stripped)


# ── 선별 설정 ──
TARGET_PRINCIPLES = [
    "Awareness and Literacy",
    "Fairness and Non-Discrimination",
    "Right to Privacy and Data Protection",
    "Proportionality and Do No Harm",
    "Transparency and Explainability",
    "Safety and Security",
    "Sustainability",
    "Responsibility and Accountability",
    "Human Oversight and Determination",
    "Multi-stakeholder and Adaptive Governance & Collaboration",
]

# 원칙별 선별 수량 (풀 크기에 따라 조절)
SELECTION_COUNTS = {
    "Fairness and Non-Discrimination": 3,
    "Right to Privacy and Data Protection": 3,
    "Proportionality and Do No Harm": 3,
    "Transparency and Explainability": 2,
    "Safety and Security": 2,
    "Sustainability": 2,
    "Responsibility and Accountability": 3,
    "Human Oversight and Determination": 2,
    "Multi-stakeholder and Adaptive Governance & Collaboration": 2,
    "Awareness and Literacy": 3,
}
# 총 25개


def load_csv_rows() -> list[dict]:
    """원본 UNESCO CSV를 로드하고 원칙명을 정규화합니다."""
    rows = []
    with open(UNESCO_CSV_PATH, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row["principle_raw"] = row["principle"]
            row["principle"] = normalize_principle(row["principle"])
            row["instruction_len"] = len(row.get("instruction", ""))
            row["response_len"] = len(row.get("response", ""))
            rows.append(row)
    return rows


def select_diverse_items(
    items: list[dict],
    count: int,
    seed: int = 42,
) -> list[dict]:
    """
    길이 다양성 기반으로 count개 항목을 선별합니다.

    전략:
      1. instruction_len 기준으로 3등분 (짧/중/긴)
      2. 각 등분에서 고르게 선택
      3. response_len은 중간 이상인 것 우선 (충분한 참고 답변)
    """
    rng = random.Random(seed)

    # response가 너무 짧은 것 제외 (500자 미만)
    valid = [it for it in items if it["response_len"] >= 500]
    if len(valid) < count:
        valid = items  # 부족하면 전체에서 선택

    # 길이 기준 정렬 후 3등분
    sorted_by_len = sorted(valid, key=lambda x: x["instruction_len"])
    n = len(sorted_by_len)
    if n == 0:
        return []

    tercile_size = max(1, n // 3)
    short = sorted_by_len[:tercile_size]
    medium = sorted_by_len[tercile_size:2 * tercile_size]
    long = sorted_by_len[2 * tercile_size:]

    selected = []
    pools = [short, medium, long]

    # 각 풀에서 순환하며 선택
    for i in range(count):
        pool = pools[i % 3]
        if not pool:
            pool = valid  # 풀 소진 시 전체에서
        choice = rng.choice(pool)
        selected.append(choice)
        # 중복 방지
        if choice in pool:
            pool.remove(choice)
        if choice in valid:
            valid.remove(choice)

    return selected


def generate_scenario_id(principle: str, instruction: str) -> str:
    """결정론적 시나리오 ID 생성"""
    raw = f"{principle}:{instruction[:100]}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def run_selection():
    """시나리오 선별 실행 및 CSV 저장"""
    print(f"[UNESCO 시나리오 선별] CSV 로드 중: {UNESCO_CSV_PATH}")
    rows = load_csv_rows()
    print(f"  총 {len(rows)}행 로드 완료")

    # 원칙별 그룹화
    by_principle = defaultdict(list)
    for row in rows:
        p = row["principle"]
        if p in TARGET_PRINCIPLES:
            by_principle[p].append(row)

    print(f"\n  원칙별 분포:")
    for p in TARGET_PRINCIPLES:
        print(f"    {p}: {len(by_principle[p])}개")

    # 선별 실행
    selected = []
    for principle in TARGET_PRINCIPLES:
        count = SELECTION_COUNTS.get(principle, 2)
        items = by_principle.get(principle, [])
        if not items:
            print(f"  [WARN] {principle}: no items, skipping")
            continue

        chosen = select_diverse_items(items, count)
        for item in chosen:
            item["scenario_id"] = generate_scenario_id(
                principle, item.get("instruction", "")
            )
        selected.extend(chosen)
        print(f"  [OK] {principle}: {len(chosen)} selected")

    # CSV 저장
    output_path = DATA_DIR / "unesco_items.csv"
    fieldnames = [
        "scenario_id", "principle", "instruction", "response",
        "instruction_len", "response_len",
    ]

    with open(output_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in selected:
            writer.writerow({
                "scenario_id": item["scenario_id"],
                "principle": item["principle"],
                "instruction": item.get("instruction", ""),
                "response": item.get("response", ""),
                "instruction_len": item["instruction_len"],
                "response_len": item["response_len"],
            })

    print(f"\n[완료] {len(selected)}개 시나리오 → {output_path}")
    return selected


if __name__ == "__main__":
    run_selection()
