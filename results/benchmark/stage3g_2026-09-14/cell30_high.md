# Authorized one-cell 30B retry with a higher response cap

14 September 2026 UTC. This is **one** unscored rerun of frozen item 2, Arm 3 unguided, sample 1. The item prompt SHA-256 remained `6069ed83a2549ab80a836e3b564c5251b4d6b911bfd6fc5eead6e489e4491cda`, the model was the same pinned Qwen3-30B-A3B Q4 checkpoint, and the MCP grant and seed were unchanged. Only the shim's per-response output cap changed from **1,200 to 8,192 tokens**. No labels or scoring evaluator were opened.

| Observation | Result |
|---|---:|
| Wall clock | 142.58 s |
| Prompt / generated tokens, summed across responses | 30,524 / 8,146 |
| Response cap reached | No; the three responses used 2,373, 1,098 and 4,675 generated tokens |
| Tool calls attempted | 4: physics `dssp` 1; classical `blast_search`, `conservation`, `blosum_score` 1 each |
| Tool calls with non-null results | 2 classical; no FM or record call |
| Receipt IDs | 2 resolving successful-result receipts; no fabricated ID observed |
| Submission | None; agent was interrupted before completion |
| Peak GPU / CPU temperature | 73.0 / 81.3 °C, reported only |
| Peak GPU power / utilization | 92.29 W / 95% |
| Minimum system memory available | 74.886 GiB |

The higher cap removed the original immediate failure: the first response produced real `dssp` and `blast_search` calls rather than exhausting its budget in reasoning. `dssp` returned an error because the supplied PDB lacked a valid PDB `HEADER`; `conservation` rejected the one-sequence `msa`; `blosum_score` was called with G→G and returned its zero-effect result. These are tool/argument outcomes, not measured fitness results.

The third response generated at **58.98 tokens/s for 79.27 s**, below the preregistered validity threshold **63.17 tokens/s** (70% of this run's three-repeat unloaded baseline, 90.24 tokens/s). The harness terminated Codex (`exit_code -15`) after that response, before any answer or `submit_answer` call. The synthetic slow and healthy gate controls both passed. No temperature gate fired and no response hit 8,192 tokens. The full task is therefore **UNDEMONSTRATED under the validity rule**, not a completed zero-FM or zero-submission result. Four observable calls before interruption were classical/physics; no FM tool was selected in the observed portion. Do not infer a model-quality or accuracy result from this trace.

Raw Codex, model, receipt, baseline, sensor and placement artifacts are in `cell30_high/`. Stage 4 remains closed. No second higher-cap cell was run.
