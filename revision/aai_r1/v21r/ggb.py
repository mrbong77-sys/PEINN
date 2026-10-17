"""GGB answers for re-scoring (Eugene 2026-10-17 14:40 KST: "GGB는 다시 채점해"). PEAOS scores a GGB answer with the
first 'score: N' or, failing that, the first standalone digit 1-7 (ggb_eval._extract_likert); answers that name no digit
get no score, and a digit from the instruction echoed back ('a scale from 1 to 7') is taken as the answer. This step
writes every GGB answer of the reported systems (Vanilla, R2D2, NeMo, Llama Guard, the main PEINN variant as assembled
by the routes, and A8 when present) with the pipeline's score, so the answers can be scored again from the text.
GGB statements are moral-philosophy items, no harmful content. -> results/ggb/ggb_answers.csv (DESIGN.md 32)
"""
from __future__ import annotations

import pandas as pd

from . import analyze as A
from . import common as C
from . import data as D
from . import matrix as MX
from . import theta as TH

COLS = ["base", "system", "arm_id", "tier", "item_id", "subscale", "rep", "score", "prompt_p2", "response_p1", "response_p2"]


def answers(check: bool, base: str, routes: pd.DataFrame) -> pd.DataFrame:
    df = MX.collect(check, base)
    if not len(df) or "ggb" not in set(df.bench):
        return pd.DataFrame(columns=COLS)
    parts = []
    for name in ("Vanilla", "R2D2", "NeMo", "LlamaGuard"):
        arm = C.ARMS[base].get(name)
        if arm:
            d = A.defence_rows(df, "ggb", arm)
            parts.append(d.assign(system=name, tier=""))
    main = f"{TH.MAIN_VARIANT}@{TH.MAIN_CAP:g}"
    pick, _ = A.assemble(df, "ggb", dict(zip(routes.sha, routes[main])))
    parts.append(pick.assign(system="PEINN"))
    if base == "qwen":
        from . import a8 as A8
        da = A8.collect(check)
        if len(da):
            parts.append(A.units(da[da.arm_id == A8.ARM], "ggb").assign(system="A8", tier=""))
    x = pd.concat(parts, ignore_index=True)
    x["base"] = base
    for c in COLS:
        if c not in x:
            x[c] = ""
    return x[COLS]


def ggb_export(check: bool = False, log=print) -> int:
    routes = TH.load_routes(check)
    out = pd.concat([answers(check, b, routes) for b in MX.bases(check)], ignore_index=True)
    f = D.odir(check) / "ggb" / "ggb_answers.csv"
    f.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(f, index=False, encoding="utf-8")
    for (b, s), g in out.groupby(["base", "system"]):
        log(f"  GGB {b} {s}: {len(g)} answers, {int(pd.to_numeric(g.score, errors='coerce').notna().sum())} scored")
    if check:
        return 0
    return 0 if C.publish([f], "v21r GGB: every answer of the reported systems with the pipeline's score (re-scoring)") else 1
