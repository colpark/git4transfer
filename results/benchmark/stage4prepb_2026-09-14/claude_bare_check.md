# Stage 4-prep-b step 0: Claude Code bare-mode preflight

14 September 2026. **UNDEMONSTRATED — stopped before any model call.**

| Requested check | Observation |
|---|---|
| `command -v claude` | `/home/aid1/.local/bin/claude` |
| `claude --version` | `2.1.269 (Claude Code)` |
| `ANTHROPIC_API_KEY` in this process environment | **Absent** (presence check only; no credential value printed) |
| Bare stream-JSON trivial call | Not run: an API key could not be set from the available environment |
| `agent_session_init` model-side tool list | **Unknown**, not an empty-list result; no init event exists |
| Bare JSON trivial call: `total_cost_usd`, `duration_ms`, `num_turns` | Unknown; no call made |
| Shell canary (`echo CANARY`) | **Not run / UNDEMONSTRATED**, neither PASS nor FAIL |
| Captured stdout and stderr | None: the three requested Claude invocations were not launched |
| Stderr warnings, including skipped MCP servers | Unknown: no Claude invocation was launched |

The requested sequence requires `ANTHROPIC_API_KEY` before the bare-mode calls. This shell has no such variable. A subscription login, keychain credential, another vendor, or a non-bare run would change the control rather than satisfy it, so none was substituted. No MCP server was mounted; no cohort or sealed item, scorer, or evaluator was touched. The claim that `--allowedTools ""` leaves (or removes) built-in tools remains **untested on this host**.

**Exit:** Stop at step 0. The panel cannot decide B1's Claude Code move from this preflight. A securely supplied Anthropic API key in the execution environment is needed for the stated test; then the model-side `agent_session_init` list and canary must be measured, not inferred from flags.
