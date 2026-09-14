# Equal diagnostic output caps — frozen before Stage 3h cells

2026-09-14 EST. Qwen 7B and Qwen3-30B-A3B both receive `max_tokens=4096` per model response through the same Responses shim. The prior 1,200-versus-8,192 comparison was descriptive only: the smaller cap could truncate planning and tool use. The new value is a harness parameter, not a task-prompt, metric, or arm change. A response whose backend `finish_reason=length` at 4,096 tokens is recorded as a cap hit. The four cells use the same diagnostic item, prompt text, temperature 0.2, seed 1, 32K context, and full Arm 3 MCP grant; mode alone changes guided versus unguided presentation.

No assay labels or scoring code are opened. The eight former pilot items remain discarded. Stage 4 remains closed.
