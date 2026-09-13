"""Cross-check Stage 3's PSSM formula against the certified classical MCP tool."""

from __future__ import annotations

import asyncio
import json
import math
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from stage3_w1 import OUT, ROOT


def body(response) -> dict:
    return response.structured_content or json.loads(response.content[0].text)


async def main() -> None:
    params = StdioServerParameters(command=str(ROOT / "benchmark-mcp/.venv/bin/python"),
                                  args=[str(ROOT / "benchmark-mcp/server.py"),
                                        "--server", "classical", "--presentation", "unguided"],
                                  cwd=ROOT)
    async with Client(params, raise_exceptions=True, read_timeout_seconds=60) as client:
        names = {tool.name for tool in (await client.list_tools()).tools}
        positive = body(await client.call_tool("pssm_score", {
            "query": "AAA", "msa": ["AAA", "AAA"], "position": 2, "mutant": "C"}))
        negative = body(await client.call_tool("pssm_score", {
            "query": "AAA", "msa": ["AAA"], "position": 2, "mutant": "C"}))
    observed = positive["result"]["delta_bits"]
    expected = -math.log2(3)
    receipt = positive["receipt"]
    artifact = Path(receipt["artifact_path"])
    result = {"tool_advertised": "pssm_score" in names,
              "known_delta_bits": observed, "hand_computed_delta_bits": expected,
              "known_input_pass": abs(observed - expected) < 1e-12,
              "negative_input_failed": negative["result"] is None and bool(negative["error"]),
              "receipt_resolves": artifact.is_file() and
              json.loads(artifact.read_text())["receipt"]["call_id"] == receipt["call_id"],
              "call_id": receipt["call_id"], "artifact_path": str(artifact)}
    assert all(result[key] for key in ("tool_advertised", "known_input_pass",
                                       "negative_input_failed", "receipt_resolves"))
    (OUT / "mcp_pssm_control.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
