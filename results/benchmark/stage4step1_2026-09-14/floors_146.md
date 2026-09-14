# Published floors, restricted to the matched 146

Aggregate-only arithmetic on the already published `floor_item_scores.csv`; no label file, evaluator, or sealed-item score was opened. The 148 values are preserved, not overwritten.

| Set | Floor | n | P@10 | Chance P@10 | Lift | Spearman |
|---|---|---:|---:|---:|---:|---:|
| 148_published_set | C | 148 | 0.175676 | 0.102654 | +0.073021 | 0.344942 |
| 148_published_set | M | 148 | 0.218243 | 0.102654 | +0.115589 | 0.490643 |
| 146_matched_set | C | 146 | 0.175342 | 0.102691 | +0.072652 | 0.344848 |
| 146_matched_set | M | 146 | 0.218493 | 0.102691 | +0.115802 | 0.489532 |

The two sealed items are excluded only in the 146 rows. These floor aggregates do not authorize scoring either matched control cell.
