"""Gate diagnosis (DESIGN.md 11): why the isolated A0 gate Hard-blocks XSTest safe texts. CPU only, no model calls.

    python -m v21r gate-diag [--check]

The route table (results/routes_summary.json) shows the A0 main operating point Hard-blocking 133 of 191 XSTest routing
texts (108 safe, 83 unsafe), so at least 50 safe texts get the fixed refusal. This step separates the candidate causes
before anything is retrained. XSTest is only the symptom: nothing here fits a threshold, a label or a model to it.

  1. symptom    XSTest texts by human label: which Hard-block condition fires (extreme energy, or harm energy with F),
                and how well E (isolated), F (A0), E and F (shipped) rank unsafe above safe (AUROC)
  2. labels     per corpus source: rows, F labelled (mask_F), energy label F >= .5, the source's polar label, and where
                the two disagree (the calibrator learns F >= .5; an unlabelled F is the placeholder 0, i.e. "safe")
  3. energy     per source on val + test: E quantiles and the Hard-block share at the A0 main thresholds
  4. neighbours the 5 nearest training rows (mpnet cosine, the calibrator's text block) of each XSTest text, by source
                and energy label, for blocked safe, passed safe and unsafe texts

Counts and statistics only (no text) -> results/diag/gate_diag.json and gate_diag.md.
"""
from __future__ import annotations

import collections
import traceback

import numpy as np
import pandas as pd

from . import common as C
from . import data as D
from . import matrix as MX
from . import models as M

MAIN = "0.1"
CAPS = ("0.005", "0.05", "0.1", "0.3")
K = 5


def auroc(y, s) -> float | None:
    """P(score of a positive > score of a negative), ties half (rank form)."""
    y, s = np.asarray(y, dtype=bool), np.asarray(s, dtype=float)
    n1, n0 = int(y.sum()), int((~y).sum())
    if not n1 or not n0:
        return None
    r = pd.Series(s).rank().to_numpy()
    return round(float((r[y].sum() - n1 * (n1 + 1) / 2) / (n1 * n0)), 4)


def hb_parts(E, F, th: dict) -> dict:
    """The two Hard-block conditions of the energy gate (common.gate), counted apart."""
    E, F = np.asarray(E, dtype=float), np.asarray(F, dtype=float)
    ext = E >= th["extreme"]
    hf = (E >= th["harm"]) & (F >= th["F"]) & ~ext
    return {"extreme": ext, "harm_and_F": hf, "any": ext | hf}


def q(x) -> dict:
    x = np.asarray(x, dtype=float)
    if not len(x):
        return {"n": 0}
    p = np.quantile(x, [0.1, 0.25, 0.5, 0.75, 0.9])
    return {"n": int(len(x)), "mean": round(float(x.mean()), 3), **{f"p{int(k * 100)}": round(float(v), 3)
                                                                       for k, v in zip((0.1, 0.25, 0.5, 0.75, 0.9), p)}}


def on(sig: dict, part: str, shas) -> dict:
    """T, I, F, E of one signals file for the given shas within one part (val, test or bench)."""
    ix = sig["part"] == part
    pos = {s: i for i, s in enumerate(sig["sha"][ix])}
    sel = np.array([pos[s] for s in shas], dtype=int)
    return {k: np.asarray(sig[k], dtype=float)[ix][sel] for k in ("T", "I", "F", "E") if k in sig}


def xstest_labels(check: bool) -> pd.DataFrame:
    """sha -> human label of the XSTest routing texts, from the judged CSVs of the first base that has them."""
    for b in MX.bases(check):
        df = MX.collect(check, b)
        if len(df) and "bench" in df and (df.bench == "xstest").any():
            x = df[(df.bench == "xstest") & df.get("neutro_posture", pd.Series(dtype=object)).notna()]
            x = x.assign(sha=D.posture_sha(x["neutro_posture"]))[["sha", "expected_label"]].dropna()
            x = x.drop_duplicates("sha")
            if len(x):
                return x.reset_index(drop=True)
    return pd.DataFrame(columns=["sha", "expected_label"])


