# Ten-item comparison

Spearman is the preregistered primary metric; precision at ten is secondary. Coverage failures are not scored as zeros.

## Spearman

| Item | Quartile | Floor C | Floor M (B3) | B1 | B2 | B4 |
|---|:---:|---:|---:|---:|---:|---:|
| cmp_001 | Q1 | 0.378 (chance P@10 0.100) | 0.262 (chance P@10 0.100) | 0.238 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: process exit=1 timed_out=False (chance P@10 0.100) |
| cmp_002 | Q1 | 0.458 (chance P@10 0.100) | 0.308 (chance P@10 0.100) | COVERAGE FAILURE: process exit=1 timed_out=False (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | 0.214 (chance P@10 0.100) |
| cmp_003 | Q1 | 0.026 (chance P@10 0.100) | 0.131 (chance P@10 0.100) | COVERAGE FAILURE: answer is not one plain JSON object (chance P@10 0.100) | COVERAGE FAILURE: selected basis is empty (chance P@10 0.100) | 0.168 (chance P@10 0.100) |
| cmp_004 | Q2 | 0.275 (chance P@10 0.100) | 0.429 (chance P@10 0.100) | -0.525 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: stable received context differs from prospective gate (chance P@10 0.100) |
| cmp_005 | Q2 | 0.266 (chance P@10 0.100) | 0.423 (chance P@10 0.100) | 0.186 (chance P@10 0.100) | COVERAGE FAILURE: would_overturn is empty (chance P@10 0.100) | 0.449 (chance P@10 0.100) |
| cmp_006 | Q2 | 0.342 (chance P@10 0.100) | 0.427 (chance P@10 0.100) | COVERAGE FAILURE: answer is not one plain JSON object (chance P@10 0.100) | COVERAGE FAILURE: selected basis is empty (chance P@10 0.100) | 0.442 (chance P@10 0.100) |
| cmp_007 | Q3 | 0.233 (chance P@10 0.100) | 0.508 (chance P@10 0.100) | 0.189 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | 0.580 (chance P@10 0.100) |
| cmp_008 | Q3 | 0.353 (chance P@10 0.100) | 0.560 (chance P@10 0.100) | COVERAGE FAILURE: one-shot process interrupted by the 2026-09-14 assistant turn abort; no retry permitted (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: stable received context differs from prospective gate (chance P@10 0.100) |
| cmp_009 | Q4 | 0.559 (chance P@10 0.100) | 0.685 (chance P@10 0.100) | 0.475 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: stable received context differs from prospective gate (chance P@10 0.100) |
| cmp_010 | Q4 | 0.383 (chance P@10 0.100) | 0.647 (chance P@10 0.100) | 0.111 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | 0.721 (chance P@10 0.100) |

## Precision at ten

| Item | Quartile | Floor C | Floor M (B3) | B1 | B2 | B4 |
|---|:---:|---:|---:|---:|---:|---:|
| cmp_001 | Q1 | 0.100 (chance P@10 0.100) | 0.100 (chance P@10 0.100) | 0.000 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: process exit=1 timed_out=False (chance P@10 0.100) |
| cmp_002 | Q1 | 0.000 (chance P@10 0.100) | 0.000 (chance P@10 0.100) | COVERAGE FAILURE: process exit=1 timed_out=False (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | 0.000 (chance P@10 0.100) |
| cmp_003 | Q1 | 0.100 (chance P@10 0.100) | 0.200 (chance P@10 0.100) | COVERAGE FAILURE: answer is not one plain JSON object (chance P@10 0.100) | COVERAGE FAILURE: selected basis is empty (chance P@10 0.100) | 0.200 (chance P@10 0.100) |
| cmp_004 | Q2 | 0.200 (chance P@10 0.100) | 0.200 (chance P@10 0.100) | 0.000 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: stable received context differs from prospective gate (chance P@10 0.100) |
| cmp_005 | Q2 | 0.000 (chance P@10 0.100) | 0.000 (chance P@10 0.100) | 0.000 (chance P@10 0.100) | COVERAGE FAILURE: would_overturn is empty (chance P@10 0.100) | 0.000 (chance P@10 0.100) |
| cmp_006 | Q2 | 0.300 (chance P@10 0.100) | 0.500 (chance P@10 0.100) | COVERAGE FAILURE: answer is not one plain JSON object (chance P@10 0.100) | COVERAGE FAILURE: selected basis is empty (chance P@10 0.100) | 0.400 (chance P@10 0.100) |
| cmp_007 | Q3 | 0.000 (chance P@10 0.100) | 0.300 (chance P@10 0.100) | 0.100 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | 0.300 (chance P@10 0.100) |
| cmp_008 | Q3 | 0.200 (chance P@10 0.100) | 0.200 (chance P@10 0.100) | COVERAGE FAILURE: one-shot process interrupted by the 2026-09-14 assistant turn abort; no retry permitted (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: stable received context differs from prospective gate (chance P@10 0.100) |
| cmp_009 | Q4 | 0.400 (chance P@10 0.100) | 0.300 (chance P@10 0.100) | 0.500 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | COVERAGE FAILURE: stable received context differs from prospective gate (chance P@10 0.100) |
| cmp_010 | Q4 | 0.200 (chance P@10 0.100) | 0.400 (chance P@10 0.100) | 0.100 (chance P@10 0.100) | COVERAGE FAILURE: rejected must be the candidate complement (chance P@10 0.100) | 0.300 (chance P@10 0.100) |

## Preregistered conditional summaries

| Arm | Scorable coverage | Mean Spearman (scorable denominator) | Mean P@10 (scorable denominator) |
|---|---:|---:|---:|
| Floor C | 10/10 | 0.327 (n=10) | 0.150 (n=10) |
| Floor M (B3) | 10/10 | 0.438 (n=10) | 0.220 (n=10) |
| B1 | 6/10 | 0.112 (n=6) | 0.117 (n=6) |
| B2 | 0/10 | UNAVAILABLE (n=0) | UNAVAILABLE (n=0) |
| B4 | 6/10 | 0.429 (n=6) | 0.200 (n=6) |

These ten items were selected by a frozen stratified rule for this comparison. They do not estimate performance on the other 135 items. The arms differ in model family and tool access, so the table does not isolate a causal effect of foundation-model tools. B4 uses a moving model alias and generic sequence/backbone evidence that can be misaligned with the declared assay endpoint; those limitations were prospectively accepted and remain part of the interpretation.
