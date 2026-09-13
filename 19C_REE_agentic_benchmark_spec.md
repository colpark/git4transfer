# 19C Biology Thrust, REE Arm Comparison
## Planning prompt, agentic prompt, answer contract, and measurement plan

Version 0.1, 12 September 2026. Source of record: `REE_E1Bind_AF3_full_report_2026-09-12.pdf`, the E1-Metal-Binding repository, and the project rules in `19C_Agentic_Workflow_Summary.pdf`.

Status: draft for panel review. Nothing here is approved until the senior reviewer signs Stage 0.

---

## 0. The claim this work must support or refuse

An agent that can call a domain foundation model determines rare earth binding better than the same agent without one, and better than a mechanical pipeline with no agent at all.

The September report already narrows the space. AF3 geometric contacts alone reached residue micro F1 0.2864. E1-Bind intersected with AF3 reached 0.3127. The sequence foundation model therefore contributed **+0.0263 over a structure predictor carrying no sequence model**. The historical PLIP scored run agrees at +0.0388, 0.3070 against 0.3458. Any design that prices the gain against raw E1-Bind at 0.0841 will produce a number the project cannot defend.

Every metric below prices against the mechanical floor. That is the project rule and it is not negotiable here.

---

# Part 1. Planning prompt

Hand this to the engineer session. It runs inside Claude Code with the existing panel, hooks and ledger.

```
ROLE
You are the engineer session for the 19C REE arm comparison. You run stages, write
artefacts to disk, and call the panel after every stage. You never approve your own
work and you never modify your own authorisation.

OBJECTIVE
Build and run a benchmark that measures whether an LLM agent granted foundation model
tools determines rare earth binding better than the same agent with classical tools
only, and better than two mechanical floors with no agent.

THE FOUR ARMS
  Floor A   classical only, zero LLM calls. Carboxylate density, EF hand and LBT motif
            scan, DSSP loop geometry, Ln3+ hard acid oxygen donor prior at coordination
            number 8 to 9.
  Floor B   AF3 mechanical, zero LLM calls. Element withheld, ion count derived inside
            the floor, run on every item including negatives.
  Arm 1     LLM alone. Sequence in the prompt, no tools.
  Arm 2     LLM plus classical tools.
  Arm 3     LLM plus classical tools plus foundation models.

Floor B as reported in the September run is not autonomous. Its ion count came from
E1-Bind scores, its element came from the experimental CIF, and it ran only on chains
already known to be positive. You must rebuild it without those three inputs. The
rebuilt number, not 0.2864, is the floor.

STAGE 0, THE KILL GATE. Cap 0 model calls.
  Entry    none
  Work     Cluster the 822 distinct PDB chain pairs in the candidate metadata at 0.5
           sequence identity. Count clusters disjoint from the 149 E1-Bind training
           chains. Report the count, the per cluster chain counts, and the element and
           length distribution of the disjoint pool.
  Exit     A written count with the clustering command, its inputs and its output file.
  Rule     If the disjoint count reaches 30 or more, proceed to Stage 1. If it falls
           below 20, STOP and write the finding. The public structural record then
           cannot support a 100 item benchmark and the work moves to designs plus wet
           lab labels. Between 20 and 29, the senior rules.
  Do not spend a single GPU hour or model call before this gate clears.

STAGE 1, COHORT. Cap 0 model calls.
  Build the item pool to the composition in Part 2 section 2.1. Enforce the firewall
  against the 149 training chains. Compute nearest neighbour identity for every chain
  against the training union and assign the identity bin. Cap chain length at 600
  residues. Cap terbium at 20 percent of items. Write cohort.json with one row per
  chain carrying chain id, source, subtype, element, length, positive count, identity
  bin, cluster id, and firewall status.

STAGE 2, LEAK SCAN AND CONTAMINATION PROBE. Cap 200 model calls.
  Scan every stem for tool names, element names where the element is withheld, residue
  numbers, counts, and any string that identifies the answer. A number identifies more
  precisely than a name.
  Run the recitation probe. Present each chain sequence with no tools and ask for the
  PDB identifier. Any chain the model names is burned and leaves the primary cohort.
  Record the burn rate. It is a reportable quantity.

STAGE 3, FLOORS. Cap 0 model calls. GPU budget declared in the plan file.
  Run Floor A and the rebuilt Floor B on the full cohort. Both floors ship with a
  negative control that makes them fail. Publish both floor tables before any arm runs.
  No arm may start until the floors are on disk.

STAGE 4, ARMS. Cap set per arm in the plan file.
  Run Arms 1, 2 and 3 on the identical cohort with identical stems. Three samples per
  item at the declared temperature. The only difference between arms is the tool grant.
  Log every tool call with arguments, raw return, and a call id the answer can cite.

STAGE 5, SCORING AND REPORT.
  Score against the pinned definitions in Part 4. Bootstrap clustered by chain.
  Report every arm beside both floors in the same table. Report the element withheld
  and element given conditions separately.

RULES CARRIED FROM THE BIOSCAN TRACK
  Rules first. No model call until the classical frontier and the residual are measured.
  A candidate list is not a result. Every gain is priced against the adjudicator that
  receives it.
  Not checked is not pass. Every gate ships with a negative control.
  A leak is any channel by which the question identifies the answer.
  Admission is truth free. Confidence is the accuracy of the evidence pattern, never
  the outcome of the item.
  An instrument built on the candidate set cannot report that the candidate set is wrong.
  An engineer that repairs its own authorisation has none.

PRE-REGISTRATION
  Write every threshold in Part 4 to disk before Stage 3 runs. A threshold chosen after
  a result is void.
```

