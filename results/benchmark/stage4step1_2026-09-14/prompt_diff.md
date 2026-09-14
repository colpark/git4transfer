# Exact ARGR prompt audit

A: 973 UTF-8 bytes; SHA-256 `d2c258f7fc7629589dba7fb93a43a4cccbb59da3fb376a27ed6d30157465c34c`. B: 2023 bytes; SHA-256 `eae159a26f343af8ee1554d9864410385c143fb8780634648710b3483060ab74`. B starts with A byte-for-byte and appends 1050 bytes.

## A — Stage 3 hashed source manifest (full)

```text
You have a protein and candidate single substitutions. Your assay queue accepts ten. Choose ten variants, rank them, and state what evidence supports each choice and what would overturn it. Report variants you considered and rejected. Do not claim a measured assay outcome.

Protein sequence:
QEELVKAFKALLKEEKFSSQGEIVAALQEQGFDNINQSKVSRMLTKFGAVRTRNAKMEMVYCLPAELGV

Candidate variants:
L27C, K9C, Q30T, V24S, V24N, F17Q, Q28T, A7D, P64I, L12D, E14P, V60G, F17A, R42T, E29H, D33Y, E66Q, K39C, L12Q, E14M, M59H, S38Q, L44S, R51K, M59N, F32V, A49Q, T45I, G21H, G48Y, S18N, L63R, Q37R, A25F, Y61E, G21S, R53K, R42M, N36I, A26S, K16W, S19P, S18F, G48D, E29R, E14V, E29F, N36M, L4A, S19N, R42L, I23G, Q20N, L4S, A10T, A49F, E29L, E66T, C62H, P64L, D33F, V40I, A26D, F47G, E66F, E66D, K9Y, Q30I, I35R, L4V, K9E, K16D, E29N, T52L, R53Y, E3Q, A7P, F32T, E15C, L12V, M43N, V24D, Q20Y, S19M, K56Y, K6Y, I23E, E29D, K13D, A25Q, A55I, L11V, R51H, A49L, N36R, F32M, A26E, D33E, S18E, I23C

```

## B — prompt the Codex B4 cell actually received (full)

```text
You have a protein and candidate single substitutions. Your assay queue accepts ten. Choose ten variants, rank them, and state what evidence supports each choice and what would overturn it. Report variants you considered and rejected. Do not claim a measured assay outcome.

Protein sequence:
QEELVKAFKALLKEEKFSSQGEIVAALQEQGFDNINQSKVSRMLTKFGAVRTRNAKMEMVYCLPAELGV

Candidate variants:
L27C, K9C, Q30T, V24S, V24N, F17Q, Q28T, A7D, P64I, L12D, E14P, V60G, F17A, R42T, E29H, D33Y, E66Q, K39C, L12Q, E14M, M59H, S38Q, L44S, R51K, M59N, F32V, A49Q, T45I, G21H, G48Y, S18N, L63R, Q37R, A25F, Y61E, G21S, R53K, R42M, N36I, A26S, K16W, S19P, S18F, G48D, E29R, E14V, E29F, N36M, L4A, S19N, R42L, I23G, Q20N, L4S, A10T, A49F, E29L, E66T, C62H, P64L, D33F, V40I, A26D, F47G, E66F, E66D, K9Y, Q30I, I35R, L4V, K9E, K16D, E29N, T52L, R53Y, E3Q, A7P, F32T, E15C, L12V, M43N, V24D, Q20Y, S19M, K56Y, K6Y, I23E, E29D, K13D, A25Q, A55I, L11V, R51H, A49L, N36R, F32M, A26E, D33E, S18E, I23C


Reference homolog FASTA for retrieval: /home/aid1/Documents/2_19C_biology/results/benchmark/stage3h_2026-09-14/audit_fastas/012.fasta
Reference structure PDB for geometric evaluation: /home/aid1/Documents/2_19C_biology/results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures/ARGR_ECOLI.pdb

Submit exactly one answer through the mounted record channel, using item_id
`pilot_item`. The answer object must contain `selected`: exactly ten entries,
each with `rank` (1–10), `mutant`, `basis`, `evidence` (receipt ID array),
`validation` (array of {category, call_id}), and `would_overturn`.
Include `rejected`: an array of {mutant, reason}, empty only if none were
rejected. If possible, include `ranking`: one {mutant, score} entry per
supplied candidate, with larger predicted scores better. The scores are your predictions, not
measured fitness. Every cited receipt must come from a successful tool call
in this run. If you cannot support a site/variant, say so; do not invent data.
Submit only when finished. Do not claim an assay result.

```

