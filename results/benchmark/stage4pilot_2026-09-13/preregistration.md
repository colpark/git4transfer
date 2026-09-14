# Stage 4 pilot pre-registration — before item selection or any arm run

Draft opened 13 September 2026, 19:53 EST (14 September 00:53 UTC).
The final text and code are frozen by SHA-256 in `freeze_hashes.json`
after the Stage 3d gate and before item selection/arm run 1. The pilot
is **closed** until Stage 3d has saved (1) amended-control results, (2) the
eight-step remount ladder, and (3) a completed 30-minute full-grant tool-call
envelope or a recorded stop reason. A stop does not authorize the pilot.

Selection uses only the already-published Stage 3 released-score Floor M
per-item Spearman rho. Sort 148 evaluable assay representatives by
`(rho, assay_id)`, split into four consecutive 37-item quartiles, and draw
two per quartile with Python `random.Random(42).sample`, sorting chosen IDs
within each quartile. The seed **42** and algorithm are declared here before
selection. Save IDs, cluster IDs, candidate counts/chance, and both frozen
Floor C and Floor M P@10/rho before any arm run. No arm outcome enters the draw.
For each selected item, prepare a ≤5 MB homolog-reference FASTA from up to
200 canonical rows of the released A2M, with neutral item-number headers;
the same path appears in every arm's base prompt. This gives the classical
retrieval tool a real, label-free input without exposing an assay identifier.
Likewise copy the released, label-free AF2 reference PDB under a neutral
item-number filename and expose that path identically to every arm; this
lets mounted structural tools take a real input without a source ID in the
prompt. Record both source-file and neutral-copy hashes before run 1.

The five arms are 1 (record only), 2 (record, classical, literature), 3
(those plus analysis, predictive, generative, physics), 3F (Arm 3 grant plus
forced-depth paragraph), and 3L (Arm 3 grant plus low-variety paragraph).
Each uses the same subject Qwen2.5 7B Q4_K_M operating point, three samples,
and both unguided and guided server presentations: **240 planned runs**.
Sampling temperature is 0.2, with backend seeds 1, 2 and 3 for the three
samples and an initial 3,072-token per-response limit. The run order is a
single `random.Random(42).shuffle` of all 240 item/arm/mode/sample cells;
save that schedule before run 1.
Two source-free W1 stem paraphrases alternate by the chosen item's sorted
position (even: Stage 3 stem; odd: a fixed equivalent paraphrase). For each
item, the base prompt is identical across arms, modes and samples;
only 3F and 3L append their respective paragraph. Server grants and mode
live solely in MCP config. The base task uses the frozen Stage 3 candidate
list and no assay labels or source identifiers beyond the protein sequence
and supplied variants. A run-specific record output directory is set by
server configuration, not by changing the prompt. The prompt, scoring code,
metric definitions, and arm grants must be hashed and frozen before run 1.

Output contract: submit one answer containing exactly ten ranked selected
mutants, a `rejected` array (which may be empty), for each selected mutant a
short basis, evidence receipt IDs, distinct validation category/receipt pairs,
and what would overturn it. Include a full candidate ranking if possible.
Do not invent receipts or assay outcomes. The universal contract is identical
in every arm. Arm 3F adds: “Each submitted candidate must carry validation
from at least three distinct categories: structural, energetic, and sequence
or geometric. A second call to the same tool with different arguments does
not count.” Arm 3L adds: “Each submitted candidate must carry at least six
validation results drawn from no more than two categories.” These are the
only arm-specific prompt bytes.

Primary decision metric is P@10: overlap of the submitted ten unique valid
variants with the ten highest measured `DMS_score` variants, divided by ten.
For each arm, average available samples and modes within an assay, then
macro-average the eight independent assays; report run coverage separately.
A malformed or absent submission is
**not** silently scored zero: report it as unavailable with coverage, and
provide a separate intention-to-treat sensitivity analysis treating a
completed but invalid answer as zero. Chance is `10/n_candidates` per item;
print pilot P@10 beside chance ~0.103, frozen Floor C 0.176 and released
Floor M 0.218. Ties use lexicographic mutant order as in Stage 3. Secondary
Spearman is computed only when the answer supplies a complete one-to-one
numeric ranking of all supplied candidates; otherwise mark rho unavailable,
not zero. Use the same Stage 3 measured-label evaluator after a blind answer
file is hashed. `rejected` is empty if absent or `[]`; calculate its rate
among completed submissions and report missing as an additional schema
defect. Evaluation depth is distinct validation categories
per selected variant, verified against real successful tool receipts.
Categories are assigned from the called tool by the frozen evaluator, not
trusted from the model's label: search/PSSM/conservation/BLOSUM/motif/ESM2/
identity are sequence; H-bond geometry is geometric; TM-align/DSSP/ESMFold/
ESM-IF are structural; OpenMM or PyRosetta is energetic; PubMed is literature.
Record tools do not validate a candidate. A claimed category that disagrees
with the tool's mapping does not count toward depth.
Fabricated IDs are unique `call_id:`-like strings in either the submitted
answer or final agent message absent from that run's successful MCP calls;
report per-arm unique-ID numerator and denominator, with any nonzero a finding.
Any tool server outside the arm's grant or native command/file/web capability
seen in the trajectory voids that run's accuracy score; report the violation
separately. A synthetic native-action trace must trip this scanner before run 1.

Report per-arm attempts/completions/interruptions, wall-clock median and
range among completed submissions (plus attempted-run median), per-arm/server
tool-call attempts and successes, empty rejected-field
rate, evaluation depth, thermal profile and duty cycle. Price 1,776 full
headline runs and 900 subset runs from measured representative arm-run times
and the full-grant sustained duty cycle. The echo-envelope time alone is
not a substitute for actual W1 run time.

After seeing pilot outcomes, only timeouts, retries, parallelism, context
size, batch size, duty cycle, server mount order, and logging may change.
**Prompts, metrics, aggregation, thresholds, scoring code, and arm definitions
may not change.** If any scored element must change, discard all eight pilot
items from the final cohort and use the remaining 140. Stop after the pilot;
do not start the full run without panel review.
