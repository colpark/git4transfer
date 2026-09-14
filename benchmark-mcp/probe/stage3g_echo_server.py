"""Single-tool echo probe with Stage 3g receipts and a must-fail input."""

import asyncio
import hashlib
import json
import time
import uuid
from pathlib import Path

from mcp.server.mcpserver import MCPServer

OUT = Path(__file__).resolve().parents[2] / "results/benchmark/stage3g_2026-09-14"


def emit_echo(text: str) -> dict:
    started = time.monotonic()
    args_hash = hashlib.sha256(json.dumps({"text": text}, sort_keys=True).encode()).hexdigest()
    result = {"text": text} if 1 <= len(text) <= 64 else None
    error = None if result else "ValueError: text must contain 1–64 characters"
    call_id = "call_id:" + uuid.uuid4().hex
    artifact = OUT / "artifacts/probe" / (call_id.split(":", 1)[1] + ".json")
    artifact.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"call_id": call_id, "tool": "echo_tool", "args_hash": args_hash,
               "runtime_s": round(time.monotonic() - started, 6), "artifact_path": str(artifact)}
    body = {"result": result, "error": error, "receipt": receipt}
    artifact.write_text(json.dumps({"args": {"text": text}, **body}, indent=2) + "\n")
    return body


def make_server() -> MCPServer:
    mcp = MCPServer("stage3g-echo", version="0.1.0")

    @mcp.tool(name="echo_tool")
    def echo_tool(text: str) -> dict:
        """Return one supplied string unchanged, with a receipt."""
        return emit_echo(text)

    return mcp


if __name__ == "__main__":
    asyncio.run(make_server().run_stdio_async())