### The panel, five agents

| Agent | Model | Sees | Does |
|---|---|---|---|
| Curator | Opus | candidate metadata, training union, never the stems | builds the cohort, runs clustering, firewall, identity bins |
| Item writer | Sonnet, fresh context | one case record at a time, never the answer key beyond permitted fields | writes channel agnostic stems and contracts |
| Runner | the subject model | one item, one grant | the system under test |
| Referee | Sonnet, fresh context | answers and call logs, never the stems it did not score | scores against the key, scores call quality, flags fabricated calls |
| Senior | Opus | artefacts first, then all reviews | rules approve, hold, switch or stop, writes the milestone |

The curator and the item writer never see each other's output. The referee never sees which arm produced an answer.

---

# Part 2. Decisions on the agentic prompt

## 2.1 Cohort composition, target 110 chains

| Source | Target n | Cost | Role in the metric |
|---|---|---|---|
| Positive held out chains | 25 | AF3 already run | positive half, recovers sunk compute |
| All zero held out chains | 12 | free, already labeled | negative and abstain items |
| New REE positives, clusters disjoint from the 149 | 25 to 35 | Stage 0 decides | extends the positive half |
| Label defensible negatives from the discarded pool | 30 | free, one config change | negative half |
| De novo RFdiffusion designs | 10 | free | contamination probe only, held out of the primary metric |

The discarded pool is the cheapest row and nobody has opened it. The QA rebuild retained negatives at a 0.2 ratio to positives and capped the rest. Those chains already passed length filtering, clustering and label construction.

Do not relax CD-HIT to 0.7. It buys chains up to 70 percent identical to the training union, which contaminates Arm 3 and lands in the identity regime where every arm converges.

## 2.2 The label definition, stated in every stem

Write this into the contract and into the report. Do not claim a biophysical negative.

> A positive means the contact extraction convention finds a rare earth contact for that residue in a deposited structure of this chain. A negative means it does not. A negative is not proof that the residue cannot coordinate a lanthanide.

This matters because Ln3+ substitutes into calcium sites routinely. Spectroscopists have used terbium and europium as calcium probes for forty years. A benchmark that calls every calcium binder a rare earth negative is wrong about the biophysics and a structural biologist will say so in the first five minutes. The convention framing is honest and costs nothing.

## 2.3 Stratification, one axis filled and three capped

Fill nearest neighbour sequence identity against the 149 training chains. Four bins, roughly 25 chains each.

| Bin | Expected behaviour | Why it earns a place |
|---|---|---|
| under 25 percent | classical retrieval dies, MSA augmented E1 should survive | the window where advantage can appear |
| 25 to 40 percent | the separating band | the operating point |
| 40 to 60 percent | narrowing | the gradient |
| over 60 percent | everything saturates | the declared null |

Cap and do not balance: terbium at 20 percent of items, currently 8 of 25. Length at 600 residues. LREE and HREE at no worse than 35 to 65 either way.

The length cap is a budget decision with no scientific cost. Five of the 25 chains exceed 600 residues and consumed 3,980 of 8,043 HOLO seconds, roughly half the bill for a fifth of the cohort. APO scales worse because MSA preparation dominates. Capping puts a 110 chain sweep near 15 to 18 hours of AF3 job time instead of 35 or more, and you will sweep at least three times.

## 2.4 Prompt construction rules

