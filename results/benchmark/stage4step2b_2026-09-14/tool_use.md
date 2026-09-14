# B4 tool use on the three sealed smoke items

14 September 2026. Counts are attempted / returned a usable value with a resolving receipt. An absent server had zero calls, not an unmounted grant. The accepted seven-server grant included record, classical, analysis, predictive, generative, physics, and lit; the model-side preflight exposed 18 MCP functions.

| Item | Record | Classical | Analysis | Predictive | Generative | Physics | Lit | ESM-2 unique usable variants | ESM-IF unique usable variants |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| AACC1 | 1/1 | 38/37 | 0/0 | 100/100 | 101/101 | 1/0 | 0/0 | 100/100 | 100/100 |
| ARGR | 1/1 | 311/311 | 0/0 | 302/302 | 304/304 | 1/0 | 0/0 | 100/100 | 100/100 |
| ENVZ | 1/1 | 203/203 | 0/0 | 225/225 | 101/101 | 1/0 | 0/0 | 100/100 | 100/100 |

ESM-2 and ESM-IF are reported separately by **unique candidate variant**, not by number of repeated calls. Thus the B4 ESM-IF-below-100 escalation does **not** fire on any of the three items. The model supplied native `variant="G52L"`-style arguments to both FM tools; the receipt `input_form` counts are in `b4_tool_audit.json`. All three B4 `submit_answer` attempts returned accepted receipts and complete ten-pick/full-ranking objects.

The physics attempt on each item was `dssp` and returned no usable value: `mkdssp` rejected the referenced PDB because it lacked a valid `HEADER` line and was not mmCIF. This is a reproducible tool/input-format defect on the supplied PDB path, not a stability result; the freeze is unchanged and no repair was made during the smoke. AACC1 also had one unusable classical call. All other attempted server calls in the table returned usable values.

Native tool invocations: **zero** across the three B4 traces. Subagents spawned: **zero** under the disabled-subagent configuration, with no subagent event in the traces. Permission denials: **no denial event observed**; Codex JSONL does not expose a separate `permission_denials` field, so this is not asserted as a numeric field value. Record receipts resolve, but receipt validity alone does not establish evidence relevance. The detailed label-free extraction is `b4_tool_audit.json` (SHA-256 `71a451e395f6a3973529df377493b5258ca61534e7e2cc3d92ccba630464f16f`).
