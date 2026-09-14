# Label-free diagnostic item selection

The eight original pilot assays were removed before the sweep. `msa_coverage.csv` contains exactly the remaining 140 assay IDs. The audit used the frozen `blast_msa` construction: BLASTP against up to 200 ProteinGym MSA-derived homolog FASTA rows per assay, at most 100 hits, distinct query-anchored rows, and at least 80% query coverage. Neither the 80% threshold nor any assay label was changed or opened.

Usable MSAs: **131/140 (93.6%)**. Nine have no distinct homolog meeting the rule; their assay IDs and failure messages are in the CSV. Among usable assays, homolog-count distribution is min 1, Q1 43, median **79**, Q3 96, max 99 (the 100-hit cap includes the query). The median-depth assay, selected by exact median then assay ID tie-break, is `ARGR_ECOLI_Tsuboyama_2023_1AOY`, with **79** usable homologs. This is the diagnostic item for all four unscored cells. The generated prompt uses the frozen Stage 4 assay stem and answer contract, with only the assay-specific sequence, candidates, reference FASTA and reference PDB substituted; no depth/low-variety paragraph was added.

This is a tool-coverage diagnostic, not a new cohort or a scored pilot item. The 140 assays remain unavailable for a Stage 4 scoring run pending panel re-registration. The label evaluator stays closed.
