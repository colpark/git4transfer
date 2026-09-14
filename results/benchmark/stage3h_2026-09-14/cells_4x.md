# Four authorized, unscored diagnostic cells

All four use the same frozen W1 task stem and contract instantiated for median-depth assay `ARGR_ECOLI_Tsuboyama_2023_1AOY` (100 supplied variants; 79 usable homologs in the label-free precheck). Both models use 32K context, Q4_K_M, seed 1, temperature 0.2, and **4,096 tokens per response**. The only presentation change is unguided versus guided MCP surface. Agent/MCP ran on node 10; model inference ran on node 11. No labels were opened, no scorer or evaluator ran, and no other pilot cells or Stage 4 arms were run. Attempts and usable returned values are distinct below.

| Diagnostic | Wall s | Prompt / generated tokens | Calls by server, attempted/usable | FM attempted/usable | Submission | Explicitly named candidates /100 | Distinct validation categories per selected pick | Pick with variant-specific cited evidence |
|---|---:|---:|---|---:|---|---:|---|---|
| 7B unguided | 83.47 | 9,733 / 3,297 | none | 0/0 | absent | 0 | no picks | no picks |
| 7B guided | 53.63 | 131,440 / 1,896 | classical 9/0; record 1/1 | 0/0 | accepted by record, **contract invalid** | 10 | 0, 0 | 0/2 |
| 30B unguided | 99.19 | 23,141 / 5,122 | classical 2/2; predictive 1/0; analysis 1/0 | 1/0 | absent; validity interrupted | 0 | no picks | no picks |
| 30B guided | 89.43 | 44,494 / 4,071 | classical 5/1; predictive 1/0; physics 1/0 | 1/0 | absent; validity interrupted | 1 | no picks | no picks |

“Explicitly named candidates” is a **lower bound** from variant strings in tool arguments or submission fields. It is not a claim about private reasoning. No response hit the 4,096-token cap in any cell. The 7B unguided run exited normally without a call. Guided 7B passed strings such as `L27C` as the **entire `blast_search.sequence`** nine times; all nine calls failed. Its record submission contained only two selected picks instead of ten and cited a non-resolving `blast_search:call_id:…` string. The record server accepts a nonempty JSON object and does not enforce the scientific task contract; `contract_audit.json` records that separate defect. Its two picks had zero validation categories and no variant-specific evidence.

The 30B reached the learned ESM-2 tool in both modes, but both `esm2_likelihood` calls omitted a variant and returned the explicit error “supply mutant as one letter or variant such as G52L.” Unguided 30B used the real BLAST→MSA path and a valid conservation score; it also gave TM-align a sequence where a PDB path belongs. Guided 30B called `blast_msa` successfully, then tried PSSM/conservation with only the query row before using the MSA output; it later called the classical composite with no variant and then with the biological string `L27C` in the one-letter `mutant` field. The latter was schema-rejected. Neither model supplied the new `variant` field during the full-grant cells: **7B never called a variant-taking scorer; 30B omitted the variant or used the old malformed field.** This does not contradict the direct MCP positive controls, which prove the native form works when supplied. No FM tool returned a usable score in any cell.

| Diagnostic | Baseline / threshold tokens/s | Rolling 60-s active-generation result | Peak GPU / CPU °C | Peak GPU W / utilization | Minimum available system GiB |
|---|---:|---|---:|---:|---:|
| 7B unguided | 47.09 / 32.97 | PASS after saved-timing reconciliation; live poll missed final response | 66.0 / 80.0 | 76.84 / 95% | 89.52 |
| 7B guided | 47.79 / 33.46 | UNDEMONSTRATED: only 45.87 s active generation | 67.0 / 81.1 | 80.71 / 95% | 89.47 |
| 30B unguided | 88.96 / 62.27 | BREACH: 57.00 t/s; per-response and session gates fired | 73.0 / 81.7 | 91.78 / 95% | 74.86 |
| 30B guided | 85.40 / 59.78 | BREACH: 54.9 t/s across short responses; session gate alone fired | 74.0 / 83.9 | 91.53 / 95% | 74.87 |

Temperatures, power and utilization are reported values, never safety aborts. The two 30B cells terminated at the preregistered throughput-validity gate and are **UNDEMONSTRATED as task completions**, not failed predictions. The gate's cross-response branch caught exactly the decline the old per-response implementation missed. Full request/response, tool-call, receipt, submission and sensor traces remain in each `cell_*/` directory. The `validity_reconciliation.json` audit distinguishes observed live stops from post-run timing reconciliation; no inference was rerun. No metric, threshold, scoring code or arm definition was changed.
