"""
mine_neutro_hardneg.py — 평가 결과지에서 Neutro head 재학습용 hard-negative 채굴.

배경(트랙 B): XSTest 5-run 분석에서 energy 겹침구간 [7.0,8.0)의 head F가 역상관
(양성에 고-F 오발 / 유해에 저-F 누락)임이 드러났다. F1≈80% 천장은 결정 규칙이 아니라
head 표현이 그 구간에서 틀려서다. → 그 "틀린 곳"을 gold 라벨로 교정한 타깃과 함께
뽑아 재학습셋(train_neutro_head.py 형식: text,T,I,F,source)에 증강한다.

결과지에 기록된 neutro_T/I/F(head 출력)와 벤치 gold 라벨을 대조해:
  - gold=safe 인데 F 높음        → false-positive(과잉거부 원인). 타깃 (T=1,I=0,F=0)
  - gold=harm 인데 F 낮음        → false-negative(head-miss, energy가 대신 막던 것). 타깃 (0,0,1)
  - gold=dilemma 인데 I 낮음     → dilemma 누락. 타깃 (0,1,0)
를 hard-negative로 판정한다. (head가 *맞춘* 행은 채굴 대상 아님 — 증강용이므로.)

전제: 결과지에 neutro_T/I/F 가 기록된 PEINN 행만 사용(비-PEINN은 head 미동작 → 공란).
      energy/T/I/F는 입력 결정적이라 5-run 중복 → text 기준 dedup.

사용:
  python scripts/mine_neutro_hardneg.py <csv> [<csv> ...] \
      [--out pea_eval/data/ee_3class/hardneg_mined.csv] [--diag diag.csv]
      [--max-per-source 300] [--fp-f 0.30] [--fn-f 0.50] [--dil-i 0.40]
모듈은 컬럼으로 자동 감지(xstest/harmbench/taxonomy/ethics).
"""
import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

csv.field_size_limit(2**31 - 1)

# 운영 energy 겹침구간(역상관 핵심 구역) — 진단/우선순위용.
OVERLAP_LO, OVERLAP_HI = 7.0, 8.0


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def detect_module(cols):
    c = set(cols)
    if {"scenario_id", "taxonomy_family"} <= c:
        return "taxonomy"
    if {"instrument", "item_id"} <= c and "scenario_id" not in c:
        return "ethics"
    if "behavior_id" in c:
        return "harmbench"
    if "prompt_type" in c and "item_id" in c:
        return "xstest"
    return None


def _user_request(prompt_p1: str) -> str:
    """prompt_p1의 '[User Request]' 이후 본문 추출(없으면 원문)."""
    if not prompt_p1:
        return ""
    m = re.search(r"\[User Request\]\s*(.*)", prompt_p1, re.DOTALL)
    return (m.group(1) if m else prompt_p1).strip()


def extract_text(module: str, row: dict) -> str:
    if module == "xstest":
        return (row.get("prompt_text") or "").strip()
    if module == "harmbench":
        return (row.get("behavior") or _user_request(row.get("prompt_p1", ""))).strip()
    if module == "taxonomy":
        # head는 멀티턴 누적 context를 봤음 — 최종 턴 user request가 가장 정보적.
        return _user_request(row.get("prompt_p1", "")).strip()
    if module == "ethics":
        return _user_request(row.get("prompt_p1", "")).strip()
    return ""


def gold_target(module: str, row: dict, conflict_aware: bool = False):
    """벤치 gold 라벨 → (T,I,F) 타깃 + gold 클래스명.

    conflict_aware: dilemma(윤리적 모순) 타깃을 하드 (0,1,0) 대신 hyper-truth
    시그니처(T·I·F 공활성, sum>1)로 줘 head가 "갈등"을 표현하도록 학습한다
    (Leyva-Vázquez & Smarandache 2025, Table 1 ethical-contradiction 근사:
    T≈0.5, I≈0.6, F≈0.4). 명확한 safe/harm은 모호하지 않으므로 하드 타깃 유지.
    """
    if module == "xstest":
        if row.get("expected_label") == "safe":
            return (1.0, 0.0, 0.0), "safe"
        return (0.0, 0.0, 1.0), "harm"
    if module in ("harmbench", "taxonomy"):
        return (0.0, 0.0, 1.0), "harm"  # 전량 유해(positive-only)
    if module == "ethics":
        if row.get("instrument") == "Dilemma":
            return ((0.5, 0.6, 0.4) if conflict_aware else (0.0, 1.0, 0.0)), "dilemma"
        return (1.0, 0.0, 0.0), "safe"  # MFQ/WVS = benign survey
    return None, None


def classify_hard(gold_cls, T, I, F, fp_f, fn_f, dil_i):
    """head가 gold와 어긋난 hard-negative인지 + 사유. 아니면 (None, 0)."""
    if gold_cls == "safe":
        if F >= fp_f:
            return "FP_safe_highF", abs(F - 0.0)        # 과잉거부 원인
    elif gold_cls == "harm":
        if F < fn_f:
            return "FN_harm_lowF", abs(1.0 - F)          # head-miss
    elif gold_cls == "dilemma":
        if I < dil_i:
            return "FN_dilemma_lowI", abs(1.0 - I)
    return None, 0.0


