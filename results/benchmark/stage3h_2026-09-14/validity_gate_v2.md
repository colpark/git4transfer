# Throughput validity gate v2 — frozen before Stage 3h cells

Named failure: sustained thermal/placement throttling makes pilot wall-clock timing unrepresentative. It is not a hardware safety gate. Firmware protects the hardware; temperature, power, memory, and GPU utilization are recorded but never abort this diagnostic.

Operating definition: for each current model serving configuration, issue the fixed integer-continuation prompt three times at temperature 0, 128 output tokens, and use the median llama.cpp `predicted_ms`-based generation tokens/second as baseline. Abort below 70% of that baseline for either (1) a single response with at least 60 seconds of active generation, or (2) any rolling 60 seconds of active generation accumulated across completed responses. Prompt prefill, tool execution, and idle gaps do not count. The active-generation rolling window is checked after each backend response, and the process is terminated at the first observed breach. If total active generation is below 60 seconds, session gate is UNDEMONSTRATED, not PASS.

Measurement limitation: llama.cpp's non-streaming endpoint exposes completion tokens and generation duration per response, not per-token timestamps. Within a response, the rolling calculation assumes constant rate; it can detect cross-response decline and reports the estimate honestly. It cannot identify a brief within-response dip earlier than that response's completion. Per-response checks remain alongside it.

Controls in `stage3h_validity.py` must pass before each cell: per-response synthetic 68.3 t/s against a 70 t/s threshold aborts, 71.7 passes, and a short response is unassessed; cross-response 100→30 t/s over two 35-second segments aborts, 100→100 passes, and one 35-second segment is unassessed. Each cell records its own baseline and controls in `baseline.json`.

| Cell | Baseline t/s | 70% threshold | Active generation | Reconciled gate |
|---|---:|---:|---:|---|
| 7B unguided | 47.09 | 32.97 | 78.68 s | PASS, 41.89 t/s single response |
| 7B guided | 47.79 | 33.46 | 45.87 s | UNDEMONSTRATED, under 60 s |
| 30B unguided | 88.96 | 62.27 | 87.67 s | BREACH, 57.00 t/s; both gates fire |
| 30B guided | 85.40 | 59.78 | 72.56 s | BREACH, 54.9 t/s cross-response only |

The live monitor missed the final completed 7B unguided response because the agent exited before its next two-second poll. `stage3h_finalize.py` reconstructed all four checks from saved llama.cpp timings without rerunning inference; `validity_reconciliation.json` preserves live versus reconciled status. No post-hoc-only breach was found. The two 30B runs were actually terminated by the live validity gate; they are interrupted/UNDEMONSTRATED as task results despite a measured throughput breach.
