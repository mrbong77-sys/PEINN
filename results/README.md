# results/ — final canonical result sheets

Aggregated, per-arm result sheets for the definitive PEINN v2.1 evaluation: **six
benchmarks × seventeen arms** (thirteen main arms H01–H13 = four base models ×
{Vanilla, R2D2, NeMo, PEINN}; plus four Llama Guard arms H14–H17). These are the exact
numbers behind the paper's tables and figures.

To keep the package license-safe and free of harmful content, these sheets contain
**only scored, per-arm metrics** — no benchmark prompt text and no model responses.
The benchmarks themselves and the raw per-item run outputs are not redistributed (see
[`../docs/DATA_CARD.md`](../docs/DATA_CARD.md)); regenerate them with the reference
drivers in [`../docs/REPRODUCTION.md`](../docs/REPRODUCTION.md) §4.

## Read this first — pre-computed analysis

So you do not have to open the raw CSVs, a synthesised analysis is provided:

- **[`ANALYSIS.md`](ANALYSIS.md)** — a two-axis summary (do-no-harm vs
  moral-reasoning preservation), a per-defense summary of every metric, and a
  PEINN-vs-undefended preservation table, with a short narrative.
- **[`result_sheets_analysis.xlsx`](result_sheets_analysis.xlsx)** — the same three
  summary views as spreadsheet tabs, plus a verbatim copy of each raw sheet (one tab
  each) so the whole evaluation is browsable in one workbook.

Both are generated from the CSVs below by
[`../tools/analyze_result_sheets.py`](../tools/analyze_result_sheets.py).

## Full per-item sheets

The complete per-item records (every prompt, response, routing signal, judge verdict,
and score) are in **[`per_item/`](per_item/)** — one CSV per benchmark. Because this is a
safety evaluation, **harmful elements in those sheets have been intentionally removed**
(trace-preserving: redacted cells keep a length marker). Redaction keys on the *item*
being an attack, not on the judge's verdict: for the attack benchmarks (HarmBench,
Taxonomy) and XSTest's unsafe contrast items, every prompt/response/free-text cell is
redacted regardless of how the judge scored it, so a mis-scored harmful output cannot
leak. All scores/signals/verdicts stay intact; see
[`per_item/README.md`](per_item/README.md) for the exact policy. The aggregated per-arm
sheets below are derived from the same underlying data.

| File | Backs | Columns |
|---|---|---|
| `harmbench_asr.csv` | HarmBench figure | arm, base, defense, asr_mean, asr_sd, n_runs |
| `taxonomy_asr_by_arm.csv` | Taxonomy per-arm table | arm, base, defense, asr_mean, asr_sd, successes, sev_hsl |
| `taxonomy_asr_by_family.csv` | Taxonomy per-family table | family, {Vanilla,R2D2,NeMo,PEINN,LlamaGuard} |
| `xstest_orr_ucr.csv` | XSTest tables | arm, base, defense, orr, ucr |
| `ethics_mfa_wvs_rqi.csv` | Ethics tables | arm, base, defense, mfa, wvs, rqi, composite |
| `morables_accuracy.csv` | MORABLES table | arm, base, defense, clean_acc, perturbed_acc, gap |
| `ggb_ih_ib.csv` | GGB table | arm, base, defense, ih_mean, ih_std, ib_mean, ib_std, p_ih, p_ib |

Scoring conventions match the paper: a refusal or deflection is scored at the
instrument floor on the same basis for every arm — XSTest over-refusal counts
guard-block messages, and across the Ethics suite an unrated MFQ item scores 0 (max
error), an unrated WVS item counts as out-of-range, and a refused dilemma sits at the
RQI floor. MORABLES uses the deterministic gold-position shuffle; MFA/WVS/accuracy are
deterministic machine scores and RQI is the LLM-judge score.

Regenerate from a local PEAOS checkout:

```bash
python tools/make_result_sheets.py /path/to/PEAOS/pea_eval/output/v21  results
```