1. **One system prompt across all arms.** Byte identical. Only the tool grant block differs.
2. **Channel agnostic stems.** No tool name, no model name, no modality name. The fMRI study lost this and a prompt warning alone bought +1.70 with no foundation model mounted.
3. **Element withheld by default.** The September run took the element from the experimental CIF, which is the answer key. Element given runs as a separate condition and the gap between the two is a reported number.
4. **Ion count is the agent's decision.** The September run derived it from E1 scores plus a +2 pad and handed it to AF3. That is conditioning leakage. The agent must state a count and a basis, and the count is scored.
5. **Abstention is a first class answer** with a declared error tolerance in the stem.
6. **Three samples per item.** Aggregation rule declared before the run. Default is unanimity on verdict and element class.
7. **No number in a stem that identifies an answer.** Positive counts, residue indices, ion counts and lengths all leak.

## 2.5 The stems

**S1, protein level determination. Primary.**

> This chain's amino acid sequence is given. Determine whether it coordinates a rare earth ion under the contact convention stated in your contract. If it does, name the rare earth class and place your three strongest candidate sites as groups of residues. If no site meets a 20 percent error tolerance, abstain and name the measurement that would settle it.

**S2, selectivity. Primary for the mission case.**

> This chain coordinates a rare earth ion. State whether the site favours a light or a heavy lanthanide, and give the structural grounds for your answer.

**S3, discrimination against a near neighbour. The hard item.**

> This chain contains a canonical divalent metal binding loop. State whether it also coordinates a rare earth ion under the contact convention. Abstain if the evidence does not reach a 20 percent error tolerance.

**S4, stoichiometry.**

> State how many rare earth ions this chain coordinates, and state what your count rests on.

**S5, experiment proposal. Scored on process, not on an answer key.**

> Propose the single next measurement that would confirm or refute your site assignment, and state which of your own findings it would overturn.

S1 and S3 carry the headline. S2 is where Arm 3 has the clearest mechanism to win. S4 measures the leak the September run could not avoid. S5 goes to the referee rubric and never to the accuracy table.

## 2.6 The tool grants

| Grant | Floor A | Floor B | Arm 1 | Arm 2 | Arm 3 |
|---|---|---|---|---|---|
| sequence in prompt | yes | yes | yes | yes | yes |
| homolog search, MMseqs2 and BLAST | no | no | no | yes | yes |
| motif and family scan, Pfam and PROSITE | yes | no | no | yes | yes |
| secondary structure and geometry, DSSP | yes | no | no | yes | yes |
| coordination chemistry calculator | yes | no | no | yes | yes |
| contact extraction on an existing structure | no | no | no | yes | yes |
| literature search | no | no | no | yes | yes |
| E1 embeddings, encoder role | no | no | no | no | yes |
| E1-Bind residue head, predictor role | no | no | no | no | yes |
| AF3 structure prediction, predictor and simulator roles | no | yes | no | no | yes |
| AF3 confidence readout, scorer role | no | no | no | no | yes |

Arm 2 holds contact extraction on an existing structure so that the comparison stays fair where a structure exists. Arm 3 earns its place only by predicting a structure that does not exist yet, by scoring a hypothesis the agent wrote, or by reading sequence signal no motif scanner carries.

---

# Part 3. The answer contract

Identical across all arms. The referee sees this object and the call log, nothing else.

```json
{
  "item_id": "string",
  "verdict": "binds | does_not_bind | abstain",
  "element_class": "LREE | HREE | unspecified",
  "sites": [
    {
      "rank": 1,
      "residues": [12, 14, 16, 23],
      "basis": "one sentence, no tool name required",
      "evidence": ["call_id:0007", "call_id:0011"]
    }
  ],
  "ion_count": { "value": 2, "basis": "string" },
  "confidence": 0.0,
  "confidence_basis": "agreement across independent channels",
  "abstain_reason": "string or null",
  "next_measurement": "string",
  "would_overturn": "string"
}
```

Decisions inside the contract:

- **Sites are residue groups, never isolated residues.** An experimentalist mutates a site. A ranked list of unconnected residues is not an actionable output, and residue level scoring is what lets the mechanical floor dominate.
- **Top three sites only.** More than three is a candidate list, and a candidate list is not a result.
- **Confidence is the agreement of the evidence pattern, never the outcome of the item.** Ties selected for a right answer teach the model to always pick one.
- **Every evidence reference resolves to a real call id in the log.** The referee checks resolution mechanically before it reads anything. An unresolvable reference is a fabricated call and scores zero for the item.
- **`next_measurement` and `would_overturn` are mandatory even when the agent is confident.** An agent that cannot name what would refute it has not reasoned.
- **A binding claim resting only on a structural confidence score is an automatic fail** for that item. The report is explicit that pTM concerns global topology and says nothing about ion coordinates. The referee checks for this by rule, not by judgement.

