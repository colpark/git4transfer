# Matched, unscored two-harness control on sealed ARGR

14 September 2026. One attempt per harness, unguided Arm 3, sample 1. Both model-side user messages were extracted from their saved session traces ([Codex received prompt](received_prompt_codex.txt), [Claude received prompt](received_prompt_claude.txt)) and independently matched **2,023 UTF-8 bytes, SHA-256 `eae159a26f343af8ee1554d9864410385c143fb8780634648710b3483060ab74`**, to the [provisionally chosen prompt](../../stage3h_2026-09-14/diagnostic_prompt.txt). This is an actual received-prompt check, not merely a launcher-code assertion. `ARGR_ECOLI_Tsuboyama_2023_1AOY` remains permanently sealed. No measured label, evaluator, or scorer was opened. The initial Claude launcher check found that its model-side grant preflight had created an empty record directory; it made **no model-cell attempt**. The one actual Claude cell then ran without retry or prompt change.

## Model-side grants

The Codex [preflight trace](codex_grant.jsonl) reported 18 `mcp__rescue_*` functions across record, classical, analysis, predictive, generative, physics and lit, plus the native names `apply_patch`, `clock__curr_time`, `list_mcp_resource_templates`, `list_mcp_resources`, `read_mcp_resource`, and `view_image`. No native shell, code execution, web fetch, package install, or executable filesystem path was exposed. None of the native names was invoked in the cell. The same launch command carried `gpt-5.6-sol`, high reasoning, read-only sandbox, and disabled shell/web/apps/subagents. The code-mode host remained up to route MCP tools, as in the panel-accepted 3i-c control.

The Claude [preflight trace](claude_grant.jsonl) and actual cell `system/init` both reported `model: claude-opus-5`, `memory_paths: null`, seven connected servers and exactly 18 `mcp__*` functions, with **no native function**. The 31-name disallow list, Max subscription login (`apiKeySource none`), isolated `/tmp/b4probe` working directory and disabled auto-memory/CLAUDE.md discovery were retained. No out-of-grant native invocation, subagent, or permission denial occurred.

## Cell table

| Measure | Codex / gpt-5.6-sol | Claude Code / claude-opus-5 |
|---|---:|---:|
| Attempt / completed / interrupted | 1 / 1 / 0 | 1 / 1 / 0 |
| Wall clock; CLI duration | 413.588 s; not separately reported | 920.133 s; 918,410 ms |
| Model turns / responses | one completed Codex turn; response count not separately frozen | 160 turns |
| Prompt/input tokens, total | 753,312 | 1,398,838 = 30 uncached + 172,566 cache creation + 1,226,242 cache read |
| Cache creation / cache read tokens | not reported / 685,696 | 172,566 / 1,226,242 |
| Generation tokens | 15,943 (including 7,437 reasoning) | 94,345 Opus (including 11,916 thinking); auxiliary Haiku 14 output |
| ESM-2 attempts / usable returns / unique variants usable | 302 / 302 / **100 of 100** | 100 / 100 / **100 of 100** |
| ESM-IF attempts / usable returns / unique variants usable | 304 / 304 / **100 of 100** | 20 / 20 / **19 of 100**, plus one WT |
| Variant argument form | ESM-2 302 `variant`; ESM-IF 301 `variant` | ESM-2 100 `variant`; ESM-IF 19 `variant` |
| `submit_answer` storage accepted | **yes**, one call | **yes**, one call |
| Answer contract compliant | **yes**: `pilot_item`, ten unique ranked `selected`, `rejected`, full 100-entry `ranking`, per-pick validation | **yes**: same required fields, ten unique ranks, 16 rejected, full 100-entry ranking |
| Candidates considered | 100/100 | 100/100 |
| Distinct named validation categories per pick | 5 for each of ten | 5 for rank 1; 4 for ranks 2–10 |
| Variant-specific usable receipts per selected pick | 3 for each of ten | 3 for each of ten |
| Native file/image/MCP-resource invocations | 0; arguments: none | 0; arguments: none |
| Subagents spawned / permission denials | 0 / none observed | 0 / `[]` |
| Cost | **unknown** on ChatGPT sign-in path; not $0 | CLI `total_cost_usd` **$4.699322 list-price estimate, not a charge** |
| Subscription usage | not surfaced per cell | `/usage` current session 47%→49%; weekly all-model 6%→7% at dashboard resolution |

Calls by server (attempted / usable; “usable” requires a returned value and a resolving real receipt):

| Server | Codex | Claude |
|---|---:|---:|
| record | 1 / 1 | 4 / 3 |
| classical | 311 / 311 | 31 / 31 |
| analysis | 0 / 0 | 1 / 1 |
| predictive | 302 / 302 | 101 / 101 |
| generative | 304 / 304 | 20 / 20 |
| physics | 1 / 0 | 2 / 0 |
| lit | 0 / 0 | 0 / 0 |
| **Total** | **919 / 918** | **159 / 156** |

The physical measurement is tool reachability and contract compliance, **not biological accuracy**. Both cells cite variant-specific usable receipts for every pick. Named validation categories are reported as submitted; a valid receipt does not by itself establish scientific relevance or independence. The two harnesses have different system contexts and auxiliary-model behavior, so these cells do not isolate model quality. Their wall times are especially non-causal: the MCP servers use a shared content-addressed cache and Codex ran first.

The reference PDB path was the **same** in every ESM-IF call from both cells, and both paths resolved. Claude's 19/100 unique ESM-IF coverage is therefore **not repaired** by supplying the path; it reflects which variants the model chose to evaluate on this attempt, not a failed ESM-IF receipt. It is also below its previous unpaired 29/100 run; those figures cannot be interpreted as a prompt effect because the prompts and operating histories differed. Claude recovered from tool-level errors sufficiently to submit: two DSSP attempts returned no usable structure assignment and an overlength `log_note` failed, followed by two successful notes and the accepted answer. Codex had one unusable DSSP attempt. No failed tool result is counted as usable evidence.

Claude's full `/usage` readouts are [before](claude_usage_before.jsonl) and [after](claude_usage_after.jsonl). Its rate-limit events reached five-hour utilization 0.49 and seven-day 0.06; the dashboard's 6%→7% weekly display has different rounding. `modelUsage` includes auxiliary `claude-haiku-4-5-20251001` (1,696 input, 14 output tokens, $0.001766 list estimate) alongside Opus. Overages were disabled at organization level.

Raw [Codex](codex_cell.jsonl) and [Claude](claude_cell.jsonl) cell streams, [Codex audit](codex_audit.json) and [Claude audit](claude_audit.json) preserve all invocations and receipt-level details. The accepted answers reside in the respective isolated record mounts under `results/benchmark/stage4prep_2026-09-14/step1_*_cell_record/`.

> "Claude Code ran on a Max subscription with apiKeySource none. total_cost_usd is a list-price accounting estimate, not a charge. Usage credits are disabled at the organization level, so a weekly cap means waiting rather than billing through."

> "Claude Code invokes an auxiliary model (Haiku 4.5) on every turn alongside the named subject model. The subject is not a single model."
