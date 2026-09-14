# Floor M MCP run status

The label-blind, serial MCP recomputation is **in progress**, not a completed
Floor M result. The active process at launch was PID 3799449 on node 10,
started with `nice -n 15 ionice -c 3`; the launch session was 9770. It writes
one resolving receipt per completed tool call to `floor_m_mcp_progress.jsonl`
and samples node-10 CPU temperature and memory before each uncached call.
Check live progress with `wc -l floor_m_mcp_progress.jsonl` against the
required **29,336** calls. An interrupted job can resume with
`benchmark-mcp/.venv/bin/python benchmark-mcp/stage3d_floor_m_mcp.py score`.

The required `floor_m_mcp.csv` and `floor_m_compare.md` are **not published
yet**. The former is written only after every candidate has both certified MCP
scores; the latter requires that complete blind prediction file and its SHA-256
seal, then runs a separate label evaluator. No partial checkpoint is an
evaluable floor. The released-score Floor M remains untouched and published
in Stage 3.

See `floor_m_runplan.md` for input hashes, method, safety stop, and measured
23–35 hour serial runtime estimate. If the run stops or a safety gate fires,
report the checkpoint count and cause; do not call missing calls failures.