def symptom(lab: pd.DataFrame, th: dict, a0: dict, shp: dict) -> dict:
    y = (lab.expected_label == "unsafe").to_numpy()
    out = {"texts": {"safe": int((~y).sum()), "unsafe": int(y.sum())},
           "auroc_unsafe_vs_safe": {"E_isolated": auroc(y, a0["E"]), "F_A0": auroc(y, a0["F"]),
                                    "E_shipped": auroc(y, shp["E"]), "F_shipped": auroc(y, shp["F"])},
           "E_isolated": {"safe": q(a0["E"][~y]), "unsafe": q(a0["E"][y])},
           "F_A0": {"safe": q(a0["F"][~y]), "unsafe": q(a0["F"][y])},
           "E_shipped": {"safe": q(shp["E"][~y]), "unsafe": q(shp["E"][y])},
           "hard_block": {}}
    for cap in CAPS:
        t = th[cap]["th"]
        p = hb_parts(a0["E"], a0["F"], t)
        out["hard_block"][cap] = {"th": {k: t[k] for k in ("extreme", "harm", "F")},
                                  **{lbl: {c: int(p[c][m].sum()) for c in p} for lbl, m in (("safe", ~y), ("unsafe", y))}}
    return out


def labels_by_source(sp: pd.DataFrame) -> dict:
    out = {}
    for s, g in sp.groupby("source", sort=True):
        lab = g["mask_F"].to_numpy(dtype=float) > 0.5
        ye = g["F"].to_numpy(dtype=float) >= 0.5
        pol = (g["polar"].astype(str) == "F").to_numpy()
        out[s] = {"rows": int(len(g)), "train": int((g.split == "train").sum()),
                  "F_labelled": int(lab.sum()), "energy_label_1": int(ye.sum()), "polar_F": int(pol.sum()),
                  "polar_F_label_0": int((pol & ~ye).sum()), "polar_T_label_1": int((~pol & ye).sum()),
                  "polar_F_F_unlabelled": int((pol & ~lab).sum())}
    return out


def energy_by_source(sp: pd.DataFrame, a0sig: dict, t: dict) -> dict:
    out = {}
    ev = sp[sp.split.isin(["val", "test"])]
    for s, g in ev.groupby("source", sort=True):
        parts = []
        for part in ("val", "test"):
            gg = g[g.split == part]
            if len(gg):
                parts.append((gg, on(a0sig, part, gg.sha)))
        if not parts:
            continue
        E = np.concatenate([p[1]["E"] for p in parts])
        F = np.concatenate([p[1]["F"] for p in parts])
        ye = np.concatenate([p[0]["F"].to_numpy(dtype=float) >= 0.5 for p in parts])
        hb = hb_parts(E, F, t)
        out[s] = {"rows": int(len(E)), "E_label0": q(E[~ye]), "E_label1": q(E[ye]),
                  "hard_block_label0": int(hb["any"][~ye].sum()), "hard_block_label1": int(hb["any"][ye].sum()),
                  "extreme_label0": int(hb["extreme"][~ye].sum())}
    return out


def neighbours(Fe: dict, sp: pd.DataFrame, lab: pd.DataFrame, groups: dict, k: int = K) -> dict:
    tr = sp[sp.split == "train"].reset_index(drop=True)
    A = Fe["cal_x"][D.rows_of(Fe, tr.sha)][:, 32:].astype("float32")
    A /= np.linalg.norm(A, axis=1, keepdims=True) + 1e-9
    src = tr.source.to_numpy()
    ye = tr["F"].to_numpy(dtype=float) >= 0.5
    out = {}
    for name, shas in groups.items():
        if not len(shas):
            out[name] = {"texts": 0}
            continue
        B = Fe["cal_x"][D.rows_of(Fe, shas)][:, 32:].astype("float32")
        B /= np.linalg.norm(B, axis=1, keepdims=True) + 1e-9
        S = B @ A.T
        top = np.argsort(-S, axis=1)[:, :k]
        cos = np.take_along_axis(S, top, axis=1)
        out[name] = {"texts": int(len(shas)), "neighbours": int(top.size),
                     "by_source": dict(collections.Counter(src[top.ravel()]).most_common()),
                     "energy_label_1_share": round(float(ye[top].mean()), 4),
                     "cos": q(cos.ravel())}
    return out


OVERREFUSAL = ("supp:orbench_80k", "supp:falsereject_train", "supp:phtest_harmless", "supp:coconot_contrast")
ADV_BENIGN = ("supp:wildjailbreak_adv_benign", "supp:wildguardmix_adv_benign")
DEV_VARIANTS = ("A0", "A0ft", "A0ftL")
BENIGN_GROUPS = ("v4_safe", "overrefusal_benign", "adversarial_benign")
HARMFUL_GROUPS = ("v4_harmful", "supp_harmful")


def parity(dev: dict, guard: dict) -> dict:
    """DESIGN.md 14: a variant is on par with Llama Guard when it refuses no more benign and no fewer harmful test rows
    than the guard's input verdicts, group by group."""
    out = {}
    for v, g in dev.items():
        ok = {k: (g[k]["refusal"] <= guard[k]["refusal"] if k in BENIGN_GROUPS else g[k]["refusal"] >= guard[k]["refusal"])
              for k in g if k in guard}
        out[v] = {"groups": ok, "all": bool(ok) and all(ok.values())}
    return out


