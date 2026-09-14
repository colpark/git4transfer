# Stage 4 step 2b preregistration wording repair

14 September 2026. This amendment is written **before any step-2b model call or label access**. It supersedes only the Spearman sentence in `stage4step1_2026-09-14/scoring_prereg.md`.

The previous text said: “Spearman is scored only when a complete 100-entry ranking exists. A missing ranking is a coverage failure on Spearman and does not suppress the precision score.” That wording was inaccurate for two items in the 146-item set, with 31 and 37 supplied candidates. The unchanged, previously frozen `pilot_score.py:full_ranking` requires one finite numeric score for **each supplied candidate**, not literally 100 entries on every item. No scoring code, aggregation rule, threshold, arm definition, or item-exclusion rule changes.

The amended preregistered text is:

> Spearman is scored wherever a complete ranking of all supplied candidates exists. A missing or incomplete ranking is a coverage failure on Spearman and does not suppress the precision score.

The rest of the Step 1 protocol remains in force: precision at ten is primary and is scored whenever ten valid unique picks exist; invalid answers are coverage failures, never scored zeros; each arm writes a blind prediction file and hashes it before the unchanged Stage 3 evaluator runs; no per-item result is read until every arm has completed. The sealed three-item smoke is pipeline validation, not a performance comparison. The amended freeze and its SHA-256 target list are recorded below after the third item is declared and before any model cell runs.

One non-scored mount-path repair is separately disclosed: `pilot_record_server.py` now permits the Step-2b result directory as a receipt destination. It changes neither the `submit_answer` schema nor any tool computation, but its new file digest is included in this replacement freeze.

## Replacement freeze

The new `freeze_hashes.json` is generated after the third sealed item and 145-item list are declared, and **before any model call**. It hashes this amendment, the 145-item list, all three final prompt bytes and their reference inputs, source/previous freeze, unchanged scorer and Stage 3 evaluator, blind-file assembly and one-shot smoke-evaluation code, the exact runner, MCP implementations and both tool surfaces. The Step 1 freeze remains in the audit trail and is explicitly superseded. The freeze's `status` remains `SMOKE_ONLY_PANEL_RULING_PENDING`; it does not authorize any 145-item cohort run.
