# Metric primacy discrepancy

## Governing order

**Precision at ten is primary; Spearman is secondary.** The governing dated amendment is `results/benchmark/stage3b_2026-09-13/preregistration_v2.md`, which states:

> “where its metric order conflicts, this dated amendment controls subsequent reporting.”

and:

> “**Primary decision metric:** precision@10, macro-averaged across independent 50%-identity clusters. Print each item's chance baseline `10/n_candidates` beside its precision@10 and report `lift = precision@10 − 10/n_candidates` ... **Secondary:** per-item Spearman rho and its macro-average.”

The subsequent Stage 4 preparation preregistration confirms rather than changes that order:

> “Primary decision metric remains P@10, with per-item chance and lift; Spearman is secondary only for a complete, valid numeric ranking.”

## Drift

`comparison_10_prereg.md` later says, “The primary accuracy metric is per-item Spearman correlation ... Precision at ten is secondary,” and `comparison.md` repeats it. No recorded amendment identifies a metric-order change, gives a reason, marks it post-result, or supersedes the Stage 3b controlling clause. The Step 3 execution amendment even says `primary_metrics_changed: false`. Therefore this is **drift**, not an effective amendment.

On the six originally scorable paired B4 items, the metrics illustrate why the controlling order matters: B4 minus Floor M is **−0.033 P@10 (n=6)** but **+0.022 Spearman (n=6)**. The governing primary sentence is therefore that B4 trails Floor M by 0.033 in paired mean P@10 on those six items; the opposite-sign Spearman result is secondary.
