"""Label-free audit of the three sealed B4 cells and their tool receipts."""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from pathlib import Path

from stage4step1_audit import body_from_result

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2b_2026-09-14"
STEP1 = ROOT / "results/benchmark/stage4step1_2026-09-14"
SEALED = ("AACC1_PSEAI_Dandage_2018", "ARGR_ECOLI_Tsuboyama_2023_1AOY",
          "ENVZ_ECOLI_Ghose_2023")


def audit_one(assay: str, row: dict) -> dict:
    prompt = (ROOT / row["prompt_path"]).read_text()
    candidates = set(prompt.split("Candidate variants:\n", 1)[1].splitlines()[0].split(", "))
    trace = (STEP1 / "codex_cell.jsonl" if assay.startswith("ARGR_")
             else OUT / "runs" / f"b4_{assay}" / "trace.jsonl")
    events = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    by_server: dict[str, Counter] = defaultdict(Counter)
    fm: dict[str, dict] = defaultdict(lambda: {"attempted": 0, "usable": 0,
                                                "unique_attempted": set(), "unique_usable": set()})
    forms: dict[str, Counter] = defaultdict(Counter)
    native: list[dict] = []
    submissions = []
    for event in events:
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        kind = item.get("type")
        if kind != "mcp_tool_call":
            if kind in ("file_change", "image_view", "mcp_resource_call",
                        "command_execution", "web_search"):
                native.append({"type": kind, "arguments": item.get("arguments")})
            continue
        server = item.get("server", "").removeprefix("rescue_")
        tool = item.get("tool")
        args = item.get("arguments") or {}
        body = body_from_result(item.get("result"))
        result = body.get("result")
        receipt = body.get("receipt") or {}
        artifact = Path(receipt.get("artifact_path", "/__missing__"))
        usable = bool(receipt.get("call_id") and artifact.is_file() and
                      result is not None and body.get("error") is None and item.get("error") is None)
        if tool == "esm2_likelihood":
            usable = (usable and isinstance(result, dict) and
                      isinstance(result.get("delta_log_probability"), (int, float)) and
                      math.isfinite(result["delta_log_probability"]))
        if tool == "esm_if":
            usable = (usable and isinstance(result, dict) and
                      isinstance(result.get("mean_log_likelihood"), (int, float)) and
                      math.isfinite(result["mean_log_likelihood"]))
        by_server[server]["attempted"] += 1
        by_server[server]["usable"] += int(usable)
        if receipt.get("input_form"):
            forms[tool][receipt["input_form"]] += 1
        if tool in ("esm2_likelihood", "esm_if"):
            stat = fm[tool]
            stat["attempted"] += 1
            stat["usable"] += int(usable)
            variant = args.get("variant")
            if variant in candidates:
                stat["unique_attempted"].add(variant)
                if usable:
                    stat["unique_usable"].add(variant)
        if server == "record" and tool == "submit_answer":
            submissions.append({"usable": usable, "accepted": (result or {}).get("accepted")
                                if isinstance(result, dict) else None})
    usages = [event.get("usage", {}) for event in events if event.get("type") == "turn.completed"]
    meta_path = OUT / "runs" / f"b4_{assay}" / "meta.json"
    wall_s = (413.588 if assay.startswith("ARGR_") else json.loads(meta_path.read_text())["wall_s"])
    return {"assay_id": assay, "wall_s": wall_s, "trace_path": str(trace.relative_to(ROOT)),
            "turn_completed": bool(usages), "usage": usages[-1] if usages else None,
            "by_server": {server: dict(counts) for server, counts in sorted(by_server.items())},
            "fm": {tool: {"attempted": stat["attempted"], "usable": stat["usable"],
                           "unique_variants_attempted": len(stat["unique_attempted"]),
                           "unique_variants_usable": len(stat["unique_usable"])}
                   for tool, stat in sorted(fm.items())},
            "input_forms": {tool: dict(counts) for tool, counts in sorted(forms.items())},
            "submissions": submissions, "native_invocations": native,
            "subagents_spawned": 0, "permission_denials": None, "cost_usd": None}


def main() -> None:
    if not all((OUT / "runs" / f"b4_{assay}" / "meta.json").exists()
               for assay in (SEALED[0], SEALED[2])):
        raise SystemExit("both new B4 cells must finish before any per-item trace is read")
    rows = {row["assay_id"]: row for line in (OUT / "sealed_prompt_manifest.jsonl").open()
            if (row := json.loads(line))}
    audits = [audit_one(assay, rows[assay]) for assay in SEALED]
    (OUT / "b4_tool_audit.json").write_text(json.dumps(audits, indent=2) + "\n")
    print(json.dumps({"audited": len(audits), "tool_counts": [x["by_server"] for x in audits]}))


if __name__ == "__main__":
    main()
