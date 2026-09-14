# Item 2 — ESM-2 convention verified before Track A release

**14 September 2026 UTC.** Track A was held at **1,507/29,336** recorded tool calls, not the 436 stated in the panel note (that was an earlier snapshot). Its intact checkpoint was inspected; no prediction file was sealed and no label evaluator was run. The following 20-candidate audit makes **zero model calls and reads no DMS labels**. It reads only the frozen candidate list, the checkpoint's `esm2_likelihood` values, and the allowlisted `mutant`/`ESM2_650M` columns of the released score archive.

**(a) Scheme: masked marginal.** The live worker contains:

```python
input_ids = tokens["input_ids"].clone()
input_ids[0, position] = tokenizer.mask_token_id
logits = model(input_ids=input_ids, attention_mask=tokens["attention_mask"]).logits[0, position]
log_probs = torch.log_softmax(logits.float(), dim=-1)
return {"delta_log_probability": mutant_logp-wt_logp, ...}
```

The server passes the WT sequence, one-based position and mutant residue to that worker unchanged. For these single substitutions, one position is masked, one forward pass is made, and natural-log mutant-minus-WT odds are returned. This matches the explicit `masked-marginals` flag in [ProteinGym's ESM-2 launch script](https://github.com/OATML-Markslab/ProteinGym/blob/main/scripts/scoring_DMS_zero_shot/scoring_ESM2_substitutions.sh) and the single-site score extraction in its [scoring implementation](https://github.com/OATML-Markslab/ProteinGym/blob/main/proteingym/baselines/esm/compute_fitness.py). [Meier et al.](https://papers.nips.cc/paper_files/paper/2021/hash/f51338d736f95dd42427296047067694-Abstract.html) distinguish this from unmasked WT marginals. A Stage 2 known-input A1R control was +0.1933317184 masked; deliberately omitting the mask gave −2.8935132027. The control would have detected the wrong scheme.

**(b) Input length:** `stage3d_floor_m_mcp.py` passes `meta["target_seq"]` to the tool, with **no MSA-seed extraction, substring window or truncation**. The first audited assay, `POLG_DEN26_Suphatrakul_2023`, passes all 900 residues of its ProteinGym `target_seq` (MSA coordinates 1–900). ProteinGym's scoring script likewise starts from the mapping-file `target_seq`; it may use an optimal window for sequences exceeding the model context. Our worker rejects sequences above 1,022 residues, so it never silently windows them. “Full `target_seq`” is verified; equality with an external full UniProt entry is **not independently verified** for all 148 items.

**(c) Checkpoint:** `facebook/esm2_t6_8M_UR50D`, **8 million parameters**, revision `c731040fcd8d73dceaa04b0a8e6329b345b0f5df`, CPU. The released comparison column is `ESM2_650M`, **650 million parameters**. This intentional weight-size difference changes the numbers and is not evidence of a scoring-scheme error.

**(d) Twenty already-computed candidates:** first 20 checkpointed ESM-2 candidates in frozen candidate-list order, all from the same assay. Values are natural-log substitution scores; larger means more model-favored. The released file's label column was not selected.

| Mutant | MCP ESM-2 8M | Released ESM-2 650M |
|---|---:|---:|
| P331I | -0.29521990 | 0.06041026 |
| Q864P | -0.43169451 | 0.88501358 |
| W292P | 0.32999396 | 0.67066836 |
| R891C | -3.07566404 | -3.97068334 |
| P822I | -0.37407064 | -2.75727534 |
| Q864E | 0.64928818 | 0.64125538 |
| R263D | -0.28074336 | -0.71805525 |
| I135W | -2.50515079 | -0.41947889 |
| Q731A | 0.90590596 | 1.09985161 |
| P727A | -0.28732109 | -3.35228014 |
| F431K | 0.32235169 | -3.27688956 |
| V643K | -0.31430244 | -0.04622746 |
| R891E | 0.41366470 | 0.68860531 |
| R246T | -0.13464737 | -0.21406579 |
| D720T | -0.81195259 | -2.98026848 |
| M116P | 1.18327618 | 0.54049039 |
| R396I | -0.25224113 | -4.66369581 |
| A642N | -0.94381475 | -0.75409150 |
| G587P | -0.72290087 | -3.86885071 |
| S23K | 0.82489657 | 0.86305737 |

Spearman rank correlation, using midranks: **ρ = 0.5578947368** (n=20, one assay). This is a small convention/weight diagnostic, **not** the 148-assay Floor M comparison or a claim about DMS accuracy.

**Decision:** scheme matches. Preserve all 1,507 valid checkpoint calls and resume Track A from that checkpoint; **do not restart from zero or patch old scores**. The 8M/650M distinction and `target_seq` handling remain explicit in every later comparison.
