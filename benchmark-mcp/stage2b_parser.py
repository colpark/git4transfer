"""Explicit Qwen/Hermes <tool_call> XML to OpenAI tool-call conversion."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

TAG = re.compile(r"<tool_call>\s*(.*?)\s*</tool_call>", re.DOTALL)


def parse_hermes(content: str, allowed: set[str]) -> list[dict]:
    matches = list(TAG.finditer(content))
    if "<tool_call>" in content and not matches:
        raise ValueError("unclosed or malformed <tool_call> tag")
    calls = []
    for index, match in enumerate(matches):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid tool-call JSON: {error}") from error
        if not isinstance(payload, dict):
            raise ValueError("tool call must be a JSON object")
        name, arguments = payload.get("name"), payload.get("arguments")
        if name not in allowed:
            raise ValueError(f"tool name {name!r} was not in the advertised grant")
        if not isinstance(arguments, dict):
            raise ValueError("tool arguments must be a JSON object")
        identifier = hashlib.sha256(f"{content}:{index}".encode()).hexdigest()[:16]
        calls.append({"id": f"toolcall_{identifier}", "type": "function",
                      "function": {"name": name,
                                   "arguments": json.dumps(arguments, separators=(",", ":"))}})
    return calls


def parse_openai_tool_calls(raw_calls: object, allowed: set[str]) -> list[dict]:
    """Validate llama.cpp's structured Chat Completions tool-call variant."""
    if not isinstance(raw_calls, list):
        raise ValueError("structured tool calls must be a list")
    calls = []
    for call in raw_calls:
        if not isinstance(call, dict) or call.get("type") != "function":
            raise ValueError("structured tool call must be a function")
        function = call.get("function")
        if not isinstance(function, dict) or function.get("name") not in allowed:
            raise ValueError("structured tool name was not in the advertised grant")
        try:
            arguments = json.loads(function.get("arguments", ""))
        except (TypeError, json.JSONDecodeError) as error:
            raise ValueError("invalid structured tool arguments") from error
        if not isinstance(arguments, dict):
            raise ValueError("structured tool arguments must be a JSON object")
        identifier = call.get("id")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("structured tool call ID is missing")
        calls.append({"id": identifier, "type": "function",
                      "function": {"name": function["name"],
                                   "arguments": json.dumps(arguments, separators=(",", ":"))}})
    return calls


def main() -> None:
    raw_path, output_path = (Path(arg) for arg in sys.argv[1:3])
    raw = json.loads(raw_path.read_text())
    content = raw["choices"][0]["message"]["content"]
    allowed = {"echo_tool"}
    parsed = {"raw_model_content": content, "parsed_tool_calls": parse_hermes(content, allowed)}
    output_path.write_text(json.dumps(parsed, indent=2) + "\n")
    assert len(parsed["parsed_tool_calls"]) == 1
    assert json.loads(parsed["parsed_tool_calls"][0]["function"]["arguments"]) == \
        {"text": "stage2b-echo-control"}
    try:
        parse_hermes('<tool_call>{"name":"echo_tool","arguments":"bad"}</tool_call>',
                     allowed)
    except ValueError:
        pass
    else:
        raise AssertionError("malformed argument negative control was not rejected")
    print("one real raw XML call parsed; malformed argument negative control rejected")


if __name__ == "__main__":
    main()
