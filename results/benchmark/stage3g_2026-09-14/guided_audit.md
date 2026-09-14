# Item 2 — guided presentation was asymmetric

There is no static `guided.json` file in the implemented MCP harness: `server.py` registers guided tools at startup. The **exact first Stage 3f model-forwarded JSON** is preserved as `guided_before_forwarded.json`; it contained 17 functions (the Codex request also contained unrelated native/app schemas filtered by the bridge). This is the complete model-visible guided list before repair:

| Server | Tools as described to the model |
|---|---|
| analysis | `seq_identity` — global BLOSUM62-aligned identity; `tmalign` — compare two PDBs with TM-align |
| classical | `blast_search` — retrieve homologs with BLASTP; `blosum_score` — BLOSUM62 substitution score; `conservation` — Shannon conservation for one MSA column; `hbond_geometry` — donor–hydrogen–acceptor geometry; `mmseqs_search` — retrieve homologs with MMseqs2; `motif_scan` — overlapping sequence-regex motifs; `pssm_score` — substitution score from a supplied MSA; **`screen_variant_classical` — guided PSSM, conservation, and BLOSUM workflow for one variant** |
| generative | `esm_if` — pinned ESM-IF1 backbone-conditioned sequence likelihood |
| lit | `pubmed_search` — live PubMed search |
| physics | `dssp` — secondary structure assignment; `openmm_snapshot_potential_delta` — explicitly not ddG; `pyrosetta_ddg` — explicitly blocked |
| predictive | `esm2_likelihood` — pinned ESM-2 650M masked-marginal log likelihood; `esmfold` — ESMFold v1 structure plus PDB artifact |
| record | **Absent** from the model request because its Stage 3f path failed server startup |

Thus **all three atomic FM tools did appear** (`esm2_likelihood`, `esm_if`, `esmfold`), but **no composite called any of them**. The one signposted workflow was classical. That is a harness presentation confound, not evidence that Qwen prefers classical science. It also cannot explain the whole zero-FM result by itself: the FM atoms were available, and the unguided rerun below still selected none.

Repair: guided predictive now also exposes `screen_variant_fm(sequence, position, mutant, pdb_path, chain)`, which returns ESM-2 650M masked-marginal and ESM-IF1 mutant-backbone scores, with both checkpoint identities in its cache key. The direct 1UBQ I3A positive and deliberately invalid-mutant negative controls passed, and the receipt resolved (`direct_controls.json`). `esmfold` remains atomic because a structure/pLDDT prediction is not a mutation-fitness score; folding confidence must not be silently promoted into the scored quantity. The after-repair MCP list in `guided_after_tools.json` has **20 tools**: the original 17, two repaired record tools, and the matching FM composite. The list is direct MCP output, not a claim that a subject model has used the new composite. No additional guided subject cell was run, so the post-repair guided condition remains unmeasured.
