# Item 1 — every W1 tool-description change, exact before/after

Compared against the Stage 3g pre-rebuild server at commit `1a3cbd03`; schemas and implementation are described separately below.
The descriptions below are our own code, not quotations from BioDesignBench. The released benchmark's provider uses short mechanism/output descriptions, category workflow guidance and cross-tool pointers; our adaptation makes the evidence channels explicit.

## `blast_msa` — ADDED

Before: (not exposed)

After: RETRIEVE→ANALYSE: BLASTP hits plus distinct query-anchored homolog rows, query first. Pass result.msa and result.query to pssm_score or conservation; no fitness label is used.

## `blast_search` — CHANGED

Before: Retrieve protein homologs from an explicit FASTA using BLASTP.

After: RETRIEVE: BLASTP homolog IDs and alignment statistics, not MSA rows. Use blast_msa to retrieve and align sequences for pssm_score or conservation; avoid repeating identical calls.

## `blosum_score` — CHANGED

Before: Return the canonical raw BLOSUM62 substitution score.

After: SCORE, classical generic substitution evidence: raw BLOSUM62 for one-letter wild type and mutant. Protein-independent; pair with MSA-based pssm_score and learned esm2_likelihood.

## `conservation` — CHANGED

Before: Return normalized Shannon conservation for one MSA column.

After: ANALYSE, classical site evidence: normalized Shannon conservation of a homolog MSA column. Use blast_msa rows; one sequence fails. Not mutation-specific; pair with pssm_score and learned esm2_likelihood.

## `dssp` — CHANGED

Before: Assign per-residue secondary structure with mkdssp 4.2.2.

After: ANALYSE, geometric structural evidence: mkdssp 4.2.2 secondary structure and solvent exposure from a valid PDB. Not stability or fitness; compare learned esmfold and esm2_likelihood separately.

## `esm2_likelihood` — CHANGED

Before: Pinned ESM-2 650M masked-marginal substitution log-likelihood.

After: SCORE, learned sequence channel: pinned ESM-2 650M masked-marginal one-letter substitution log-odds. Not measured fitness or ddG; compare complementary classical pssm_score/BLOSUM and ESM-IF1.

## `esm_if` — CHANGED

Before: Pinned ESM-IF1 backbone-conditioned sequence log-likelihood.

After: SCORE, learned structure-conditioned channel: pinned ESM-IF1 sequence log-likelihood on a supplied backbone. Not ddG or measured fitness; compare esm2_likelihood and classical PSSM independently.

## `esmfold` — CHANGED

Before: Pinned ESMFold v1 structure prediction; returns CA count and PDB artifact.

After: PREDICT, learned structure channel: pinned ESMFold v1 PDB artifact, CA count and confidence. pLDDT is local structural confidence, not fitness/stability; compare geometry with dssp or tmalign.

## `hbond_geometry` — CHANGED

Before: Classify an explicit donor-hydrogen-acceptor triplet by distance and angle.

After: ANALYSE, geometric evidence: distance/angle hydrogen-bond check on supplied coordinates. Not energy, ddG or variant fitness; compare dssp and learned sequence scores separately.

## `log_note` — CHANGED

Before: Append an auditable note for a synthetic smoke item.

After: RECORD: append an auditable working note or rejection rationale; not final submission. Use submit_answer exactly once when evaluation is finished.

## `mmseqs_search` — CHANGED

Before: Retrieve protein homologs from an explicit FASTA using MMseqs2.

After: RETRIEVE: MMseqs2 homolog IDs and alignment statistics, not sequences. Use blast_msa for query-anchored rows before pssm_score or conservation; compare learned esm2_likelihood separately.

## `motif_scan` — CHANGED

Before: Find overlapping sequence-regex motifs with one-based coordinates.

After: ANALYSE: one-based overlapping sequence-regex motif hits. A motif is contextual evidence, not a measured variant effect; compare pssm_score and learned esm2_likelihood.

## `openmm_snapshot_potential_delta` — CHANGED

Before: Diagnostic: two unminimized PDB potential-energy snapshots; NOT ddG or a stability ranker.

