# Stage 4-prep-b step 0: Max subscription, tool subtraction

14 September 2026. **The shell canary passed, but the model-side tool catalog was not empty.** No MCP server, cohort item, sealed item, scorer or evaluator was used. All three model calls ran from the empty `/tmp/b1probe` directory. Claude Code was already signed in through `claude.ai` on a `max` subscription; no API key or `--bare` was used. Binary: `/home/aid1/.local/bin/claude`; version: `2.1.269 (Claude Code)`.

## Model-side catalog

The first `system/init` event (the stream's agent-session-init equivalent) reported `mcp_servers: []` and these **26** default tools, in order:

`Task, Bash, CronCreate, CronDelete, CronList, DesignSync, Edit, EnterWorktree, ExitWorktree, ListAgents, Monitor, NotebookEdit, PushNotification, Read, RemoteTrigger, ReportFindings, ScheduleWakeup, SendMessage, Skill, TaskOutput, TaskStop, ToolSearch, WebFetch, WebSearch, Workflow, Write`

Passing **exactly those 26 names**, comma-separated, to `--disallowedTools` produced a second model-side `system/init` list of **`Glob, Grep`**. Thus the list is **NOT EMPTY**; subtracting the initially visible list revealed two tools not listed initially. `Task` and `Bash` were absent in the second event. Both init events reported no MCP servers. The events still advertised global agents, skills and slash commands despite the empty working directory; no claim is made that subscription-mode Claude Code is otherwise memory-free. No disallow-list repair or additional call was attempted.

## Canary and cost

With the unchanged 26-name disallow list, the JSON canary prompt requested `echo CANARY`. Claude replied: “I don't have a shell execution tool available in this session — only file search tools (Glob and Grep). I can't run `echo CANARY` or any other shell command right now.” The saved canary session contains one assistant thinking entry and one text entry, **zero `tool_use` entries**, and `/tmp/b1probe` remained empty. **Canary PASS:** no shell ran and no tool was called. This does **not** certify the stricter B1 requirement of no tools visible, because `Glob` and `Grep` remained visible.

| Call | CLI result | `duration_ms` | `num_turns` | `total_cost_usd` |
|---|---|---:|---:|---:|
| Default `ok`, stream JSON | `ok`; 26 tools in init | 1,421 | 1 | 0.0425572 |
| Subtracted `ok`, stream JSON | `ok`; `Glob`, `Grep` in init | 1,135 | 1 | 0.0461790 |
| Shell canary, JSON | refused; no tool call | 2,047 | 1 | **0.0077980** |

The JSON field is **nonzero** on this subscription path: it is a list-price/accounting estimate emitted by Claude Code, **not evidence of an extra dollar charge** to the Max subscription. The three reported figures total $0.0965342 on that basis. It does not price a full item.

## Full `/usage` readouts

Before the three model calls (subscription `/usage`, no model turn):

```text
You are currently using your subscription to power your Claude Code usage

Current session: 43% used · resets Sep 14, 4pm (America/Panama)
Current week (all models): 6% used · resets Sep 21, 3am (America/Panama)
Current week (Fable): 9% used · resets Sep 21, 3am (America/Panama)

What's contributing to your limits usage?
Approximate, based on local sessions on this machine — does not include other devices or claude.ai. Behaviors are independent characteristics, not a breakdown.

Last 7d · 4488 requests · 146 sessions
  85% of your usage came from subagent-heavy sessions
  74% of your usage came from sessions active for 8+ hours
  74% of your usage was at >150k context
  Top skills: /run-loop 9%
  Top subagents: ml-reviewer 6%, senior-reviewer 6%, domain-reviewer 4%, run-loop 2%, task-proposer 1%, review 1%
```

After the three model calls:

```text
You are currently using your subscription to power your Claude Code usage

Current session: 43% used · resets Sep 14, 4pm (America/Panama)
Current week (all models): 6% used · resets Sep 21, 3am (America/Panama)
Current week (Fable): 9% used · resets Sep 21, 3am (America/Panama)

What's contributing to your limits usage?
Approximate, based on local sessions on this machine — does not include other devices or claude.ai. Behaviors are independent characteristics, not a breakdown.

Last 7d · 4489 requests · 149 sessions
  85% of your usage came from subagent-heavy sessions
  74% of your usage came from sessions active for 8+ hours
  74% of your usage was at >150k context
  Top skills: /run-loop 9%
  Top subagents: ml-reviewer 6%, senior-reviewer 6%, domain-reviewer 4%, run-loop 2%, task-proposer 1%, review 1%
```

Displayed usage delta: **0 percentage points** for both session and weekly windows at the dashboard's integer-percent resolution; local-history counters changed by +1 request and +3 sessions, but are explicitly approximate and exclude other devices. The meter is readable, not precise enough to price three trivial turns or a 146-item sweep. All three CLI calls exited 0; no warning or skipped-MCP message appeared in their observed output.

**Exit:** Stop. B1's no-tools catalog is **not certified** on this exact configuration. The panel decides whether Claude Code merits a further subtraction test; this stage neither fixes the list nor moves B1.
