"""Unscored receipt and contract audit for the sealed Claude Opus cell.

Reads only the Claude JSONL, frozen prompt, and tool artifact existence. No
assay labels, evaluator, floor scores, or scoring code are imported.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def finite(value: object) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(value)


def parse_body(item: dict) -> dict | None:
    content = item.get("content")
    if not isinstance(content, list):
        return None
    for block in content:
        if not isinstance(block, dict) or not isinstance(block.get("text"), str):
            continue
        try:
            value = json.loads(block["text"])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("trace", type=Path)
    cli.add_argument("prompt", type=Path)
    args = cli.parse_args()

    candidates_line = args.prompt.read_text().split("Candidate variants:\n", 1)[1].splitlines()[0]
    candidates = set(candidates_line.split(", "))
    events = [json.loads(line) for line in args.trace.read_text().splitlines()]
    calls: list[dict] = []
    by_use_id: dict[str, dict] = {}
    result_event = None
    for event in events:
        if event.get("type") == "result":
            result_event = event
        message = event.get("message", {})
        content = message.get("content") if isinstance(message, dict) else None
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") == "tool_use":
                call = {"use_id": block.get("id"), "tool": block.get("name"),
                        "args": block.get("input", {}), "body": None}
                calls.append(call)
                by_use_id[call["use_id"]] = call
            elif block.get("type") == "tool_result":
                target = by_use_id.get(block.get("tool_use_id"))
                if target is not None:
                    target["body"] = parse_body(block)
                    target["tool_result_is_error"] = block.get("is_error", False)

    by_receipt: dict[str, dict] = {}
    counts: dict[str, Counter] = defaultdict(Counter)
    forms: dict[str, Counter] = defaultdict(Counter)
    failures: list[dict] = []
    native: list[dict] = []
    for call in calls:
        full_name = call["tool"] or ""
        if not full_name.startswith("mcp__"):
            native.append({"tool": full_name, "args": call["args"]})
        parts = full_name.split("__")
        server = parts[1] if len(parts) >= 3 else "native"
        tool = parts[-1]
        body = call["body"] or {}
        value = body.get("result")
        receipt = body.get("receipt") if isinstance(body.get("receipt"), dict) else {}
        path = receipt.get("artifact_path")
        resolved = bool(receipt.get("call_id") and path and Path(path).is_file())
        usable = bool(value is not None and body.get("error") is None and
                      not call.get("tool_result_is_error") and resolved)
        if tool == "esm2_likelihood":
            usable &= isinstance(value, dict) and finite(value.get("delta_log_probability"))
        if tool == "esm_if":
            usable &= isinstance(value, dict) and finite(value.get("mean_log_likelihood"))
        call["usable"] = usable
        call["receipt_resolves"] = resolved
        if receipt.get("call_id"):
            by_receipt[receipt["call_id"]] = call
        counts[server]["attempted"] += 1
        if usable:
            counts[server]["usable"] += 1
        else:
            failures.append({"server": server, "tool": tool,
                             "variant": call["args"].get("variant"),
                             "error": body.get("error") or "unparsed or unresolved result"})
        if "input_form" in receipt:
            forms[tool][receipt["input_form"]] += 1

    esm2 = [c for c in calls if c["tool"] == "mcp__rescue_predictive__esm2_likelihood"]
    esm_if = [c for c in calls if c["tool"] == "mcp__rescue_generative__esm_if"]
    submissions = [c for c in calls if c["tool"] == "mcp__rescue_record__submit_answer"]
    submission = submissions[0] if submissions else None
    answer = submission["args"].get("answer", {}) if submission else {}
    picks = answer.get("ranked_selection", []) if isinstance(answer, dict) else []
    pick_audit = []
    for pick in picks:
        variant = pick.get("variant")
        linked = [by_receipt.get(value) for value in pick.get("receipts", [])]
        linked = [value for value in linked if value is not None]
        usable_linked = [value for value in linked if value["usable"]]
        specific = [value for value in usable_linked
                    if value["args"].get("variant") == variant]
        pick_audit.append({
            "rank": pick.get("rank"), "variant": variant,
            "cited_receipts": len(pick.get("receipts", [])),
            "resolving_usable_receipts": len(usable_linked),
            "variant_specific_usable_receipts": len(specific),
            "cited_usable_tool_types": sorted({value["tool"].split("__")[-1]
                                               for value in usable_linked}),
            "formal_validation_entries": 0,  # The required validation field is absent.
        })

    selected = answer.get("selected") if isinstance(answer, dict) else None
    rejected = answer.get("rejected") if isinstance(answer, dict) else None
    ranking = answer.get("ranking") if isinstance(answer, dict) else None
    contract_ok = bool(submission and submission["usable"] and
                       submission["args"].get("item_id") == "pilot_item" and
                       isinstance(selected, list) and len(selected) == 10 and
                       isinstance(rejected, list) and isinstance(ranking, list) and
                       len(ranking) == 100 and
                       all(isinstance(row, dict) and "validation" in row for row in selected))
    output = {
        "candidate_count": len(candidates),
        "tool_calls_total": len(calls),
        "by_server": {name: dict(count) for name, count in sorted(counts.items())},
        "esm2": {"attempted": len(esm2),
                 "unique_variants_attempted": len({c["args"].get("variant") for c in esm2} & candidates),
                 "usable": sum(c["usable"] for c in esm2),
                 "unique_variants_usable": len({c["args"].get("variant") for c in esm2 if c["usable"]} & candidates)},
        "esm_if": {"attempted": len(esm_if),
                   "unique_variants_attempted": len({c["args"].get("variant") for c in esm_if} & candidates),
                   "usable": sum(c["usable"] for c in esm_if),
                   "unique_variants_usable": len({c["args"].get("variant") for c in esm_if if c["usable"]} & candidates)},
        "input_forms_by_tool": {name: dict(count) for name, count in sorted(forms.items())},
        "failed_or_unusable": failures,
        "native_invocations": native,
        "submit_answer": {"attempted": len(submissions),
                          "record_accepted": bool(submission and submission["usable"] and
                                                  (submission["body"] or {}).get("result", {}).get("accepted")),
                          "item_id": submission["args"].get("item_id") if submission else None,
                          "answer_keys": sorted(answer) if isinstance(answer, dict) else [],
                          "ten_ranked_selection_entries": len(picks) == 10,
                          "contract_compliant": contract_ok},
        "pick_audit": pick_audit,
        "result": {"duration_ms": result_event.get("duration_ms") if result_event else None,
                   "num_turns": result_event.get("num_turns") if result_event else None,
                   "total_cost_usd": result_event.get("total_cost_usd") if result_event else None,
                   "usage": result_event.get("usage") if result_event else None,
                   "modelUsage": result_event.get("modelUsage") if result_event else None,
                   "subagent_stats": result_event.get("subagent_stats") if result_event else None,
                   "permission_denials": result_event.get("permission_denials") if result_event else None},
    }
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
