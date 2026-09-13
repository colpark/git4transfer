# Stage 3 W1 transfer package

Start with [finding.md](finding.md) for the results and stop condition, then
[preregistration.md](preregistration.md) for the frozen cohort and scoring
conventions. The CSV/JSON files contain the cohort, label-blind candidates,
floor predictions, per-item scores, controls, contamination checks, and
recitation traces. Source scripts are in [`benchmark-mcp/`](../../../benchmark-mcp/).

`input/DMS_substitutions.csv` is included. The three original ProteinGym
PG_v1.3 archives are **not** in this transfer: they are approximately 3.46 GB
combined and remain local. Obtain the same-named archives from the
[ProteinGym release](https://github.com/OATML-Markslab/ProteinGym) and place
them under `input/` to rerun preparation, scoring, and evaluation:

| Archive | SHA-256 |
|---|---|
| `DMS_ProteinGym_substitutions.zip` | `3a83766254ac9ac9984ec25cb73c6e010ea4418f5e35f143933e6b6e6473b921` |
| `DMS_msa_files.zip` | `f8c894f0f113f5f49f2945c512b73f488bdf582097dff04658fbb703d92fe34d` |
| `zero_shot_substitutions_scores.zip` | `3fd7cdb5e78f1d43cabfabfeb6578c252b63af23ba2ab44db0094dc3a42de36d` |

`input_hashes.json` also records hashes for the included reference metadata
and Stage 1 assay table. The main W1 scripts require Biopython. The recitation
and MCP-control scripts additionally require the original Stage 2b model host
and certified MCP server; their saved outputs can be audited without those
services. No agent-arm or Stage 4 run is included.
