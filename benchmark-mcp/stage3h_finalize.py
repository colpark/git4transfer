"""Reconcile completed backend timings with live validity observations, no reruns."""

from __future__ import annotations

import json
import re
from pathlib import Path

from stage3f_pilot_cell import model_responses
from stage3h_validity import response_breach, session_windows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3h_2026-09-14"


def main() -> None:
    audit = []
    for model in ("7b", "30b"):
        for mode in ("unguided", "guided"):
            path = OUT / f"cell_{model}_{mode}/result.json"
            data = json.loads(path.read_text())
            responses = model_responses(path.parent / "shim")
            if sum(row["generation_tokens"] for row in responses) != data["generation_tokens"]:
                raise RuntimeError(f"backend token mismatch: {path}")
            checks = [{**row, "breach": response_breach(row["generation_tokens"],
                       row["generation_s"], data["baseline_tps"])} for row in responses]
            windows = session_windows(responses, data["baseline_tps"])
            breach = any(row["breach"] is True for row in checks) or any(row["breach"] for row in windows)
            live = data.get("live_session_gate", data["session_gate"])
            if data.get("stop_reason") and not breach:
                raise RuntimeError(f"live abort has no reconstructed breach: {path}")
            status = "BREACH" if breach else "PASS" if windows or any(row["breach"] is False for row in checks) else "UNDEMONSTRATED"
            data["live_session_gate"] = live
            data["response_checks"] = checks
            data["session_checks"] = windows
            data["session_gate"] = status
            data["active_generation_s"] = sum(row["generation_s"] for row in responses)
            data["posthoc_only_breach"] = bool(breach and not data.get("stop_reason"))
            named = set(data.get("considered_variants", []))
            for line in (path.parent / "trace.jsonl").read_text().splitlines():
                if not line.startswith("{"):
                    continue
                event = json.loads(line)
                if event.get("type") != "item.started" or event.get("item", {}).get("type") != "mcp_tool_call":
                    continue
                args = event["item"].get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        continue
                for field in ("variant", "mutant", "sequence"):
                    candidate = args.get(field)
                    if isinstance(candidate, str) and re.fullmatch(
                            r"[ACDEFGHIKLMNPQRSTVWY][1-9][0-9]*[ACDEFGHIKLMNPQRSTVWY]", candidate):
                        named.add(candidate)
            data["considered_variants"] = sorted(named)
            data["candidates_considered_lower_bound"] = len(named)
            path.write_text(json.dumps(data, indent=2) + "\n")
            audit.append({"cell": path.parent.name, "live_status": live, "reconciled_status": status,
                          "active_generation_s": data["active_generation_s"],
                          "response_count": len(responses), "posthoc_only_breach": data["posthoc_only_breach"]})
    (OUT / "validity_reconciliation.json").write_text(json.dumps(audit, indent=2) + "\n")
    print(json.dumps(audit))


if __name__ == "__main__":
    main()
