"""One unscored Stage 3f pilot cell with a throughput-validity gate."""

from __future__ import annotations

import json
import statistics
import subprocess
import threading
import time
import urllib.request
from collections import Counter
from pathlib import Path

import pilot_run
import stage3d_runtime as host

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3f_2026-09-14"
PILOT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SHIM = ROOT / "benchmark-mcp/pilot_responses_shim.py"
PROMPT = "Continue this integer sequence, one number per line, starting with 1. Keep counting until stopped."
BASELINE_MAX_TOKENS = 128
FRACTION = 0.70
WINDOW_S = 60


def request_baseline() -> dict:
    payload = {"model": "qwen2.5-7b-instruct-q4_k_m", "messages": [{"role": "user", "content": PROMPT}],
               "temperature": 0, "max_tokens": BASELINE_MAX_TOKENS, "stream": False}
    body = json.dumps(payload).encode()
    request = urllib.request.Request("http://127.0.0.1:18080/v1/chat/completions", body,
                                     {"Content-Type": "application/json"})
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=180) as response:
        raw = json.load(response)
    wall = time.monotonic() - start
    generated = int(raw["usage"]["completion_tokens"])
    timings = raw.get("timings", {})
    generation_ms = timings.get("predicted_ms")
    generation_s = generation_ms / 1000 if isinstance(generation_ms, (int, float)) and generation_ms > 0 else wall
    return {"prompt_tokens": raw["usage"]["prompt_tokens"], "generation_tokens": generated,
            "response_wall_s": wall, "generation_s": generation_s,
            "generation_tps": generated / generation_s, "timing_source": "llama.cpp predicted_ms" if generation_ms else "wall",
            "timings": timings}


def classify_tps(tps: float, baseline: float, elapsed_s: float) -> bool | None:
    if elapsed_s < WINDOW_S:
        return None
    return tps < FRACTION * baseline


def model_responses(shim_dir: Path) -> list[dict]:
    rows = []
    for parsed in sorted(shim_dir.glob("shim_*_parsed.json")):
        stem = parsed.name.removesuffix("_parsed.json")
        forwarded = shim_dir / (stem + "_forwarded.json")
        raw_path = shim_dir / (stem + "_raw_model.json")
        if not forwarded.is_file() or not raw_path.is_file():
            continue
        raw = json.loads(raw_path.read_text())
        usage = raw.get("usage", {})
        timings = raw.get("timings", {})
        wall_s = max(raw_path.stat().st_mtime - forwarded.stat().st_mtime, 0.001)
        generated = int(usage.get("completion_tokens", 0))
        generation_ms = timings.get("predicted_ms")
        generation_s = generation_ms / 1000 if isinstance(generation_ms, (int, float)) and generation_ms > 0 else wall_s
        rows.append({"response": stem, "prompt_tokens": usage.get("prompt_tokens", 0),
                     "generation_tokens": generated, "backend_wall_s": wall_s,
                     "generation_s": generation_s, "generation_tps": generated / generation_s,
                     "timing_source": "llama.cpp predicted_ms" if generation_ms else "wall"})
    return rows


