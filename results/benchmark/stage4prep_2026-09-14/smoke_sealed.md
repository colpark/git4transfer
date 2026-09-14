# Prompt-only smokes on sealed items (unscored)

14 September 2026. The planned four-cell grid allocated frontier B1a/B1b to sealed AACC1_PSEAI_Dandage_2018 and Qwen B2a/B2b to sealed ARGR_ECOLI_Tsuboyama_2023_1AOY. Neither item is scorable. No labels or evaluator were opened.

| Cell | Status | Wall | Prompt / generation tokens | Raw selected | Parser-accepted picks | Recitation |
|---|---|---:|---:|---:|---:|---|
| B1a, with instruction, AACC1 | UNDEMONSTRATED | — | — | — | — | not tested |
| B1b, without instruction, AACC1 | UNDEMONSTRATED | — | — | — | — | not tested |
| B2a, with instruction, ARGR | completed | 98.305 s | 783 / 7,378 | 10 | 0 | no unprompted PDB or assay ID detected |
| B2b, without instruction, ARGR | completed | 31.447 s | 777 / 2,416 | 10 | 0 | no unprompted PDB or assay ID detected |

B1 was not sent an item: its non-item preflight showed that a native `apply_patch` tool remained model-visible despite zero MCP mounts and a disabled execution host. The call failed closed, but that does not certify the required *no tools of any kind* condition. See [b1_toolfree_control.md](b1_toolfree_control.md).

B2 used one direct model response per cell. Both forwarded requests omit the `tools` field. The frozen parser rejected B2a because its `rejected` set was not the complement of the 100 candidates, and B2b because the answer was nested under `pilot_item` rather than using the required top-level contract. Both also supplied only 20 of 100 ranking entries; their raw ten nominations must not be treated as accepted submissions or scored as zero. The instruction conditions produced different raw nominations, but a single unscored item cannot establish an instruction effect. The unchanged raw answers, requests and parser results are in `qwen30b_promptonly_a/` and `qwen30b_promptonly_b/`.

The four-run smoke target is **2 completed, 2 not attempted because the B1 grant failed preflight**. B1 remains not ready; B2 transport is reachable but contract compliance is not demonstrated.
