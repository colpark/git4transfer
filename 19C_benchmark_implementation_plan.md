# 19C Protein Benchmark, Implementation Plan
## Five workflows, OpenHands plus MCP, BioDesignBench method replicated and extended

Version 1.0, 12 September 2026. Supersedes the REE arm comparison pack, which is now one workflow among five rather than the whole project.

---

## 1. What we replicate and what we add

BioDesignBench established the method. We copy it rather than reinvent it.

| Their component | We copy | We change |
|---|---|---|
| 17 tools behind one MCP interface | yes | add ligand and metal aware tools they lack |
| Unguided and guided presentation modes | yes | unchanged |
| Six component rubric, 72 algorithmic and 28 judge | yes | add metal specific quality terms |
| Judge panel, subject's own family excluded | yes | unchanged |
| Hardcoded pipeline, human expert, human oracle baselines | yes | expert on a subset only |
| Forced depth plus compute matched low variety control | yes | unchanged |
| Five layer contamination defence | yes | add deposition date and release date fields |
| **No LLM alone arm** | **no** | we add one. Graham's requirement and their gap |
| **No classical tool arm** | **no** | we add one. Without it no FM claim is possible |

Their eleven conditions never isolate the foundation model. Every LLM condition had all 17 tools. That is the hole our arms fill, and it is the whole 19C thesis.

## 2. What Stage 0b taught, applied here

Three rules govern every decision below.

1. **Count the scarce unit before committing to a target.** Stage 0 counted 78 clusters and the binding number was 19.
2. **A prediction task with a one call answer is not an agentic task.** Reframe it or drop it.
3. **A public dataset predating the model cutoff cannot support an LLM alone arm.** Measure the burn, do not assume it away.

## 3. The five workflows, ranked by feasibility

Feasibility means can we start this month. Strategic value runs almost exactly opposite, and that tension is real.

| # | Workflow | Group | Ground truth | Contamination | Tools ready | Start |
|---|---|---|---|---|---|---|
| W1 | Variant effect, budgeted prioritisation | prediction | measured DMS | high | yes | week 1 |
| W2 | Stability ranking under an assay budget | prediction | measured ddG | high | yes | week 2 |
| W3 | Binder design, replication cell | interface | in silico proxy | none | yes | week 3 |
| W4 | Metal binding scaffold, de novo | ligand | in silico proxy, wet lab later | none | mostly | week 5 |
| W5 | Selectivity conditioned pocket design | ligand | in silico proxy | none | no | week 8 |

### W1, variant effect under a budget

ProteinGym deep mutational scanning assays. The naive form is one ESM call and a Spearman correlation, which is not an agentic task. **Reframe it.** Give the agent a protein and a mutation set, and ask which ten variants it would send to the assay queue, with reasons. That forces generation, multi metric evaluation, comparison and filtering, which is exactly the loop BioDesignBench found agents skip.

The FM ablation here is the cleanest in the whole project. Classical arm gets a position specific scoring matrix and conservation from an MSA. FM arm gets ESM-2 likelihoods and ESM-IF. That comparison is well characterised in the literature, so if our harness cannot reproduce a known gap, the harness is broken and we find out in week one.

Scarce unit is the assay, not the variant. Count it before setting a target.

### W2, stability ranking under a budget

MegaScale folding stability. Same tool stack, same budgeted reframe, different signal. Serves as an independent replicate of W1's harness result on a different measurement type.

Scarce unit is the domain, not the mutation.

### W3, binder design replication cell

The RFdiffusion, ProteinMPNN, AlphaFold pipeline on binder tasks. BioDesignBench reports binder tasks as their highest scoring cell, likely because the task aligns with that core pipeline.

We run it to calibrate. If our harness places a frontier agent near their reported numbers, our instrument is sound. If it does not, we debug before any RESCUE result is generated. This is the single most valuable week of engineering in the plan and it produces no novel science at all.

### W4, metal binding scaffold, de novo

The RESCUE pipeline as an agentic task. Give the agent a target element and a coordination requirement, let it scaffold, design, relax and validate. Ground truth is in silico now, with wet lab labels arriving from the DBTL loop later.

Zero contamination, because the sequences do not exist until the agent makes them. That is what survives Stage 0b when the prediction version did not.

Assets in hand: 503 pockets, 1,807 pocket derived inputs, 350 designs, 28 AF3 prioritised Tier 1 and 2, two validated motif families from 2OJR LBT and 1NCZ EF hand geometries.

### W5, selectivity conditioned pocket design

