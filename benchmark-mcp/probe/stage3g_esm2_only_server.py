"""One-tool FM reachability probe; same served 650M backend and receipt identity."""

import asyncio
import sys
from pathlib import Path

from mcp.server.mcpserver import MCPServer

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import predictive
from common import emit


def make_server() -> MCPServer:
    mcp = MCPServer("stage3g-esm2-only", version="0.1.0")

    @mcp.tool(name="esm2_likelihood")
    def esm2_likelihood(sequence: str, position: int, mutant: str) -> dict:
        """Score a single mutant with pinned ESM-2 650M masked-marginal log odds."""
        arguments = {"sequence": sequence, "position": position, "mutant": mutant}
        identity = {**arguments, "model": predictive.ESM2_MODEL,
                    "revision": predictive.ESM2_REVISION}
        return emit("predictive", "esm2_likelihood", identity,
                    lambda: predictive.esm2_likelihood(**arguments))

    return mcp


if __name__ == "__main__":
    asyncio.run(make_server().run_stdio_async())