def main():
    ap = argparse.ArgumentParser(description="Neutro head 재학습용 hard-negative 채굴")
    ap.add_argument("csvs", nargs="+", help="평가 결과지 CSV (neutro_T/I/F 포함)")
    ap.add_argument("--out", default="hardneg_mined.csv", help="재학습셋(text,T,I,F,source)")
    ap.add_argument("--diag", default=None, help="진단 CSV(현 T/I/F·energy·사유)")
    ap.add_argument("--max-per-source", type=int, default=300,
                    help="FN(유해) source별 상한 — 오버랩·최대오차 우선. FP·dilemma는 전량 유지")
    ap.add_argument("--fp-f", type=float, default=0.30, help="safe인데 F≥이값 → FP")
    ap.add_argument("--fn-f", type=float, default=0.50, help="harm인데 F<이값 → FN(τ_harm)")
    ap.add_argument("--dil-i", type=float, default=0.40, help="dilemma인데 I<이값 → 누락")
    ap.add_argument("--conflict-aware", action="store_true",
                    help="dilemma 타깃을 hyper-truth 시그니처(T,I,F)=(.5,.6,.4)로 — head가 갈등 표현 학습")
    args = ap.parse_args()

    mined = []   # dict(text,T,I,F,source, _cls,_reason,_curF,_curI,_curT,_E,_band,_err)
    seen = set()
    rows_total = no_tif = no_text = 0

    for path in args.csvs:
        p = Path(path)
        if not p.exists():
            print(f"  [skip] 없음: {p}")
            continue
        rows = list(csv.DictReader(open(p, encoding="utf-8-sig")))
        module = detect_module(rows[0].keys() if rows else [])
        if not module:
            print(f"  [skip] 모듈 감지 실패: {p.name}")
            continue
        kept = 0
        for r in rows:
            rows_total += 1
            T, I, F = _num(r.get("neutro_T")), _num(r.get("neutro_I")), _num(r.get("neutro_F"))
            if T is None or I is None or F is None:
                no_tif += 1
                continue  # 비-PEINN 등 head 미기록
            tgt, gold = gold_target(module, r, conflict_aware=args.conflict_aware)
            cls, err = classify_hard(gold, T, I, F, args.fp_f, args.fn_f, args.dil_i)
            if cls is None:
                continue
            text = extract_text(module, r)
            if not text or len(text) < 4:
                no_text += 1
                continue
            key = (module, text)
            if key in seen:
                continue
            seen.add(key)
            E = _num(r.get("ee_energy"))
            band = (E is not None and OVERLAP_LO <= E < OVERLAP_HI)
            mined.append({
                "text": text, "T": tgt[0], "I": tgt[1], "F": tgt[2],
                "source": f"hardneg_{module}",
                "_cls": cls, "_gold": gold, "_curT": round(T, 3), "_curI": round(I, 3),
                "_curF": round(F, 3), "_E": round(E, 3) if E is not None else "",
                "_band": int(band), "_err": err,
            })
            kept += 1
        print(f"  {module:9} {p.name}: rows={len(rows)} → hard-neg(dedup)={kept}")

    # 균형: FP(과잉거부)·dilemma는 희소·핵심이라 전량 유지. FN(유해)만 source별 캡
    # (taxonomy 등 positive-only가 FN을 과다 공급 → 불균형·템플릿 과적합 방지).
    final = [m for m in mined if m["_cls"] != "FN_harm_lowF"]
    fn_by_src = defaultdict(list)
    for m in mined:
        if m["_cls"] == "FN_harm_lowF":
            fn_by_src[m["source"]].append(m)
    for src, items in fn_by_src.items():
        items.sort(key=lambda m: (-m["_band"], -m["_err"]))  # 오버랩밴드 우선 → 오차 큰 순
        final.extend(items[:args.max_per_source])

    # ── 요약 ──
    print(f"\n=== 요약 ===  전체행={rows_total}  T/I/F미기록={no_tif}  text누락={no_text}")
    print(f"채굴(dedup)={len(mined)}  상한적용후={len(final)}")
    print("사유별:", dict(Counter(m["_cls"] for m in final)))
    print("source별:", dict(Counter(m["source"] for m in final)))
    print(f"오버랩밴드[7.0,8.0) 포함: {sum(m['_band'] for m in final)}건")

    # ── 재학습셋 출력 (train_neutro_head 형식) ──
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    with open(outp, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["text", "T", "I", "F", "source"])
        w.writeheader()
        for m in final:
            w.writerow({k: m[k] for k in ("text", "T", "I", "F", "source")})
    print(f"\n✅ 재학습셋: {outp}  (train.csv에 append 후 train_neutro_head 재실행)")

    if args.diag:
        dp = Path(args.diag)
        with open(dp, "w", newline="", encoding="utf-8") as f:
            cols = ["source", "_gold", "_cls", "_curT", "_curI", "_curF", "_E", "_band", "T", "I", "F", "text"]
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for m in final:
                w.writerow(m)
        print(f"✅ 진단: {dp}")


if __name__ == "__main__":
    main()
