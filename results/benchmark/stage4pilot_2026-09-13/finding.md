# Stage 4 pilot: stopped by the frozen CPU thermal gate

**13 September 2026 EST. Pilot incomplete; no accuracy claim.** Stage 3d's
8/8 remount ladder and 30-minute, 430/430 full-grant echo envelope passed
before the pilot opened. Seed 42 then selected eight distinct 50%-identity
clusters, two from each released Floor M per-item rho quartile; all item IDs,
frozen floors, prompts, arm grants, scoring code, and 240-cell order were
hashed and published before arm run 1 (`selection.csv`,
`preselection_freeze.json`, `freeze_hashes.json`). No scored element was
changed after the first arm run.

The first randomized cell was item 2, Arm 3 guided, sample 1. It ran for
**67.278 s** and was **UNDEMONSTRATED**: the node-11 CPU-adjacent thermal
zone reached **85.2°C**, crossing the frozen 85°C gate, and the watchdog
terminated the owned model/agent before a response or MCP tool call
completed. There was no submission and no fabricated call ID to score.
The llama.cpp log shows about 9,000 prompt tokens processed and at least
2,651 generation tokens at roughly 42 tokens/s before the stop. This
continuous, long-generation workload differs materially from Stage 3d's
short echo turns. The Stage 3d envelope was a valid reachability/placement
measurement, but it did **not** establish safety for full W1 items.

| Observation | Pilot first cell | Frozen gate |
|---|---:|---:|
| GPU temperature, peak sampled | 70°C | <76°C |
| GPU T.Limit margin, minimum | 23°C | >10°C |
| CPU zone, peak sampled | **85.2°C — fired** | <85°C |
| GPU power draw, peak sampled | 82.33 W | <100 W |
| Available shared memory, minimum | 88.682 GiB | ≥20 GiB |
| GPU utilization, peak sampled | 95% | reported only |

**Planned 240; attempted 1; completed 0; interrupted 1.** By arm, Arm 3
has one attempted/one interrupted; Arms 1, 2, 3F and 3L have zero attempts,
not zero-percent performance. Tool-call attempts/successes were 0/0 for the
first cell, so per-server success rates are undefined. `rejected` emptiness,
evaluation depth, fabricated-ID rate, P@10, and Spearman are **not
evaluable**. The per-item chance baseline for this cell is 0.100; its frozen
Floor C and released Floor M P@10 are both 0.200. The whole-cohort reference
values remain chance 0.103, C 0.176, M 0.218. The partial blind run file was
**not** sealed and the label evaluator was **not** run. No item was silently
scored zero. Its archival SHA-256 is
`1edac111ea911ba2491e0bd17c77e8ca0ec25f7670aff5b53ee786b3e380a41d`;
this is not the complete-run seal required by the scorer.

The observed one-cell active-agent fraction was 0.997, but a 67-second
interrupted cell cannot price 1,776 headline or 900 subset runs. Both
wall-clock projections and a recommended full-run schedule are **unknown**.
No further pilot or full-run cell should start at this operating point. The
panel must rule on a safe operational adjustment (e.g. batch/context/duty
configuration) and require a long-task thermal challenge at that point;
inter-run waits alone cannot cool a single continuous generation. Scientific
prompts, metrics, aggregation, thresholds, scoring code, and arm definitions
remain frozen. W2 still awaits its separate ddG ruling. Floor M MCP
recomputation continues independently on node 10 and is not a completed
floor result.