Design a pocket that prefers terbium over calcium, or a heavy lanthanide over a light one. This converts the dead prediction question into a live design question, which removes the cohort dependency entirely.

Least ready. Needs bond valence sum, dual ion AF3 comparison, and a coordination geometry readout none of which exist as tools today. Highest strategic value, because selectivity is the DOE separation question and no single tool answers it.

**Run the rule check first.** Compute pocket volume and donor count across the 25 AF3 HOLO structures already on disk and test whether either tracks the deposited element's ionic radius. One day, no GPU. If a rule separates the elements, W5 has the same problem localisation had and we learn it before building anything.

---

## 4. MCP server registration

Every tool goes over MCP, including the classical ones. The grant lives entirely in config so the ablation stays auditable, and the agent framework stays swappable. Harbor runs OpenHands and Codex both, so we implement against MCP and keep the harness choice reversible.

```
protein-mcp/
  servers/
    generative/   rfdiffusion, proteinmpnn, ligandmpnn, esm_if
    predictive/   af3, boltz2, esmfold, esm2_likelihood
    physics/      pyrosetta_relax, pyrosetta_ddg, interface_energy, dssp, bond_valence_sum
    analysis/     plip, tmalign, seq_identity, coordination_geometry, pocket_volume,
                  interface_metrics
    classical/    mmseqs_search, blast_search, pssm_score, conservation, motif_scan,
                  blosum_score, hbond_geometry
    lit/          reuse scireason-mcp pubmed, 8 tools, already running
    record/       submit_answer, log_note
  schemas/        one definition per tool, emitted to OpenAI and Anthropic schemas
  presentation/   unguided.json, guided.json
```

**The classical server is not optional and not a formality.** FMADV Test C requires that the foundation model was necessary and not merely sufficient. A classical comparator written after the FM result is visible is worthless. Write and measure these before any arm runs.

Server contract, applies to all:

- Every tool returns `{result, receipt: {call_id, tool, args_hash, runtime_s, artifact_path}}`.
- Long jobs submit and poll. `af3_submit` returns a job id at once. Jobs run 80 to 1,713 seconds and a blocking call hits the MCP timeout.
- Cache on argument hash. Repeated calls across arms and samples must not re-burn GPU.
- Stochastic tools expose a seed argument and never hide it. An agent that runs one seed and reports it is treating a sampler as an oracle, which is the failure BioDesignBench named, and we can only score it if the seed is visible.

---

## 5. Arms

| Arm | Grant | Answers |
|---|---|---|
| Floor M | hardcoded pipeline, zero model calls | their 54.5 equivalent, the frontier |
| Floor C | classical tools only, scripted, zero model calls | can rules alone do this |
| Arm 1 | LLM, record server only | contamination bound |
| Arm 2 | LLM plus classical plus literature | the honest comparator |
| Arm 3 | Arm 2 plus generative, predictive, physics, analysis | system under test |
| Arm 3F | Arm 3 plus forced depth in the spec | is depth the lever |
| Arm 3L | Arm 3 plus low variety at matched compute | is it variety or effort |
| Expert | human, same tools, subset only | the reference |

Arm 3F and Arm 3L differ by one paragraph in the task spec and nothing else. Both instructions also run against Floor M as the intervention's negative control, since a pipeline that already evaluates across categories should not move.

Every arm runs in both presentation modes. Expect guidance to move coverage and not depth, and write that prediction down before running it.

---

## 6. Prompts

Task specs are channel agnostic. No tool name, no model name, no number that identifies an answer. Two paraphrases per stem, alternated across items, which serves as both a contamination layer and a prompt sensitivity control.

**W1 and W2 stem shape.**

> You have a protein and a set of candidate variants. Your assay queue accepts ten. Choose them, rank them, and state for each what evidence supports it and what would overturn it. Report the variants you considered and rejected.

The rejection clause is load bearing. It is the only way to measure filtering, and BioDesignBench found no LLM condition ever discarded a candidate across 836 observations.

**W3, W4 and W5 stem shape.**

> Design a protein meeting the specification below. Generate candidates, evaluate them, and submit only those that survive your own evaluation. State what you rejected and why.

**Forced depth paragraph, Arm 3F.**

> Each submitted candidate must carry validation from at least three distinct categories: structural, energetic, and sequence or geometric. A second call to the same tool with different arguments does not count.

**Low variety paragraph, Arm 3L.**

> Each submitted candidate must carry at least six validation results drawn from no more than two categories.

---

## 7. Scoring