def dev_groups(sp: pd.DataFrame) -> dict:
    """DESIGN.md 13: groups of the test split (never used for fitting) on which variants are compared; not XSTest."""
    te = sp[sp.split == "test"]
    y = te["F"].to_numpy(dtype=float) >= 0.5
    supp = te.source.astype(str).str.startswith("supp:").to_numpy()
    return {"v4_safe": te[~supp & ~y], "v4_harmful": te[~supp & y],
            "overrefusal_benign": te[te.source.isin(OVERREFUSAL).to_numpy() & ~y],
            "adversarial_benign": te[te.source.isin(ADV_BENIGN).to_numpy() & ~y], "supp_harmful": te[supp & y]}


def dev_by_variant(check: bool, sp: pd.DataFrame, th_all: dict, cap: str = MAIN) -> dict:
    """Refusal share (Hard-block or Reasoned-Refusal) per test group at each variant's operating point `cap`."""
    from . import theta as TH
    out = {}
    for v in DEV_VARIANTS:
        if v not in th_all or cap not in th_all[v]:
            continue
        sig = M.load_signals(check, v)
        t = th_all[v][cap]["th"]
        res = {}
        for g, d in dev_groups(sp).items():
            if not len(d):
                continue
            x = on(sig, "test", d.sha)
            T, I, F, E = TH.inputs(v, x)
            r = C.gate(T, I, F, E, t, **TH.options(v))
            res[g] = {"rows": int(len(d)), "refusal": round(float(np.isin(r, ("Hard-block", "Reasoned-Refusal")).mean()), 4),
                      "hard_block": round(float((r == "Hard-block").mean()), 4)}
        out[v] = res
    return out


def run(check: bool) -> dict:
    th = C.jload(D.odir(check) / "thresholds.json")["variants"]["A0"]
    t = th[MAIN]["th"]
    sp = D.load_split(check)
    a0sig, shsig = M.load_signals(check, "A0"), M.load_signals(check, "SHIPPED")
    lab = xstest_labels(check)
    have = set(a0sig["sha"][a0sig["part"] == "bench"])
    lab = lab[lab.sha.isin(have)].reset_index(drop=True)
    res = {"main_cap": MAIN, "main_th": t, "labels_by_source": labels_by_source(sp),
           "energy_by_source": energy_by_source(sp, a0sig, t),
           "dev": dev_by_variant(check, sp, C.jload(D.odir(check) / "thresholds.json")["variants"])}
    gf = D.odir(check) / "diag" / "dev_guard.json"
    if gf.exists():
        res["dev_guard"] = C.jload(gf)["groups"]
        res["dev_parity"] = parity(res["dev"], res["dev_guard"])
        # every operating point of the curve: where (if anywhere) each variant is on par with the guard
        tha = C.jload(D.odir(check) / "thresholds.json")["variants"]
        caps = sorted({c for v in DEV_VARIANTS if v in tha for c in tha[v]}, key=float)
        res["dev_curve"] = {c: dev_by_variant(check, sp, tha, c) for c in caps}
        res["dev_parity_points"] = [f"{v}@{c}" for c, d in res["dev_curve"].items()
                                    for v, x in parity(d, res["dev_guard"]).items() if x["all"]]
    if len(lab):
        a0, shp = on(a0sig, "bench", lab.sha), on(shsig, "bench", lab.sha)
        res["xstest"] = symptom(lab, th, a0, shp)
        y = (lab.expected_label == "unsafe").to_numpy()
        hb = hb_parts(a0["E"], a0["F"], t)["any"]
        Fe = D.load_features(check)
        res["neighbours"] = neighbours(Fe, sp, lab, {"safe_blocked": lab.sha[~y & hb].tolist(),
                                                     "safe_passed": lab.sha[~y & ~hb].tolist(),
                                                     "unsafe": lab.sha[y].tolist()})
    else:
        res["xstest"] = {"texts": 0, "note": "no judged XSTest rows with a routing sha yet"}
    return res


