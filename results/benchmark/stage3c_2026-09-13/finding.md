# Stage 3c finding — parser repaired, thermal gate stops the envelope

**13 September 2026. Stage 4 remains CLOSED.** The panel's watchdog
correction was applied before inference. GPU utilization became a reported
placement signal, not an abort condition. The frozen gates were GPU ≥76°C or
T.Limit margin ≤20°C, either CPU-adjacent ACPI zone ≥85°C, available shared
memory <20 GiB, and readable GPU power draw ≥100 W. Synthetic must-fail
controls tripped every gate and unreadable sensor; a 100%-utilization sample
with safe temperatures did **not** trip. Thresholds, sources and caveats are
in `watchdog.md`.

The minimal **20-word** echo prompt passed: Qwen2.5 7B Q4 on node 11 called
the node-10 MCP echo tool once, read the correct returned string, cited its
resolving `call_id`, and failed the forged-ID acceptance control. A
W1-length but non-scoring echo prompt also passed one real call. The raw
model response used native structured `tool_calls`; the repaired bridge
correctly delivered them. These are agent reachability results for **one
tool**, not W1 accuracy or full-server reachability. Codex's own wrapper
made even the short task a 6,299-token model prompt; this limitation is
disclosed in `probe_parser.md`.

The subsequent continuous W1-length echo loop completed **104 of 105 agent
runs** in approximately **403.7 seconds**. The final run was interrupted
after a real MCP invocation but before a final receipt citation, so its
outcome is **UNDEMONSTRATED**, not a model failure. Peak sampled GPU
utilization was 95%, GPU temperature 69°C, CPU-zone temperature 82.4°C,
power draw 60.83 W, and minimum available memory 88.703 GiB. The
predeclared **20°C T.Limit headroom gate** fired; no threshold was revised
mid-run. The last-five-minute GPU-temperature median was 65°C, but the
10-minute checkpoint and 30-minute steady-state envelope were not reached.
The owned model process and bridge were stopped; node 11 returned to idle.

**STOP.** Per the stage order, record/classical/analysis/predictive/
generative/physics/lit remounts were not attempted; the first tool-count
failure and its tool-block size are therefore unknown. Only the one-tool
forwarded block is measured (233 bytes). Floor M MCP recomputation remains
blocked on full-grant reachability, Stage 4 wall-clock pricing remains
blocked on a sustained envelope, and the PyRosetta-to-OpenMM ruling still
gates W2. The Stage 3 accepted floors and Stage 3b metric amendment were
not changed. A panel ruling on the declared GPU T.Limit margin or operating
point is needed before another run; no Stage 4 work is authorized.