Copy the 72 and 28 split. Anything with a reliable quantitative proxy is scored by code. Anything requiring judgement goes to a panel with the subject's own model family excluded.

| Component | Points | Design tasks | Prediction tasks |
|---|---|---|---|
| Approach | 20 | judge | judge |
| Orchestration | 15 | judge | judge |
| Quality | 35 | structure metrics, plus coordination terms for W4 and W5 | Spearman and top-k precision against the assay |
| Feasibility | 15 | algorithmic | algorithmic |
| Novelty | 5 | algorithmic | not applicable, redistribute |
| Diversity | 10 | algorithmic | algorithmic over the submitted set |

Behavioural metrics, scored on every arm and every item, and label free.

| Metric | Definition |
|---|---|
| Evaluation depth | distinct validation categories per candidate, not call count |
| Filtering rate | items where a generated candidate was dropped |
| Coverage | pipeline stages invoked at all |
| Stochastic handling | seeds run per sampler, and whether outputs were compared |
| Call quality | right tool, right rank, value read back correctly, zero unresolvable receipts |
| Recitation burn | items where the model named the source entry unprompted |

The behavioural axis carries the project. It needs no answer key, it runs on every item in every workflow, and it is where BioDesignBench found the effect.

---

## 8. Stages and gates

Every stage begins with a count and ends with a panel ruling. No stage starts before the previous one clears.

| Stage | Work | Gate |
|---|---|---|
| S1 | Count the scarce unit for all five workflows. Assays for W1, domains for W2, target and motif families for W3 to W5 | any workflow under 30 independent units drops to secondary |
| S2 | Build the MCP servers. Smoke test every tool from the agent, both presentation modes | every mounted server records a successful call, or the model is unusable and we learn it now |
| S3 | Floor M and Floor C on W1. Contamination audit at 8 grams. Recitation probe | floors on disk before any arm runs, both with negative controls |
| S4 | W1 full arm sweep | our FM against classical gap reproduces the known literature gap, or the harness is broken |
| S5 | W3 replication cell | our numbers land near their published cell, or we debug before generating RESCUE results |
| S6 | W2, then W4 | as specified |
| S7 | W5, after the rule check clears | if a rule separates elements by radius, W5 stops |

S4 and S5 are the two that can end the project cheaply. Both are validation stages that produce no novel science, and both come before anything we would want to publish.

---

## 9. Owners and schedule

| Weeks | Work | Owner |
|---|---|---|
| 1 | S1 counts, all five. Zero compute | engineer agent, panel rules |
| 1 to 3 | S2 server build. Classical server first | BNL engineering |
| 2 | DUA conversation with Duke for per task data | David |
| 3 to 4 | S3 and S4 on W1 | BNL |
| 5 to 6 | S5 replication cell. Harbor containerisation | BNL with CMU |
| 7 to 9 | S6, W2 then W4 | BNL, Xin and Gilchan |
| 8 | W5 rule check, one day | BNL |
| 10 plus | S7 if the rule check clears | BNL |

Parallel and not blocking: the straddle defect memo to Xin Dai and Qun Liu, which is independent of everything above and more urgent than all of it.

---

## 10. What kills each workflow

Write these down now so nobody argues later.

| Workflow | Kill condition |
|---|---|
| W1 | Recitation burn exceeds half the items, so no Arm 1 exists |
| W2 | Fewer than 30 independent domains after clustering |
| W3 | Our numbers do not land near their published cell and we cannot explain why |
| W4 | AF3 proxy scoring turns out to be circular, since AF3 is also the instrument |
| W5 | A geometric rule separates elements by ionic radius, so no learned model has room |

W4's kill condition is the one to think hardest about. Using AF3 to score designs that AF3 helped produce is the same circularity that took down the de novo items in the REE pack. Boltz-2 as an independent re-predictor is the mitigation, which is exactly what BioDesignBench does for their Quality component, and it is why that tool appears in the predictive server above.

---

## 11. Three things this plan does not claim

The corpus is not balanced. Two thirds of the merged set is therapeutic or methodological, materials sits at 4 of 93, and critical minerals exists only because we put it there.

The measured ground truth claim needs an audit. Of 93 tasks, 17 carry measured wet lab ground truth and 5 are RESCUE's. Somebody must confirm those 5 mean assay results rather than PLIP read from a deposited structure, because the second kind carries the straddle defect and the scarcity with it.

Nothing here establishes foundation model advantage. It establishes an instrument capable of measuring it, and the instrument is the deliverable whichever way the measurement lands.
