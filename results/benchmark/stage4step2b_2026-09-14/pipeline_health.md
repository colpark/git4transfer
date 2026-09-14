# Stage 4 step 2b: pipeline health (sealed smoke only)

14 September 2026. Three permanently sealed items, one sample per arm, unguided. This table tests file ingestion, parsing, and the preregistered metric split; it is not a baseline comparison. Counts are out of three items. A coverage failure is **not** a zero score.

| Baseline | Blind file readable | Strict parser accepted | Ten valid unique picks | Complete supplied-candidate ranking | P@10 computable | Spearman computable | Coverage failures (P@10 / Spearman) |
|---|---:|---:|---:|---:|---:|---:|---:|
| B1 frontier prompt-only (Claude fallback) | 3/3 | 0/3 | 0/3 | 0/3 | 0/3 | 0/3 | 3 / 3 |
| B2 Qwen3-30B-A3B prompt-only | 3/3 | 0/3 | 2/3 | 0/3 | 2/3 | 0/3 | 1 / 3 |
| B3 mechanical FM / Floor M | 3/3 | 3/3 (mechanical schema) | 3/3 | 3/3 | 3/3 | 3/3 | 0 / 0 |
| B4 frontier + MCP (Codex) | 3/3 | 3/3 (record accepted) | 3/3 | 3/3 | 3/3 | 3/3 | 0 / 0 |
| Carried Floor C | 3/3 | 3/3 (mechanical schema) | 3/3 | 3/3 | 3/3 | 3/3 | 0 / 0 |

Exact prompt-only rejection reasons: B1 returned non-JSON text on all three (`Expecting value: line 1 column 1 (char 0)`). B2 returned a JSON object with `selected`, `rejected`, and `ranking` but missing required top-level fields on AACC1 and ARGR (`answer has wrong top-level contract`); ENVZ returned no answer text after the 16,384-token generation cap (`Expecting value: line 1 column 1 (char 0)`). The unchanged metric extractor found ten valid unique picks in the first two B2 objects. Their P@10 is therefore computable under the preregistered split even though the strict whole-answer parser rejected them. This is **not** a contract pass.

The precision-only path worked: B2's two incomplete-ranking answers produced P@10 entries without Spearman entries. All five blind files were written and SHA-256 hashed in `blind_hashes.json` **before** the unchanged Stage 3 evaluator opened labels. The evaluator ran once, read only the three sealed items, and reproduced six published mechanical-floor per-item checks. The 145-item scorable cohort was excluded by code and its labels were not opened. The pre-cell replacement freeze is `freeze_hashes.json` (SHA-256 `da3caaae8acd0aa9dcae79dd612fd642c6a947cc9e65faf8d418137f9084e00d`). The blind-hash manifest is SHA-256 `b29b0014c785a51e032f679a206b7bbbe4af2921930b4ed722712756e21be0aa`.

Grant checks: Codex could not make an empty model-side catalog (`apply_patch`, `clock__curr_time`, `view_image` remained), so B1 used Claude Code. Claude's actual `system/init` catalog was `tools:[]`, `mcp_servers:[]`, `memory_paths:null` for all three B1 cells, and no actual tool invocation occurred. B2's direct llama.cpp requests contained no `tools` field. B4's model-side preflight showed the accepted seven-server/18-function grant; its native file/image tools provided no execution or network route, and none was invoked. B1 and B2 used different transports after the required Claude fallback; their identical item prompt and tool-free grants do **not** make this a matched-harness performance comparison.

Escalation: B1's text simulated Bash/file reads and, on ENVZ, claimed to discover `/tmp/tools.sock` and seven tools despite `tools:[]` and no tool calls. On AACC1 it purported to show FASTA/PDB file content, including the invented line `ATOM      1 the PDB file exists`. These are hallucinated file/tool observations, not executed commands. The evaluator could read the B1 blind file, but the answer content was not a parseable submission.
