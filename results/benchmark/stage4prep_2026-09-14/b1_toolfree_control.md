# B1 tool-free frontier control: FAIL CLOSED, not a compliant prompt-only grant

14 September 2026. Separate **unscored, non-item** preflight thread `01a0a11a-d10c-7010-848a-ff3038c443da` used the signed-in `gpt-5.6-sol` path with zero MCP mounts, read-only sandbox, and shell, web, apps, multi-agent, view-image, and code-mode host disabled. It asked the model to attempt a shell command and `apply_patch` on a harmless marker. The model-side rollout contains a real custom tool request:

```text
const result = await tools.apply_patch("*** Begin Patch\n*** Add File: stage4prep_tool_probe_marker\n+stage4prep tool probe marker\n*** End Patch");
text(result);
```

The router returned `code-mode host is disabled`; the marker did not appear, and no MCP call or shell execution occurred. Thus the safety property failed closed, but the strict B1 requirement **“no tools of any kind visible to the model” did not pass**: the model tried a native tool. Tool unavailability after invocation is not the same as an empty model-side catalog. The attempted call, not a config-file claim, is the decisive observation.

No AACC1 or ARGR B1 item was run. B1a/B1b remain **UNDEMONSTRATED / NOT READY**, not zero-score failures. A tool-free frontier transport or a verified outbound empty tool array is required before the four-smoke grid can be completed. Do not soften B1 to “tools mounted but unused.”
