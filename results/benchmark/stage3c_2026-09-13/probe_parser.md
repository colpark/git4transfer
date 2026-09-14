# Stage 3c parser and one-tool reachability probe

**PASS for the minimal probe and the W1-length load probe.** The exact
user-task text in `prompt_short.txt` is 136 ASCII characters / 20 whitespace
words, below the 200-token cap; it asks only for one `echo_tool` call. It is
not a W1 item. Codex added its own instructions and tool wrapper, so the
model saw **6,299 total prompt tokens** despite the short task text. This
limits how completely the probe isolates parser behavior from prefill load;
the long-context comparison added 1,081 model prompt tokens and also passed.

| Probe | User-task length | Model prompt tokens | Agent MCP attempts / successes | Receipt and value | Tool block forwarded |
|---|---:|---:|---:|---|---:|
| Short echo | 136 chars | 6,299 | 1 / 1 | exact string and resolving `call_id` cited | 233 bytes |
| W1-length echo | 1,792 chars | 7,380 | 1 / 1 | exact string and resolving `call_id` cited | 233 bytes |

The length-loaded text is a label-blind Stage 3 W1 protein sequence and
candidate-list context, explicitly inert; no variants were ranked, scored,
or submitted. Its source prompt was 1,854 characters. The real backend reply
in each probe had an empty `content` string and one native structured
`tool_calls` entry. The repaired bridge validated the advertised
`echo_tool` name, JSON-object arguments, and call ID; the agent then made a
real MCP call and read the returned receipt. The trace, raw model response,
parsed bridge item, and receipt artifact are retained under this output
directory; `reachability.csv` gives their paths.

The direct MCP control made **2 attempts / 1 intended success**: a valid
string returned a resolving receipt; the empty string returned an error.
The Stage 2 tamper predicate rejected a forged receipt ID. The same forged-ID
substitution was applied to each agent citation and rejected. A fabricated
ID would be **FAIL**, not partial credit. `probe_controls.json` and the
per-probe audits contain these control results.

The subject was Qwen2.5 7B Instruct Q4_K_M, 32K configured context, served
by llama.cpp on node 11 with 99 GPU layers; agent/MCP ran on node 10.
This establishes criterion-(c) reachability for **one tool**, not the later
remounts or a scientific W1 answer.
