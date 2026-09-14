# Qwen3-30B-A3B full-MCP control, sealed ARGR, uncapped

14 September 2026. **One attempt only**, unguided, unscored, on permanently sealed `ARGR_ECOLI_Tsuboyama_2023_1AOY`. Agent and seven MCP servers ran on node 10; Qwen3-30B-A3B Q4_K_M served on node 11 at 32K context. The forwarded model request carried exactly the 18 mounted MCP functions and no native functions. The old 4,096-token per-response cap was not applied; `max_tokens=32768` was only the context-bound serving limit. No labels, scorer or evaluator were opened.

| Measure | Observation |
|---|---:|
| Outcome | **INTERRUPTED / UNDEMONSTRATED** by existing throughput-validity gate; process exit −15, not a model-declared completion |
| Cell wall clock | 266.865 s |
| Model responses | 3 |
| Prompt tokens by response | 7,807; 14,401; 19,722; total **41,930** |
| Generated tokens by response | 1,709; 866; 9,916; total **12,491** |
| Classical calls | 6 attempted, 3 usable: `blast_msa` twice and `blosum_score` once |
| Predictive/FM calls | `esm2_likelihood` **1 attempted, 0 usable**; `esmfold` 0 |
| Generative/FM calls | `esm_if` 0 attempted, 0 usable |
| Physics calls | `dssp` 1 attempted, 0 usable |
| Analysis / record / lit calls | 0 / 0 / 0 |
| Candidate variants considered, trace lower bound | **1 of 100**, `L27C` |
| `submit_answer` | absent; no accepted or rejected answer |
| Selected-pick depth / variant-specific citations | not applicable: no picks submitted |
| Invoiced model cost | no per-cell bill exposed; local serving cost not measured in dollars |

The single ESM-2 call omitted both `variant` and `mutant`. The server returned the actionable error `supply mutant as one letter or variant such as G52L`; it did **not** return a score. Input-form receipts show the one usable BLOSUM call supplied `variant="L27C"` plus `wt="L"` (`input_form=both`). One PSSM call also used both-form input but sent placeholder MSA rows and failed the equal-length/query-first check. The later PSSM retry used the actual `blast_msa` rows but omitted the mutant and failed. An initial malformed `blosum_score` call (`wt="Q', "`) was subsequently corrected to the usable L27C call. Thus the trace shows **partial recovery from a classical argument error**, not recovery of the FM error. The two `blast_msa` calls used `max_hits=50` and succeeded; this run did **not** exercise the frontier cell's `max_hits=200` error, so equivalent recovery from that error is unknown. The `dssp` call supplied an invalid structure format and returned no usable assignment.

The three usable classical calls had resolving receipts and existing artifact paths. MCP protocol completion is not being confused with scientific usability: three other classical calls, the ESM-2 call, and the physics call returned errors or failed schema validation. Neither a valid receipt nor the model's mention of ESM-2 is counted as a usable score.

Validity baseline was 89.368 generated tokens/s (three fixed-prompt repeats), with the frozen 70% stop threshold **62.557 tokens/s**; all six synthetic must-fail/healthy controls passed. Response throughputs fell 66.949 → 57.628 → **47.558** tokens/s. The third response lasted 208.505 active-generation seconds, so the per-response 60-second window and the session window both breached; the watchdog terminated the cell after that completed response. This is a **measurement-validity interruption**, not a safety-temperature abort or a 4,096-token cap. Reported peaks were GPU **76.0°C**, CPU zone **86.7°C**, GPU power **91.96 W**; minimum available system memory **74.816 GiB**. Temperature, power, utilization and memory were reported, never gates.

The raw [trace](qwen30b_full/trace.jsonl), [result](qwen30b_full/result.json), forwarded-request/shim records and sensors in `qwen30b_full/` support these counts. Compared with the accepted Stage 3i-d frontier control (100/100 usable ESM-2, 100/100 usable ESM-IF, contract-compliant submission), this Qwen attempt remained incomplete. Because the validity gate interrupted it, the control **does not cleanly settle ability versus operating point**; it demonstrates an ESM-2 argument-shape failure before interruption and cannot be cited as a zero-score outcome.
