"""One uncapped, unscored Stage 3i-d frontier-control attempt.

Reuses the accepted Stage 3i-c command, mounts, and frozen Stage 3h item.
No labels, scorer, or evaluator are imported.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

from stage3ic_run import ORDER, OUT as PREVIOUS, PROMPT, ROOT, parse_result, run, session_rollout

OUT = ROOT / "results/benchmark/stage3id_2026-09-14"
FORBIDDEN = ("exec_command", "shell", "web__", "spawn_agent", "apps")
INERT_NATIVE_ADDITION = {"clock__curr_time"}


def interpret_preflight() -> dict:
    """Check the panel's four standing properties using the saved live catalog."""
    previous = json.loads((PREVIOUS / "catalog_full/result.json").read_text())["catalog"]
    result = json.loads((OUT / "preflight_catalog/result.json").read_text())
    catalog = result.get("catalog") or {}
    names = set(catalog.get("catalog_names") or [])
    old_names = set(previous["catalog_names"])
    added = names - old_names
    removed = old_names - names
    old_mcp = {name for name in old_names if name.startswith("mcp__rescue_")}
    live_mcp = {name for name in names if name.startswith("mcp__rescue_")}
    ok = (
        result["exit_code"] == 0
        and not result["timed_out"]
        and live_mcp == old_mcp
        and len(live_mcp) == 18
        and not removed
        and added <= INERT_NATIVE_ADDITION
        and not any(any(fragment in name for fragment in FORBIDDEN) for name in names)
    )
    state = {
        "accepted_3ic_catalog_bytes": previous["catalog_bytes"],
        "live_catalog_bytes": catalog.get("catalog_bytes"),
        "live_mcp_function_count": len(live_mcp),
        "mcp_names_match_3ic": live_mcp == old_mcp,
        "added_native_tools": sorted(added),
        "removed_tools": sorted(removed),
        "preflight_thread_id": result["thread_id"],
        "pass": ok,
    }
    (OUT / "preflight_state.json").write_text(json.dumps(state, indent=2) + "\n")
    print(json.dumps(state), flush=True)
    if not ok:
        raise SystemExit("standing state differs; do not run the cell")
    return state


def preflight() -> None:
    prompt = (
        "Unscored standing-state check. From the actual ALL_TOOLS catalog, "
        "use the code executor to print exactly one JSON object with catalog_bytes "
        "equal to the UTF-8 byte length of JSON.stringify(ALL_TOOLS), and "
        "catalog_names equal to ALL_TOOLS.map(x=>x.name). Do not call an MCP tool."
    )
    run(ORDER, OUT / "preflight_catalog", prompt, 180)
    interpret_preflight()


def cell() -> None:
    state = json.loads((OUT / "preflight_state.json").read_text())
    if not state["pass"]:
        raise SystemExit("preflight did not pass")
    result = run(ORDER, OUT / "cell_frontier_run", PROMPT.read_text(), 1200)
    print(json.dumps({
        "thread_id": result["thread_id"],
        "wall_s": result["wall_s"],
        "exit_code": result["exit_code"],
        "timed_out": result["timed_out"],
        "completed_call_count": len(result["calls"]),
    }), flush=True)


def recover_completed_trace() -> None:
    """Parse already-saved output after a post-run parser error; never invokes Codex."""
    run_out = OUT / "cell_frontier_run"
    trace = (run_out / "trace.jsonl").read_text()
    events = [json.loads(line) for line in trace.splitlines() if line.startswith("{")]
    first = next((e for e in events if e.get("type") == "thread.started"), {})
    thread_id = first.get("thread_id")
    if not thread_id or not any(e.get("type") == "turn.completed" for e in events):
        raise SystemExit("saved cell has no completed turn; cannot recover")
    rollout_path = session_rollout(thread_id)
    if rollout_path is None:
        raise SystemExit("saved cell rollout missing")
    rollout = [json.loads(line) for line in rollout_path.read_text().splitlines()]
    first_ts = datetime.fromisoformat(rollout[0]["timestamp"].replace("Z", "+00:00"))
    last_ts = datetime.fromisoformat(rollout[-1]["timestamp"].replace("Z", "+00:00"))
    result = {"thread_id": thread_id, "mounts": list(ORDER),
              "wall_s": round((last_ts - first_ts).total_seconds(), 3),
              "wall_source": "session first-to-last timestamp; launcher return code lost in post-run parser error",
              "exit_code": None, "turn_completed": True, "timed_out": False,
              "post_run_parser_error": "model_catalog encountered string output block",
              **parse_result(trace, thread_id)}
    (run_out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"thread_id": thread_id, "wall_s": result["wall_s"],
                      "turn_completed": True, "calls": len(result["calls"])}), flush=True)


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("preflight", "interpret", "cell", "recover"):
        raise SystemExit("usage: stage3id_run.py preflight|interpret|cell|recover")
    if sys.argv[1] == "preflight":
        preflight()
    elif sys.argv[1] == "interpret":
        interpret_preflight()
    elif sys.argv[1] == "recover":
        recover_completed_trace()
    else:
        cell()
