# Item 3 — same item, Arm 3 unguided, sample 1 (unscored)

Frozen item 2 `AACC1_PSEAI_Dandage_2018`, registered Qwen2.5-7B-Instruct Q4_K_M, 32K context, identical item prompt and 1,200-token **per-response** cap. The record mount was repaired. The first model-forwarded unguided grant contained **18 atomic tools**, including `submit_answer`, `esm2_likelihood`, `esm_if` and `esmfold`. No label file or evaluator was opened.

| Observation | Unguided 7B | Old guided Stage 3f, for description only |
|---|---:|---:|
| Outcome | **FAILED**, normal Codex exit but no submission | FAILED; record channel absent |
| Wall clock | 34.69 s | 80.45 s |
| Summed prompt / generated tokens | 85,125 / 1,142 across model requests | 206,862 / 2,954 |
| Record calls attempted / succeeded | 0 / 0, although mounted | 0 / 0, not mounted successfully |
| Classical calls attempted / succeeded | **7 / 7**: one `mmseqs_search`, six `blosum_score` | 16 / 7 |
| Analysis, predictive, generative, physics, lit calls | **0 / 0 each** | 0 / 0 each |
| Fabricated cited call-ID rate | **Unknown**: no submitted answer/citations | Unknown |
| `rejected` populated / evaluation depth | **Unknown** without a submission | Unknown |
| Peak GPU / CPU temperature | 64.0 / 77.9 °C, reported only | 66.0 / 81.1 °C |
| Peak GPU power / utilization; minimum memory available | 79.53 W / 95%; 89.50 GiB | 77.11 W / 95%; 88.65 GiB |
| Model throughput | Minimum 41.94 tokens/s; unloaded median 48.17, 70% gate 33.72 | Minimum 40.14; baseline 48.15, gate 33.70 |

No response sustained 60 seconds, so the synthetic throttle controls passed but the in-cell sustained-window gate was not directly exercised. The final message again asked the user whether to proceed, rather than calling the visible record tool. It also named `L52G`, which was **not** in the supplied candidate list (`G52L` was); this is unscored output-contract evidence, not a fitness assessment.

The observed guided-to-unguided change is 16→7 classical calls and still **0 FM calls / 0 submissions**. It is **not a causal presentation delta**: metadata registration and record availability were repaired between these cells, and the guided one had a biased composite list. A post-repair guided subject run would be required to isolate mode, and was not authorized in the *earlier* Stage 3g pass. The raw `cell7/` trace, forwarded schemas, responses, sensors and `result.json` are preserved.

## Rebuilt surface: same 7B item, unguided, sample 1

`cell7_surface_unguided/` is a **new unscored diagnostic**, not a replacement for the frozen prior trace. It used the exact same item prompt SHA, registered model, seed and 1,200-token per-response cap; the first forwarded request exposed 19 tools, including `blast_msa`, ESM-2, ESM-IF1, ESMFold and `submit_answer`. Wall clock **57.30 s**; 162,312 prompt and 2,051 generated tokens summed over requests; no context/step limit, output-cap exhaustion or validity abort.

Twelve classical calls were attempted: `blast_search` 1, `blast_msa` 1, `blosum_score` 10. By API status, **11 returned values and 1 failed** (`blast_msa`, correctly rejecting no ≥80%-coverage homolog). There were **zero** analysis, predictive, generative, physics, literature or record calls. Ten generic BLOSUM substitutions were tool-scored, but the calls contained only one-letter `wt`/`mutant`, no position or variant ID, and their wild types do not reliably match the named candidates. Thus **zero position-linked candidate evaluations are auditable**; ten candidates were *named* in the final text out of 100, with no valid per-candidate validation. The final message attributed unsupported BLOSUM scores to those variants and asked the user whether to proceed. No `submit_answer` call and no submitted object. This is a normal noncompliant finish, not an interrupted run. No labels were opened.
