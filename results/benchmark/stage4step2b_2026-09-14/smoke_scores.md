# SMOKE, NOT A COMPARISON: sealed-item P@10

These are three pipeline-validation items, not an estimate of arm performance. No aggregate, ordering, or delta is valid from this table. An em dash denotes a coverage failure, never a scored zero. All three items supplied 100 candidates, so their per-item chance P@10 is 0.100. The Floor C and B3/Floor M columns are frozen mechanical predictions, not reruns.

| Permanently sealed item | Chance | Floor C | B3 / Floor M | B1 prompt-only | B2 prompt-only | B4 MCP |
|---|---:|---:|---:|---:|---:|---:|
| AACC1_PSEAI_Dandage_2018 | 0.100 | 0.200 | 0.200 | — | 0.300 | 0.200 |
| ARGR_ECOLI_Tsuboyama_2023_1AOY | 0.100 | 0.200 | 0.200 | — | 0.000 | 0.200 |
| ENVZ_ECOLI_Ghose_2023 | 0.100 | 0.100 | 0.100 | — | — | 0.100 |

B2's AACC1 and ARGR entries are precision-only: ten valid unique picks existed, while strict whole-answer parsing failed and no complete candidate ranking existed. Its ARGR `0.000` is a genuine computed P@10, distinct from the em-dash coverage failures. B1 has no computable metric on these items. Spearman coverage and exact rejection reasons are in `pipeline_health.md`; no Spearman values or arm aggregates are reported here.

The evaluator's output `smoke_eval_rows.csv` is SHA-256 `930d481884d6e8e64b5cdf904635a3dd2633ea0809d27b7e5045913a82cf223c`. It was produced once after the five blind prediction files were hashed; `evaluation_integrity.json` records the six mechanical-floor cross-checks.