def inspect_trace(path: Path) -> dict:
    calls = Counter()
    successes = Counter()
    failed = Counter()
    receipts = set()
    if not path.is_file():
        return {"attempted": {}, "succeeded": {}, "failed": {}, "receipt_ids": []}
    for line in path.read_text().splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item", {})
        if item.get("type") != "mcp_tool_call":
            continue
        server = item.get("server", "unknown").removeprefix("rescue_")
        if event.get("type") == "item.started":
            calls[server] += 1
        if event.get("type") == "item.completed":
            body = item.get("result") or {}
            structured = body.get("structured_content")
            if not structured:
                try:
                    structured = json.loads(body.get("content", [])[0].get("text", "{}"))
                except (IndexError, ValueError, AttributeError):
                    structured = {}
            if item.get("error") is None and structured.get("error") is None and structured.get("result") is not None:
                successes[server] += 1
                receipt = structured.get("receipt", {})
                artifact = Path(receipt.get("artifact_path", "/__missing__"))
                if artifact.is_file():
                    saved = json.loads(artifact.read_text())
                    if saved.get("receipt", {}).get("call_id") == receipt.get("call_id"):
                        receipts.add(receipt["call_id"])
            else:
                failed[server] += 1
    return {"attempted": dict(calls), "succeeded": dict(successes), "failed": dict(failed),
            "receipt_ids": sorted(receipts)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "pilot_cell.json").exists():
        raise SystemExit("Stage 3f pilot cell already recorded; refusing a second run")
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("model or shim port already occupied; refusing to reuse")
    cell = next(row for row in json.loads((PILOT / "run_schedule.json").read_text())["runs"]
                if row["item"] == 2 and row["arm"] == "3" and row["mode"] == "guided" and row["sample"] == 1)
    item = next(row for row in json.loads((PILOT / "selection.json").read_text())["items"]
                if row["assay_id"] == cell["assay_id"])
    prompt_file = Path(item["prompt_files"]["3"]["path"])
    if pilot_run.digest(prompt_file) != item["prompt_files"]["3"]["sha256"]:
        raise SystemExit("frozen pilot prompt hash changed")
    run_out = OUT / "pilot_001"
    run_out.mkdir(exist_ok=True)
    host.REMOTE_LOG = "/tmp/stage3f_llama_20260914.log"
    model_pid = None
    tunnel = None
    shim = None
    monitor_stop = threading.Event()
    state = {"abort": None, "active_agent": None, "samples": [], "response_checks": []}
    monitor = None
    try:
        model_pid = host.start_model(99, 128)
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N", "-L",
                                   "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(monitor_stop)
        baselines = [request_baseline() for _ in range(3)]
        baseline = statistics.median(row["generation_tps"] for row in baselines)
        threshold = FRACTION * baseline
        controls = {"synthetic_throttle_aborts": classify_tps(0.69 * baseline, baseline, 60) is True,
                    "synthetic_healthy_passes": classify_tps(0.71 * baseline, baseline, 60) is False,
                    "short_window_unassessed": classify_tps(0.1 * baseline, baseline, 59.9) is None}
        validity = {"prompt": PROMPT, "max_tokens": BASELINE_MAX_TOKENS, "repeats": baselines,
                    "baseline_median_tps": baseline, "abort_below_tps": threshold,
                    "fraction": FRACTION, "window_s": WINDOW_S, "controls": controls}
        (OUT / "validity_baseline.json").write_text(json.dumps(validity, indent=2) + "\n")
        print(json.dumps({"baseline_tps": baseline, "threshold_tps": threshold, "controls": controls}), flush=True)
        if not all(controls.values()):
            raise RuntimeError("validity-gate controls failed")
        shim_dir = run_out / "shim"
        shim_dir.mkdir(exist_ok=True)
        allowed = ",".join("mcp__rescue_" + name for name in pilot_run.ALL_SERVERS)
        shim_log = (run_out / "shim_server.log").open("w")
        shim = subprocess.Popen([str(PY), str(SHIM), "--port", "18081", "--allow", allowed,
                                 "--output", str(shim_dir), "--seed", "1", "--temperature", "0.2",
                                 "--max-tokens", "1200"], cwd=ROOT, stdout=shim_log,
                                stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 20
        while not host.port_open(18081) and time.monotonic() < deadline:
            time.sleep(0.2)
        if not host.port_open(18081):
            raise RuntimeError("shim failed to start")
        def watch():
            checked = set()
            while not monitor_stop.wait(2):
                try:
                    sample = host.sample()
                    state["samples"].append(sample)
                    with (run_out / "reported_sensors.jsonl").open("a") as output:
                        output.write(json.dumps(sample) + "\n")
                except Exception as error:
                    state.setdefault("sensor_errors", []).append(str(error))
                for response in model_responses(shim_dir):
                    if response["response"] in checked:
                        continue
                    checked.add(response["response"])
                    breach = classify_tps(response["generation_tps"], baseline, response["generation_s"])
                    state["response_checks"].append({**response, "breach": breach})
                    if breach is True:
                        state["abort"] = "sustained model throughput below 70% baseline"
                        active = state["active_agent"]
                        if active and active.poll() is None:
                            active.terminate()
                        return
        monitor = threading.Thread(target=watch, daemon=True)
        monitor.start()
        started = time.monotonic()
        process = subprocess.Popen(pilot_run.command(cell, run_out), cwd=ROOT, text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        state["active_agent"] = process
        try:
            stdout, stderr = process.communicate(input=prompt_file.read_text(), timeout=900)
            timed_out = False
        except subprocess.TimeoutExpired:
            process.terminate()
            stdout, stderr = process.communicate(timeout=15)
            timed_out = True
        state["active_agent"] = None
        wall_s = time.monotonic() - started
        trace = run_out / "trace.jsonl"
        trace.write_text(stdout)
        (run_out / "stderr.txt").write_text(stderr)
        calls = inspect_trace(trace)
        submission = run_out / "submissions/pilot_item.json"
        answer = json.loads(submission.read_text()).get("answer") if submission.is_file() else None
        claimed = set()
        if isinstance(answer, dict):
            for variant in answer.get("selected", []):
                if isinstance(variant, dict):
                    claimed.update(variant.get("evidence", []))
                    claimed.update(variant.get("validation", []))
        fabricated = sorted(x for x in claimed if x not in calls["receipt_ids"])
        selected = answer.get("selected", []) if isinstance(answer, dict) else []
        depth = [len(set(entry.get("validation", []))) for entry in selected if isinstance(entry, dict)]
        status = ("UNDEMONSTRATED" if timed_out or state["abort"] else
                  "COMPLETED" if process.returncode == 0 and isinstance(answer, dict) else "FAILED")
        rows = model_responses(shim_dir)
        result = {**cell, "status": status, "wall_s": wall_s, "exit_code": process.returncode,
                  "timed_out": timed_out, "stop_reason": state["abort"],
                  "prompt_tokens_total": sum(r["prompt_tokens"] for r in rows),
                  "generation_tokens_total": sum(r["generation_tokens"] for r in rows),
                  "calls": calls, "fabricated_call_ids": fabricated,
                  "fabricated_call_id_rate": len(fabricated) / len(claimed) if claimed else None,
                  "rejected_populated": bool(answer.get("rejected")) if isinstance(answer, dict) else None,
                  "evaluation_depth_per_selection": depth if isinstance(answer, dict) else None,
                  "peak_gpu_c": max((s["gpu_c"] for s in state["samples"]), default=None),
                  "peak_cpu_c": max((max(s["cpu_zone0_c"], s["cpu_zone4_c"]) for s in state["samples"]), default=None),
                  "peak_power_w": max((s["gpu_power_w"] for s in state["samples"]), default=None),
                  "response_throughput": rows, "validity_checks": state["response_checks"],
                  "baseline_tps": baseline, "threshold_tps": threshold, "trace_path": str(trace),
                  "submission_path": str(submission) if submission.is_file() else None}
        (OUT / "pilot_cell.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"status": status, "wall_s": wall_s, "tokens": result["generation_tokens_total"],
                          "calls": calls["attempted"], "stop_reason": state["abort"]}), flush=True)
    finally:
        monitor_stop.set()
        if monitor:
            monitor.join(timeout=10)
        if shim:
            shim.terminate()
            shim.wait(timeout=10)
            shim_log.close()
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if model_pid:
            host.stop_owned(model_pid)


if __name__ == "__main__":
    main()
