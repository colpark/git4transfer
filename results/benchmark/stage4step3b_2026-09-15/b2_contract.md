# B2 contract diagnosis

## (a) Is the complement requirement explicit?

Yes. Every B2 comparison prompt contains these exact lines:

> “rejected contains every other candidate exactly once, each as an object with exactly mutant and reason.”

The same response paragraph also says:

> “selected contains exactly ten unique objects in rank order”

Thus the exact-set-difference requirement is explicit in the arm prompt, although the parser's diagnostic wording (“candidate complement”) is more compact than the prompt.

## (b) Valid unique picks independent of contract acceptance

| Cell | First strict rejection | Valid unique selected mutants in candidate set |
|---|---|---:|
| cmp_001 | rejected must be the candidate complement | 10 |
| cmp_002 | rejected must be the candidate complement | 10 |
| cmp_003 | selected basis is empty | 10 |
| cmp_004 | rejected must be the candidate complement | 9 |
| cmp_005 | would_overturn is empty | 10 |
| cmp_006 | selected basis is empty | 10 |
| cmp_007 | rejected must be the candidate complement | 10 |
| cmp_008 | rejected must be the candidate complement | 10 |
| cmp_009 | rejected must be the candidate complement | 10 |
| cmp_010 | rejected must be the candidate complement | 10 |

Nine answers contain 10 valid unique picks. `cmp_004` contains 9 because one selected mutant is outside its supplied candidate set. These counts do not make the answers contract-valid and are not scores.

## (c) Precision-only extraction path

It did **not** fire. The three-item smoke's `stage4step2b_run.py` parsed raw JSON first, then called `pilot_score.selected_mutants(answer, candidates)` independently of strict `parse_answer` acceptance; that preserved P@10 whenever ten ranked, unique, in-candidate selections existed.

In Step 3, `stage4step3_finalize.prompt_answer` calls the strict `stage4step3_prompt.parse_answer` first. Any exception returns `(None, reason)`. Blind assembly then writes a whole-answer `COVERAGE FAILURE`, and the scorer never calls `selected_mutants`; it only calls `full_ranking` after strict acceptance. Therefore B2 is 0/10 measured coverage even though nine cells have a ten-pick set. This is a design/measurement failure, not a zero accuracy result. Per instruction, neither contract nor scorer is changed here.
