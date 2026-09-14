# Stage 3g finding — rebuilt surface diagnoses reachability, not accuracy

14 September 2026 UTC. **Stage 4 remains closed.** No DMS labels, evaluator or scoring code were opened. This is one-item tool-use diagnosis, not a benchmark result.

**The published reference was read first.** BioDesignBench's 17-tool provider and the current 19-tool reference MCP server are not identical; both repositories currently declare **Apache-2.0, not MIT**. Guided behaviour in the provider comes from exposed composites **and** workflow/category guidance, while atomic descriptions are essentially mode-invariant. We adapted the observable principles—explicit evidence channels, cross-tool references, symmetric guided options and a retrieval→scoring composite—not a purported verbatim scheme. See `their_surface.md` and the exact 20 changed/one added description diff in `our_surface_diff.md`.

**Harness and MSA.** The Codex custom model catalog removed the fallback warning in fresh 7B and 30B echo probes; both made real calls with resolving receipts. The earlier Stage 3f no-submission cell had a separate deterministic defect: its record server did not mount, so `submit_answer` was absent. The rebuilt record channel is visible. `blast_msa` now provides a documented path from BLAST hits to query-anchored rows, and one-sequence conservation fails in a positive/negative MCP control. But on **item 2**, zero of 199 non-query homologs meet the preregistered ≥80% query-coverage rule. The new tool correctly fails there. No threshold or task sequence was altered, so PSSM/conservation remain unavailable for this item (`msa_path.md`).

| Rebuilt-surface diagnostic | 7B unguided | 7B guided | 30B unguided |
|---|---:|---:|---:|
| Wall clock | 57.30 s | 74.78 s | 367.25 s |
| Classical calls attempted / API values | 12 / 11 | 7 / 2 | 9 / 1 |
| FM calls attempted / usable values | 0 / 0 | 0 / 0 | **1 / 0** |
| Record submissions accepted | 0 | 0 | **1** (two repeats rejected) |
| Position-linked candidates successfully evaluated | 0 / 100 | 0 / 100 | 0 / 100 |
| Run status | normal finish without submission | 1,200-token response cap, incomplete | syntactic submission, scientifically unsupported |

The isolated 7B `esm2_likelihood` probe **passed** again; zero FM selection in the crowded 7B grant is not schema unreadability. The rebuilt guided list had both classical and FM composites, yet selected only the classical one and sent malformed full variant strings as one-letter arguments. Its cap prevents a completed mode-effect claim. 30B selected ESM-2 in its **first** full-item response, proving full-grant tool-channel reachability, but passed `mutant="G52L"`; ESM-2 rejected the call, so there was **no FM score**. Its accepted ten-pick answer cited one real BLAST receipt for all picks, with only one validation category per pick and no variant-specific evidence. Receipt validity is not evidence relevance. Fifteen candidate names appeared in selected/rejected fields, not 100 evaluated. The 30B/7B comparison is descriptive because their per-response caps were 8,192/1,200; neither result supports an accuracy claim.

**Thermal/timing caveat.** 30B peak GPU/CPU temperature was 77.0/86.4 °C, power 91.43 W, all reported only. Generation throughput declined across responses, but the existing validity gate checks each response separately and none reached its 60-second window. It did not establish representative long-run timing. We did not alter the gate.

**Panel recommendation:** attribute the original zero-FM/no-submit cell to a combination of a broken record mount, asymmetric guided affordance, incomplete MSA path and subject argument/selection behaviour—not a single model failure. The rebuilt surface demonstrates FM *selection* in 30B but not successful FM *use* on the full item. The Arm 3F four-verb W1 adaptation is **proposed only** in `our_surface_diff.md`; frozen prompts were not changed because this request also forbids prompt changes. Tool schemas/descriptions now materially differ from the frozen pilot, so the eight pilot items must be **discarded** from a future full-run comparison; use the remaining 140 only after panel re-registration. No further pilot work starts before that ruling.
