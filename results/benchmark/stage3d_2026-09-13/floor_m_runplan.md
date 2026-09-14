# Floor M MCP recomputation: frozen run plan

Recorded 2026-09-14 00:53 UTC, before the bulk run. This is Parallel Track A
only. It does not use a subject model, Codex, node 11, or measured labels.

- Frozen inputs: 148 assays / 14,668 unique candidates. Candidate SHA-256
  `af4bfd695de3b32c5199b15a312b8c00a4125644051b07782589329c212314cf`;
  released blind prediction SHA-256
  `754b1c7e6e010b3815e58cf5280dde16709dd8fc8a1269ac7a9ae843a6f28613`.
- Predictor: unchanged certified `esm2_likelihood` and `esm_if` tools through
  the MCP interface. Their two receipts and exact values are checkpointed per
  candidate in `floor_m_mcp_progress.jsonl`; a resolving artifact and exact
  arguments are required. No data from `DMS_score` is read by `score`.
- Frozen rank ensemble: percentile ranks of Stage 3 Floor C, local ESM2, and
  local ESM-IF averaged equally, as in Stage 3. No unavailable-model fallback
  is silently invented. The P53_HUMAN reference/PDB mismatch is disclosed.
- Only after all 29,336 tool calls finish, write `floor_m_mcp.csv` atomically
  and seal its SHA-256. `evaluate` refuses to access the label archive until
  that seal exists and matches. The negative control was run before the bulk
  job and correctly raised `complete hashed blind prediction file required
  before labels`.
- Node 10 (`spark-112b`) only, serial, OS nice 15 / idle I/O class. Before
  each uncached call, abort if any readable acpitz zone reaches 83°C or
  MemAvailable falls below 20 GiB. At declaration, zones 0/4 were 45.7°C.
  This is a conservative Track A host-protection rule, not the Stage 3d node
  11 watchdog. Sensor readings are checkpointed. No GPU inference is used.
- Timed, genuinely uncached MCP examples: on a 69-aa item, ESM2 2.12 s and
  ESM-IF 3.61 s; on a 900-aa item, ESM2 2.24 s and ESM-IF 6.32 s. Serial
  extrapolation is at least 23 h and may be ~30–35 h for the full length
  mix, before interruption overhead. Existing model workers reload weights
  per cache miss. A persistent-worker change would be a new tool build and
  recertification, so the run leaves the certified tools unchanged.

An incomplete checkpoint is not a floor result. The released-score Floor M
remains frozen. `floor_m_compare.md` is written only by the post-seal evaluator.