After: ANALYSE, physics diagnostic: potential-energy difference of two supplied unminimized PDB snapshots. Neither ddG nor stability/fitness ranker; complementary to learned esm2_likelihood, never interchangeable.

## `pssm_score` — CHANGED

Before: Score a substitution in a supplied MSA with pre-registered pseudocounts.

After: SCORE, classical evolutionary evidence: substitution log-odds from aligned homologs. Supply full query, one-letter mutant and blast_msa rows; compare orthogonal learned esm2_likelihood, not measured fitness.

## `pubmed_search` — CHANGED

Before: Search live PubMed via NCBI E-utilities; scireason MCP is unavailable.

After: RETRIEVE, literature evidence: live PubMed titles/records via NCBI E-utilities. Prior publications provide context, not this assay's label; compare sequence and structural tools independently.

## `pyrosetta_ddg` — CHANGED

Before: Blocked PyRosetta ddG; no physics ddG substitute is authorized.

After: SCORE, physics channel BLOCKED: PyRosetta ddG unavailable on this host. Do not treat openmm_snapshot_potential_delta as ddG or use it to rank W1 fitness.

## `screen_variant_classical` — CHANGED

Before: Guided workflow: PSSM, conservation, and BLOSUM for one variant.

After: GUIDED RETRIEVE→SCORE: BLASTP, construct homolog MSA, then PSSM, conservation and BLOSUM for one position/one-letter mutant. Classical channel; compare screen_variant_fm for complementary learned evidence.

## `screen_variant_fm` — CHANGED

Before: Guided FM workflow: ESM-2 650M mutation score and ESM-IF1 backbone score.

After: GUIDED LEARNED SCORES: ESM-2 650M masked-marginal mutation score plus ESM-IF1 backbone-conditioned plausibility. Compare screen_variant_classical's BLAST/PSSM/BLOSUM channel before ranking.

## `seq_identity` — CHANGED

Before: Global BLOSUM62-aligned identity including terminal gap columns.

After: ANALYSE: global BLOSUM62-aligned sequence identity including terminal gaps. Detect redundancy; not fitness or independent validation. For mutation evidence compare pssm_score and esm2_likelihood.

## `submit_answer` — CHANGED

Before: Accept one JSON answer per synthetic smoke item, without scoring it.

After: SUBMIT: record the one final ranked answer after evaluating and filtering candidates. Receipts must resolve; this records an unscored answer, not a measured assay result.

## `tmalign` — CHANGED

Before: Compare two explicit PDBs with the TM-align structure algorithm.

After: ANALYSE: TM-align two explicit PDB backbones for structural similarity. Not measured stability; complement learned esmfold structure and sequence plausibility with geometric comparison.

## Non-description surface changes

`blast_msa` is a new unguided retrieval→alignment tool. It returns the exact query first and distinct BLAST-hit sequences globally aligned to query columns; it fails if no row passes the preregistered 80% coverage requirement. Guided `screen_variant_classical` now takes sequence, reference FASTA, position, one-letter mutant and max_hits, and chains BLAST→MSA→PSSM/conservation/BLOSUM. Guided `screen_variant_fm` remains its learned-channel counterpart, unchanged in computation. Neither scoring formula nor any assay label changed. A direct positive, malformed-mutant negative, and one-sequence conservation negative are in `surface_controls.json`.

## Arm 3F paragraph — proposed, not applied to frozen prompts

The request asks both to rewrite this paragraph and not to change prompts. The immutable pilot prompt and its manifest remain untouched; the following is a W1 adaptation for panel approval, **not** the text used in any run:

> Consider the supplied variants as the candidate pool; do not invent new variants. Evaluate each shortlisted candidate across multiple complementary evidence categories, including learned and classical channels when granted, and record values for candidates you reject. Rank the supplied pool, then submit only the ten best-supported variants with auditable evidence and validation receipts. Do not submit unevaluated picks.

The public design-task intervention instead requires at least five generated designs, four categories per design, a composite ranking and only three final sequences; copying those counts into a fixed 100-variant W1 task would change the task. If the panel adopts this proposed prompt, all eight pilot items must be discarded under the existing tuning-set rule. Separately, the executable tool-surface change already makes those eight pilot items non-comparable with future runs; discard them for the full-run analysis.
