"""
augment_neutro_istates.py — (트랙 B2b) Neutrosophic I-state exemplar 합성 증강.

배경: B2 파일럿에서 train.csv는 *명확 safe/harm + dilemma*는 있으나 **ignorance/
contradiction/paradox/vagueness가 사실상 0**(60건 중 ignorance 0, contradiction 1)임이
확인됨. 재라벨만으론 head가 이 상태들을 학습할 수 없다. → 논문(Leyva-Vázquez &
Smarandache 2025, Table 1)의 5현상 시그니처에 맞춰 **benign 추상 명제를 합성**해
soft target (T,I,F)와 함께 train.csv에 증강한다.

전부 benign 추상/철학 명제라 우발 유해 0. LLM 미사용·결정적.

soft target (논문 Table 1 근사):
  ignorance     (T,I,F)=(0.15, 0.83, 0.15)   미지/결정불가 사실
  contingency   (0.40, 0.48, 0.12)           미래 우연
  paradox       (0.05, 1.00, 0.50)           논리 자기참조
  contradiction (0.50, 0.60, 0.40)           윤리 모순(hyper-truth; T·F 공활성)
  vagueness     (0.62, 0.28, 0.22)           경계 모호(sorites)

사용:
  python scripts/augment_neutro_istates.py --repeat 2 \
      --out pea_eval/data/ee_3class/aug_istates.csv
"""
import argparse
import csv
import random
from collections import Counter
from pathlib import Path

csv.field_size_limit(2**31 - 1)

# (T, I, F) soft target per 현상
TARGET = {
    "ignorance":     (0.15, 0.83, 0.15),
    "contingency":   (0.40, 0.48, 0.12),
    "paradox":       (0.05, 1.00, 0.50),
    "contradiction": (0.50, 0.60, 0.40),
    "vagueness":     (0.62, 0.28, 0.22),
}


def _combos():
    out = []  # (text, phenomenon)

    # ── ignorance: 알 수 없거나 결정 불가능한 사실 ──
    vast = ["grains of sand on Earth", "stars in the observable universe",
            "atoms in the Pacific Ocean", "blades of grass in Brazil",
            "raindrops that fell on London in 1850", "leaves on all trees in the Amazon"]
    for v in vast:
        out.append((f"Is the exact number of {v} odd or even right now?", "ignorance"))
    unknowable_past = ["what Julius Caesar ate for breakfast on his 30th birthday",
                       "the exact words Socrates whispered the moment before he died",
                       "how many times Shakespeare sneezed in his lifetime",
                       "the precise thought in Cleopatra's mind at noon on her last day"]
    for u in unknowable_past:
        out.append((f"What was {u}?", "ignorance"))
    unobservable = ["intelligent life exists in the Andromeda galaxy at this exact moment",
                    "a particular electron beyond the cosmic horizon is spinning up or down",
                    "any undiscovered prime gap pattern holds past all computable bounds"]
    for u in unobservable:
        out.append((f"Is it true that {u}?", "ignorance"))

    # ── contingency: 미래 우연 ──
    cities = ["Seoul", "New York", "Cairo", "Oslo"]
    for c in cities:
        out.append((f"Will it rain in {c} on this date exactly one year from now?", "contingency"))
    fut = ["a specific lottery ticket will win next month",
           "the price of gold will be higher this day next year",
           "the next coin I flip tomorrow will land heads",
           "my favorite team will win their match next season"]
    for f in fut:
        out.append((f"Is it the case that {f}?", "contingency"))

    # ── paradox: 논리 자기참조/역설 ──
    out += [(p, "paradox") for p in [
        "This sentence is false.",
        "The next sentence is true. The previous sentence is false. Which is which?",
        "Is the answer to this very question 'no'?",
        "A barber shaves everyone who does not shave themselves. Who shaves the barber?",
        "Does the set of all sets that do not contain themselves contain itself?",
        "Can an omnipotent being create a stone so heavy it cannot lift it?",
        "If 'heterological' means 'not describing itself', is 'heterological' heterological?",
        "I am lying right now. Is that statement true or false?",
        "This card's other side says the statement on this side is true; that side says this side is false.",
        "Achilles can never overtake the tortoise because he must first reach where it was — true?",
    ]]

    # ── contradiction: 윤리 모순 (T·F 공활성, hyper-truth) ──
    out += [(c, "contradiction") for c in [
        "Lying to save an innocent life is morally right and morally wrong at the same time.",
        "Stealing a loaf of bread to feed a starving child is both justified and unjustified.",
        "Breaking a solemn promise to prevent a greater harm is simultaneously good and bad.",
        "Punishing one innocent to save five is at once defensible and indefensible.",
        "A just war is both a moral necessity and a moral failure.",
        "Telling a dying patient a comforting falsehood is kind and cruel together.",
        "Civil disobedience that breaks the law to uphold justice is lawful in spirit yet unlawful in fact.",
        "Sacrificing privacy for collective safety is both protective and violating.",
    ]]

    # ── vagueness: 경계 모호 (sorites) ──
    out += [(v, "vagueness") for v in [
        "A person who is exactly 1.75 meters tall is tall.",
        "A 40-year-old person is old.",
        "A heap of ten thousand grains with a single grain removed is still a heap.",
        "Someone with exactly 1,000 hairs on their head is bald.",
        "A room at exactly 25 degrees Celsius is hot.",
        "A coffee with three grains of sugar is sweet.",
        "A wealthy person becomes non-wealthy the moment they lose one cent.",
        "A pile of two grains of sand is a heap.",
        "A 2-day-old loaf of bread is fresh.",
        "Someone who has read 49 of 50 chapters has finished the book.",
    ]]
    return out


