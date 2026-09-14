"""Summarize completed or safety-stopped Stage 3d artifacts without rerunning work."""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3d_2026-09-13"


def fmt(value, digits=1):
    return "unknown" if value is None else f"{value:.{digits}f}"


def main() -> None:
    controls = json.loads((OUT / "watchdog_controls.json").read_text())
    rows = list(csv.DictReader((OUT / "reachability.csv").open()))
    if len(rows) != 8:
        raise SystemExit("remount ladder incomplete; no completed Stage 3d report")
    envelope = json.loads((OUT / "thermal_envelope.json").read_text())
    samples = [json.loads(line) for line in (OUT / "watchdog_samples.jsonl").open()]
    end = samples[-1]["time_unix"]
    steady = [sample for sample in samples if sample["time_unix"] >= end - 300]
    busy_steady = [sample for sample in steady if sample["gpu_util_pct"] >= 50]
    def median(key):
        return statistics.median(sample[key] for sample in steady) if steady else None
    def cpu(sample):
        return max(sample["cpu_zone0_c"], sample["cpu_zone4_c"])
    peak_cpu = max(cpu(sample) for sample in samples)
    first_failure = next((row["server_count"] for row in rows if row["verdict"] != "PASS"), None)
    ladder_lines = ["| Servers | Added | Forwarded tool bytes | Functions | First prompt | Max prompt | Sum prompt | Min 32K headroom | MCP attempts/successes | Verdict |",
                    "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    enriched = []
    for row in rows:
        first_path = Path(row["shim_meta_path"])
        first_index = int(first_path.name.split("_")[1])
        tokens = []
        for index in (first_index, first_index + 1):
            path = first_path.parent / f"shim_{index:03d}_parsed.json"
            if path.is_file():
                tokens.append(json.loads(path.read_text()).get("backend_usage", {}).get("prompt_tokens", 0))
        max_tokens = max(tokens) if tokens else None
        sum_tokens = sum(tokens) if tokens else None
        enriched.append({**row, "max_prompt_tokens": max_tokens,
                         "sum_prompt_tokens": sum_tokens,
                         "min_context_headroom_tokens": 32768 - max_tokens if max_tokens else None})
        ladder_lines.append(f"| {row['server_count']} | {row['added_server']} | "
            f"{row['forwarded_tool_block_bytes']} | {row['forwarded_function_count']} | "
            f"{row.get('model_prompt_tokens', 'unknown')} | {max_tokens} | {sum_tokens} | "
            f"{32768 - max_tokens if max_tokens else 'unknown'} | "
            f"{row['agent_tool_attempts']}/{row['agent_tool_successes']} | {row['verdict']} |")
    with (OUT / "reachability_context.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(enriched[0]))
        writer.writeheader()
        writer.writerows(enriched)
    (OUT / "reachability.md").write_text("# Stage 3d sequential remount ladder\n\n" +
        "The source tool block includes Codex wrapper definitions; the forwarded block is the "
        "actual function set sent to the model. First, maximum and summed prompt tokens "
        "include both the call and post-tool model requests; headroom uses the maximum "
        "single request. A no-call outcome is not a success.\n\n" +
        "\n".join(ladder_lines) + "\n\n" +
        ("No server count failed; all eight mounted grants passed the real echo receipt audit.\n"
         if first_failure is None else f"First failure at server count {first_failure}.\n"))
    status = "PASS" if envelope.get("thirty_minute_envelope_pass") else "STOPPED"
    profile = ("# Stage 3d full-grant placement and thermal envelope\n\n"
        f"Status: **{status}**. Stop reason: {envelope.get('stop_reason') or envelope.get('abort') or 'none'}. "
        f"Elapsed {fmt(envelope.get('tool_loop_elapsed_s'), 2)} s; "
        f"{envelope.get('tool_loop_successes', 0)}/{envelope.get('tool_loop_attempts', 0)} "
        "agent echo runs passed.\n\n"
        f"Measured active-agent duty cycle: {fmt(envelope.get('duty_cycle'), 3)} "
        "(sum of agent-run wall times / envelope elapsed, including thermal waits). "
        "This is not model-only GPU duty cycle.\n\n"
        "| Metric | Peak/worst sampled | Last-five-minute median | Gate |\n"
        "|---|---:|---:|---:|\n"
        f"| GPU temperature | {fmt(max(s['gpu_c'] for s in samples))}°C | "
        f"{fmt(median('gpu_c'))}°C | <76°C |\n"
        f"| GPU T.Limit margin | {fmt(min(s['gpu_tlimit_margin_c'] for s in samples))}°C | "
        f"{fmt(median('gpu_tlimit_margin_c'))}°C | >10°C |\n"
        f"| CPU zone maximum | {fmt(peak_cpu)}°C | "
        f"{fmt(statistics.median(cpu(s) for s in steady))}°C | <85°C |\n"
        f"| GPU power draw | {fmt(max(s['gpu_power_w'] for s in samples), 2)} W | "
        f"{fmt(median('gpu_power_w'), 2)} W | <100 W |\n"
        f"| Available shared memory | {fmt(min(s['mem_available_gib'] for s in samples), 3)} GiB | "
        f"{fmt(median('mem_available_gib'), 3)} GiB | ≥20 GiB |\n"
        f"| GPU utilization (reported only) | {fmt(max(s['gpu_util_pct'] for s in samples), 0)}% | "
        f"{fmt(median('gpu_util_pct'), 0)}% | none |\n\n"
        "Raw timestamped samples are in `watchdog_samples.jsonl`. The latest five minutes "
        "describe this observed workload only; no temperature is extrapolated beyond it. "
        f"Within the same window, {len(busy_steady)} samples had GPU utilization ≥50%; "
        f"their median GPU temperature was {fmt(statistics.median(s['gpu_c'] for s in busy_steady) if busy_steady else None)}°C, "
        f"CPU-zone maximum {fmt(statistics.median(cpu(s) for s in busy_steady) if busy_steady else None)}°C, "
        f"and GPU power {fmt(statistics.median(s['gpu_power_w'] for s in busy_steady) if busy_steady else None, 2)} W.\n")
    (OUT / "placement.md").write_text(profile)
    floor_progress = OUT / "floor_m_mcp_progress.jsonl"
    completed = sum(1 for _ in floor_progress.open()) if floor_progress.exists() else 0
    finding = ("# Stage 3d finding\n\n"
        f"The panel-amended watchdog controls {'passed' if controls['all_pass'] else 'FAILED'} "
        "before inference, including the 10°C margin boundary and 100% utilization non-gate. "
        f"The remount ladder passed {sum(r['verdict'] == 'PASS' for r in rows)}/8 steps; "
        f"{'no server count failed' if first_failure is None else 'first failure was count ' + first_failure}. "
        f"The 30-minute full-grant envelope **{status}** after "
        f"{fmt(envelope.get('tool_loop_elapsed_s'), 1)} s; "
        f"stop reason: {envelope.get('stop_reason') or envelope.get('abort') or 'none'}. "
        f"Its observed active-agent duty cycle was {fmt(envelope.get('duty_cycle'), 3)}.\n\n"
        f"Parallel Track A has {completed}/29,336 certified MCP score calls checkpointed and "
        "is **in progress**, not an evaluated Floor M. The released-score Floor M remains frozen. "
        "Parallel Track B's W2 ddG substitution request is ready for panel ruling; W2 did not run.\n\n"
        + ("Stage 4 pilot gate is open to selection; the pilot is not itself a full-run authorization.\n"
           if status == "PASS" else "Stage 4 pilot remains closed after the safety stop.\n"))
    (OUT / "finding.md").write_text(finding)
    print(json.dumps({"remount_passes": sum(r["verdict"] == "PASS" for r in rows),
                      "envelope_status": status, "floor_m_calls_checkpointed": completed}))


if __name__ == "__main__":
    main()