## Unified diff

```diff
--- A: stage3 manifest ARGR (973 bytes)
+++ B: Codex B4 actual (2023 bytes)
@@ -5,3 +5,18 @@
 
 Candidate variants:
 L27C, K9C, Q30T, V24S, V24N, F17Q, Q28T, A7D, P64I, L12D, E14P, V60G, F17A, R42T, E29H, D33Y, E66Q, K39C, L12Q, E14M, M59H, S38Q, L44S, R51K, M59N, F32V, A49Q, T45I, G21H, G48Y, S18N, L63R, Q37R, A25F, Y61E, G21S, R53K, R42M, N36I, A26S, K16W, S19P, S18F, G48D, E29R, E14V, E29F, N36M, L4A, S19N, R42L, I23G, Q20N, L4S, A10T, A49F, E29L, E66T, C62H, P64L, D33F, V40I, A26D, F47G, E66F, E66D, K9Y, Q30I, I35R, L4V, K9E, K16D, E29N, T52L, R53Y, E3Q, A7P, F32T, E15C, L12V, M43N, V24D, Q20Y, S19M, K56Y, K6Y, I23E, E29D, K13D, A25Q, A55I, L11V, R51H, A49L, N36R, F32M, A26E, D33E, S18E, I23C
+
+
+Reference homolog FASTA for retrieval: /home/aid1/Documents/2_19C_biology/results/benchmark/stage3h_2026-09-14/audit_fastas/012.fasta
+Reference structure PDB for geometric evaluation: /home/aid1/Documents/2_19C_biology/results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures/ARGR_ECOLI.pdb
+
+Submit exactly one answer through the mounted record channel, using item_id
+`pilot_item`. The answer object must contain `selected`: exactly ten entries,
+each with `rank` (1–10), `mutant`, `basis`, `evidence` (receipt ID array),
+`validation` (array of {category, call_id}), and `would_overturn`.
+Include `rejected`: an array of {mutant, reason}, empty only if none were
+rejected. If possible, include `ranking`: one {mutant, score} entry per
+supplied candidate, with larger predicted scores better. The scores are your predictions, not
+measured fitness. Every cited receipt must come from a successful tool call
+in this run. If you cannot support a site/variant, say so; do not invent data.
+Submit only when finished. Do not claim an assay result.
```

## Exactly what B adds

- A local reference homolog FASTA path: `results/benchmark/stage3h_2026-09-14/audit_fastas/012.fasta`.
- A local reference structure PDB path: `results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures/ARGR_ECOLI.pdb`.
- An instruction to submit exactly once through the mounted record channel with `item_id=pilot_item`.
- Required `selected` array: exactly ten entries with `rank`, `mutant`, `basis`, receipt-ID `evidence`, categorical `validation`, and `would_overturn`.
- Required `rejected` array and optional full candidate `ranking` of `{mutant, score}` with larger predicted score better.
- Receipt provenance, no invented data, no measured-assay claim, and submit-only-when-finished instructions.

## Runner audit and freeze finding

`benchmark-mcp/pilot_run.py:run_cell` reads `item['prompt_files'][arm]['path']` and sends **that file's bytes** to `codex exec` on stdin. `benchmark-mcp/pilot_prepare.py` writes those files by appending per-item FASTA/PDB paths and the record contract to the Stage 3 manifest stem; it also alternates two opening stems. `benchmark-mcp/stage3id_run.py` imports `PROMPT` from `stage3ic_run.py`, where it points to the 2,023-byte diagnostic file, and passes its text to Codex. Thus the hashed Stage 3 `prompt_manifest.jsonl` **does not match the prompt the runner sends**. It was a source artifact, not the executable prompt. The Stage 4 pilot selection separately hashed its eight enriched prompt files, but the Stage 4-prep 146-item manifest hashes source and prompt-only variants, not 146 enriched executable prompts. The prior 146 freeze therefore described the wrong artifact for full-MCP arms and **FAILED** as an executable-prompt freeze; it is superseded here, not deemed satisfied.
