# Task 5/6: Claude Opus ARGR cell not run

The Task 4 model-side grant contained three native MCP-resource tools and an extra `pyrosetta_ddg` MCP function. The instruction explicitly says to **stop if any native name survives**. Therefore the frozen ARGR prompt was never sent to Claude Opus, no `cell_claude_opus.jsonl` or `.err` exists, and no cell was retried or scored.

| Requested cell measure | Result |
|---|---|
| Wall clock, `duration_ms`, `num_turns` | Not measured: cell not run |
| Prompt, generated, cache-creation and cache-read tokens | Not measured for cell |
| Calls attempted / usable by server | Not measured for cell |
| FM calls and usable variant-specific scores | Not measured for cell |
| Receipt `input_form` and candidates considered | Not measured for cell |
| `submit_answer` and ten-pick contract | Not measured for cell |
| Validation categories and variant-specific citations | Not measured for cell |
| Cell `subagent_stats.spawned`, permission denials, `modelUsage`, `total_cost_usd` | Not measured for cell |
| `/usage` before/after cell | Not read: no cell was authorized after the failed grant |

The **separate unscored `ok` grant preflight**, not this cell, reported `claude-opus-5`, auxiliary Haiku 4.5, zero spawned subagents, no permission denials, 43% five-hour and 5% seven-day utilization in its `rate_limit_event`, and CLI `total_cost_usd` 0.084799. Those figures must not be presented as ARGR-cell measurements. The already-accepted Codex B4 ARGR control remains the only completed B4 harness cell.
