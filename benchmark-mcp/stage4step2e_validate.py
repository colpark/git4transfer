"""Fail-closed, label-free post-run validator for prospective B4 v3."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from stage4step2e_contract import (ContractError, load_contract, validate_answer,
                                   validate_artifact)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2e_2026-09-14"
ALLOWED = {("b4v3_record", "submit_answer"),
           ("b4v3_classical", "score_variant_classical"),
           ("b4v3_fm", "score_variant_fm"),
           ("b4v3_structure", "structure_context")}
SAFE_ITEM_TYPES = {"agent_message", "reasoning", "mcp_tool_call"}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def audit_trace_pairs(events: list[dict]) -> dict:
    started: dict[str, dict] = {}
    completed: dict[str, dict] = {}
    for event in events:
        if event.get("type") not in {"item.started", "item.completed"}:
            continue
        item = event.get("item") or {}
        kind, item_id = item.get("type"), item.get("id")
        if kind not in SAFE_ITEM_TYPES or not isinstance(item_id, str):
            raise ContractError(f"forbidden or malformed trace item: {kind!r}")
        if kind != "mcp_tool_call":
            continue
        key = (item.get("server"), item.get("tool"))
        if key not in ALLOWED:
            raise ContractError(f"MCP pair outside allowlist: {key}")
        target = started if event["type"] == "item.started" else completed
        if item_id in target:
            raise ContractError(f"duplicate {event['type']} id: {item_id}")
        target[item_id] = item
    if set(started) != set(completed):
        raise ContractError(f"unmatched MCP events: started_only={sorted(set(started)-set(completed))}, "
                            f"completed_only={sorted(set(completed)-set(started))}")
    for item_id in started:
        before, after = started[item_id], completed[item_id]
        for field in ("server", "tool", "arguments"):
            if before.get(field) != after.get(field):
                raise ContractError(f"MCP {field} changed across start/completion: {item_id}")
    submissions = [x for x in completed.values() if x.get("tool") == "submit_answer"]
    if len(submissions) != 1:
        raise ContractError("trace must contain exactly one completed submit_answer call")
    return {"started": started, "completed": completed, "submission": submissions[0]}


def result_receipt(item: dict) -> dict | None:
    result = item.get("result") or {}
    try:
        body = result.get("structured_content") or json.loads(result["content"][0]["text"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return body.get("receipt")


def rollout_path(thread_id: str) -> Path:
    found = list((Path.home() / ".codex/sessions").rglob(f"*{thread_id}.jsonl"))
    if len(found) != 1:
        raise ContractError(f"expected one rollout for {thread_id}, found {len(found)}")
    return found[0]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()
    run, contract_path = Path(args.run).resolve(), Path(args.contract).resolve()
    if (run / "mechanical_integrity.json").exists():
        raise SystemExit("refusing to replace mechanical decision")
    contract = load_contract(contract_path)
    launch = json.loads((run / "launch.json").read_text())
    prompt_path = Path(launch["prompt_path"])
    if sha(prompt_path) != launch["prompt_sha256"]:
        raise SystemExit("launch prompt changed")
    events = [json.loads(x) for x in (run / "trace.jsonl").read_text().splitlines() if x.strip()]
    try:
        paired = audit_trace_pairs(events)
    except ContractError as exc:
        raise SystemExit(str(exc)) from exc
    thread_ids = {e.get("thread_id") for e in events if e.get("type") == "thread.started"}
    if len(thread_ids) != 1:
        raise SystemExit("trace lacks one thread id")
    thread_id = next(iter(thread_ids))
    rollout_file = rollout_path(thread_id)
    rollout = [json.loads(x) for x in rollout_file.read_text().splitlines() if x.strip()]
    session = next(e["payload"] for e in rollout if e.get("type") == "session_meta")
    world = next(e["payload"]["state"] for e in rollout if e.get("type") == "world_state")
    turn = next(e["payload"] for e in rollout if e.get("type") == "turn_context")
    users, developers = [], []
    for event in rollout:
        payload = event.get("payload") or {}
        if (event.get("type") == "response_item" and payload.get("type") == "message"
                and payload.get("role") in {"user", "developer"}):
            text = "".join(x.get("text", "") for x in payload.get("content", []) if isinstance(x, dict))
            (users if payload["role"] == "user" else developers).append(text)
    if not users or users[-1] != prompt_path.read_text():
        raise SystemExit("received prompt is not byte-identical")
    requirements = json.loads((OUT / "release_requirements.json").read_text())
    stable = requirements["expected_stable_context"]
    base = (session.get("base_instructions") or {}).get("text", "")
    observed = {"base_instructions_sha256": hashlib.sha256(base.encode()).hexdigest(),
        "developer_message_sha256": [hashlib.sha256(x.encode()).hexdigest() for x in developers],
        "cli_version": session.get("cli_version"), "approval_policy": turn.get("approval_policy"),
        "sandbox_type": (turn.get("sandbox_policy") or {}).get("type")}
    if observed != stable:
        raise SystemExit("stable received context differs from prospective gate")
    expected_model = requirements.get("immutable_model_id")
    if expected_model:
        if world.get("model") != expected_model:
            raise SystemExit("immutable model identity mismatch")
    elif requirements.get("moving_alias_panel_waiver") is not True:
        raise SystemExit("no immutable model identity or panel waiver")
    if world.get("apps_instructions") is not False or (world.get("orchestrator_skills") or {}).get("enabled") is not False:
        raise SystemExit("apps or orchestrator skills unexpectedly enabled")
    submission_file = run / "submissions" / f"{contract['neutral_item_id']}.json"
    if not submission_file.is_file() or paired["submission"].get("status") != "completed":
        raise SystemExit("record server did not accept exactly one submission")
    submission = json.loads(submission_file.read_text())
    verdict = validate_answer(submission.get("answer"), contract, run / "artifacts")
    if verdict != submission.get("validation"):
        raise SystemExit("stored answer verdict is not reproducible")
    artifacts, artifact_receipts = [], {}
    for path in sorted((run / "artifacts").glob("*/*.json")):
        body = json.loads(path.read_text())
        try:
            success = validate_artifact(body, path, contract, require_success=False)
        except ContractError as exc:
            raise SystemExit(str(exc)) from exc
        receipt = body["receipt"]
        artifact_receipts[receipt["call_id"]] = receipt
        artifacts.append({"call_id": receipt["call_id"], "successful": success,
                          "path": str(path), "sha256": sha(path)})
    completed_science = {k: v for k, v in paired["completed"].items() if v.get("tool") != "submit_answer"}
    trace_receipts = {result_receipt(v).get("call_id"): result_receipt(v)
                      for v in completed_science.values() if isinstance(result_receipt(v), dict)}
    if len(trace_receipts) != len(completed_science) or trace_receipts != artifact_receipts:
        raise SystemExit("trace and artifact receipt sets/bodies differ")
    manifest = {"thread_id": thread_id, "trace_sha256": sha(run / "trace.jsonl"),
                "rollout_sha256": sha(rollout_file), "submission_sha256": sha(submission_file),
                "start_completion_pairs": len(paired["started"]), "unmatched_starts": 0,
                "unmatched_completions": 0, "stable_context": observed, "artifacts": artifacts}
    (run / "receipt_manifest.json").write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    result = {"structural_and_receipt_integrity_passed": True,
              "broad_integrity_passed": False, "human_content_audit_required": True,
              "labels_opened": False, "evaluation_authorized": False,
              "contract_sha256": verdict["contract_sha256"],
              "receipt_manifest_sha256": sha(run / "receipt_manifest.json")}
    (run / "mechanical_integrity.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
