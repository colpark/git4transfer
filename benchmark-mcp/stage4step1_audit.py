"""Mechanical, label-free audit of the two sealed matched-control traces."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step1_2026-09-14"
PROMPT = ROOT / "results/benchmark/stage3h_2026-09-14/diagnostic_prompt.txt"
CANDIDATES = set(PROMPT.read_text().split("Candidate variants:\n", 1)[1].splitlines()[0].split(", "))


def body_from_result(result: object) -> dict:
    if not isinstance(result, dict):
        return {}
    if isinstance(result.get("structured_content"), dict):
        return result["structured_content"]
    for block in result.get("content", []):
        if isinstance(block, dict) and isinstance(block.get("text"), str):
            try:
                value = json.loads(block["text"])
            except ValueError:
                continue
            if isinstance(value, dict):
                return value
    return {}


def codex_trace() -> tuple[list[dict], dict]:
    events = [json.loads(x) for x in (OUT / "codex_cell.jsonl").read_text().splitlines()]
    calls = []
    native = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        kind = item.get("type")
        if kind == "mcp_tool_call":
            calls.append({"server": item.get("server", "").removeprefix("rescue_"),
                          "tool": item.get("tool"), "args": item.get("arguments") or {},
                          "body": body_from_result(item.get("result")),
                          "transport_error": item.get("error")})
        elif kind in ("file_change", "image_view", "mcp_resource_call", "command_execution", "web_search"):
            native.append({"type": kind, "arguments": item.get("arguments")})
    usages = [e["usage"] for e in events if e.get("type") == "turn.completed"]
    return calls, {"usage": usages[-1] if usages else {}, "native": native,
                   "turn_completed": bool(usages), "model": "gpt-5.6-sol",
                   "cost": None, "subagents": 0, "permission_denials": None,
                   "responses": sum(e.get("type") == "item.completed" and e.get("item", {}).get("type") == "agent_message" for e in events)}


def claude_trace() -> tuple[list[dict], dict]:
    events = [json.loads(x) for x in (OUT / "claude_cell.jsonl").read_text().splitlines()]
    calls, by_id = [], {}
    for event in events:
        message = event.get("message")
        for block in message.get("content", []) if isinstance(message, dict) else []:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                name = block.get("name", "")
                parts = name.split("__")
                c = {"server": parts[1].removeprefix("rescue_") if len(parts) >= 3 else "native",
                     "tool": parts[-1], "args": block.get("input") or {}, "body": {},
                     "full_tool_name": name, "transport_error": None}
                calls.append(c)
                by_id[block.get("id")] = c
            elif block.get("type") == "tool_result":
                target = by_id.get(block.get("tool_use_id"))
                if target is not None:
                    target["body"] = body_from_result(block)
                    target["transport_error"] = block.get("is_error") or None
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    native = [{"type": c["full_tool_name"], "arguments": c["args"]} for c in calls if c["server"] == "native"]
    return calls, {"usage": result.get("usage", {}), "native": native,
                   "turn_completed": result.get("subtype") == "success", "model": init.get("model"),
                   "cost": result.get("total_cost_usd"), "subagents": (result.get("subagent_stats") or {}).get("spawned"),
                   "permission_denials": result.get("permission_denials"),
                   "duration_ms": result.get("duration_ms"), "num_turns": result.get("num_turns"),
                   "modelUsage": result.get("modelUsage"), "mcp_servers": init.get("mcp_servers"),
                   "model_side_tools": init.get("tools"), "memory_paths": init.get("memory_paths"),
                   "rate_limit_events": [e for e in events if e.get("type") == "rate_limit_event"]}


def audit(kind: str) -> dict:
    calls, meta = codex_trace() if kind == "codex" else claude_trace()
    by_server = defaultdict(Counter)
    by_receipt = {}
    forms = defaultdict(Counter)
    fm = defaultdict(lambda: {"attempted": 0, "usable": 0, "unique_variants_attempted": set(),
                              "unique_variants_usable": set()})
    considered = set()
    for c in calls:
        result = c["body"].get("result") if isinstance(c["body"], dict) else None
        receipt = c["body"].get("receipt", {}) if isinstance(c["body"], dict) else {}
        artifact = Path(receipt.get("artifact_path", "/__missing__")) if isinstance(receipt, dict) else Path("/__missing__")
        resolves = bool(receipt.get("call_id") and artifact.is_file()) if isinstance(receipt, dict) else False
        usable = bool(c["server"] != "native" and resolves and result is not None and
                      c["body"].get("error") is None and c["transport_error"] is None)
        if c["tool"] == "esm2_likelihood":
            usable &= isinstance(result, dict) and isinstance(result.get("delta_log_probability"), (int, float)) and math.isfinite(result["delta_log_probability"])
        if c["tool"] == "esm_if":
            usable &= isinstance(result, dict) and isinstance(result.get("mean_log_likelihood"), (int, float)) and math.isfinite(result["mean_log_likelihood"])
        c["usable"] = usable
        c["receipt"] = receipt
        by_server[c["server"]]["attempted"] += 1
        if usable:
            by_server[c["server"]]["usable"] += 1
        if isinstance(receipt, dict) and receipt.get("call_id"):
            by_receipt[receipt["call_id"]] = c
            if receipt.get("input_form"):
                forms[c["tool"]][receipt["input_form"]] += 1
        variant = c["args"].get("variant")
        if variant in CANDIDATES:
            considered.add(variant)
        if c["tool"] in ("esm2_likelihood", "esm_if"):
            data = fm[c["tool"]]
            data["attempted"] += 1
            data["usable"] += int(usable)
            if variant in CANDIDATES:
                data["unique_variants_attempted"].add(variant)
                if usable:
                    data["unique_variants_usable"].add(variant)
    submissions = [c for c in calls if c["tool"] == "submit_answer" and c["server"] == "record"]
    submission = submissions[0] if submissions else None
    answer = submission["args"].get("answer", {}) if submission else {}
    selected = answer.get("selected") if isinstance(answer, dict) else None
    rejected = answer.get("rejected") if isinstance(answer, dict) else None
    ranking = answer.get("ranking") if isinstance(answer, dict) else None
    if isinstance(ranking, list):
        considered.update(x.get("mutant") for x in ranking if isinstance(x, dict) and x.get("mutant") in CANDIDATES)
    pick_audit = []
    if isinstance(selected, list):
        for pick in selected:
            if not isinstance(pick, dict):
                continue
            mutant = pick.get("mutant")
            refs = [r for r in pick.get("evidence", []) if isinstance(r, str)]
            val = pick.get("validation", [])
            valrefs = [x.get("call_id") for x in val if isinstance(x, dict)] if isinstance(val, list) else []
            linked = [by_receipt[r] for r in refs + valrefs if r in by_receipt]
            specific = [c for c in linked if c["usable"] and c["args"].get("variant") == mutant]
            pick_audit.append({"rank": pick.get("rank"), "mutant": mutant,
                               "validation_categories": sorted({x.get("category") for x in val if isinstance(x, dict) and x.get("category")} ) if isinstance(val, list) else [],
                               "variant_specific_usable_receipts": len({c["receipt"].get("call_id") for c in specific}),
                               "evidence_receipts": len(refs), "validation_receipts": len(valrefs)})
    valid_selected = bool(isinstance(selected, list) and len(selected) == 10 and
                          all(isinstance(x, dict) and x.get("rank") in range(1, 11) and x.get("mutant") in CANDIDATES and
                              isinstance(x.get("basis"), str) and isinstance(x.get("evidence"), list) and
                              isinstance(x.get("validation"), list) and isinstance(x.get("would_overturn"), str)
                              for x in selected) and
                          {x["rank"] for x in selected} == set(range(1, 11)) and
                          len({x["mutant"] for x in selected}) == 10)
    contract = bool(submission and submission["usable"] and
                    submission["args"].get("item_id") == "pilot_item" and
                    valid_selected and isinstance(rejected, list))
    if isinstance(rejected, list):
        considered.update(x.get("mutant") for x in rejected if isinstance(x, dict) and x.get("mutant") in CANDIDATES)
    out = {"kind": kind, "candidate_count": len(CANDIDATES), "meta": meta,
           "by_server": {k: dict(v) for k, v in sorted(by_server.items())},
           "fm": {k: {"attempted": v["attempted"], "usable": v["usable"],
                      "unique_variants_attempted": len(v["unique_variants_attempted"]),
                      "unique_variants_usable": len(v["unique_variants_usable"])} for k, v in fm.items()},
           "input_forms": {k: dict(v) for k, v in forms.items()},
           "submission": {"attempts": len(submissions), "record_accepted": bool(submission and submission["usable"] and
                                                                      (submission["body"].get("result") or {}).get("accepted")),
                          "contract_compliant": contract, "item_id": submission["args"].get("item_id") if submission else None,
                          "selected_count": len(selected) if isinstance(selected, list) else None,
                          "rejected_count": len(rejected) if isinstance(rejected, list) else None,
                          "ranking_count": len(ranking) if isinstance(ranking, list) else None},
           "candidates_considered": len(considered), "pick_audit": pick_audit,
           "native_invocations": meta["native"]}
    return out


def main() -> None:
    expected = PROMPT.read_text()
    codex_events = [json.loads(x) for x in (OUT / "codex_cell.jsonl").read_text().splitlines()]
    thread_id = next(e["thread_id"] for e in codex_events if e.get("type") == "thread.started")
    codex_paths = list((Path.home() / ".codex/sessions").rglob(f"*{thread_id}.jsonl"))
    if len(codex_paths) != 1:
        raise SystemExit("cannot resolve unique Codex model-side session")
    received = {}
    codex_messages = [json.loads(x) for x in codex_paths[0].read_text().splitlines()]
    for event in codex_messages:
        payload = event.get("payload", {})
        if event.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "user":
            content = "".join(block.get("text", "") for block in payload.get("content", []) if isinstance(block, dict))
            if content.startswith("You have a protein and candidate single substitutions."):
                received["codex"] = content
                break
    claude_events = [json.loads(x) for x in (OUT / "claude_cell.jsonl").read_text().splitlines()]
    init = next(e for e in claude_events if e.get("type") == "system" and e.get("subtype") == "init")
    claude_session = init["session_id"]
    claude_path = Path.home() / ".claude/projects/-tmp-b4probe" / f"{claude_session}.jsonl"
    if not claude_path.is_file():
        raise SystemExit("Claude model-side session missing")
    for line in claude_path.read_text().splitlines():
        event = json.loads(line)
        message = event.get("message", {})
        content = message.get("content") if event.get("type") == "user" and isinstance(message, dict) else None
        if isinstance(content, str) and content.startswith("You have a protein and candidate single substitutions."):
            received["claude"] = content
            break
    if set(received) != {"codex", "claude"} or any(value != expected for value in received.values()):
        raise SystemExit("model-side prompt mismatch; matched control invalid")
    for kind, value in received.items():
        (OUT / f"received_prompt_{kind}.txt").write_text(value)
    for kind in ("codex", "claude"):
        if not (OUT / f"{kind}_cell.jsonl").is_file():
            continue
        out = audit(kind)
        (OUT / f"{kind}_audit.json").write_text(json.dumps(out, indent=2) + "\n")
        print(json.dumps({"kind": kind, "by_server": out["by_server"],
                          "fm": out["fm"], "submission": out["submission"],
                          "considered": out["candidates_considered"]}))


if __name__ == "__main__":
    main()
