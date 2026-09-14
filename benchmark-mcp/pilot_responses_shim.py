"""Bounded Responses-to-llama.cpp bridge with an explicit Qwen XML parser.

Only MCP namespaces named on the command line are forwarded to the model.
Codex's unrelated native/app tools are intentionally excluded from this
one-tool reachability grant. Every forwarded schema and raw model reply is saved.
"""

from __future__ import annotations

import argparse
import json
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from stage2b_parser import parse_hermes, parse_openai_tool_calls

MODEL = "qwen2.5-7b-instruct-q4_k_m"


def content_text(content: object) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(part.get("text", "")) for part in content
                         if isinstance(part, dict))
    return str(content)


def chat_messages(payload: dict, names: dict[str, tuple[str, str]]) -> list[dict]:
    messages = []
    if payload.get("instructions"):
        messages.append({"role": "system", "content": payload["instructions"]})
    for item in payload.get("input", []):
        kind = item.get("type")
        if kind == "message":
            role = item.get("role", "user")
            if role == "developer":
                role = "system"
            messages.append({"role": role, "content": content_text(item.get("content", ""))})
        elif kind == "function_call":
            namespace, name = item.get("namespace"), item.get("name")
            backend = next((key for key, pair in names.items()
                            if pair == (namespace, name)), name)
            messages.append({"role": "assistant", "content": None,
                             "tool_calls": [{"id": item.get("call_id", "unknown"),
                                             "type": "function",
                                             "function": {"name": backend,
                                                          "arguments": item.get("arguments", "{}")}}]})
        elif kind == "function_call_output":
            messages.append({"role": "tool", "tool_call_id": item.get("call_id", "unknown"),
                             "content": content_text(item.get("output", ""))})
    return messages


def flatten_tools(payload: dict, allowed: set[str]) -> tuple[list[dict], dict[str, tuple[str, str]]]:
    tools = []
    names = {}
    for namespace in payload.get("tools", []):
        server = namespace.get("name")
        if namespace.get("type") != "namespace" or server not in allowed:
            continue
        for function in namespace.get("tools", []):
            if function.get("type") != "function":
                continue
            name = function["name"]
            backend = name if server == "mcp__stage2b_probe" else f"{server}__{name}"
            names[backend] = (server, name)
            tools.append({"type": "function", "function": {
                "name": backend, "description": function.get("description", ""),
                "parameters": function.get("parameters", {"type": "object", "properties": {}})}})
    return tools, names


def response_item(call: dict, names: dict[str, tuple[str, str]]) -> dict:
    backend = call["function"]["name"]
    namespace, name = names[backend]
    return {"id": "fc_" + uuid.uuid4().hex, "type": "function_call",
            "status": "completed", "call_id": call["id"], "namespace": namespace,
            "name": name, "arguments": call["function"]["arguments"]}


