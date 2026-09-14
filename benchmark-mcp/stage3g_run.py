"""Stage 3g unscored subject probes; no label or scoring imports."""

from __future__ import annotations

import argparse
import json
import re
import shlex
import statistics
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import pilot_run
import stage3d_runtime as host
from stage3f_pilot_cell import inspect_trace, model_responses, classify_tps

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3g_2026-09-14"
PILOT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
CATALOG = ROOT / "benchmark-mcp/stage3g_model_catalog.json"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SHIM = ROOT / "benchmark-mcp/pilot_responses_shim.py"
ECHO = ROOT / "benchmark-mcp/probe/stage3g_echo_server.py"
FM_ONLY = ROOT / "benchmark-mcp/probe/stage3g_esm2_only_server.py"
MODEL30 = "/home/aid1/models/stage3g/Qwen3-30B-A3B-Q4_K_M.gguf"
MODEL30_BYTES = 18556685824
ECHO_TEXT = "stage3g-metadata-control"
ECHO_PROMPT = ("Call echo_tool once with text stage3g-metadata-control. "
               "Report the returned text and exact receipt call_id.")
FM_PROMPT = ("Call esm2_likelihood once for A1R in sequence ACDEFGHIKLMNPQRSTVWY "
             "(position 1, mutant R). Report its delta_log_probability and exact receipt call_id.")
BASE_PROMPT = "Continue this integer sequence, one number per line, starting with 1. Keep counting until stopped."
WINDOW_S = 60
FRACTION = 0.7


def start_model(model: str) -> int:
    if model == "7b":
        host.REMOTE_LOG = "/tmp/stage3g_qwen7b_20260914.log"
        return host.start_model(99, 128)
    if host.remote("ss -ltn '( sport = :18080 )' | tail -n +2"):
        raise RuntimeError("node 11 model port occupied")
    size = int(host.remote(f"stat -c %s {MODEL30}"))
    if size != MODEL30_BYTES:
        raise RuntimeError(f"Qwen3 30B Q4 checkpoint size {size}, expected {MODEL30_BYTES}")
    args = [host.LLAMA, "-m", MODEL30, "--host", "127.0.0.1", "--port", "18080",
            "--ctx-size", "32768", "--n-gpu-layers", "99", "--threads", "2",
            "--threads-batch", "2", "--batch-size", "128", "--parallel", "1",
            "--jinja", "--no-webui"]
    command = ("nohup " + shlex.join(args) +
               " > /tmp/stage3g_qwen30b_20260914.log 2>&1 < /dev/null & echo $!")
    pid = int(host.remote(command))
    if not owned(pid, model):
        raise RuntimeError("started Qwen3 server PID did not resolve")
    return pid


def owned(pid: int, model: str) -> bool:
    if model == "7b":
        return host.exact_owned_pid(pid)
    command = host.remote(f"ps -p {pid} -o args= || true")
    return host.LLAMA in command and MODEL30 in command and "--port 18080" in command


def stop_model(pid: int, model: str) -> None:
    if owned(pid, model):
        host.remote(f"kill -TERM {pid}")


def baseline(model_name: str) -> dict:
    payload = {"model": model_name, "messages": [{"role": "user", "content": BASE_PROMPT}],
               "temperature": 0, "max_tokens": 128, "stream": False}
    request = urllib.request.Request("http://127.0.0.1:18080/v1/chat/completions",
                                     json.dumps(payload).encode(),
                                     {"Content-Type": "application/json"})
    start = time.monotonic()
    with urllib.request.urlopen(request, timeout=180) as stream:
        raw = json.load(stream)
    wall = time.monotonic() - start
    generated = int(raw["usage"]["completion_tokens"])
    ms = raw.get("timings", {}).get("predicted_ms")
    generation_s = ms / 1000 if isinstance(ms, (int, float)) and ms > 0 else wall
    return {"prompt_tokens": raw["usage"].get("prompt_tokens"),
            "generation_tokens": generated, "generation_s": generation_s,
            "wall_s": wall, "tps": generated / generation_s,
            "timing_source": "llama.cpp predicted_ms" if ms else "response wall"}


