"""Read-only, label-free trace audit for the one Stage 3i-d cell."""

from __future__ import annotations

import json
import re
import shutil
from collections import Counter, defaultdict
from pathlib import Path

from stage3ic_run import PROMPT, ROOT, session_rollout

OUT = ROOT / "results/benchmark/stage3id_2026-09-14"
RUN = OUT / "cell_frontier_run"
NATIVE = ("apply_patch", "view_image", "list_mcp_resource_templates",
          "list_mcp_resources", "read_mcp_resource")


def body_of(item: dict) -> dict:
    result = item.get("result") or {}
    body = result.get("structured_content")
    if isinstance(body, dict):
        return body
    try:
        return json.loads(result["content"][0]["text"])
    except (TypeError, KeyError, IndexError, ValueError):
        return {}


def main() -> None:
    run = json.loads((RUN / "result.json").read_text())
    trace = [json.loads(x) for x in (RUN / "trace.jsonl").read_text().splitlines()
             if x.startswith("{")]
    rollout_path = session_rollout(run["thread_id"])
    if rollout_path is None:
        raise SystemExit("session rollout missing")
    shutil.copy2(rollout_path, RUN / "model_rollout.jsonl")
    rollout = [json.loads(x) for x in rollout_path.read_text().splitlines()]
    started = [e["item"] for e in trace if e.get("type") == "item.started"
               and e.get("item", {}).get("type") == "mcp_tool_call"]
    completed = [e["item"] for e in trace if e.get("type") == "item.completed"
                 and e.get("item", {}).get("type") == "mcp_tool_call"]
    attempts = Counter(x.get("server") for x in started)
    usable = Counter()
    receipt_variant = {}
    receipt_tool = {}
    receipt_result = {}
    input_forms = defaultdict(Counter)
    errors = Counter()
    for item in completed:
        server = item.get("server")
        body = body_of(item)
        receipt = body.get("receipt") or {}
        call_id = receipt.get("call_id")
        artifact = Path(receipt.get("artifact_path") or "/__missing__")
        if item.get("error") or body.get("error") or body.get("result") is None:
            errors[server] += 1
            continue
        if not call_id or not artifact.is_file():
            errors[server] += 1
            continue
        try:
            saved = json.loads(artifact.read_text())
        except (OSError, ValueError):
            errors[server] += 1
            continue
        if saved.get("receipt", {}).get("call_id") != call_id or saved.get("error"):
            errors[server] += 1
            continue
        usable[server] += 1
        args = saved.get("args") or {}
        variant = args.get("variant")
        if not variant and all(args.get(k) is not None for k in ("wt", "position", "mutant")):
            variant = f"{args['wt']}{args['position']}{args['mutant']}"
        receipt_variant[call_id] = variant
        receipt_tool[call_id] = item.get("tool")
        receipt_result[call_id] = saved.get("result")
        input_forms[item.get("tool")][receipt.get("input_form", "unspecified")] += 1
    fm_tools = {"esm2_likelihood", "esm_if", "esmfold"}
    fm_attempts = [x for x in started if x.get("tool") in fm_tools]
    fm_usable = [x for x in completed if x.get("tool") in fm_tools
                 and (body_of(x).get("receipt") or {}).get("call_id") in receipt_result]
    esm2_usable = [x for x in fm_usable if x.get("tool") == "esm2_likelihood"
                   and isinstance(body_of(x).get("result", {}).get("delta_log_probability"), (int, float))]

    submission_path = RUN / "submissions/pilot_item.json"
    answer = json.loads(submission_path.read_text())["answer"] if submission_path.is_file() else None
    submit_attempts = [x for x in started if x.get("tool") == "submit_answer"]
    candidate_text = PROMPT.read_text().split("Candidate variants:", 1)[1].split("Reference homolog", 1)[0]
    candidates = set(re.findall(r"\b[ACDEFGHIKLMNPQRSTVWY]\d+[ACDEFGHIKLMNPQRSTVWY]\b", candidate_text))
    considered = set()
    for item in started:
        args = item.get("arguments") or {}
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        v = args.get("variant")
        if not v and all(args.get(k) is not None for k in ("wt", "position", "mutant")):
            v = f"{args['wt']}{args['position']}{args['mutant']}"
        if v in candidates:
            considered.add(v)
    picks = []
    if isinstance(answer, dict):
        for section in ("selected", "rejected", "ranking"):
            for entry in answer.get(section, []):
                if isinstance(entry, dict) and entry.get("mutant") in candidates:
                    considered.add(entry["mutant"])
        for pick in answer.get("selected", []):
            val = pick.get("validation") or []
            ids = list(pick.get("evidence") or []) + [x.get("call_id") for x in val if isinstance(x, dict)]
            specific = [cid for cid in ids if receipt_variant.get(cid) == pick.get("mutant")]
            picks.append({"rank": pick.get("rank"), "mutant": pick.get("mutant"),
                          "validation_categories": sorted({x.get("category") for x in val
                                                          if isinstance(x, dict) and x.get("category")}),
                          "variant_specific_receipts": specific,
                          "all_receipts_resolve": all(cid in receipt_result for cid in ids),
                          "evidence_count": len(pick.get("evidence") or []),
                          "validation_count": len(val)})

    responses = []
    native_invocations = []
    for event in rollout:
        payload = event.get("payload") or {}
        if event.get("type") == "token_usage_record":
            usage = payload.get("usage") or {}
            responses.append({"response_id": payload.get("response_id"),
                              "input_tokens": usage.get("input_tokens"),
                              "output_tokens": usage.get("output_tokens"),
                              "reasoning_output_tokens": usage.get("reasoning_output_tokens")})
        if event.get("type") != "response_item":
            continue
        if payload.get("type") == "custom_tool_call" and payload.get("name") == "exec":
            code = payload.get("input") or ""
            for name in NATIVE:
                if re.search(r"\btools\." + re.escape(name) + r"\s*\(", code):
                    native_invocations.append({"tool": name, "arguments_in_exec_source": code})
        elif payload.get("type") in ("custom_tool_call", "function_call") and payload.get("name") in NATIVE:
            native_invocations.append({"tool": payload["name"],
                                       "arguments": payload.get("arguments") or payload.get("input")})

    result = {
        "thread_id": run["thread_id"], "wall_s": run["wall_s"],
        "exit_code": run["exit_code"], "timed_out": run["timed_out"],
        "response_tokens": responses,
        "total_input_tokens": sum(x["input_tokens"] or 0 for x in responses),
        "total_output_tokens": sum(x["output_tokens"] or 0 for x in responses),
        "calls_attempted_by_server": dict(attempts),
        "calls_usable_by_server": dict(usable),
        "completed_error_or_unresolved_by_server": dict(errors),
        "fm_attempted": len(fm_attempts), "fm_usable": len(fm_usable),
        "esm2_usable_variant_scores": len(esm2_usable),
        "input_forms_by_tool": {k: dict(v) for k, v in input_forms.items()},
        "submission": "accepted" if answer is not None else "rejected" if submit_attempts else "absent",
        "submit_attempts": len(submit_attempts),
        "selected_count": len(answer.get("selected", [])) if isinstance(answer, dict) else None,
        "selected_ranks": [x.get("rank") for x in answer.get("selected", [])] if isinstance(answer, dict) else None,
        "rejected_count": len(answer.get("rejected", [])) if isinstance(answer, dict) else None,
        "ranking_count": len(answer.get("ranking", [])) if isinstance(answer, dict) else None,
        "candidates_considered_lower_bound": len(considered),
        "candidate_count": len(candidates), "picks": picks,
        "native_invocations": native_invocations,
        "cost_usd": None,
        "cost_note": "ChatGPT sign-in path did not expose a per-cell dollar charge.",
    }
    (RUN / "analysis.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ("wall_s", "timed_out", "fm_attempted",
                      "fm_usable", "esm2_usable_variant_scores", "submission",
                      "selected_count", "candidates_considered_lower_bound")}, indent=2))


if __name__ == "__main__":
    main()
