# Comprehensive ten-item comparison

## Executive result

The preregistered primary metrics are Spearman correlation and precision at 10. All other metrics below were specified after model completion and are exploratory.

| Arm | Coverage | Mean Spearman (95% bootstrap CI) | Mean P@10 (95% bootstrap CI) | Kendall tau-b | NDCG@10 | AP(top-10) | AUC(top-10) |
|---|---:|---:|---:|---:|---:|---:|---:|
| Floor C | 10/10 | 0.327 [0.239, 0.407] | 0.150 [0.070, 0.230] | 0.226 | 0.633 | 0.227 | 0.637 |
| Floor M (B3) | 10/10 | 0.438 [0.335, 0.538] | 0.220 [0.120, 0.320] | 0.305 | 0.671 | 0.252 | 0.661 |
| B1 | 6/10 | 0.112 [-0.164, 0.318] | 0.117 [0.017, 0.283] | 0.082 | 0.572 | 0.170 | 0.455 |
| B2 | 0/10 | — | — | — | — | — | — |
| B4 | 6/10 | 0.429 [0.276, 0.582] | 0.200 [0.067, 0.317] | 0.297 | 0.630 | 0.263 | 0.680 |

## Additional exploratory summaries

| Arm | Pearson | P@5 | P@20 | MRR(true best) | Top-1 hit | Top-5 overlap | Norm. top-10 regret ↓ | Mean true percentile of predicted top-10 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Floor C | 0.334 | 0.100 | 0.335 | 0.106 | 0.000 | 0.100 | 0.137 | 0.663 |
| Floor M (B3) | 0.427 | 0.200 | 0.340 | 0.166 | 0.100 | 0.200 | 0.131 | 0.683 |
| B1 | 0.128 | 0.167 | 0.225 | 0.051 | 0.000 | 0.167 | 0.171 | 0.573 |
| B2 | — | — | — | — | — | — | — | — |
| B4 | 0.393 | 0.200 | 0.342 | 0.076 | 0.000 | 0.200 | 0.150 | 0.639 |

## Paired Spearman comparisons

Positive values favor the first-named arm. Intervals resample paired items; sign-test p-values are exploratory and unadjusted.

| Contrast | Paired n | Mean difference (95% bootstrap CI) | Win/tie/loss | Exact sign p |
|---|---:|---:|---:|---:|
| floor_m − floor_c | 10 | 0.111 [0.021, 0.188] | 8/0/2 | 0.109 |
| b4 − floor_m | 6 | 0.022 [-0.028, 0.059] | 5/0/1 | 0.219 |
| b4 − floor_c | 6 | 0.144 [-0.019, 0.282] | 5/0/1 | 0.219 |
| b1 − floor_m | 6 | -0.380 [-0.639, -0.171] | 0/0/6 | 0.031 |
| b1 − floor_c | 6 | -0.236 [-0.472, -0.079] | 0/0/6 | 0.031 |
| b4 − b1 | 3 | 0.421 [0.263, 0.609] | 3/0/0 | 0.250 |

## Coverage failures

### B1

- cmp_002: process exit=1 timed_out=False
- cmp_003: answer is not one plain JSON object
- cmp_006: answer is not one plain JSON object
- cmp_008: one-shot process interrupted by the 2026-09-14 assistant turn abort; no retry permitted

### B2

- cmp_001: rejected must be the candidate complement
- cmp_002: rejected must be the candidate complement
- cmp_003: selected basis is empty
- cmp_004: rejected must be the candidate complement
- cmp_005: would_overturn is empty
- cmp_006: selected basis is empty
- cmp_007: rejected must be the candidate complement
- cmp_008: rejected must be the candidate complement
- cmp_009: rejected must be the candidate complement
- cmp_010: rejected must be the candidate complement

### B4

- cmp_001: process exit=1 timed_out=False
- cmp_004: stable received context differs from prospective gate
- cmp_008: stable received context differs from prospective gate
- cmp_009: stable received context differs from prospective gate

## Interpretation and limitations

- Floor M has the strongest fully covered preregistered result. B4's conditional mean is similar, but its 6/10 coverage prevents claiming equivalence or superiority.
- B4 and B1 conditional means describe different, non-random item subsets. Cross-arm conditional means are therefore vulnerable to coverage-selection bias; paired contrasts are more defensible but often have very small n.
- B2 has zero schema-valid outputs and cannot be scored. This is a coverage result, not evidence of zero biological accuracy.
- The ten assays were selected by a frozen stratified rule and do not estimate the other 135 assays. Model family and tool access differ together, so this is not a causal tool-access experiment.
- Bootstrap intervals are descriptive with at most ten assay-level units. Exploratory metrics and sign tests were not preregistered, and no multiplicity correction was applied.
- The prospective human content audit was replaced by a disclosed automated audit at the user's instruction; this is a protocol deviation.
- B4 uses a moving model alias and generic sequence/backbone proxy evidence, which may be misaligned with each assay endpoint.

## Integrity

Blind bundle SHA-256: `0702ebfa8ff14ecdb6585c3024eecc6b62014bf334c60ea3571c567992701b5d`  
Frozen primary rows SHA-256: `17a1fbd8b8f62122358bbfdebebf0e2edcbdadd40948f0c048dd4e563c226726`  
Comprehensive rows SHA-256: `2219aefe26d8cffee67d3635db3fe6f91fd8749731e9b3239cf7e4f1f4ca38f9`  
Only the authorized ten labels were read; the other 135 remained unopened by this analysis.
