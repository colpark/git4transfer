# Stage 3 W1 finding — floors before arms

**Status:** the W1 floor gate and recitation diagnostic are on disk; no agent arm or Stage 4 run has started. The user's 13 September instruction opened W1 Stage 3. The PyRosetta-to-OpenMM substitution remains unresolved for W2 and is not used here.

## Scarce-unit denominator and blinding

Stage 1 supplied 174 independent 50%-identity assay clusters. The predeclared 50–1,000-aa/real-MSA/candidate rules yielded **148 eligible clusters** (one assay each) and **14,668 label-blind single-substitution candidates**; 25 clusters had no length-and-MSA-eligible assay and one had fewer than 20 valid variants. Each item had 31–100 candidates and asks for the ten highest-fitness mutations, using [ProteinGym's stated score direction](https://github.com/OATML-Markslab/ProteinGym/blob/main/README.md). The 148—not 14,668—is the independent n. Three PG_v1.3 archives passed ZIP checks and have SHA-256s in `input_hashes.json`. The released A2Ms supplied 21,221,125 valid rows; 124,822 rows with ambiguous/noncanonical residues or unequal alignment length were excluded and counted. This canonical-residue parsing correction was logged in `preregistration.md` before any floor or measured outcome was read. `cohort_controls.json` includes deliberately duplicated-candidate and missing-cluster controls, both rejected.

## Frozen floor results

| Floor, 148 independent items each | Macro Spearman, 95% cluster bootstrap | Precision@10, 95% cluster bootstrap |
|---|---:|---:|
| C: released-MSA PSSM + BLOSUM62 | **0.3449** [0.3213, 0.3667] | **0.1757** [0.1547, 0.1973] |
| M: fixed rank ensemble of C + released ESM2-650M + ESM-IF1 | **0.4906** [0.4636, 0.5165] | **0.2182** [0.1939, 0.2432] |
| Paired M − C | **+0.1457** [+0.1258, +0.1653] | **+0.0426** [+0.0250, +0.0601] |

All 148 items have both published model score fields, so no Floor M missing-data fallback was invoked. M beat C on Spearman in 133 of 148 items; precision@10 improved in 67, worsened in 27, and tied in 54. Both floors used scripted formulas and made **zero subject-LLM calls or new FM inference calls**. Floor M *does use upstream published FM predictions*; “zero calls this stage” does not mean model-free. It is a W1-specific deterministic analogue, not BioDesignBench's exact published mechanical pipeline or score. The source score CSVs also bundle `DMS_score`, but the blind predictor allowlisted only mutant and the two model columns; the measured-label evaluator ran only after `floor_predictions_blind.csv` was written. The hand-computed PSSM value matched the certified classical MCP tool with a resolving receipt. Bulk floor calculations use that fixed formula in a script, **not** one MCP call per variant; this implementation boundary is disclosed for panel review.

Controls in `floor_controls.json` show that permuting raw labels preserves a selected assay's candidate scores, altering a bundled label leaves the model-field allowlist result unchanged, inverting measured labels reverses Spearman, and missing MSA or ESM2 inputs fail instead of silently producing scores. These are checks of specific failure paths, not proof against every possible leakage channel. The full per-item floor scores, coverage, and 2,000-replicate intervals are saved separately; these metrics are on a deterministic 31–100-candidate subset per assay and must **not** be compared directly with ProteinGym's full-assay published Spearman numbers.

## Contamination and recitation

The source-free prompt audit found **0/148** shared contiguous eight-word fragments with withheld title/assay metadata and **0/148** exact source identifiers; injected eight-word and identifier leaks were detected, and a clean control stayed clean. **All 148 assay publications predate 2025.** No model pretraining corpus was available for a direct overlap test, so that exposure remains unknown, not cleared.

The fixed recitation probe completed **20 attempted / 20 completed** deterministic cluster items with the same source-free prompt skeleton, no tools, and the Stage 2b Qwen2.5 7B Q4 subject on node 11. It named the correct exact DMS, UniProt, or PDB source identifier unprompted in **0/20** outputs. This is a narrow memory diagnostic, **not** Arm 1 scoring and not evidence that the model has not seen these public proteins. Source-absence, exact-match positive, and wrong-ID controls passed. No run was interrupted. The model-host watchdog sampled 226 times; peaks were **7% GPU utilization**, **56°C GPU**, and **84.4°C CPU**, leaving only **0.6°C** below the CPU stop line. The temporary llama.cpp server and SSH tunnel were stopped after the probe; the pre-existing `devstral` service was untouched. This long-output recitation workload ran hotter than Stage 2b's shorter tool probes, so its narrow thermal margin is not a license to increase load in Stage 4.

**Exit:** stop at Stage 3 for panel review. The W1 floors are preregistered and published before any arms. W2's OpenMM deviation remains a separate unresolved ruling; Stage 4 is not opened by this finding.
