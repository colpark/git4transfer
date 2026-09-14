# The single unscored pilot cell

14 September 2026 UTC. Exactly one cell was run: frozen item 2 (`AACC1_PSEAI_Dandage_2018`), Arm 3, guided presentation, sample 1. Node 10 hosted the Codex agent and MCP servers; node 11 served Qwen2.5-7B-Instruct Q4_K_M at 32K context. The existing frozen task prompt and arm grant were used. The only changed generation parameter was a **1,200-token cap per model response** (not an aggregate cap across the cell). No DMS labels, evaluator or score were opened.

| Observation | Result |
|---|---:|
| Outcome | **FAILED**: Codex exited 0 but no `submit_answer` artifact exists; final trace is an ordinary agent message. This is not a completed answer. |
| Wall clock | 80.45 s |
| Prompt tokens | 206,862 summed across 16 model requests; repeated context, not unique input tokens |
| Generated tokens | 2,954 summed across 16 requests; largest single response 519, under the 1,200 cap |
| MCP attempts / successful values | Classical 16 / 7 (blast 2/2, BLOSUM 5/8, guided screen 0/3, conservation 0/3). Record, analysis, predictive, generative, physics and lit were mounted but **not attempted**. |
| Failed tool calls | 9 rejected invalid arguments. In three `conservation` calls, for example, the model passed `G52L` as the full `query` sequence; this is a caller error, not a sequence-length limit of the protein. |
| Fabricated call-ID rate | **Not estimable**: no submitted answer or cited IDs. Seven successful tool receipts resolved; no claim-based fabrication test was possible. |
| `rejected` populated / evaluation depth | **Not estimable** without a submitted selection. Do not count either as zero. |
| Peak GPU / CPU temperature | 66.0 °C / 81.1 °C, reported only |
| Peak GPU power / utilization | 77.11 W / 95%, reported only |
| Minimum model generation throughput | 40.14 tokens/s vs 48.15 baseline and 33.70 threshold |
| Memory headroom | At least 88.65 GiB reported during the cell |

The 16 completed model responses each generated for at most 12.93 seconds; none by itself met the declared 60-second validity window. The synthetic throttle and healthy controls passed before the cell. Observed response throughput never approached the threshold, but the sustained-window gate was **not directly exercised by this cell**. The old 85 °C abort did not fire because it was withdrawn. The agent's final message blamed “sequence length constraints,” while the receipt errors show malformed query arguments; do not recast this as server failure or model inability to reach MCP. The raw Codex trace, shim requests/responses, receipt artifacts, sensor series and machine-readable summary are under `pilot_001/` and `pilot_cell.json`.

This cell measures cost and behaviour only. It does **not** justify a P@10, Spearman, empty-rejected rate, evaluation-depth value or Stage 4 headline.
