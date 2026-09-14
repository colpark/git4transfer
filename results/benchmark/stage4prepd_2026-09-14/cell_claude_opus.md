# One sealed Claude Opus cell: strong tool reachability, noncompliant answer contract

14 September 2026. **One** unguided Arm 3/sample 1 attempt on permanently sealed `ARGR_ECOLI_Tsuboyama_2023_1AOY`; no retry, prompt edit, score, evaluator or label read. The exact **973-byte** prompt from the Stage 3 manifest was sent. The raw [Claude stream](cell_claude_opus.jsonl), empty [stderr](cell_claude_opus.err), [receipt/contract audit](cell_audit.json), and [audit code](audit_trace.py) are retained. The cell repeated the verified 18-MCP-function, seven-connected-server model-side catalog with `memory_paths: null`; no native tool appeared or was invoked.

| Cell measure | Claude Opus observation | Accepted Codex B4 reference, for context only |
|---|---:|---:|
| Wall / CLI duration | **751.68 s** / 750,002 ms | 858.744 s |
| Model turns | **160** | 34 responses |
| Noncached prompt/input tokens | **28** | 123,072 uncached input |
| Cache creation / cache read | **133,061 / 886,643** | 1,319,680 cached input; cache creation not separately reported |
| Summed input/context tokens | **1,019,732** | 1,442,752 |
| Generation/output tokens | **50,976** | 10,460 |
| ESM-2 variant-specific usable scores | **100/100 unique variants** (101 attempted/usable calls; S18N repeated) | 100/100 |
| ESM-IF usable scores | **29 unique variants + 1 WT control** (30/30 calls usable) | 100/100 variants |
| Ten-pick record submission | One storage-accepted call with ten unique ranks; **NOT contract-compliant** | One accepted, contract-compliant submission |
| `subagent_stats.spawned` / permission denials | **0 / []** | no subagent / no prohibited call reported |
| CLI `total_cost_usd` | **3.0499405**, list-price accounting estimate, not a subscription charge | dollar figure unavailable on signed-in Codex path |

This table is **descriptive, not a prompt-matched harness comparison**. The accepted Codex cell used a **2,023-byte** Stage 3h diagnostic prompt (`eae159a2…`), which appended a reference FASTA/PDB and an explicit `pilot_item` answer contract. The mandated Claude prompt is the **973-byte** Stage 3 manifest prompt (`d2c258f7…`) and contains neither the paths nor the record schema. The difference was identified before the cell and the instructed 973-byte prompt was not changed. It explains at least the missing reference FASTA and is a direct confound for submission-format comparisons.

| Server | Calls attempted | Usable returned values | Trace note |
|---|---:|---:|---|
| record | 3 | 3 | two `log_note`, one storage-accepted `submit_answer` |
| classical | 17 | 14 | 14 BLOSUM usable; `blast_msa` and two `blast_search` calls failed for absent reference FASTA |
| analysis | 3 | 3 | TM-align |
| predictive | 105 | 105 | 101 ESM-2, four ESMFold |
| generative | 30 | 30 | ESM-IF; 29 variants plus WT |
| physics | 1 | 0 | DSSP rejected the ESMFold PDB header/format |
| lit | 0 | 0 | mounted, not called |
| **Total** | **159** | **155** | four unavailable/errored results not counted as usable |

Receipt `input_form` was **`variant`** on all 101 ESM-2, 29 variant-taking ESM-IF and 14 BLOSUM calls. The WT ESM-IF control had no variant form. All ten selected variants belong to the 100 candidates and have ranks 1–10. Every pick cites **2–5 resolving usable receipts** and at least one explicitly variant-specific receipt; the top two cite five tool types, most others three, and rank 9 two. However, the required separate `validation` field is absent on **all ten**, so formal validation depth under the Codex contract is **zero**, not 2–5 independent checks. Tool categories cited as evidence are not silently reclassified as validation.

The record tool returned `accepted: true` for `item_id="hth69_QEELVKAFKALLK"`. It stored an answer under `ranked_selection` with ten entries, rather than the required `item_id="pilot_item"` and `selected`/`rejected`/`ranking` schema. It lacks the contract's per-pick `validation` field and a 100-entry predicted ranking. **Record acceptance is storage success, not contract compliance.** The model's final prose began “Submitted,” but that does not change the schema audit. No fabricated receipt was found among the ten picks; all cited IDs in the submitted list resolved to usable calls. The missing explicit contract in the 973-byte prompt limits attribution of this format failure to Claude itself.

The CLI reported `modelUsage` for **`claude-opus-5`** (50,976 output tokens, $3.0484715 list estimate) and auxiliary **`claude-haiku-4-5-20251001`** (1,399 input, 14 output tokens, $0.001469 list estimate). The CLI result recorded no permission denials or MCP server errors. Before/after full subscription readouts are [usage_before.json](usage_before.json) and [usage_after.json](usage_after.json): displayed current-session utilization **44% → 45%**, weekly all-model **6% → 6%** (integer-resolution dashboard). The cell's `rate_limit_event` moved from five-hour **0.43 → 0.45** and seven-day **0.05 → 0.06**; overage was rejected with `org_level_disabled`. These are the measured meter changes for this one cell, not a 146-item cost projection.
