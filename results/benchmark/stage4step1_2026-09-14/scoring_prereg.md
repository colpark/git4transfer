# Scoring split and label protocol — preregistered before arm runs

14 September 2026. This file is part of the provisional Stage 4 step 1 freeze. No new arm has been scored and no label file is opened by this stage's matched control.

> Precision at ten is scored whenever ten valid unique picks exist. Spearman is scored only when a complete 100-entry ranking exists. A missing ranking is a coverage failure on Spearman and does not suppress the precision score. Invalid answers are coverage failures, never scored zeros.

> Each arm writes a blind prediction file which is hashed before the evaluator runs. The Stage 3 evaluator and its hash are reused unchanged. No per-item result is read until every arm has completed.

> Precision at ten is primary and prints beside the per-item chance baseline. Spearman is secondary. Per-item lift over chance is a reported column.

The 146-item floor recalculation in this stage is an aggregate-only restriction of **already published** Stage 3 floor scores, not an arm score or a new opening of labels. The two sealed harness items are excluded. Future 146-item arm predictions require a new blind-file hash and the unchanged evaluator before any per-item comparison.
