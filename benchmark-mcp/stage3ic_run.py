"""Unscored Stage 3i-c remount probes and one frozen frontier item.

This runner never imports labels, evaluators, or scoring code.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3ic_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SERVER = ROOT / "benchmark-mcp/server.py"
RECORD = ROOT / "benchmark-mcp/pilot_record_server.py"
PROMPT = ROOT / "results/benchmark/stage3h_2026-09-14/diagnostic_prompt.txt"
PDB = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures/ARGR_ECOLI.pdb"
PHYSICS_PDB = ROOT / "benchmark-mcp/fixtures/1ubq.pdb"
SEQUENCE = "QEELVKAFKALLKEEKFSSQGEIVAALQEQGFDNINQSKVSRMLTKFGAVRTRNAKMEMVYCLPAELGV"
CAP_ENFORCED = False  # No supported 4096-token response cap on this Codex path.
ORDER = ("record", "classical", "analysis", "predictive", "generative", "physics", "lit")
TOOLS = {
    "record": ("submit_answer", "log_note"),
    "classical": ("mmseqs_search", "blast_search", "blast_msa", "pssm_score",
                  "conservation", "motif_scan", "blosum_score", "hbond_geometry"),
    "analysis": ("seq_identity", "tmalign"),
    "predictive": ("esm2_likelihood", "esmfold"),
    "generative": ("esm_if",),
    "physics": ("dssp", "openmm_snapshot_potential_delta"),
    "lit": ("pubmed_search",),
}
PROBES = {
    "record": ("log_note", {"item_id": "stage3ic_probe", "note": "frontier_remount_ladder"}),
    "classical": ("blosum_score", {"wt": "L", "mutant": "C"}),
    "analysis": ("seq_identity", {"sequence_a": "ACDE", "sequence_b": "ACDE"}),
    "predictive": ("esm2_likelihood", {"sequence": SEQUENCE, "variant": "L27C"}),
    "generative": ("esm_if", {"pdb_path": str(PDB), "chain": "A", "sequence": SEQUENCE}),
    "physics": ("dssp", {"pdb_path": str(PHYSICS_PDB)}),
    "lit": ("pubmed_search", {"term": "Tsuboyama 2023 protein stability", "max_hits": 1}),
}


def mount_config(name: str, run_out: Path) -> str:
    args = ([str(RECORD), "--out", str(run_out), "--presentation", "unguided"]
            if name == "record" else
            [str(SERVER), "--server", name, "--presentation", "unguided"])
    return (f"mcp_servers.rescue_{name}={{command={json.dumps(str(PY))},"
            f"args={json.dumps(args)},enabled_tools={json.dumps(TOOLS[name])},"
            'default_tools_approval_mode="approve",startup_timeout_sec=30,tool_timeout_sec=300}')


def command(mounts: tuple[str, ...], run_out: Path) -> list[str]:
    cmd = ["codex", "exec", "--json", "--ignore-user-config", "--skip-git-repo-check",
           "-m", "gpt-5.6-sol", "-s", "read-only",
           "-c", 'approval_policy="never"', "-c", 'model_reasoning_effort="high"',
           "-c", 'web_search="disabled"', "-c", "tools.view_image=false"]
    for feature in ("shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "apps",
                    "browser_use", "computer_use", "image_generation", "goals", "plugins",
                    "remote_plugin", "code_mode"):
        cmd.extend(("--disable", feature))
    for name in mounts:
        cmd.extend(("-c", mount_config(name, run_out)))
    return cmd + ["-"]


def catalog_probe() -> str:
    return ("First use the code executor to print this exact JSON object from the actual "
            "ALL_TOOLS catalog: "
            "{catalog_bytes:new TextEncoder().encode(JSON.stringify(ALL_TOOLS)).length,"
            "catalog_names:ALL_TOOLS.map(x=>x.name)}. "
            "The printed tool output, not your recollection, is the audit record. ")


def prompt_for(name: str) -> str:
    tool, args = PROBES[name]
    return ("Unscored grant-reachability probe. " + catalog_probe() +
            f"Then call only mcp__rescue_{name}__{tool} once with arguments "
            f"{json.dumps(args, separators=(',', ':'))}. "
            "Read back the result and its real receipt call_id. Do not call submit_answer. "
            "If the call fails, report that; do not fabricate a receipt.")


def session_rollout(thread_id: str) -> Path | None:
    root = Path.home() / ".codex/sessions"
    paths = list(root.rglob(f"*{thread_id}.jsonl"))
    return paths[0] if len(paths) == 1 else None


def model_catalog(thread_id: str) -> dict | None:
    rollout = session_rollout(thread_id)
    if rollout is None:
        return None
    for line in rollout.read_text().splitlines():
        event = json.loads(line)
        if event.get("type") != "response_item":
            continue
        payload = event.get("payload", {})
        if payload.get("type") != "custom_tool_call_output":
            continue
        for block in payload.get("output", []):
            if not isinstance(block, dict):
                continue
            value = block.get("text", "")
            if "catalog_bytes" not in value:
                continue
            try:
                candidate = json.loads(value)
            except ValueError:
                continue
            if isinstance(candidate, dict) and "catalog_names" in candidate:
                return candidate
    return None


def parse_result(trace: str, thread_id: str) -> dict:
    events = [json.loads(line) for line in trace.splitlines() if line.startswith("{")]
    calls = []
    for event in events:
        if event.get("type") not in ("item.started", "item.completed"):
            continue
        item = event.get("item", {})
        if item.get("type") not in ("mcp_tool_call", "command_execution", "file_change",
                                    "web_search", "image_view", "mcp_resource_call"):
            continue
        if event["type"] == "item.completed":
            receipt = None
            if item.get("type") == "mcp_tool_call":
                result = item.get("result") or {}
                try:
                    body = result.get("structured_content") or json.loads(result["content"][0]["text"])
                    receipt = body.get("receipt")
                except (KeyError, IndexError, TypeError, ValueError):
                    pass
            calls.append({"type": item.get("type"), "server": item.get("server"),
                          "tool": item.get("tool"), "arguments": item.get("arguments"),
                          "error": item.get("error"), "receipt": receipt})
    usage = [e.get("usage") for e in events if e.get("type") == "turn.completed"]
    catalog = model_catalog(thread_id)
    if catalog is not None:
        catalog["mcp_function_count"] = sum(
            str(n).startswith("mcp__rescue_") for n in catalog["catalog_names"])
    return {"calls": calls, "usage": usage[-1] if usage else None, "catalog": catalog}


def run(mounts: tuple[str, ...], run_out: Path, prompt: str, timeout_s: int) -> dict:
    if run_out.exists():
        raise SystemExit(f"refusing to overwrite {run_out}")
    run_out.mkdir(parents=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(command(mounts, run_out), input=prompt, text=True,
                              capture_output=True, cwd=ROOT, timeout=timeout_s)
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        proc = exc
        timed_out = True
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    if isinstance(stdout, bytes):
        stdout = stdout.decode(errors="replace")
    if isinstance(stderr, bytes):
        stderr = stderr.decode(errors="replace")
    (run_out / "trace.jsonl").write_text(stdout)
    (run_out / "stderr.txt").write_text(stderr)
    first = next((json.loads(line) for line in stdout.splitlines()
                  if line.startswith("{") and '"thread.started"' in line), {})
    thread_id = first.get("thread_id", "")
    result = {"thread_id": thread_id, "mounts": list(mounts),
              "wall_s": round(time.monotonic() - started, 3),
              "exit_code": None if timed_out else proc.returncode,
              "timed_out": timed_out, **parse_result(stdout, thread_id)}
    (run_out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def ladder() -> None:
    for index, name in enumerate(ORDER, 1):
        mounts = ORDER[:index]
        result = run(mounts, OUT / f"ladder_{index}_{name}", prompt_for(name), 600)
        expected, _ = PROBES[name]
        matching = [call for call in result["calls"]
                    if call["server"] == f"rescue_{name}" and call["tool"] == expected]
        valid = valid_calls(matching)
        print(json.dumps({"server": name, "attempted": len(matching), "valid_receipts": len(valid),
                          "catalog": result["catalog"], "wall_s": result["wall_s"]}), flush=True)
        if len(valid) != 1 or result["catalog"] is None or result["timed_out"]:
            raise SystemExit(f"ladder failed at {name}; no later mount or cell")


def valid_calls(calls: list[dict]) -> list[dict]:
    valid = []
    for call in calls:
        receipt = call.get("receipt") or {}
        artifact = Path(receipt.get("artifact_path", "/__missing__"))
        if not receipt.get("call_id") or not artifact.is_file() or call.get("error") is not None:
            continue
        try:
            body = json.loads(artifact.read_text())
        except (OSError, ValueError):
            continue
        if (body.get("error") is None and body.get("result") is not None
                and body.get("receipt", {}).get("call_id") == receipt["call_id"]):
            valid.append(call)
    return valid


def repair_ladder() -> None:
    """Repeat physics on a valid Stage 2 PDB, then lit, preserving failed first pass."""
    for index, name in ((6, "physics"), (7, "lit")):
        result = run(ORDER[:index], OUT / f"ladder_{index}_{name}_retry",
                     prompt_for(name), 600)
        expected, _ = PROBES[name]
        matching = [call for call in result["calls"]
                    if call["server"] == f"rescue_{name}" and call["tool"] == expected]
        valid = valid_calls(matching)
        print(json.dumps({"server": name, "attempted": len(matching),
                          "valid_results_and_receipts": len(valid),
                          "catalog": result["catalog"], "wall_s": result["wall_s"]}), flush=True)
        if len(valid) != 1 or result["catalog"] is None or result["timed_out"]:
            raise SystemExit(f"repair ladder failed at {name}; no cell")


def cell() -> None:
    if not CAP_ENFORCED:
        raise SystemExit("Stage 3i-c cell withheld: this signed-in Codex CLI has no verified "
                         "4096-token response cap; panel ruling required")
    result = run(ORDER, OUT / "cell_frontier_run", PROMPT.read_text(), 1200)
    print(json.dumps({"thread_id": result["thread_id"], "exit_code": result["exit_code"],
                      "timed_out": result["timed_out"], "wall_s": result["wall_s"],
                      "call_count": len(result["calls"])}), flush=True)


def full_catalog() -> None:
    prompt = (
        "Unscored grant metadata audit. Use the code executor to print one JSON object "
        "computed from ALL_TOOLS. Include catalog_bytes as UTF-8 bytes of "
        "JSON.stringify(ALL_TOOLS), catalog_names as all tool names, and per_server as "
        "an object mapping each of record,classical,analysis,predictive,generative,physics,lit "
        "to {count,bytes}, where count is the number of ALL_TOOLS names beginning with "
        "mcp__rescue_<server>__ and bytes is UTF-8 bytes of JSON.stringify(the filtered "
        "ALL_TOOLS entries). Do not call any MCP tool or report a value from memory."
    )
    result = run(ORDER, OUT / "catalog_full", prompt, 180)
    print(json.dumps({"catalog": result["catalog"], "usage": result["usage"],
                      "thread_id": result["thread_id"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("ladder", "repair_ladder", "catalog_full", "cell"))
    args = parser.parse_args()
    if args.mode == "ladder":
        ladder()
    elif args.mode == "repair_ladder":
        repair_ladder()
    elif args.mode == "catalog_full":
        full_catalog()
    else:
        cell()
