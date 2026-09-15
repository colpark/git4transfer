# Ten-item comparison preregistration

Recorded before any label was opened for these ten items.

## Selection

This comparison uses a deterministic ten-item subset of the previously preregistered 30-item batch. The subset takes the first three canonical entries from Floor M rho quartiles Q1 and Q2 and the first two canonical entries from Q3 and Q4. The allocation is therefore 3/3/2/2. This rule uses only the already-published quartile assignments and canonical identifier order; it does not use any newly exposed label or per-item result.

Seed inherited from the 30-item preregistration: **42**.

Canonical identifier-list serialization: each identifier below followed by one LF byte, including the last identifier.

SHA-256 of canonical identifier list: `135710fe4cd6b1c7ea246e7aa6d64aefe5b8e8411d46e7308ba12529cc4811a1`

| Position | Published Floor M rho quartile | Item ID |
|---:|:---:|---|
| 1 | Q1 | A0A192B1T2_9HIV1_Haddox_2018 |
| 2 | Q1 | A4_HUMAN_Seuma_2022 |
| 3 | Q1 | HIS7_YEAST_Pokusaeva_2019 |
| 4 | Q2 | GLPA_HUMAN_Elazar_2016 |
| 5 | Q2 | HXK4_HUMAN_Gersing_2022_activity |
| 6 | Q2 | LGK_LIPST_Klesmith_2015 |
| 7 | Q3 | FKBP3_HUMAN_Tsuboyama_2023_2KFV |
| 8 | Q3 | NUSA_ECOLI_Tsuboyama_2023_1WCL |
| 9 | Q4 | CASP3_HUMAN_Roychowdhury_2020 |
| 10 | Q4 | CBX4_HUMAN_Tsuboyama_2023_2K28 |

## Consequence for the earlier batch record

The user's instruction on 2026-09-14 explicitly authorizes these ten items for comparison and label exposure. This preregistration therefore supersedes the earlier statement that all 30 items would open together. These ten become the comparison cohort and are burned when their labels are exposed. The other 20 members of the earlier 30-item selection remain unopened, as do the original 115-item batch two. No estimate for the full 145-item cohort follows from these ten.

## Frozen comparison rules

All model-arm predictions must be complete, validated, and hashed before any label for these ten items is read. Floor predictions are copied from their already-frozen blind prediction artifacts. The label-bearing evaluator is run only after a blind-bundle hash has been recorded.

The arms are displayed in this fixed non-performance order: Floor C, Floor M (B3), B1, B2, B4.

- **Floor C:** the frozen Stage 3 classical score and its induced full candidate ranking.
- **Floor M (B3):** the frozen Stage 3 protein-language-model score and its induced full candidate ranking.
- **B1:** the established prompt-only Claude Opus 5 answer channel with no scientific or filesystem tools. It receives the neutral endpoint description and candidate set and must return the frozen structured answer. Simulated tool use, fabricated observations, malformed output, missing candidates, or duplicate candidates are coverage failures.
- **B2:** the established prompt-only Qwen3-30B-A3B-Q4_K_M pipeline with temperature 0.2, seed 1, and the same neutral endpoint description and candidate set. The same structured-answer and coverage rules apply.
- **B4:** the corrected prospective Step 2e v3 item-bound agent. It receives the same neutral endpoint description and candidate set plus the frozen item-bound scientific tools. Raw sequence, FASTA/PDB paths, internal item identity, assay author/year, and publication identity remain server-side. Every accepted candidate must have item-bound completed receipts, and submission is server-recorded and validated.

The model-visible comparison content shared by B1, B2, and B4 is the neutral item handle, endpoint description, candidate set, response requirements, and no label. Differences in model family and tool access remain properties of the arms, so this is an arm comparison rather than a causal estimate of tool access alone.

The corrected B4 v3 pipeline has no immutable provider snapshot identifier. This ten-item comparison accepts that limitation prospectively and records every observable model alias, version string, base-instruction hash, developer-instruction hash, tool catalog, transcript, and receipt. The documented pretrained-recognition, platform-catalog, assay-proxy, and optional-metadata limitations are retained in the report rather than treated as absent.

The outstanding B1 answer-channel issue is resolved for this comparison as follows: B1 may run as the prompt-only arm, but any simulated tool/filesystem evidence or fabricated observation makes that item a coverage failure. Invalid answers are coverage failures, never scored zeros.

## Metrics and aggregation

The primary accuracy metric is per-item Spearman correlation over the full candidate ranking. Precision at ten is secondary. Candidate membership, tie handling, ranking direction, label transformation, and scoring code are unchanged from the frozen Stage 3 evaluator.

For each arm, the report will show every item-level Spearman and precision-at-ten result and the arm's scorable coverage as a count out of ten. It will show the arithmetic mean Spearman and arithmetic mean precision-at-ten over scorable items only, with the denominator printed. Coverage failures will be printed as `COVERAGE FAILURE` with their reason and will never be imputed as zero. No pairwise delta, hypothesis test, arm rank, or claim about the other 135 items is preregistered.

Chance precision at ten is `10 / n_candidates` and will be printed per item. There is no analogous universal chance value for the observed-label Spearman statistic.

## Opening rule

The ten labels may be opened only after all five arm artifacts are either frozen as valid predictions or frozen as coverage failures, and after the complete blind bundle and its manifest have been hashed. Once any label opens, no prompt, endpoint description, candidate list, metric, aggregation rule, threshold, scorer, coverage rule, or arm definition may change for these ten items.
