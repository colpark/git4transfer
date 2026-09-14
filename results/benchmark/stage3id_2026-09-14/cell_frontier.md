# Stage 3i-d frontier control: one uncapped, unscored cell

14 September 2026. Item `ARGR_ECOLI_Tsuboyama_2023_1AOY` (the frozen Stage 3h median-coverage diagnostic item, 79 usable homologs); Arm 3, unguided, sample 1. The exact [frozen prompt](../stage3h_2026-09-14/diagnostic_prompt.txt) has SHA-256 `eae159a26f343af8ee1554d9864410385c143fb8780634648710b3483060ab74`. One item attempt was run, without a model-output cap, prompt edit, retry, label access, evaluator, or scorer.

## Standing-state preflight

- Session: `codex login status` returned “Logged in using ChatGPT”; the authenticated model catalog exposed exact id `gpt-5.6-sol` with a 272,000-token context window. The unchanged accepted command selected `model_reasoning_effort="high"`.
- Firewall: accepted read-only, no `--add-dir`; shell/unified execution, web, apps, and multi-agent/subagent features remained disabled in the unchanged Stage 3i-c launch command. The prior named-threat and shell must-fail controls were accepted by the panel and were not rerun.
- Code-mode routing host: up, as witnessed by the live model-side `ALL_TOOLS` introspection, while the excluded execution/network functions were absent.
- Grant: the same seven mounted servers and the same 18 MCP functions appeared in the live model-side catalog. Preflight thread `01a0a0ce-260d-7a43-bc24-ff8852cab03a`; [preflight trace](preflight_catalog/trace.jsonl). The catalog was 11,137 bytes versus Stage 3i-c's 10,825 because native `clock__curr_time` appeared; no MCP function was added or removed. This inert clock is disclosed, not treated as an extra computation route. No server ladder was rerun.

## Cell outcome

Thread `01a0a0cf-289b-7fa1-94c1-78610c07fbca`; [raw Codex trace](cell_frontier_run/trace.jsonl), [read-only analysis](cell_frontier_run/analysis.json), [accepted submission](cell_frontier_run/submissions/pilot_item.json). The turn completed. The model-session first-to-last elapsed time was **858.744 seconds (14 min 18.744 s)**. The launching wrapper then crashed in its post-run catalog summarizer on a string-valued output block; it did **not** affect the completed cell. The saved trace was reparsed without a model call. For that reason the CLI process exit code is unavailable, whereas `turn.completed` and the accepted record are directly observed.

| Measure | Observed |
|---|---:|
| Model responses | 34 |
| Prompt/input tokens, summed over responses | 1,442,752 (1,319,680 cached) |
| Generated/output tokens, summed over responses | 10,460 (including 4,028 reasoning tokens) |
| Maximum output in one response | 3,268 tokens |
| FM calls attempted / usable | 201 / 201 |
| ESM-2 variant-specific scores | 100 / 100 candidates |
| ESM-IF calls | 100 variant-specific, 1 wild-type baseline; all usable |
| Record submission | 1 attempt, accepted |
| Picks / rejected / full predicted ranking | 10 / 90 / 100 |
| Candidates considered | 100 of 100, based on tool arguments and submitted ranking |
| Native `apply_patch`, `view_image`, MCP-resource invocations | **0**; arguments: none |
| Dollar cost | Unknown: ChatGPT sign-in exposed no per-cell dollar charge or model price. Not $0. |

### Per-response token accounting

Input tokens are prompt/context tokens for each response, so their sum includes repeated context; output tokens are generated tokens including reasoning. Full response IDs and reasoning-token counts are in `analysis.json`.

| Response | Input | Output | Response | Input | Output |
|---:|---:|---:|---:|---:|---:|
| 1 | 10,350 | 175 | 18 | 40,413 | 132 |
| 2 | 12,623 | 79 | 19 | 42,007 | 354 |
| 3 | 12,901 | 341 | 20 | 46,961 | 218 |
| 4 | 13,757 | 159 | 21 | 51,673 | 605 |
| 5 | 15,021 | 612 | 22 | 62,559 | 1,135 |
| 6 | 15,661 | 40 | 23 | 65,188 | 918 |
| 7 | 15,729 | 31 | 24 | 66,134 | 31 |
| 8 | 15,788 | 127 | 25 | 66,193 | 31 |
| 9 | 15,943 | 31 | 26 | 66,252 | 106 |
| 10 | 16,002 | 43 | 27 | 66,386 | 31 |
| 11 | 16,073 | 94 | 28 | 66,445 | 31 |
| 12 | 16,195 | 31 | 29 | 66,504 | 108 |
| 13 | 30,220 | 96 | 30 | 66,640 | 31 |
| 14 | 34,742 | 492 | 31 | 66,706 | 389 |
| 15 | 35,262 | 31 | 32 | 81,065 | 86 |
| 16 | 35,321 | 112 | 33 | 83,336 | 3,268 |
| 17 | 39,809 | 204 | 34 | 86,893 | 288 |

### Tool calls and argument forms

“Usable” means a non-null result, no body error, a resolving artifact, and a matching real `call_id`; mere receipt presence was insufficient.

| Server | Attempted | Usable | Explanation |
|---|---:|---:|---|
| record | 1 | 1 | `submit_answer` accepted |
| classical | 104 | 103 | First `blast_msa(max_hits=200)` failed its valid-range check; the subsequent `max_hits=50` call worked. BLAST and MMseqs each worked; 100 PSSM scores worked. |
| analysis | 0 | 0 | Mounted, not selected in this cell. |
| predictive | 100 | 100 | `esm2_likelihood` with `variant="..."` on all 100 candidates; `input_form="variant"` in every receipt. No ESMFold call. |
| generative | 101 | 101 | `esm_if` with `variant="..."` on 100 candidates plus one wild-type baseline. |
| physics | 1 | 0 | `dssp` failed on the supplied headerless AF2 PDB: mkdssp treated it as mmCIF and could not parse it. It was not cited as valid evidence. |
| lit | 0 | 0 | Mounted, not selected in this cell. |

The model supplied native biological `variant` strings for all 100 ESM-2, 100 ESM-IF variant, and 100 PSSM calls. The two failed calls are counted as failures, not zero-valued measurements. The ESM-2 results each carried numeric `delta_log_probability` and resolving receipts.

### Submission and evidence audit

The answer has unique ranks 1–10 and all required `mutant`, `basis`, `evidence`, `validation`, and `would_overturn` fields. All cited receipts resolved to successful calls in this run. It included 90 rejected candidates and a predicted ranking of all 100, with no claim of measured assay outcome.

| Rank | Pick | Distinct named validation categories | Variant-specific receipt channels |
|---:|---|---:|---:|
| 1 | R51K | 5 | 3 |
| 2 | S18E | 5 | 3 |
| 3 | G21S | 5 | 3 |
| 4 | D33E | 5 | 3 |
| 5 | E66D | 5 | 3 |
| 6 | R53K | 5 | 3 |
| 7 | A25Q | 5 | 3 |
| 8 | M59N | 5 | 3 |
| 9 | A10T | 5 | 3 |
| 10 | E3Q | 5 | 3 |

For every pick, the three variant-specific channels were ESM-2, PSSM, and ESM-IF. The other two category receipts were shared homolog retrieval and a wild-type backbone baseline. The answer reused the same five receipts in `evidence` and `validation`; **five named categories is not five independent holdout validations**. That limitation does not break this Arm 3 harness-control contract, but it must not be sold as forced-depth performance. No `apply_patch`, `view_image`, or MCP-resource tool was invoked; the native-tool argument log is empty.
