# Stage 3i MCP grant verification — not attempted

The required authenticated model-selection preflight failed before the remount ladder. The frozen diagnostic prompt is `results/benchmark/stage3h_2026-09-14/diagnostic_prompt.txt` (SHA-256 `eae159a26f343af8ee1554d9864410385c143fb8780634648710b3483060ab74`). The selected assay remains `ARGR_ECOLI_Tsuboyama_2023_1AOY`; Stage 3h recorded 79 usable homologs. Neither prompt nor server surface was altered for Stage 3i.

| Server | Requested tools | Forwarded bytes | Functions | Model call with resolving receipt |
|---|---|---:|---:|---|
| record | submit_answer, log_note | Unknown | Unknown | Not attempted |
| classical | mmseqs_search, blast_search, blast_msa, pssm_score, conservation, motif_scan, blosum_score, hbond_geometry | Unknown | Unknown | Not attempted |
| analysis | seq_identity, tmalign | Unknown | Unknown | Not attempted |
| predictive | esm2_likelihood, esmfold | Unknown | Unknown | Not attempted |
| generative | esm_if | Unknown | Unknown | Not attempted |
| physics | dssp, openmm_snapshot_potential_delta | Unknown | Unknown | Not attempted |
| lit | pubmed | Unknown | Unknown | Not attempted |

Total serialized tool-block bytes, function count actually forwarded, prompt tokens and context headroom are **unknown**. Static tool names are not evidence of agent reachability. No native-tool exclusion was verified. The grant gate is **UNDEMONSTRATED**, not failed.