def _norm(s):
    return " ".join(s.lower().split())


def main():
    ap = argparse.ArgumentParser(description="(B2b) Neutrosophic I-state 합성 증강")
    ap.add_argument("--out", default="aug_istates.csv")
    ap.add_argument("--count", type=int, default=300, help="목표 상한")
    ap.add_argument("--per-cat-cap", type=int, default=0, help="현상별 상한(0=무제한)")
    ap.add_argument("--repeat", type=int, default=2, help="각 행 N회 복제(오버샘플)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--exclude", default=None, help="이 CSV의 text 제외(원문 오염 방지)")
    args = ap.parse_args()

    items = _combos()
    seen, uniq = set(), []
    for t, c in items:
        k = _norm(t)
        if k not in seen:
            seen.add(k); uniq.append((t, c))

    if args.exclude and Path(args.exclude).exists():
        excl = {_norm(r["text"]) for r in csv.DictReader(open(args.exclude, encoding="utf-8")) if r.get("text")}
        uniq = [(t, c) for t, c in uniq if _norm(t) not in excl]

    rng = random.Random(args.seed)
    rng.shuffle(uniq)
    if args.per_cat_cap > 0:
        cnt, capped = Counter(), []
        for t, c in uniq:
            if cnt[c] < args.per_cat_cap:
                capped.append((t, c)); cnt[c] += 1
        uniq = capped
    uniq = uniq[:args.count]

    print(f"고유 {len(uniq)}건  현상:", dict(Counter(c for _, c in uniq)))
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "T", "I", "F", "source"])
        w.writeheader()
        for _ in range(max(1, args.repeat)):
            for t, c in uniq:
                T, I, F = TARGET[c]
                w.writerow({"text": t, "T": T, "I": I, "F": F, "source": f"aug_istate_{c}"})
    total = len(uniq) * max(1, args.repeat)
    print(f"✅ I-state 합성셋: {outp}  고유 {len(uniq)} × repeat {max(1,args.repeat)} = {total}행")
    print("   soft target = 논문 Table 1 시그니처. contradiction은 T·F 공활성(hyper-truth) 학습용.")


if __name__ == "__main__":
    main()
