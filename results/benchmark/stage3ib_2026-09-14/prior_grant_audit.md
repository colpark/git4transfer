# Prior-cell grant audit — model-side payloads and traces

The saved `shim_001_request.json` is what Codex sent to the local provider shim; `shim_001_forwarded.json` is what the Qwen server actually received. The original request contained native Codex tools (`exec_command`, `write_stdin`, `view_image`, MCP resource tools, user/plugin/goal tools, web search, a `multi_agent_v1` namespace, and five Codex-app namespaces) in addition to six or seven RESCUE server namespaces, depending on the run. The shim stripped the native entries. The **forwarded model-side tool arrays contained only atomic `mcp__rescue_*` functions**. The 11 full-item traces below contain **zero native tool-call items**. This is a stronger finding than reading config alone, but the Codex-side grant was not the strict MCP-only allowlist the specification required.

| Saved full-item run | Codex request entries | Forwarded MCP functions | Native calls in trace |
|---|---:|---:|---:|
| Stage 3f pilot_001, 7B guided | 24 | 17 | 0 |
| Stage 3g cell7 / cell30 / cell30_high | 25 each | 18 each | 0 each |
| Stage 3g 7B surface unguided / guided | 25 each | 19 / 21 | 0 each |
| Stage 3g 30B surface unguided | 25 | 19 | 0 |
| Stage 3h 7B unguided / guided | 25 each | 19 / 21 | 0 each |
| Stage 3h 30B unguided / guided | 25 each | 19 / 21 | 0 each |

The final unguided model-side list comprised record `log_note`, `submit_answer`; classical `blast_msa`, `blast_search`, `blosum_score`, `conservation`, `hbond_geometry`, `mmseqs_search`, `motif_scan`, `pssm_score`; analysis `seq_identity`, `tmalign`; predictive `esm2_likelihood`, `esmfold`; generative `esm_if`; physics `dssp`, `openmm_snapshot_potential_delta`, **`pyrosetta_ddg`**; and lit `pubmed_search`. Guided mode added `screen_variant_classical` and `screen_variant_fm`. Stage 3f's forwarded list lacked record and `blast_msa` and included the classical composite. The blocked PyRosetta tool being visible is another surface disclosure; it was not called in these full-item traces.

**Disposition of prior results.** The local Qwen models did not receive callable native tools in the captured forwarded requests, and none were called. Nevertheless the upstream Codex request had native capabilities and the MCP-only rule was enforced by a shim, not by the configured arm grant. The prior 7B/30B behavioral observations may be described as **shim-filtered MCP-only at the model boundary**, but must not be cited as proof that the Codex arm itself was natively tool-free. Stage 3f additionally lacked the record server, so its non-submission has that separate confound. The request instructions also described terminal/patch capabilities even when the shim withheld them, a possible behavioral prompt confound.

The deleted ChatGPT login cannot be inspected for its earlier state. For these captured runs, however, the shim saved the model request, the forwarded Qwen function array, and raw local-model responses; the recorded calls were served through the custom local path, not by ChatGPT. This does not establish what happened in any run lacking those matching artifacts. Unknowns remain unknown.
