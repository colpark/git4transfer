# Stage 4-prep re-registration: 146 scorable assays

14 September 2026, freeze written at **18:06:28 UTC**, before any Stage 4-prep model smoke. The 13 September `stage4pilot_2026-09-13/freeze_hashes.json` **FAILED as a current freeze and is SUPERSEDED**, not deemed satisfied: MCP variant schemas, descriptions and harness paths changed after it was hashed. A stale freeze is replaced in the audit trail; it does not burn seven items that never ran.

The source floor table has 148 evaluable W1 assay representatives. The full [146-item list](cohort_146.csv) removes exactly two permanently sealed harness-validation assays:

- Pilot item 2, `AACC1_PSEAI_Dandage_2018`: a subject ran for 67 seconds and was interrupted. It is not scored even though the attempt was incomplete.
- `ARGR_ECOLI_Tsuboyama_2023_1AOY`: Stage 3h and 3i-d diagnostic subjects ran on it. It is never scored.

Pilot items **1, 3, 4, 5, 6, 7, and 8** return to the scorable 146 because they never ran or revealed arm behavior. No measured label file was opened in this stage. Existing published Floor C/M aggregate scores were read only as already released; no 146-item floor estimate was computed. The cohort CSV and [146-item prompt-hash manifest](prompt_manifest_146.jsonl) are sorted by assay id and contain no labels.

The replacement [hash set](freeze_hashes.json) records **35 SHA-256 targets**, including the preregistration, source and 146-item floor/prompt manifests, original and prompt-only template/parser/control code, scorer, evaluator, floor code, old and preparation runners, response shim, record mount, validity gate, all seven server implementations, variant schema code, and the MCP tool schema/description inventory in both presentation modes. The live unguided inventory has 19 listed functions, **18 in the frozen Arm 3 grant**; guided has 21. The 19th unguided function is the blocked `pyrosetta_ddg`, not mounted in the accepted 18-function grant.

Selected digest anchors (full path/digest list is in `freeze_hashes.json`):

| Component | SHA-256 |
|---|---|
| Replacement preregistration | `31df91542677914f22756564f70444e7b0b70f86bf9757366ee993ba06b37c97` |
| 146-item list | `1a99ae9981f3e09f608448b8f62726fa443a8fec1088e63d54611409caa20074` |
| Published floor scores | `4f92dab496e5015f818e19eb476668a5151805bd325b823c5629ea2a` |
| 146-item prompt manifest | `cfd187072a05b0c713c2610259d191a51bd06d7938850feb8723d87bc25679d9` |
| Prompt-only template and parser | `2472f16713dc495da38415891062301ad37dd5383c1413f41c1a9142c5524f88` |
| Scoring code | `24896f361c8de45c19f2d69b99bb897b9b20cdb1735a9bb2489f047177630bcb` |
| Evaluator | `723fbf5c03831d470b54fa5d566a7782304e43900a3bed932355084aa56d7b91` |
| Qwen preparation runner | `e9dda36e82f0a7a0f8093c72a7362886ea4fa7e4a8a5b7b82755b17211d54745` |
| MCP server schemas and descriptions | `7a58de0096b3fc9426e5b28a96d5e8bb06841be2851b24bf07c49e30aab34207` |
| Unguided / guided model-visible surfaces | `7d3af333b81e6ef098777fdfc2cc248467e84d87f58aba865a00c0e8fe646f82` / `d98860c8b4fc4dda0435a057e55d135e942b9ec783e41c3ec0581ca875f43263` |

The complete freeze file has SHA-256 `7e0b58a5fdd3ef80d129e6a03fb6df597920a6e6ee2917255c73e0dae4ef2611`. Any scored-element change after this point makes this replacement stale and requires another explicitly superseding freeze before cohort scoring. No scored run is authorized here.