def render(r: dict) -> str:
    L = ["# 게이트 진단 (DESIGN.md 11)", "", f"주 운영점 {r['main_cap']} 문턱: {r['main_th']}", ""]
    x = r.get("xstest", {})
    if "hard_block" in x:
        L += ["## 1. XSTest 증상", "", f"- 문장 수: {x['texts']}", f"- AUROC(위험 > 안전): {x['auroc_unsafe_vs_safe']}", "",
              "| 운영점 | 안전: 극단 E | 안전: harm E∧F | 안전 계 | 위험 계 |", "|---|---|---|---|---|"]
        for cap, h in x["hard_block"].items():
            L.append(f"| {cap} | {h['safe']['extreme']} | {h['safe']['harm_and_F']} | {h['safe']['any']} | {h['unsafe']['any']} |")
        L += ["", f"- E(격리) 안전 {x['E_isolated']['safe']}", f"- E(격리) 위험 {x['E_isolated']['unsafe']}",
              f"- F(A0) 안전 {x['F_A0']['safe']}", ""]
    L += ["## 2. 출처별 라벨", "", "| 출처 | 행 | F 라벨 있음 | 에너지 라벨 1 | polar F | polar F인데 라벨 0 | polar T인데 라벨 1 |",
          "|---|---|---|---|---|---|---|"]
    for s, v in r["labels_by_source"].items():
        L.append(f"| {s} | {v['rows']} | {v['F_labelled']} | {v['energy_label_1']} | {v['polar_F']} | {v['polar_F_label_0']} | {v['polar_T_label_1']} |")
    L += ["", "## 3. 출처별 에너지와 차단 (val + test, 주 운영점)", "", "| 출처 | 행 | 라벨 0 차단 | 라벨 0 극단 E | 라벨 1 차단 | 라벨 0 E 중앙값 |",
          "|---|---|---|---|---|---|"]
    for s, v in r["energy_by_source"].items():
        L.append(f"| {s} | {v['rows']} | {v['hard_block_label0']} | {v['extreme_label0']} | {v['hard_block_label1']} | {v['E_label0'].get('p50')} |")
    if "neighbours" in r:
        L += ["", "## 4. XSTest 문장의 학습 이웃 (mpnet 코사인 상위 5)", ""]
        for g, v in r["neighbours"].items():
            L.append(f"- {g}: 문장 {v['texts']}, 이웃 에너지 라벨 1 비율 {v.get('energy_label_1_share')}, 출처 {v.get('by_source')}")
    if r.get("dev"):
        L += ["", "## 5. 변형 비교: test 분할 거절 비율 (주 운영점, 평가 벤치 아님, DESIGN.md 13)", "",
              "| 변형 | " + " | ".join(next(iter(r["dev"].values())).keys()) + " |",
              "|---|" + "---|" * len(next(iter(r["dev"].values())))]
        for v, g in r["dev"].items():
            L.append(f"| {v} | " + " | ".join(f"{x['refusal']:.3f} (n {x['rows']})" for x in g.values()) + " |")
        if r.get("dev_guard"):
            gg = r["dev_guard"]
            L.append("| Llama Guard 3 (입력) | " + " | ".join(f"{gg[k]['refusal']:.3f} (n {gg[k]['rows']})" if k in gg else ""
                                                       for k in next(iter(r["dev"].values()))) + " |")
            L += ["", "- Llama Guard 동등(무해는 거절이 같거나 적고, 유해는 같거나 많음): "
                  + ", ".join(f"{v} {'예' if x['all'] else '아니오'} {x['groups']}" for v, x in r["dev_parity"].items())]
            L += [f"- 곡선 전체에서 동등인 운영점: {', '.join(r.get('dev_parity_points') or []) or '없음'}", "",
                  "| 운영점 | 변형 | " + " | ".join(gg) + " |", "|---|---|" + "---|" * len(gg)]
            for c, d in (r.get("dev_curve") or {}).items():
                for v, g in d.items():
                    L.append(f"| {c} | {v} | " + " | ".join(f"{g[k]['refusal']:.3f}" if k in g else "" for k in gg) + " |")
    if "error" in r:
        L += ["", "## 오류", "", "```", r["error"], "```"]
    return "\n".join(L) + "\n"


def gate_diag(check: bool = False, log=print) -> int:
    """Never stops the pipeline: an error is written into the report and pushed, so the review hold that follows
    carries it."""
    try:
        res = run(check)
    except Exception:                                                     # noqa: BLE001
        res = {"error": traceback.format_exc()[-3000:], "labels_by_source": {}, "energy_by_source": {},
               "main_cap": MAIN, "main_th": {}}
        log(res["error"])
    o = D.odir(check) / "diag"
    f = C.jdump(res, o / "gate_diag.json")
    md = o / "gate_diag.md"
    md.write_text(render(res), encoding="utf-8")
    log(md.read_text(encoding="utf-8"))
    if check:
        return 0
    C.publish([f, md], "v21r D: gate diagnosis (why the isolated gate blocks XSTest safe texts; counts only)")
    return 0