def cell_and_prompt(mode: str) -> tuple[dict, str]:
    cell = next(row for row in json.loads((PILOT / "run_schedule.json").read_text())["runs"]
                if row["item"] == 2 and row["arm"] == "3" and row["mode"] == mode and row["sample"] == 1)
    item = next(row for row in json.loads((PILOT / "selection.json").read_text())["items"]
                if row["assay_id"] == cell["assay_id"])
    path = Path(item["prompt_files"]["3"]["path"])
    if pilot_run.digest(path) != item["prompt_files"]["3"]["sha256"]:
        raise RuntimeError("frozen task prompt changed")
    return cell, path.read_text()


def command(phase: str, run_out: Path, model: str) -> tuple[list[str], str, set[str]]:
    slug = "stage2b-qwen7b" if model == "7b" else "stage3g-qwen30b"
    if phase.startswith("cell"):
        cell, prompt = cell_and_prompt("unguided")
        args = pilot_run.command(cell, run_out)
        index = args.index("stage2b-qwen7b")
        args[index] = slug
        args[-1:-1] = ["-c", f'model_catalog_json="{CATALOG}"']
        allowed = {"mcp__rescue_" + name for name in pilot_run.ALL_SERVERS}
        return args, prompt, allowed
    if phase.startswith("echo"):
        prompt, server, script, namespace = ECHO_PROMPT, "stage3g_echo", ECHO, "mcp__stage3g_echo"
    else:
        prompt, server, script, namespace = FM_PROMPT, "stage3g_fm", FM_ONLY, "mcp__stage3g_fm"
    args = ["codex", "exec", "--json", "--ignore-user-config", "--skip-git-repo-check",
            "-m", slug, "-s", "read-only", "-c", 'approval_policy="never"',
            "-c", 'model_provider="stage3g_llama"',
            "-c", 'model_providers.stage3g_llama={name="Stage 3g llama.cpp",'
                  'base_url="http://127.0.0.1:18081/v1",wire_api="responses"}',
            "-c", f'model_catalog_json="{CATALOG}"', "-c", "model_context_window=32768",
            "-c", "model_auto_compact_token_limit=30000",
            "-c", f'mcp_servers.{server}={{command="{PY}",args=["{script}"],'
                  'default_tools_approval_mode="approve",startup_timeout_sec=30,tool_timeout_sec=150}',
            "-"]
    return args, prompt, {namespace}