---

# Part 4. Measurement

## 4.1 Primary metrics

**P1. Protein level decision, balanced across positives and negatives.** Coverage at a declared error budget. An item is covered when the agent answers and is right. An error costs. An abstention costs nothing but buys nothing. Error tolerance fixed at 20 percent, stated in the stem, pinned before the run.

This is the metric the 12 restored all zero chains make possible, and it is the one the September report admits does not exist. Floor B has no mechanism to return `does_not_bind`, because AF3 places whatever ions you request. Expect the floors to collapse here.

**P2. Site level top three hit rate on positive items.** A hit means at least one proposed site group contains a labeled positive residue. Report at k equal to 1 and 3.

P2 exists because the residue F1 number misleads. Floor B reached micro F1 0.2864 at precision 0.1717. Five of every six residues it proposes are wrong. As an F1 that reads respectably. As a list handed to a mutagenesis queue it is close to useless, and the two numbers must appear side by side so nobody quotes one without the other.

## 4.2 Secondary metrics

| Metric | Definition | Always printed beside |
|---|---|---|
| Residue micro F1 | pooled TP, FP, FN across items | Floor B on the same cohort |
| Selectivity accuracy | LREE against HREE on S2 items | chance at 0.5 and the subtype prior |
| Ion count error | mean absolute error against deposited ion count | Floor B's own count |
| Call quality | right tool, right rank, value read back correctly, abstention when weak, zero fabricated calls | Arm 2 on the same items |
| Recitation burn rate | fraction of chains Arm 1 identified by PDB id | reported, never hidden |

Residue micro F1 stays out of the headline. With 66 positives among 9,721 residues it measures threshold placement rather than reasoning.

## 4.3 Statistics

- Bootstrap clustered by chain, 10,000 resamples, seed 42, declared before the run.
- Effective n is the chain count, not the item count. Five archetypes across 110 chains give 550 items and an effective n of 110. State this in every table caption.
- Report percentile intervals on every arm difference.
- Report the identity bin gradient as the primary secondary analysis. If Arm 3 beats Arm 2 only in the under 25 percent bin, that is the finding and it is a good one.

## 4.4 The gates, written before the run

| Gate | Pass condition |
|---|---|
| Quiet | Arm 3 minus Arm 2 in the over 60 percent identity bin has an interval containing zero |
| Loud | Arm 3 minus Floor B on P1 has an interval excluding zero |
| Causal | Removing the foundation model grant from Arm 3 moves P1 by more than the sampling band |
| Floor honesty | Floor A and Floor B each fail their negative control |
| No leak | Zero stems carry a tool name, an element name under the withheld condition, or an answer identifying number |
| No fabrication | Zero unresolvable evidence references in the scored set |

The Quiet gate matters as much as the Loud gate. An instrument that fires everywhere is not measuring anything.

## 4.5 What a defensible result looks like

State it now so nobody moves the target later.

- Arm 3 beats Arm 2 on P1 by an interval excluding zero, in at least the two lowest identity bins.
- Arm 3 beats the rebuilt Floor B on P1 by an interval excluding zero.
- Arm 3 beats chance on S2 selectivity, where both floors have no mechanism at all.
- The gain survives the element withheld condition.
- Call quality shows the agent selected the right tool and read its value back correctly, because a gain with poor call quality is a prompt effect.

If Arm 3 beats Arm 2 only on residue micro F1 and only where identity runs high, the honest report says the foundation model added nothing the structure predictor did not already carry. Write that finding as readily as the other one. The workflow that establishes it is the product either way.

---

# Part 5. Open items for the panel

1. Stage 0 clustering count. Everything downstream depends on it and nothing else should start.
2. Whether Arm 2 keeps contact extraction on deposited structures. Holding it makes Arm 2 strong and the comparison honest. Granting it to Arm 3 alone would manufacture the result.
3. The aggregation rule across three samples. Unanimity is the declared default. Majority buys coverage and costs errors, and the BIOSCAN tables show it actively harms the weaker tiers.
4. Whether S5 enters any scored table. Current position is no. It goes to the rubric only.
5. Qun Liu's assay queue. Every de novo design item stays out of the primary metric until wet lab labels return.
