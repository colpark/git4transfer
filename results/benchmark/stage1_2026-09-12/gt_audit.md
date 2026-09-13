# Ground-truth provenance audit: claimed 17/93, five RESCUE tasks

The [implementation plan](https://github.com/colpark/git4transfer/blob/main/19C_benchmark_implementation_plan.md) asserts that 17 of 93 merged tasks have measured wet-lab ground truth, five of them RESCUE's. The public `git4transfer` snapshot contains the plan, the earlier REE spec, and the REE E1/AF3 report, but **no 93-task manifest, five task IDs, label-provenance column, or assay records**. The five cannot be mapped individually to an assay or structure from the supplied materials. "Measured wet-lab" is therefore **not checked and not accepted** for any of them.

| Claimed RESCUE slot | Task ID in available sources | Assay result verified? | PLIP-structure result verified for this slot? | Classification |
|---|---|---|---|---|
| 1 | unavailable | no | no | unresolved; do not count as measured assay |
| 2 | unavailable | no | no | unresolved; do not count as measured assay |
| 3 | unavailable | no | no | unresolved; do not count as measured assay |
| 4 | unavailable | no | no | unresolved; do not count as measured assay |
| 5 | unavailable | no | no | unresolved; do not count as measured assay |

This is not evidence that all five lack assays; it is evidence that the claim has no auditable per-task mapping here. The available local REE labeling source, `E1-Metal-Binding-main/data/dataset_artifacts/ree_plip_2026-05-12_qa_rebuild/metadata/ree_binding_metadata.csv`, uses PLIP-derived residue contacts from deposited structures, **not** binding-affinity or selectivity assays. The transferred REE report likewise states that its AF3-assisted result is computational contact concordance and that no binding assay was performed. If any of the five merge tasks are drawn from those rows, they must be reclassified as structural labels and inherit the Stage 0b 50%-family train/test straddle defect (six of 37 held-out chains). No individual merge task can be assigned that provenance without the missing manifest.

**Control that would expose a false pass:** require each of the five task IDs to resolve to an original assay DOI, measured quantity, sample/condition, and raw measurement file; a PLIP/PDB-only task must fail the wet-lab gate. That join cannot run because the key file is absent. Obtain the merge manifest and assay provenance before treating 17/93 or 5/93 as verified.