def inspect_probe(trace: Path, phase: str) -> dict:
    events = [json.loads(line) for line in trace.read_text().splitlines() if line.startswith("{")]
    calls = [e["item"] for e in events if e.get("type") == "item.completed"
             and e.get("item", {}).get("type") == "mcp_tool_call"]
    expected_tool = "echo_tool" if phase.startswith("echo") else "esm2_likelihood"
    genuine = []
    for call in calls:
        if call.get("tool") != expected_tool:
            continue
        try:
            body = json.loads(call["result"]["content"][0]["text"])
            receipt = body["receipt"]
            artifact = Path(receipt["artifact_path"])
            if artifact.is_file() and json.loads(artifact.read_text())["receipt"]["call_id"] == receipt["call_id"]:
                genuine.append({"result": body["result"], "receipt": receipt})
        except (KeyError, IndexError, TypeError, ValueError, OSError):
            pass
    messages = [e["item"].get("text", "") for e in events if e.get("type") == "item.completed"
                and e.get("item", {}).get("type") == "agent_message"]
    cited = set(re.findall(r"call_id:[A-Za-z0-9_-]+", "\n".join(messages)))
    resolved = {row["receipt"]["call_id"] for row in genuine}
    value_ok = (len(genuine) == 1 and genuine[0]["result"] is not None and
                (genuine[0]["result"].get("text") == ECHO_TEXT if phase.startswith("echo")
                 else abs(genuine[0]["result"].get("delta_log_probability", float("inf")) +
                          0.16856098175048828) < 1e-4))
    warnings = [e["item"].get("message", "") for e in events if e.get("item", {}).get("type") == "error"
                and "Model metadata" in e["item"].get("message", "")]
    return {"tool_attempts": len(calls), "genuine_receipts": genuine, "cited_ids": sorted(cited),
            "fabricated_ids": sorted(cited - resolved), "value_ok": value_ok,
            "metadata_warnings": warnings,
            "pass": len(calls) == 1 and value_ok and not (cited - resolved) and not warnings}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("echo7", "cell7", "fm7", "echo30", "cell30"))
    phase = parser.parse_args().phase
    model = "30" if phase.endswith("30") else "7b"
    model_name = "Qwen3-30B-A3B-Q4_K_M" if model == "30" else "qwen2.5-7b-instruct-q4_k_m"
    run_out = OUT / phase
    if (run_out / "result.json").exists():
        raise SystemExit(f"{phase} already recorded; refusing to rerun")
    run_out.mkdir(parents=True, exist_ok=True)
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("local model or shim port occupied")
    args, prompt, allowed = command(phase, run_out, model)
    model_pid = None
    tunnel = None
    shim = None
    monitor = None
    stop = threading.Event()
    state = {"abort": None, "active": None, "sensors": [], "checks": []}
    shim_log = None
    try:
        model_pid = start_model(model)
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N", "-L",
                                   "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(stop, timeout_s=300 if model == "30" else 180)
        placement = {"host": host.HOST, "model": model_name, "checkpoint": MODEL30 if model == "30" else host.MODEL,
                     "quantization": "Q4_K_M", "context": 32768,
                     "before_baseline": host.sample(),
                     "nvidia_memory_csv": host.remote("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits")}
        (run_out / "placement.json").write_text(json.dumps(placement, indent=2) + "\n")
        baselines = [baseline(model_name) for _ in range(3)]
        base_tps = statistics.median(row["tps"] for row in baselines)
        controls = {"synthetic_throttle_aborts": classify_tps(0.69 * base_tps, base_tps, 60) is True,
                    "synthetic_healthy_passes": classify_tps(0.71 * base_tps, base_tps, 60) is False}
        (run_out / "baseline.json").write_text(json.dumps({"repeats": baselines, "median_tps": base_tps,
            "threshold_tps": FRACTION * base_tps, "window_s": WINDOW_S, "controls": controls}, indent=2) + "\n")
        if not all(controls.values()):
            raise RuntimeError("validity controls failed")
        shim_dir = run_out / "shim"
        shim_dir.mkdir(exist_ok=True)
        shim_log = (run_out / "shim_server.log").open("w")
        shim = subprocess.Popen([str(PY), str(SHIM), "--port", "18081", "--allow", ",".join(sorted(allowed)),
                                 "--output", str(shim_dir), "--seed", "1", "--temperature", "0.2",
                                 "--max-tokens", "1200", "--model", model_name],
                                cwd=ROOT, stdout=shim_log, stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 20
        while not host.port_open(18081) and time.monotonic() < deadline:
            time.sleep(0.2)
        if not host.port_open(18081):
            raise RuntimeError("shim failed to start")
        def watch():
            checked = set()
            while not stop.wait(2):
                try:
                    sample = host.sample()
                    state["sensors"].append(sample)
                    with (run_out / "reported_sensors.jsonl").open("a") as output:
                        output.write(json.dumps(sample) + "\n")
                except Exception as error:
                    state.setdefault("sensor_errors", []).append(str(error))
                for response in model_responses(shim_dir):
                    if response["response"] in checked:
                        continue
                    checked.add(response["response"])
                    breach = classify_tps(response["generation_tps"], base_tps, response["generation_s"])
                    state["checks"].append({**response, "breach": breach})
                    if breach is True:
                        state["abort"] = "60-second generation throughput below 70% baseline"
                        active = state["active"]
                        if active and active.poll() is None:
                            active.terminate()
                        return
        monitor = threading.Thread(target=watch, daemon=True)
        monitor.start()
        start = time.monotonic()
        process = subprocess.Popen(args, cwd=ROOT, text=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        state["active"] = process
        try:
            stdout, stderr = process.communicate(input=prompt, timeout=900)
            timed_out = False
        except subprocess.TimeoutExpired:
            process.terminate()
            stdout, stderr = process.communicate(timeout=15)
            timed_out = True
        state["active"] = None
        trace = run_out / "trace.jsonl"
        trace.write_text(stdout)
        (run_out / "stderr.txt").write_text(stderr)
        responses = model_responses(shim_dir)
        cap_exhausted = []
        for raw_path in sorted(shim_dir.glob("shim_*_raw_model.json")):
            raw = json.loads(raw_path.read_text())
            if (raw.get("choices", [{}])[0].get("finish_reason") == "length" and
                    raw.get("usage", {}).get("completion_tokens", 0) >= 1200):
                cap_exhausted.append(raw_path.name)
        result = {"phase": phase, "model": model_name, "wall_s": time.monotonic() - start,
                  "exit_code": process.returncode, "timed_out": timed_out,
                  "stop_reason": state["abort"], "prompt_sha256": pilot_run.hashlib.sha256(prompt.encode()).hexdigest(),
                  "prompt_tokens_total": sum(row["prompt_tokens"] for row in responses),
                  "generation_tokens_total": sum(row["generation_tokens"] for row in responses),
                  "cap_exhausted_responses": cap_exhausted,
                  "model_responses": responses, "validity_checks": state["checks"],
                  "baseline_tps": base_tps, "threshold_tps": FRACTION * base_tps,
                  "sensor_errors": state.get("sensor_errors", []),
                  "peak_gpu_c": max((s["gpu_c"] for s in state["sensors"]), default=None),
                  "peak_cpu_c": max((max(s["cpu_zone0_c"], s["cpu_zone4_c"]) for s in state["sensors"]), default=None),
                  "peak_gpu_power_w": max((s["gpu_power_w"] for s in state["sensors"]), default=None),
                  "peak_gpu_util_pct": max((s["gpu_util_pct"] for s in state["sensors"]), default=None),
                  "min_mem_available_gib": min((s["mem_available_gib"] for s in state["sensors"]), default=None),
                  "trace_path": str(trace)}
        if phase.startswith("cell"):
            calls = inspect_trace(trace)
            submission = run_out / "submissions/pilot_item.json"
            answer = json.loads(submission.read_text()).get("answer") if submission.is_file() else None
            cited = set(re.findall(r"call_id:[A-Za-z0-9_-]+", json.dumps(answer))) if answer else set()
            result.update({"calls": calls, "submission_path": str(submission) if submission.is_file() else None,
                           "submitted": isinstance(answer, dict), "fabricated_ids": sorted(cited - set(calls["receipt_ids"])),
                           "fabricated_id_rate": len(cited - set(calls["receipt_ids"])) / len(cited) if cited else None,
                           "rejected_populated": bool(answer.get("rejected")) if isinstance(answer, dict) else None,
                           "evaluation_depth": [len(set(v.get("category") for v in entry.get("validation", [])
                                  if isinstance(v, dict))) for entry in answer.get("selected", [])
                                  if isinstance(entry, dict)] if isinstance(answer, dict) else None,
                           "answer_contract_status": "COMPLETED" if isinstance(answer, dict) and process.returncode == 0
                                                     else "UNDEMONSTRATED" if timed_out or state["abort"] or cap_exhausted
                                                     else "FAILED"})
        else:
            result["probe"] = inspect_probe(trace, phase)
        (run_out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"phase": phase, "wall_s": round(result["wall_s"], 2),
                          "status": result.get("answer_contract_status", result.get("probe", {}).get("pass")),
                          "calls": result.get("calls", {}).get("attempted", result.get("probe", {}).get("tool_attempts"))}), flush=True)
    finally:
        stop.set()
        if monitor:
            monitor.join(timeout=10)
        if shim:
            shim.terminate()
            shim.wait(timeout=10)
        if shim_log:
            shim_log.close()
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if model_pid:
            stop_model(model_pid, model)


if __name__ == "__main__":
    main()
