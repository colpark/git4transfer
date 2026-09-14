# Stage 4-prep-c finding — second harness control UNDEMONSTRATED

14 September 2026. The accepted Codex B4 control remains valid; this stage sought an independent Claude Code/Opus control, not a replacement. The frozen sealed ARGR prompt was verified byte-for-byte (973 bytes, 100 variants) in a fresh `/tmp` directory, and memory was disabled with documented environment controls. The sole Opus `ok` preflight confirmed `memory_paths: null`, `apiKeySource: "none"`, and all **seven** RESCUE MCP servers connected.

**The model-side grant failed.** Its `system/init` listed three native resource tools—`ListMcpResourcesTool`, `ReadMcpResourceDirTool`, `ReadMcpResourceTool`—despite the fixed 28-name `--disallowedTools` list. It also exposed `mcp__rescue_physics__pyrosetta_ddg`, making **19** MCP functions rather than the Codex B4 cell's **18**. These are observations from the model's catalog, not assumptions from config. The explicit Task 4 stop condition fired; no ARGR cell, evaluator, scorer, label read, further probe or disallow-list repair followed. A trivial `ok` response did not use any tool, but an unused native tool remains a grant failure.

The preflight stderr was empty, all seven servers reported connected, permission denials were empty, and no subagent spawned. Auxiliary Haiku 4.5 appeared in `modelUsage` alongside Opus. The preflight's `total_cost_usd` was **0.084799**, a subscription-side accounting estimate, not a charge. Its rate-limit event showed 43% five-hour and 5% seven-day utilization; no full-cell usage delta exists.

Disclosures to carry verbatim if this path is later used:

> "Claude Code ran on a Max subscription with apiKeySource none. total_cost_usd is a list-price accounting estimate, not a charge. Usage credits are disabled at the organization level (overageStatus rejected, org_level_disabled), so a weekly cap means waiting rather than billing through."

> "Claude Code invokes an auxiliary model (Haiku 4.5) on every turn alongside the named subject model. The subject is not a single model."

These disclosures describe the observed grant preflight; they are **not** claims that the ARGR cell ran. The exact config and raw init event are retained in [rescue_seven.json](rescue_seven.json) and [grant_verify.jsonl](grant_verify.jsonl). The failed grant should be assessed as a Claude Code path/configuration difference; it does not invalidate the already-passed Codex B4 control or demonstrate a biological-tool failure.

**Disposition: UNDEMONSTRATED (Task 4 blocked). Stage 4 remains closed. The panel decides whether to authorize a changed Claude grant before any second harness cell.**
