# results/per_item/ — full per-item result sheets (harm-redacted)

The complete per-item evaluation records for all six benchmarks × seventeen arms — every
prompt, response, routing signal (`ee_energy`, `neutro_T/I/F`, `neutro_route`), judge
verdict, and score — so a reviewer can audit the scoring item by item rather than only
through the aggregated sheets in the parent folder.

## ⚠️ Notice: harmful content intentionally removed

These sheets come from a **safety evaluation**, so the raw records contain harmful attack
prompts and, on successful attacks, harmful model outputs. **Harmful elements have been
intentionally removed.** Redaction is *trace-preserving*: a removed cell is not blanked
but replaced with a length-annotated marker, e.g.

```
[REDACTED: harmful content, 1160 chars]
```

so you can still see that substantive content existed and roughly how long it was. Every
scoring, routing-signal, verdict, and metadata column is kept intact.

**Redaction keys on the *item*, not on the judge.** An earlier version redacted only the
cells the LLM judge scored as harmful (e.g. `asr_binary=1`); wherever the judge
false-negatived a harmful completion, its raw text stayed exposed. The current policy
instead redacts **every** prompt/response/free-text cell of an *attack* item regardless of
the judge verdict, so a mis-scored harmful output cannot leak. What was removed, per
benchmark:

| Benchmark | Removed (length-annotated) | Kept in full |
|---|---|---|
| **HarmBench** | `behavior`, prompts (`prompt_p1/p2`), chain-of-thought, and responses (`response_p1/p2`) — **all rows** (every item is an attack) | `behavior_id`, categories, `asr_judgment`, `asr_binary`, latency, all routing signals |
| **Jailbreak Taxonomy** | all prompts (turn-1 and the second-pass **P2**), responses, chain-of-thought, and the judge free-text reasons — **all rows** (every item is a jailbreak attack) | family, sub-technique, verdicts (`judge_binary_verdict`, `judge_hsl`, `judge_mda`, `judge_trc_*`), latency, signals |
| **XSTest** | prompt, response, chain-of-thought, and judge text of the **unsafe contrast** items (`expected_label=unsafe`) — **all such rows** | all **safe** items in full, verdict, `over_refusal`, `unsafe_compliance`, signals |
| **Ethics** | — (no harmful content) | full sheet |
| **MORABLES** | — (no harmful content) | full sheet |
| **GGB** | — (no harmful content) | full sheet |

Short verdict/label fields (`HARMFUL`/`SAFE`, `UNSAFE`, `full_compliance`, etc.) and all
numeric scores/signals are never redacted — only free text that can carry harmful
material — so every table and figure in the paper remains fully reproducible from these
sheets. XSTest **safe** prompts are benign by construction and are kept verbatim. The
harmful benchmark prompts themselves are not redistributed (see
[`../../docs/DATA_CARD.md`](../../docs/DATA_CARD.md)).

## Files

`harmbench_per_item.csv` · `taxonomy_per_item.csv` · `xstest_per_item.csv` ·
`ethics_per_item.csv` · `morables_per_item.csv` · `ggb_per_item.csv`

Regenerate from a local PEAOS checkout, then apply the conservative item-keyed redaction:

```bash
python tools/export_per_item_sheets.py /path/to/PEAOS/pea_eval/output/v21  results/per_item
python tools/reredact_per_item.py        # redacts attack-item text regardless of judge verdict
```

The aggregated per-arm metrics and the summary analysis are one level up in
[`../`](../).
