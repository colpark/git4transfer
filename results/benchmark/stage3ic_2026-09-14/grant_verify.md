# Stage 3i-c model-side grant and remount ladder

`codex login status` remained **Logged in using ChatGPT**. The authenticated Codex model catalog still listed exact ID `gpt-5.6-sol`, 272,000-token context; probe turn context recorded high effort, approval never, and read-only sandbox. No custom provider, node 11 or subagent was used.

The full-grant session `01a0a0b4-1d99-70f3-ab85-9a9e6dd3045a` computed its catalog **inside the model's code-mode executor from `ALL_TOOLS`**, not from `config.toml`. Its exact 23 names were:

`apply_patch`, `list_mcp_resource_templates`, `list_mcp_resources`, `mcp__rescue_analysis__seq_identity`, `mcp__rescue_analysis__tmalign`, `mcp__rescue_classical__blast_msa`, `mcp__rescue_classical__blast_search`, `mcp__rescue_classical__blosum_score`, `mcp__rescue_classical__conservation`, `mcp__rescue_classical__hbond_geometry`, `mcp__rescue_classical__mmseqs_search`, `mcp__rescue_classical__motif_scan`, `mcp__rescue_classical__pssm_score`, `mcp__rescue_generative__esm_if`, `mcp__rescue_lit__pubmed_search`, `mcp__rescue_physics__dssp`, `mcp__rescue_physics__openmm_snapshot_potential_delta`, `mcp__rescue_predictive__esm2_likelihood`, `mcp__rescue_predictive__esmfold`, `mcp__rescue_record__log_note`, `mcp__rescue_record__submit_answer`, `read_mcp_resource`, `view_image`.

The 18 MCP functions match the requested seven-server unguided grant; `pubmed_search` is the actual tool name for the requested lit/PubMed capability. No shell, web, package-install or subagent tool appeared. `clock__curr_time` transiently appeared in the record and first lit catalog probes but not in the full-grant catalog; this is disclosed model-side catalog variability, not silently treated as fixed.

| Server | MCP functions | Model-visible UTF-8 catalog bytes | Probe called | Resolving successful receipt |
|---|---:|---:|---|---|
| record | 2 | 788 | `log_note` | `call_id:322fadaa38ee4fdfac0b4c60be04071f` |
| classical | 8 | 3,715 | `blosum_score` | `call_id:3da6b272ddd24390b1f659134142618a` |
| analysis | 2 | 841 | `seq_identity` | `call_id:4a39ecab506846e4bc790a0d0e05ea32` |
| predictive | 2 | 918 | `esm2_likelihood` | `call_id:7ff0ba82871d460daab1e60c2c2eacdd` |
| generative | 1 | 551 | `esm_if` | `call_id:4876e9b7732e4d1b948ce2b15bb6e72b` |
| physics | 2 | 872 | `dssp`, retry on 1UBQ | `call_id:5a6cc5966ffa46ec8b5f10126c8893d5` |
| lit | 1 | 418 | `pubmed_search`, post-physics retry | `call_id:d160b799393a4ddab888925d9fa80ccf` |

All seven listed receipts resolve to existing artifact files whose `error` is null and `result` is non-null. The initial physics call on the headerless AlphaFold PDB **failed** (`mkdssp` rejected it) although it emitted a receipt. The first runner incorrectly counted a receipt as success and proceeded to lit. The error is preserved in `ladder_6_physics/`; the certification predicate was corrected to require a non-error result, then physics passed on the existing Stage 2 1UBQ fixture and lit passed again afterward. This is why a receipt is not a usable value.

The per-server bytes are UTF-8 lengths of `JSON.stringify(ALL_TOOLS.filter(...server...))` computed by the model-side executor, **not a captured raw provider HTTP request**; raw transport bytes are unknown on the direct ChatGPT path. The sum of separate per-server arrays is 8,103 bytes; the full model-visible catalog (MCP plus five native tools) was 10,825 bytes. The full-grant catalog probe used 26,710 input tokens, leaving **245,290 tokens** against the catalog's 272,000-token context. This is probe headroom, not a measured cell prompt size. Full traces and result JSON for each rung and retry are in this directory.