class Handler(BaseHTTPRequestHandler):
    output: Path
    allowed: set[str]
    backend: str
    model: str
    lock = threading.Lock()
    sequence = 0

    def log_message(self, format: str, *args: object) -> None:
        print(format % args, flush=True)

    def do_GET(self) -> None:
        if self.path.startswith("/v1/models"):
            body = json.dumps({"models": [], "object": "list", "data": []}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/v1/responses":
            self.send_error(404)
            return
        with self.lock:
            Handler.sequence += 1
            index = Handler.sequence
        prefix = f"shim_{index:03d}"
        raw_request = self.rfile.read(int(self.headers.get("Content-Length", "0")))
        (self.output / f"{prefix}_request.json").write_bytes(raw_request)
        try:
            payload = json.loads(raw_request)
            tools, names = flatten_tools(payload, self.allowed)
            if not tools:
                raise ValueError("no allowed MCP tool in provider request")
            chat = {"model": self.model,
                    "messages": chat_messages(payload, names),
                    "tools": tools, "tool_choice": "auto",
                    "temperature": self.temperature, "seed": self.seed,
                    "max_tokens": self.max_tokens, "stream": False}
            chat_bytes = json.dumps(chat, separators=(",", ":")).encode()
            tool_bytes = json.dumps(tools, separators=(",", ":")).encode()
            (self.output / f"{prefix}_forwarded.json").write_bytes(chat_bytes)
            request = urllib.request.Request(self.backend, chat_bytes,
                                             {"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=300) as backend_response:
                raw = json.load(backend_response)
            (self.output / f"{prefix}_raw_model.json").write_text(
                json.dumps(raw, indent=2) + "\n")
            message = raw["choices"][0]["message"]
            content = message.get("content") or ""
            structured_calls = message.get("tool_calls")
            calls = (parse_openai_tool_calls(structured_calls, set(names))
                     if structured_calls is not None else parse_hermes(content, set(names)))
            items = [response_item(call, names) for call in calls]
            if not items:
                items = [{"id": "msg_" + uuid.uuid4().hex, "type": "message",
                          "status": "completed", "role": "assistant",
                          "content": [{"type": "output_text", "text": content,
                                       "annotations": []}]}]
            meta = {"source_tool_count": len(payload.get("tools", [])),
                    "forwarded_function_count": len(tools),
                    "forwarded_tool_block_bytes": len(tool_bytes),
                    "source_tool_block_bytes": len(json.dumps(
                        payload.get("tools", []), separators=(",", ":")).encode()),
                    "allowed_namespaces": sorted(self.allowed),
                    "raw_model_content": content,
                    "raw_model_tool_calls": structured_calls,
                    "parsed_items": items,
                    "backend_usage": raw.get("usage", {})}
            (self.output / f"{prefix}_parsed.json").write_text(
                json.dumps(meta, indent=2) + "\n")
            self.send_events(payload, items, raw.get("usage", {}))
        except Exception as error:
            (self.output / f"{prefix}_error.txt").write_text(repr(error) + "\n")
            body = json.dumps({"error": {"message": str(error),
                                         "type": "stage2b_shim_error"}}).encode()
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    def send_events(self, request: dict, items: list[dict], usage: dict) -> None:
        response_id = "resp_" + uuid.uuid4().hex
        created = int(time.time())
        output = []
        events = []
        base = {"id": response_id, "object": "response", "created_at": created,
                "status": "in_progress", "model": request.get("model"),
                "output": [], "parallel_tool_calls": False,
                "usage": None}
        events.append({"type": "response.created", "response": base.copy()})
        for index, item in enumerate(items):
            added = {**item, "status": "in_progress"}
            if item["type"] == "function_call":
                added["arguments"] = ""
            else:
                added["content"] = []
            events.append({"type": "response.output_item.added",
                           "output_index": index, "item": added})
            if item["type"] == "function_call":
                events.append({"type": "response.function_call_arguments.delta",
                               "item_id": item["id"], "output_index": index,
                               "delta": item["arguments"]})
                events.append({"type": "response.function_call_arguments.done",
                               "item_id": item["id"], "output_index": index,
                               "arguments": item["arguments"]})
            else:
                text = item["content"][0]["text"]
                events.append({"type": "response.content_part.added",
                               "item_id": item["id"], "output_index": index,
                               "content_index": 0,
                               "part": {"type": "output_text", "text": "", "annotations": []}})
                events.append({"type": "response.output_text.delta",
                               "item_id": item["id"], "output_index": index,
                               "content_index": 0, "delta": text})
                events.append({"type": "response.output_text.done",
                               "item_id": item["id"], "output_index": index,
                               "content_index": 0, "text": text})
                events.append({"type": "response.content_part.done",
                               "item_id": item["id"], "output_index": index,
                               "content_index": 0, "part": item["content"][0]})
            events.append({"type": "response.output_item.done", "output_index": index,
                           "item": item})
            output.append(item)
        totals = {"input_tokens": usage.get("prompt_tokens", 0),
                  "output_tokens": usage.get("completion_tokens", 0),
                  "total_tokens": usage.get("total_tokens", 0),
                  "output_tokens_details": {"reasoning_tokens": 0}}
        completed = {**base, "status": "completed", "output": output, "usage": totals}
        events.append({"type": "response.completed", "response": completed})
        for sequence, event in enumerate(events):
            event["sequence_number"] = sequence
        wire = b"".join((f"event: {event['type']}\ndata: " +
                         json.dumps(event, separators=(",", ":")) + "\n\n").encode()
                        for event in events)
        wire += b"data: [DONE]\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Content-Length", str(len(wire)))
        self.end_headers()
        self.wfile.write(wire)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18081)
    parser.add_argument("--backend", default="http://127.0.0.1:18080/v1/chat/completions")
    parser.add_argument("--allow", required=True,
                        help="Comma-separated exact MCP namespace names")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, required=True)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--max-tokens", type=int, default=3072)
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    Handler.output = args.output
    Handler.allowed = set(args.allow.split(","))
    Handler.backend = args.backend
    Handler.seed = args.seed
    Handler.temperature = args.temperature
    Handler.max_tokens = args.max_tokens
    Handler.model = args.model
    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(f"Stage 2b Responses shim listening on 127.0.0.1:{args.port}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
