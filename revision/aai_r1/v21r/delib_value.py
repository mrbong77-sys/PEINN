"""DESIGN.md 43: what the I channel's routing does and what deliberation adds (Eugene 2026-10-19 KST, option B).

CPU only, from results/forced (no generation, no judging):
  selection  per variant, how the routing texts of each kind are routed at the main cap; the texts whose route PEINN's
             dilemma condition changes (the gate again without the Deliberation tier, same signals and thresholds); and,
             threshold-free, how well each head's deliberation signal ranks the 36 Ethics dilemmas above the other
             1,485 bench texts (AUROC, average precision; I, p(ambiguous) for A2/A2ft, 1 - 2|p - .5| for A3/A3ft) with a
             bootstrap over texts for the I-against-softmax differences;
  effect     the RQI of the Ethics dilemmas answered under the Deliberation posture against the bare Direct answer, per
             base model, for the dilemmas PEINN deliberates and for the rest (forced answers, one verdict per answer).

    python -m v21r delib-value   -> results/analysis/delib_value.json, delib_value.md
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import rankdata

from . import bench_stats as BS
from . import common as C
from . import data as D
from . import paper_ablation as P
from . import theta as TH

VARIANTS = ("A0ftM", "A0ft", "A2ft", "A3ft", "A1ft", "A0", "A2", "A3")
CAT = {"Dilemma": "dilemma", "MFQ": "MFQ", "WVS": "WVS"}


def categories(check: bool) -> pd.Series:
    cat = {}
    for b in ("ethics", "xstest", "ggb", "morables", "harmbench", "taxonomy"):
        d = pd.read_csv(D.odir(check) / "forced" / f"{b}_qwen.csv.gz", low_memory=False, dtype={"sha": str})
        if b == "ethics":
            cat.update({s: CAT[i] for s, i in d[["sha", "instrument"]].drop_duplicates().itertuples(index=False)})
        elif b == "xstest":
            cat.update({s: f"xstest_{e}" for s, e in d[["sha", "expected_label"]].drop_duplicates().itertuples(index=False)})
        else:
            cat.update({s: b for s in d.sha.unique()})
    return pd.Series(cat, name="cat")


def auc(y: np.ndarray, s: np.ndarray) -> float:
    r = rankdata(s)
    n1, n0 = y.sum(), len(y) - y.sum()
    return float((r[y == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def ap(y: np.ndarray, s: np.ndarray) -> float:
    o = np.argsort(-s, kind="stable")
    yy = y[o]
    return float((np.cumsum(yy) / np.arange(1, len(yy) + 1))[yy == 1].mean())


def _signals(check: bool, v: str, idx) -> pd.DataFrame:
    s = pd.read_csv(D.odir(check) / "forced" / f"signals_{v}.csv.gz", dtype={"sha": str})
    return s[s.part == "bench"].drop_duplicates("sha").set_index("sha").loc[idx]


def delib_value(check: bool = False, log=print) -> int:
    o = D.odir(check)
    rt = pd.read_csv(o / "forced" / "routes.csv.gz", dtype={"sha": str}).set_index("sha")
    cat = categories(check).loc[rt.index]
    cap = f"{TH.MAIN_CAP:g}"
    out = {"rule": "DESIGN.md 43", "cap": cap, "texts": cat.value_counts().to_dict(), "routes": {}, "detection": {}}
    for v in VARIANTS:
        if f"{v}@{cap}" in rt:
            out["routes"][v] = pd.crosstab(cat, rt[f"{v}@{cap}"]).to_dict(orient="index")
    # what PEINN's dilemma condition changes: the same gate without the Deliberation tier
    th = C.jload(o / "thresholds.json")["variants"][TH.MAIN_VARIANT][cap]["th"]
    s = _signals(check, TH.MAIN_VARIANT, rt.index)
    T, I, F, E = (s[k].to_numpy(dtype=float) for k in "TIFE")
    act = C.gate(T, I, F, E, th, **TH.options(TH.MAIN_VARIANT))
    if not (act == rt[f"{TH.MAIN_VARIANT}@{cap}"].to_numpy()).all():
        raise SystemExit("delib-value: the gate does not reproduce the exported routes")
    cf = C.gate(T, I, F, E, th, **dict(TH.options(TH.MAIN_VARIANT), deliberation=False))
    ch = pd.DataFrame({"cat": cat, "route": act, "without_I": cf}, index=rt.index)
    ch = ch[ch.route != ch.without_I]
    out["changed_by_I"] = ch.groupby(["cat", "route", "without_I"]).size().rename("n").reset_index().to_dict(orient="records")
    # threshold-free detection of the Ethics dilemmas
    y = (cat == "dilemma").to_numpy().astype(int)
    moral = cat.isin(["dilemma", "morables", "ggb", "MFQ", "WVS"]).to_numpy()
    sig = {}
    for v in VARIANTS:
        if v == "A1ft" or not (o / "forced" / f"signals_{v}.csv.gz").exists():
            continue
        sv = _signals(check, v, rt.index)
        sig[v] = (1 - 2 * (sv.F - 0.5).abs() if TH.kind(v) == "A3" else sv.I).to_numpy(dtype=float)
        out["detection"][v] = {"auroc": round(auc(y, sig[v]), 4), "ap": round(ap(y, sig[v]), 4),
                               "auroc_moral": round(auc(y[moral], sig[v][moral]), 4),
                               "ap_moral": round(ap(y[moral], sig[v][moral]), 4)}
    rng = np.random.default_rng(0)
    pos, neg = np.where(y == 1)[0], np.where(y == 0)[0]
    out["detection_diff"] = {}
    for a, b in (("A0ft", "A2ft"), ("A0", "A2")):
        if a in sig and b in sig:
            dap, dau = [], []
            for _ in range(2000):
                i = np.r_[rng.choice(pos, len(pos)), rng.choice(neg, len(neg))]
                dap.append(ap(y[i], sig[a][i]) - ap(y[i], sig[b][i]))
                dau.append(auc(y[i], sig[a][i]) - auc(y[i], sig[b][i]))
            out["detection_diff"][f"{a}-{b}"] = {
                "ap": round(ap(y, sig[a]) - ap(y, sig[b]), 4), "ap_ci95": [round(float(x), 4) for x in np.percentile(dap, [2.5, 97.5])],
                "auroc": round(auc(y, sig[a]) - auc(y, sig[b]), 4),
                "auroc_ci95": [round(float(x), 4) for x in np.percentile(dau, [2.5, 97.5])]}
    # the Deliberation posture against the bare answer on the Ethics dilemmas (RQI on 0-100)
    sel = set(ch[(ch.cat == "dilemma") & (ch.route == "Deliberation")].index)
    eff = []
    for b in P.ORDER:
        d = BS.ethics_rows(P.forced(check, "ethics", b).assign(system="PEINN"))
        dl = d[d.instrument == "Dilemma"].assign(rq=lambda x: (x.rqi_fixed - 1) / 4 * 100)
        for grp, m in (("all", dl.sha.notna()), ("deliberated_by_PEINN", dl.sha.isin(sel)), ("rest", ~dl.sha.isin(sel))):
            p = dl[m].pivot_table(index=["item_id", "rep"], columns="tier", values="rq")
            dd = (p["Deliberation"] - p["Direct-Answer"]).dropna()
            eff.append({"base": b, "group": grp, "texts": int(dl[m].sha.nunique()), "pairs": int(len(dd)),
                        "direct": round(float(p["Direct-Answer"].mean()), 4), "deliberation": round(float(p["Deliberation"].mean()), 4),
                        "diff": round(float(dd.mean()), 4), "share_higher": round(float((dd > 0).mean()), 4),
                        "share_lower": round(float((dd < 0).mean()), 4)})
    out["rqi_effect"] = eff
    od = o / "analysis"
    od.mkdir(parents=True, exist_ok=True)
    C.jdump(out, od / "delib_value.json")
    md = ["# I 라우팅의 선별과 숙고 효과 (DESIGN.md 43)", "",
          f"주 운영점 {cap}. 딜레마 = Ethics 딜레마 {int(y.sum())}문장, 나머지 벤치 문장 {int(len(y) - y.sum())}개.", "",
          "## PEINN의 딜레마 조건이 바꾸는 경로", "", "| 범주 | PEINN | 딜레마 조건 없을 때 | 문장 |", "|---|---|---|---|"]
    md += [f"| {r['cat']} | {r['route']} | {r['without_I']} | {r['n']} |" for r in out["changed_by_I"]]
    md += ["", "## 딜레마 검출(문턱 없음)", "", "| 변형 | AUROC | AP | 도덕 문항 안 AUROC | 도덕 문항 안 AP |", "|---|---|---|---|---|"]
    md += [f"| {v} | {r['auroc']:.3f} | {r['ap']:.3f} | {r['auroc_moral']:.3f} | {r['ap_moral']:.3f} |" for v, r in out["detection"].items()]
    md += [""] + [f"- {k}: AP 차이 {r['ap']:+.3f} (95% {r['ap_ci95']}), AUROC 차이 {r['auroc']:+.3f} (95% {r['auroc_ci95']}), 문장 부트스트랩 2,000회"
                  for k, r in out["detection_diff"].items()]
    md += ["", "## 딜레마 RQI: Deliberation 자세 대 Direct (0–100)", "",
           "| 기반 모델 | 묶음 | 문장 | 쌍 | Direct | Deliberation | 차이 | 높아진 쌍 | 낮아진 쌍 |", "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r['base']} | {r['group']} | {r['texts']} | {r['pairs']} | {C.fx(r['direct'], 1)} | {C.fx(r['deliberation'], 1)} | "
           f"{r['diff']:+.1f} | {r['share_higher']:.0%} | {r['share_lower']:.0%} |" for r in eff]
    (od / "delib_value.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    log("\n".join(md))
    return 0
