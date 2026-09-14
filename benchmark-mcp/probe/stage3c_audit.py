"""Audit one agent-to-MCP echo call and reject fabricated receipt citations."""

from __future__ import annotations

import json
import re
from pathlib import Path

CALL_ID = re.compile(r"call_id:[0-9a-f]{32}")


def audit(trace: Path, shim_meta: Path, expected_text: str) -> dict:
    events = [json.loads(line) for line in trace.read_text().splitlines()
              if line.startswith("{")]
    calls = [event["item"] for event in events
             if event.get("item", {}).get("type") == "mcp_tool_call"
             and event["item"].get("server") == "stage2b_probe"
             and event["item"].get("tool") == "echo_tool"]
    attempts = len({item["id"] for item in calls})
    successes = []
    for item in calls:
        if item.get("status") != "completed":
            continue
        try:
            body = json.loads(item["result"]["content"][0]["text"])
            receipt = body["receipt"]
            artifact = Path(receipt["artifact_path"])
            if (body["result"] == {"text": expected_text} and body["error"] is None
                    and artifact.is_file() and
                    json.loads(artifact.read_text())["receipt"]["call_id"] ==
                    receipt["call_id"]):
                successes.append(receipt["call_id"])
        except (KeyError, IndexError, TypeError, ValueError, OSError):
            continue
    messages = "\n".join(event["item"].get("text", "") for event in events
                          if event.get("item", {}).get("type") == "agent_message")
    cited = CALL_ID.findall(messages)
    def accepts(candidate: list[str]) -> bool:
        return (len(candidate) == 1 and candidate[0] in successes and
                expected_text in messages)
    forged = successes[0][:-1] + ("0" if successes[0][-1] != "0" else "1") \
        if successes else "call_id:" + "0" * 32
    forged_rejected = not accepts([forged])
    meta = json.loads(shim_meta.read_text())
    passed = attempts == 1 and len(successes) == 1 and accepts(cited) and forged_rejected
    return {"agent_tool_attempts": attempts, "agent_tool_successes": len(successes),
            "correct_value_read_back": expected_text in messages,
            "receipt_cited_and_resolves": accepts(cited),
            "forged_call_id_rejected": forged_rejected,
            "source_tool_block_bytes": meta.get("source_tool_block_bytes"),
            "forwarded_tool_block_bytes": meta.get("forwarded_tool_block_bytes"),
            "forwarded_function_count": meta.get("forwarded_function_count"),
            "raw_model_content": meta.get("raw_model_content"),
            "raw_model_tool_calls": meta.get("raw_model_tool_calls"),
            "verdict": "PASS" if passed else "FAIL",
            "call_id": successes[0] if successes else None,
            "trace_path": str(trace), "shim_meta_path": str(shim_meta)}
