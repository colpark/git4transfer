# Stage 4-prep finding — 146 registered, cohort sweep not ready

14 September 2026. The 13 September freeze **FAILED as a current freeze and was SUPERSEDED**, not treated as an item-burning event. The replacement hash set covers 35 files/surfaces and verifies unchanged after the sealed smokes. Exactly 146 assays are scorable; pilot items 1 and 3–8 returned to the pool. `AACC1_PSEAI_Dandage_2018` and `ARGR_ECOLI_Tsuboyama_2023_1AOY` are permanently sealed harness-validation items. No cohort labels were opened and no accuracy was scored.

| Baseline | Preparation result | Remaining blocker |
|---|---|---|
| **B1a/B1b** frontier, prompt-only | Frozen prompts and deterministic parser exist. No item smoke sent. | The zero-MCP Codex preflight still exposed native `apply_patch` to the model, though execution failed closed. Strict **no tools of any kind** is unverified. |
| **B2a/B2b** Qwen3-30B-A3B, prompt-only | Two one-turn, tool-free smokes completed on sealed ARGR. Both made ten raw nominations. | The frozen parser correctly rejected both: incomplete 100-candidate accounting, plus wrong top-level shape in B2b. **Zero accepted submissions**, not zero accuracy. |
| **B3** no-LLM mechanical FM / Floor M | Existing blinded, published **148-item** Spearman 0.4906 and P@10 0.2182 stand. | A matched 146-item aggregate has not been computed and is not implied by the 148-item value. |
| **B4** frontier, full MCP | One prior sealed ARGR cell passed: 100 usable ESM-2, 100 usable ESM-IF and a compliant submission. | Cohort-scale ChatGPT-plan quota is not exposed. 146 cells project to 34.83 serial hours / 210.64M summed context tokens; the authenticated account does not establish that this fits the remaining window. |

Classical no-LLM Floor C also remains published on 148 items (Spearman 0.3449; P@10 0.1757), not silently converted to 146. The replacement preregistration keeps P@10 and per-item chance/lift primary, Spearman secondary, and invalid answers as coverage failures rather than scored zeros.

The additional **one** Qwen full-MCP sealed control was uncapped at the old 4,096-token limit, but the pre-registered throughput gate interrupted it after 266.865 seconds and 12,491 generated tokens. Of eight tool calls, three classical results were usable; one ESM-2 call lacked a variant and yielded **no usable FM score**. The model corrected a malformed BLOSUM call, but did not repair the ESM-2 call or submit an answer. It never hit the frontier cell's `max_hits=200` error. This is **UNDEMONSTRATED**, not a Qwen zero-score result or a clean ability-versus-operating-point verdict. Temperature and power were reported, not safety-abort triggers.

Carry this disclosure verbatim wherever B1 or B2 appears:

> "No foundation model was reachable in this condition. The instruction not to use foundation models could not be enforced and was not verified. It is reported as an instruction-compliance variable, not a capability control."

The two sealed prompt-only runs did not show unprompted PDB/assay identifiers, but the four-cell smoke grid is only **2/4 completed** because B1's strict grant failed preflight. The API-key alternative is priceable at approximately **$179.49–$873.11** for 146 B4-like cells depending on cache behavior, before other fees, but an API key/account tier was not verified and it is not proven cheaper than the included plan. The actual plan quota and paid-route decision remain unknown.

**Ready:** superseding freeze, 146-item list, parser and must-fail controls, B2 tool-free transport, historical B3/Floor C records, and one B4 sealed harness control. **Not ready:** B1 strict tool-free grant, B2 contract-compliant output, matched 146-item floor aggregates, a clean uncapped Qwen full-MCP control, and a funded/reachable B4 cohort budget. **Stage 4 remains closed; the panel must rule before any cohort-wide baseline run.**
