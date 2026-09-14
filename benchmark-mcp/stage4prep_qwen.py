"""Sealed-only Qwen prompt-only smokes and one uncapped full-MCP control.

No scorer, evaluator, assay labels, or cohort prompt is imported.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import stage3d_runtime as host
from stage3g_run import CATALOG, MODEL30, baseline, owned, start_model
from stage3h_run import trace_details
from stage3h_validity import FRACTION, controls, response_breach, session_windows
from stage3f_pilot_cell import inspect_trace, model_responses
from stage3ic_run import ORDER, PROMPT, ROOT, mount_config
from stage4prep_promptonly import parse_answer

OUT = ROOT / "results/benchmark/stage4prep_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SHIM = ROOT / "benchmark-mcp/pilot_responses_shim.py"
PROMPT_ONLY_MAX = 16384
FULL_MAX = 32768  # Only the model's 32K context, not a 4,096 response cap.
MODEL_NAME = "Qwen3-30B-A3B-Q4_K_M"
SEALED = "ARGR_ECOLI_Tsuboyama_2023_1AOY"


def source_prompt() -> str:
    manifest = ROOT / "results/benchmark/stage3_2026-09-13/prompt_manifest.jsonl"
    for line in manifest.read_text().splitlines():
        row = json.loads(line)
        if row.get("assay_id") == SEALED:
            return row["prompt"]
    raise RuntimeError("sealed ARGR source prompt absent")


def full_command(run_out: Path) -> list[str]:
    args = ["codex", "exec", "--json", "--ignore-user-config", "--skip-git-repo-check",
            "-m", "stage3g-qwen30b", "-s", "read-only", "-c", 'approval_policy="never"',
            "-c", 'model_provider="stage4prep_llama"',
            "-c", 'model_providers.stage4prep_llama={name="Stage 4 prep llama.cpp",'
                  'base_url="http://127.0.0.1:18081/v1",wire_api="responses"}',
            "-c", f'model_catalog_json="{CATALOG}"',
            "-c", "model_context_window=32768", "-c", "model_auto_compact_token_limit=30000",
            "-c", 'web_search="disabled"']
    for feature in ("shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "apps",
                    "browser_use", "computer_use", "image_generation", "goals", "plugins",
                    "remote_plugin", "code_mode"):
        args.extend(("--disable", feature))
    for server in ORDER:
        args.extend(("-c", mount_config(server, run_out)))
    return args + ["-"]


def send_promptonly(run_out: Path, condition: str) -> dict:
    from stage4prep_promptonly import build_prompt, candidates_from_source_prompt

    source = source_prompt()
    prompt = build_prompt(source, condition == "a")
    frozen_path = OUT / f"promptonly_{SEALED}_{condition}.txt"
    if frozen_path.read_text() != prompt:
        raise RuntimeError("frozen prompt-only prompt changed")
    request = {"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}],
               "temperature": 0.2, "seed": 1, "max_tokens": PROMPT_ONLY_MAX,
               "stream": False}
    if "tools" in request:
        raise RuntimeError("prompt-only request contains tools")
    (run_out / "forwarded_request.json").write_text(json.dumps(request, indent=2) + "\n")
    started = time.monotonic()
    endpoint = urllib.request.Request("http://127.0.0.1:18080/v1/chat/completions",
                                      json.dumps(request).encode(),
                                      {"Content-Type": "application/json"})
    with urllib.request.urlopen(endpoint, timeout=900) as response:
        raw = json.load(response)
    wall_s = time.monotonic() - started
    (run_out / "raw_response.json").write_text(json.dumps(raw, indent=2) + "\n")
    content = raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
    (run_out / "answer.txt").write_text(content)
    try:
        answer = parse_answer(content, candidates_from_source_prompt(source))
        parser_status = "ACCEPTED"
        parser_error = None
        picks = list(answer.selected)
    except ValueError as error:
        parser_status = "REJECTED"
        parser_error = str(error)
        picks = []
    result = {"condition": condition, "item": SEALED, "model": MODEL_NAME,
              "wall_s": round(wall_s, 3), "prompt_tokens": raw.get("usage", {}).get("prompt_tokens"),
              "generation_tokens": raw.get("usage", {}).get("completion_tokens"),
              "finish_reason": raw.get("choices", [{}])[0].get("finish_reason"),
              "tools_field_present": False, "parser_status": parser_status,
              "parser_error": parser_error, "picks": picks}
    (run_out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def run_full(run_out: Path, baseline_tps: float, state: dict, stop: threading.Event) -> dict:
    shim_dir = run_out / "shim"
    shim_dir.mkdir()
    shim_log = (run_out / "shim_server.log").open("w")
    allowed = ",".join("mcp__rescue_" + name for name in ORDER)
    shim = subprocess.Popen([str(PY), str(SHIM), "--port", "18081", "--allow", allowed,
                             "--output", str(shim_dir), "--seed", "1", "--temperature", "0.2",
                             "--max-tokens", str(FULL_MAX), "--model", MODEL_NAME],
                            cwd=ROOT, stdout=shim_log, stderr=subprocess.STDOUT)
    process = None
    monitor = None
    try:
        deadline = time.monotonic() + 20
        while not host.port_open(18081) and time.monotonic() < deadline:
            time.sleep(0.2)
        if not host.port_open(18081):
            raise RuntimeError("response shim failed to start")

        def watch() -> None:
            checked = set()
            while not stop.wait(2):
                try:
                    sensor = host.sample()
                    state["sensors"].append(sensor)
                    with (run_out / "reported_sensors.jsonl").open("a") as handle:
                        handle.write(json.dumps(sensor) + "\n")
                except Exception as error:
                    state.setdefault("sensor_errors", []).append(str(error))
                for response in model_responses(shim_dir):
                    if response["response"] in checked:
                        continue
                    checked.add(response["response"])
                    breach = response_breach(response["generation_tokens"],
                                             response["generation_s"], baseline_tps)
                    state["response_checks"].append({**response, "breach": breach})
                    state["session_checks"] = session_windows(state["response_checks"], baseline_tps)
                    if breach is True or any(row["breach"] for row in state["session_checks"]):
                        state["abort"] = "response" if breach is True else "session"
                        if process is not None and process.poll() is None:
                            process.terminate()
                        return

        monitor = threading.Thread(target=watch, daemon=True)
        monitor.start()
        started = time.monotonic()
        process = subprocess.Popen(full_command(run_out), cwd=ROOT, text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        try:
            stdout, stderr = process.communicate(input=PROMPT.read_text(), timeout=1200)
            timed_out = False
        except subprocess.TimeoutExpired:
            process.terminate()
            stdout, stderr = process.communicate(timeout=15)
            timed_out = True
        (run_out / "trace.jsonl").write_text(stdout)
        (run_out / "stderr.txt").write_text(stderr)
        responses = model_responses(shim_dir)
        calls = inspect_trace(run_out / "trace.jsonl")
        details = trace_details(run_out / "trace.jsonl", run_out)
        result = {"model": MODEL_NAME, "item": SEALED, "mode": "unguided",
                  "wall_s": round(time.monotonic() - started, 3),
                  "prompt_tokens": sum(row["prompt_tokens"] for row in responses),
                  "generation_tokens": sum(row["generation_tokens"] for row in responses),
                  "response_count": len(responses), "response_context_bound": FULL_MAX,
                  "legacy_4096_cap": False, "exit_code": process.returncode,
                  "timed_out": timed_out, "validity_abort": state["abort"],
                  "session_gate": "BREACH" if state["abort"] else "PASS" if state["session_checks"] else "UNDEMONSTRATED",
                  "calls": calls, "response_checks": state["response_checks"],
                  "session_checks": state["session_checks"],
                  "baseline_tps": baseline_tps, "threshold_tps": FRACTION * baseline_tps,
                  "peak_gpu_c": max((row["gpu_c"] for row in state["sensors"]), default=None),
                  "peak_cpu_c": max((max(row["cpu_zone0_c"], row["cpu_zone4_c"])
                                     for row in state["sensors"]), default=None),
                  "peak_gpu_power_w": max((row["gpu_power_w"] for row in state["sensors"]), default=None),
                  "min_mem_available_gib": min((row["mem_available_gib"] for row in state["sensors"]), default=None),
                  "sensor_errors": state.get("sensor_errors", []), **details}
        (run_out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        stop.set()
        if monitor is not None:
            monitor.join(timeout=10)
        shim.terminate()
        shim.wait(timeout=10)
        shim_log.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("promptonly_a", "promptonly_b", "full"))
    mode = parser.parse_args().mode
    run_out = OUT / ("qwen30b_" + mode)
    if run_out.exists():
        raise SystemExit("sealed Qwen run already exists; no retry")
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("model or shim port already occupied")
    run_out.mkdir(parents=True)
    model_pid = None
    tunnel = None
    stop = threading.Event()
    state = {"abort": None, "sensors": [], "response_checks": [], "session_checks": []}
    try:
        model_pid = start_model("30")
        if not owned(model_pid, "30"):
            raise RuntimeError("Qwen model process identity check failed")
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N", "-L",
                                   "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(stop, timeout_s=300)
        placement = {"host": host.HOST, "model": MODEL_NAME, "checkpoint": MODEL30,
                     "quantization": "Q4_K_M", "context": 32768,
                     "initial_sensors": host.sample(),
                     "memory_csv": host.remote("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits")}
        (run_out / "placement.json").write_text(json.dumps(placement, indent=2) + "\n")
        if mode.startswith("promptonly"):
            result = send_promptonly(run_out, mode[-1])
        else:
            repeats = [baseline(MODEL_NAME) for _ in range(3)]
            baseline_tps = statistics.median(row["tps"] for row in repeats)
            checks = controls()
            (run_out / "validity_baseline.json").write_text(json.dumps({
                "repeats": repeats, "median_tps": baseline_tps,
                "threshold_tps": FRACTION * baseline_tps, "window_active_generation_s": 60,
                "controls": checks}, indent=2) + "\n")
            if not all(checks.values()):
                raise RuntimeError("validity must-fail controls did not pass")
            result = run_full(run_out, baseline_tps, state, stop)
        print(json.dumps({"mode": mode, "wall_s": result["wall_s"],
                          "parser_or_submission": result.get("parser_status", result.get("submission")),
                          "validity_gate": result.get("session_gate")}), flush=True)
    finally:
        stop.set()
        if tunnel is not None:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if model_pid is not None and owned(model_pid, "30"):
            host.remote(f"kill -TERM {model_pid}")


if __name__ == "__main__":
    main()
