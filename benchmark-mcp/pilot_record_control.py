"""No-model MCP control for per-run record mount and duplicate submission."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4pilot_2026-09-13"


async def main() -> None:
    run_out = OUT / "control_record"
    params = StdioServerParameters(
        command=str(ROOT / "benchmark-mcp/.venv/bin/python"),
        args=[str(ROOT / "benchmark-mcp/pilot_record_server.py"),
              "--out", str(run_out), "--presentation", "unguided"], cwd=ROOT)
    async with Client(params, raise_exceptions=True, read_timeout_seconds=30) as client:
        listed = {tool.name for tool in (await client.list_tools()).tools}
        first = await client.call_tool("submit_answer", {"item_id": "control", "answer": {"x": 1}})
        second = await client.call_tool("submit_answer", {"item_id": "control", "answer": {"x": 2}})
    def body(reply):
        return reply.structured_content or json.loads(reply.content[0].text)
    first, second = body(first), body(second)
    path = run_out / "submissions/control.json"
    receipt = Path(first["receipt"]["artifact_path"])
    checks = {"tool_listed": "submit_answer" in listed,
              "first_submission_accepted": first["error"] is None and path.is_file(),
              "correct_answer_stored": json.loads(path.read_text())["answer"] == {"x": 1},
              "receipt_resolves": receipt.is_file() and
              json.loads(receipt.read_text())["receipt"]["call_id"] == first["receipt"]["call_id"],
              "duplicate_different_answer_rejected": second["result"] is None and
              "already been submitted" in second["error"]}
    output = {"all_pass": all(checks.values()), "checks": checks}
    (OUT / "pilot_record_controls.json").write_text(json.dumps(output, indent=2) + "\n")
    if not output["all_pass"]:
        raise AssertionError(output)
    print(json.dumps(output))


if __name__ == "__main__":
    asyncio.run(main())
