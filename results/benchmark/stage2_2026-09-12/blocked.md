# Stage 2 blocks, substitutions, and host disposition

## PyRosetta → OpenMM (methodological deviation)

`pyrosetta_ddg` is **BLOCKED**, not certified. No PyRosetta installation or institutional license credential was available in this workspace, and no PyRosetta calculation was run. The current host is Linux **aarch64** with an NVIDIA GB10 GPU. The [PyRosetta licensing page](https://www.pyrosetta.org/home/licensing-pyrosetta) says academic/non-profit use can be free, but it still requires the applicable non-commercial license; [downloads](https://www.pyrosetta.org/downloads) list current quarterly builds without establishing that a compatible aarch64 wheel imports and runs here. An old aarch64 listing is not evidence for a current executable build. Thus architecture compatibility is **unverified**, not pass. The MCP tool returns null plus this reason, which an agent reached and correctly read.

`openmm_delta_energy` is the **SUBSTITUTED** physics path. OpenMM 8.6.1 executed on this host through MCP: the same prepared matched-topology PDB on both sides gave **0 kJ/mol**, and an invalid PDB failed. The tool returns a potential-energy difference for two prepared structures, **not folding ΔΔG**, and is not interchangeable with a PyRosetta ΔΔG protocol. Any later W2 analysis must keep this distinction explicit; model/assay accuracy is untouched by this smoke. [OpenMM license/platform documentation](https://docs.openmm.org/latest/userguide/library/01_introduction.html).

## Literature service substitution

The proposed `scireason-mcp` PubMed service is **BLOCKED** here: no local installation, connected MCP server, or reachable configured endpoint was found; the plan does not name its eight tools, so none can be silently certified. A one-tool NCBI E-utilities `pubmed_search` server was **SUBSTITUTED** and certified through MCP. PMID 3041007 returned a ubiquitin paper; a unique nonsense query returned null. This is not reuse of all eight scireason tools. [NCBI E-utilities reference](https://www.ncbi.nlm.nih.gov/books/NBK25499/).

## Model and host caveats

Pinned ESM-2 8M and ESMFold v1 ran through MCP. ESMFold completed on this aarch64/GB10 host despite a PyTorch warning that the GPU's 12.1 capability exceeds the wheel's declared 12.0 maximum. The PDB's B-factor field was reported **as written** (0–1-like values in this output), not renamed pLDDT on an assumed 0–100 scale. Structure confidence is not a measured W1/W2 effect. The ESMFold load also warned that two contact-head regression weights were newly initialized; no contact-head prediction is exposed or used. Pinned ESM-IF1 ran after an explicit compatibility shim for Biotite 1.7.1's renamed peptide-backbone filter and a local torch-scatter build; its absent contact-regression weights are irrelevant to the exposed sequence-likelihood score, but are disclosed. [ESM model documentation](https://github.com/facebookresearch/esm), [ESM-IF1 documentation](https://github.com/facebookresearch/esm/blob/main/examples/inverse_folding/README.md).

Classical, analysis, DSSP/OpenMM physics, record, NCBI literature fallback, and ESM-2 CPU are executable on the **current aarch64 host** and should be portable to a CMU CPU host after an environment rebuild. ESMFold is executable on the current GB10 GPU; a specific CMU GPU allocation was not provided, so CMU deployment is **unknown**, not pass. ESM-IF1 ran on CPU here. No tested server is shown to be intrinsically **BNL-only**; neither the BNL HTTP endpoints nor BNL deployment was available for certification. These are local STDIO servers, not a claim that remote production hosting is ready.

## Boundary before Stage 3

The individual classical score conventions were frozen before installing the FM backends. A cross-score variant ranking aggregation was **not** numerically pre-registered; smoke ranking is plumbing only and must not be reused as a scored rule. A later scoring rule requires panel pre-registration before any arm/cohort run. No model scoring run, arm, cohort, or task spec was built here.
