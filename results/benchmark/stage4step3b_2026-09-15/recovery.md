# B4 stable-context recovery

## Disposition

Task 1 returned **COSMETIC**, so the additive post-hoc normalization was authorized. The validator and scorer ran over the existing `cmp_004`, `cmp_008`, and `cmp_009` traces/submissions. No model prediction was rerun or changed.

The gate repair canonicalizes only the proven Markdown heading capitalization. Developer messages remain byte-exact and ordered; CLI version, sandbox type, and approval policy remain exact. The original fail-closed decisions remain on disk unchanged. New validation decisions are under `validation/` and are tied to `posthoc_gate_amendment.json` and `recovery_freeze.json`.

## Coverage

| State | B4 scorable coverage |
|---|---:|
| Before | 6/10 |
| After | 9/10 |

`cmp_001` remains a coverage failure because its model process exited 1. It was not rerun.

## Recovered results

| Cell | P@10 | Chance P@10 | Spearman |
|---|---:|---:|---:|
| cmp_004 | 0.200 | 0.100 | 0.562 |
| cmp_008 | 0.200 | 0.100 | 0.640 |
| cmp_009 | 0.200 | 0.100 | 0.687 |

## Audit trail

- Post-hoc amendment SHA-256: `820fa3ff74240407592a3607a647188fae9ac493ea0ba00fa0cd6375c9d2bd39`
- Recovery freeze SHA-256: `67fa806fb0c805b2fec6d1d3e71c5ae548efe40eff3cde411f5d01b26bf697ba`
- Validation summary SHA-256: `57116b752edcaebb35801e1b4a55277b0e37d89918ee70a84d895eee671dc06a`
- Blind bundle SHA-256: `343c1faa037e0b481b1e7bfb06a5c093b6a8d47ce4aec6409ba01cb94bfc2669`
- Evaluation rows SHA-256: `27299f16a4a885729153d80bef803aa91e1ac2f8456d90a168651af71cb58a36`
- The bundle was assembled post-hoc after these exact ten labels had already opened in Step 3; recovered predictions are nevertheless proven unchanged from their pre-label frozen traces. This limitation is recorded, not relabeled as prospective blinding.
- This scorer opened exactly the same ten authorized archive members and none of the other 135.
