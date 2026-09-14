# Provisional prompt recommendation — panel ruling pending

14 September 2026. Recommend the **enriched 2,023-byte ARGR prompt** for the matched, unscored control, and its same-template per-item equivalent for any future scored run. The two harnesses must receive byte-identical item text. This is a recommendation, **not panel approval** to open Stage 4.

The enriched prompt retains the original sequence and 100 candidates, and adds a reference homolog FASTA path, reference structure PDB path, and the existing `pilot_item` answer contract. Supplying reference files removes a retrieval/preparation step an agent would otherwise perform. That is a deliberate task affordance: it must be disclosed and held identical across Arms 1/2/3/3F/3L (even if an arm cannot use a file), rather than treated as evidence of an agent's autonomous retrieval. The paths contain no measured labels. Each arm's available tools remain controlled by the grant.

The schema is essential. The 973-byte stem asks for ten selections but not the submission fields. The earlier Claude cell therefore tested format guessing: it produced a `ranked_selection` object rather than the frozen `selected` contract. A schema-free stem is not an interpretable science control. The enriched prompt uses the already-established record contract; no score, metric, threshold, or arm definition is altered here.

For the 146 items, the literal ARGR-specific paths must be replaced by each item's reference FASTA/PDB paths by a frozen generator. A frozen per-item manifest must hash the **final bytes supplied to the runner**, not just the shorter source stem. If the panel chooses another prompt, this provisional freeze must be superseded before any cohort run.
