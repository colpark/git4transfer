"""Stage 3d remount ladder then full-grant sustained tool-call envelope.

The only remotely terminated process is the llama-server PID started here.
Recorded evidence is under results/benchmark/stage3d_2026-09-13/.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import math
import shlex
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters
from stage3d_watchdog import classify, run_controls

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3d_2026-09-13"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "benchmark-mcp/probe"))
from stage3c_audit import audit  # noqa: E402

HOST = "192.168.100.11"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
ECHO = ROOT / "benchmark-mcp/probe/stage3d_echo_server.py"
SERVER = ROOT / "benchmark-mcp/server.py"
SHIM = ROOT / "benchmark-mcp/stage2b_responses_shim.py"
MODEL = "/home/aid1/.ollama/models/blobs/sha256-2bada8a7450677000f678be90653b85d364de7db25eb5ea54136ada5f3933730"
LLAMA = "/home/aid1/stage2b_llama.cpp/build/bin/llama-server"
TEMPLATE = "/home/aid1/stage2b_llama.cpp/models/templates/Qwen-Qwen2.5-7B-Instruct.jinja"
REMOTE_LOG = "/tmp/stage3d_llama_20260913.log"
ORDER = ("record", "classical", "analysis", "predictive", "generative", "physics", "lit")
ECHO_TEXT = "stage3d-parser-control"
PROMPT_SHORT = ("Call echo_tool once with the string stage3d-parser-control. "
                "Report its returned text and exact receipt call_id. Do not invent a receipt.")
SAMPLE_CMD = ("nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,temperature.gpu.tlimit,power.draw "
              "--format=csv,noheader,nounits; "
              "for z in /sys/class/thermal/thermal_zone0 /sys/class/thermal/thermal_zone4; "
              "do read -r v < \"$z/temp\"; printf '%s\\n' \"$v\"; done; "
              "awk '/^MemAvailable:/ {print $2}' /proc/meminfo")


def remote(command: str, timeout: int = 20) -> str:
    process = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                              HOST, command], capture_output=True, text=True, timeout=timeout)
    if process.returncode:
        raise RuntimeError(process.stderr.strip() or f"SSH exit {process.returncode}")
    return process.stdout.strip()


def sample() -> dict:
    lines = remote(SAMPLE_CMD).splitlines()
    gpu, gpu_c, tlimit, power = (part.strip() for part in lines[0].split(","))
    return {"time_unix": time.time(), "gpu_util_pct": float(gpu),
            "gpu_c": float(gpu_c), "gpu_tlimit_margin_c": float(tlimit),
            "gpu_power_w": float(power),
            "cpu_zone0_c": int(lines[1]) / 1000,
            "cpu_zone4_c": int(lines[2]) / 1000,
            "mem_available_gib": round(int(lines[3]) / 1024**2, 3)}


def exact_owned_pid(pid: int) -> bool:
    command = remote(f"ps -p {pid} -o args= || true")
    return LLAMA in command and "--port 18080" in command and MODEL in command


def stop_owned(pid: int) -> None:
    if exact_owned_pid(pid):
        remote(f"kill -TERM {pid}")


def port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def start_model(gpu_layers: int, batch_size: int) -> int:
    if remote("ss -ltn '( sport = :18080 )' | tail -n +2"):
        raise RuntimeError("node 11 port 18080 is already occupied; refusing to replace a server")
    args = [LLAMA, "-m", MODEL, "--host", "127.0.0.1", "--port", "18080",
            "--ctx-size", "32768", "--n-gpu-layers", str(gpu_layers), "--threads", "2",
            "--threads-batch", "2", "--batch-size", str(batch_size), "--parallel", "1",
            "--jinja", "--chat-template-file", TEMPLATE, "--no-webui"]
    command = "nohup " + shlex.join(args) + f" > {shlex.quote(REMOTE_LOG)} 2>&1 < /dev/null & echo $!"
    pid = int(remote(command))
    if not exact_owned_pid(pid):
        raise RuntimeError("started Stage 3d llama-server PID did not resolve to the requested model")
    return pid


def wait_model(stop: threading.Event, timeout_s: int = 180) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline and not stop.is_set():
        try:
            with urllib.request.urlopen("http://127.0.0.1:18080/v1/models", timeout=2):
                return
        except Exception:
            time.sleep(2)
    raise RuntimeError("model did not become ready or safety monitor stopped it")


async def direct_controls() -> dict:
    params = StdioServerParameters(command=str(PY), args=[str(ECHO)], cwd=ROOT)
    async with Client(params, raise_exceptions=True, read_timeout_seconds=30) as client:
        listed = {tool.name for tool in (await client.list_tools()).tools}
        good = await client.call_tool("echo_tool", {"text": ECHO_TEXT})
        bad = await client.call_tool("echo_tool", {"text": ""})
    def body(response):
        return response.structured_content or json.loads(response.content[0].text)
    good, bad = body(good), body(bad)
    receipt = good["receipt"]
    artifact = Path(receipt["artifact_path"])
    forged = receipt["call_id"][:-1] + ("0" if receipt["call_id"][-1] != "0" else "1")
    result = {"tool_listed": "echo_tool" in listed,
              "positive_value": good["result"] == {"text": ECHO_TEXT},
              "positive_receipt_resolves": artifact.is_file() and
              json.loads(artifact.read_text())["receipt"]["call_id"] == receipt["call_id"],
              "negative_input_errors": bad["result"] is None and bool(bad["error"]),
              "forged_id_rejected": forged != receipt["call_id"] and
              not (OUT / "artifacts/probe" / (forged.split(":")[1] + ".json")).exists(),
              "attempted_calls": 2, "successful_calls": 1}
    (OUT / "probe_controls.json").write_text(json.dumps(result, indent=2) + "\n")
    if not all(result[key] for key in ("tool_listed", "positive_value",
                                   "positive_receipt_resolves", "negative_input_errors",
                                   "forged_id_rejected")):
        raise RuntimeError("direct MCP positive/negative/tamper control failed")
    return result


def codex_command(count: int) -> list[str]:
    config = ["codex", "exec", "--json", "--ignore-user-config", "--skip-git-repo-check",
              "-m", "stage2b-qwen7b", "-s", "read-only", "-c", 'approval_policy="never"',
              "-c", 'model_provider="stage3d_llama"',
              "-c", 'model_providers.stage3d_llama={name="Stage 3d llama.cpp",'
              'base_url="http://127.0.0.1:18081/v1",wire_api="responses"}',
              "-c", "model_context_window=32768", "-c", "model_auto_compact_token_limit=30000",
              "-c", f'mcp_servers.stage2b_probe={{command="{PY}",args=["{ECHO}"],'
              'default_tools_approval_mode="approve",startup_timeout_sec=30,tool_timeout_sec=60}']
    for name in ORDER[:count-1]:
        config += ["-c", f'mcp_servers.rescue_{name}={{command="{PY}",'
                   f'args=["{SERVER}","--server","{name}","--presentation","unguided"],'
                   'default_tools_approval_mode="approve",startup_timeout_sec=30,tool_timeout_sec=150}']
    return config + ["-"]


def run_agent(count: int, index: int, shim_dir: Path, gpu_layers: int,
              state: dict, prompt: str, phase: str) -> dict:
    before = set(shim_dir.glob("shim_*_parsed.json"))
    start = time.monotonic()
    label = f"{phase}_count{count}_run{index:04d}"
    process = subprocess.Popen(codex_command(count), cwd=ROOT, text=True,
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    state["active_agent"] = process
    try:
        stdout, stderr = process.communicate(input=prompt, timeout=300)
        interrupted = bool(state["abort"])
        exit_code = process.returncode
    except subprocess.TimeoutExpired:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
        interrupted, exit_code = True, None
    finally:
        state["active_agent"] = None
    trace = OUT / f"{label}_trace.jsonl"
    trace.write_text(stdout)
    (OUT / f"{label}_stderr.txt").write_text(stderr)
    meta_files = sorted(set(shim_dir.glob("shim_*_parsed.json")) - before)
    chosen = next((path for path in meta_files if any(
        item.get("type") == "function_call"
        for item in json.loads(path.read_text()).get("parsed_items", []))), None)
    if chosen is None:
        result = {"agent_tool_attempts": 0, "agent_tool_successes": 0,
                  "verdict": "UNDEMONSTRATED" if interrupted else "FAIL",
                  "source_tool_block_bytes": "", "forwarded_tool_block_bytes": "",
                  "reason": "no parsed tool call", "trace_path": str(trace)}
    else:
        result = audit(trace, chosen, ECHO_TEXT)
        meta = json.loads(chosen.read_text())
        tokens = meta.get("backend_usage", {}).get("prompt_tokens")
        result["model_prompt_tokens"] = tokens
        result["context_headroom_tokens"] = 32768 - tokens if isinstance(tokens, int) else None
        result.pop("raw_model_content", None)
        result.pop("raw_model_tool_calls", None)
        if interrupted:
            result["verdict"] = "UNDEMONSTRATED"
        elif exit_code:
            result["verdict"] = "FAIL"
    return {"model": "Qwen2.5-7B-Instruct Q4_K_M", "quantization": "Q4_K_M",
            "gpu_layers": gpu_layers, "context": 32768, "server_count": count,
            "phase": phase, "prompt_chars": len(prompt),
            "added_server": "probe" if count == 1 else ORDER[count-2],
            "mounted_servers": ",".join(("probe",) + ORDER[:count-1]),
            "elapsed_s": round(time.monotonic() - start, 3), "exit_code": exit_code,
            "interrupted": interrupted, **result}


def write_rows(rows: list[dict], name: str) -> None:
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def w1_length_prompt() -> tuple[str, dict]:
    path = ROOT / "results/benchmark/stage3_2026-09-13/prompt_manifest.jsonl"
    record = json.loads(path.open().readline())
    original = record["prompt"]
    context = original.split("\n\nProtein sequence:\n", 1)[1]
    prompt = (PROMPT_SHORT + "\n\nInert length-matched reference context; do not rank or "
              "score its variants:\nProtein sequence:\n" + context)
    assert len(prompt) >= 1500 and len(prompt) <= len(original) + 300
    return prompt, {"source_assay_id": record["assay_id"],
                    "source_prompt_chars": len(original), "probe_prompt_chars": len(prompt),
                    "source_file": str(path)}


def summarize_samples(samples: list[dict]) -> dict:
    return {"sample_count": len(samples),
            "max_gpu_util_pct": max(row["gpu_util_pct"] for row in samples),
            "max_gpu_c": max(row["gpu_c"] for row in samples),
            "steady_gpu_c_last_5min_median": sorted(row["gpu_c"] for row in samples
                if row["time_unix"] >= samples[-1]["time_unix"] - 300)[
                len([row for row in samples if row["time_unix"] >= samples[-1]["time_unix"] - 300])//2],
            "min_gpu_tlimit_margin_c": min(row["gpu_tlimit_margin_c"] for row in samples),
            "max_gpu_power_w": max(row["gpu_power_w"] for row in samples),
            "max_cpu_c": max(max(row["cpu_zone0_c"], row["cpu_zone4_c"]) for row in samples),
            "min_mem_available_gib": min(row["mem_available_gib"] for row in samples)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, default=30.0)
    parser.add_argument("--gpu-layers", type=int, default=99)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()
    if args.minutes < 30:
        raise SystemExit("the 30-minute tool-call envelope must not be shortened")
    run_controls()
    if port_open(18080) or port_open(18081):
        raise SystemExit("local Stage 3d ports are occupied; refusing to reuse services")
    initial = sample()
    initial_gate = classify(initial)
    if initial_gate:
        raise SystemExit(f"unsafe initial state: {initial_gate}")
    if not 1 <= args.gpu_layers <= 99:
        raise SystemExit("GPU layers must be 1–99; CPU-only fallback is forbidden")
    if not 1 <= args.batch_size <= 128:
        raise SystemExit("batch size must be 1–128")
    long_prompt, long_meta = w1_length_prompt()
    (OUT / "prompt_short.txt").write_text(PROMPT_SHORT + "\n")
    (OUT / "prompt_long.txt").write_text(long_prompt + "\n")
    (OUT / "prompt_length_meta.json").write_text(json.dumps(long_meta, indent=2) + "\n")
    state = {"abort": None, "samples": [], "model_pid": None, "active_agent": None}
    stop = threading.Event()
    shim_dir = OUT / "shim"
    shim_dir.mkdir(exist_ok=True)
    rows, thermal_rows = [], []
    phase = "startup"
    envelope_start_mono = None
    envelope_started_unix = None
    active_s = 0.0
    tunnel = shim = None
    def watch() -> None:
        while not stop.is_set():
            try:
                item = sample()
                state["samples"].append(item)
                with (OUT / "watchdog_samples.jsonl").open("a") as handle:
                    handle.write(json.dumps(item) + "\n")
                state["abort"] = classify(item)
            except Exception as error:
                state["abort"] = f"thermal monitor failed: {error}"
            if state["abort"]:
                if state["active_agent"] and state["active_agent"].poll() is None:
                    state["active_agent"].terminate()
                if state["model_pid"]:
                    try:
                        stop_owned(state["model_pid"])
                    except Exception:
                        pass
                stop.set()
                return
            stop.wait(2)
    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    try:
        state["model_pid"] = start_model(args.gpu_layers, args.batch_size)
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N",
                                   "-L", "18080:127.0.0.1:18080", HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        wait_model(stop)
        allowed = ",".join(["mcp__stage2b_probe"] + [f"mcp__rescue_{s}" for s in ORDER])
        shim_log = (OUT / "shim_server.log").open("w")
        shim = subprocess.Popen([str(PY), str(SHIM), "--port", "18081", "--allow", allowed,
                                 "--output", str(shim_dir)], cwd=ROOT, stdout=shim_log,
                                stderr=subprocess.STDOUT)
        deadline = time.monotonic() + 20
        while not port_open(18081) and time.monotonic() < deadline and not stop.is_set():
            time.sleep(0.2)
        if not port_open(18081):
            raise RuntimeError("Responses shim did not start")
        asyncio.run(direct_controls())
        phase = "remount_ladder"
        for count in range(1, 9):
            if stop.is_set():
                raise RuntimeError(state["abort"] or "safety stop")
            row = run_agent(count, 1, shim_dir, args.gpu_layers, state,
                            PROMPT_SHORT, "remount")
            rows.append(row)
            write_rows(rows, "reachability.csv")
            print(json.dumps({"phase": phase, "server_count": count,
                              "verdict": row["verdict"],
                              "attempts": row["agent_tool_attempts"],
                              "successes": row["agent_tool_successes"],
                              "forwarded_tool_block_bytes": row.get("forwarded_tool_block_bytes"),
                              "forwarded_function_count": row.get("forwarded_function_count"),
                              "model_prompt_tokens": row.get("model_prompt_tokens"),
                              "context_headroom_tokens": row.get("context_headroom_tokens")}),
                  flush=True)
            if row["verdict"] != "PASS":
                raise RuntimeError(f"remount stopped at server count {count}: {row['verdict']}")
        phase = "full_grant_sustained_tool_call_envelope"
        envelope_start_mono = time.monotonic()
        envelope_started_unix = time.time()
        index = 0
        checkpoint_written = False
        while time.monotonic() - envelope_start_mono < args.minutes * 60 and not stop.is_set():
            index += 1
            row = run_agent(8, index, shim_dir, args.gpu_layers, state,
                            long_prompt, "sustained")
            thermal_rows.append(row)
            write_rows(thermal_rows, "thermal_calls.csv")
            active_s += row["elapsed_s"]
            print(json.dumps({"phase": "sustained", "run": index,
                              "elapsed_total_s": round(time.monotonic()-envelope_start_mono, 1),
                              "verdict": row["verdict"]}), flush=True)
            if row["verdict"] != "PASS":
                raise RuntimeError(f"sustained tool-call loop failed: {row['verdict']}")
            if not checkpoint_written and time.monotonic() - envelope_start_mono >= 600:
                checkpoint_written = True
                window = [entry for entry in state["samples"]
                          if entry["time_unix"] >= envelope_started_unix]
                checkpoint = {"phase": "ten_minute_sustained", "elapsed_s":
                              round(time.monotonic()-envelope_start_mono, 2),
                              "attempts": len(thermal_rows),
                              "successes": sum(item["verdict"] == "PASS" for item in thermal_rows),
                              **summarize_samples(window)}
                (OUT / "ten_minute_checkpoint.json").write_text(
                    json.dumps(checkpoint, indent=2) + "\n")
                print(json.dumps(checkpoint), flush=True)
            latest = state["samples"][-1]
            cpu_c = max(latest["cpu_zone0_c"], latest["cpu_zone4_c"])
            delay = 15 if cpu_c >= 83.5 else 5 if cpu_c >= 82 else 0
            if delay:
                stop.wait(delay)
        if stop.is_set():
            raise RuntimeError(state["abort"] or "tool-call loop interrupted")
        elapsed = time.monotonic() - envelope_start_mono
        window = [entry for entry in state["samples"] if entry["time_unix"] >= envelope_started_unix]
        envelope = {"model": "Qwen2.5-7B-Instruct Q4_K_M", "model_host": HOST,
                   "agent_host": "192.168.100.10", "context_configured": 32768,
                   "gpu_layers_requested": args.gpu_layers,
                   "batch_size": args.batch_size, "cpu_threads": 2,
                   "tool_loop_attempts": len(thermal_rows),
                   "tool_loop_successes": sum(r["verdict"] == "PASS" for r in thermal_rows),
                   "tool_loop_elapsed_s": round(elapsed, 2),
                   "tool_loop_active_agent_s": round(active_s, 2),
                   "duty_cycle": round(active_s / elapsed, 4) if elapsed else None,
                   "duty_cycle_definition": "sum of agent-run wall times / envelope elapsed; includes agent and tool overhead",
                   "mounted_server_count": 8,
                   "ten_minute_placement_pass": checkpoint_written and not state["abort"],
                   "thirty_minute_envelope_pass": elapsed >= 1800 and not state["abort"],
                   "abort": state["abort"], **summarize_samples(window)}
        (OUT / "thermal_envelope.json").write_text(json.dumps(envelope, indent=2) + "\n")
        print(json.dumps({"phase": "thermal_envelope", **envelope}), flush=True)
        if not envelope["thirty_minute_envelope_pass"]:
            raise RuntimeError("30-minute tool-call envelope did not complete")
        summary = {**envelope, "remount_passes": sum(
            row["verdict"] == "PASS" for row in rows if row["phase"] == "remount"),
            "remount_attempts": sum(row["phase"] == "remount" for row in rows)}
        (OUT / "runtime_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(json.dumps(summary), flush=True)
    except Exception as error:
        if envelope_start_mono is not None:
            elapsed = time.monotonic() - envelope_start_mono
            window = [entry for entry in state["samples"]
                      if entry["time_unix"] >= envelope_started_unix]
            partial = {"thirty_minute_envelope_pass": False,
                       "mounted_server_count": 8,
                       "stop_reason": state["abort"] or str(error),
                       "tool_loop_elapsed_s": round(elapsed, 2),
                       "tool_loop_active_agent_s": round(active_s, 2),
                       "duty_cycle": round(active_s / elapsed, 4) if elapsed else None,
                       "duty_cycle_definition": "sum of agent-run wall times / envelope elapsed; includes agent and tool overhead",
                       "tool_loop_attempts": len(thermal_rows),
                       "tool_loop_successes": sum(r["verdict"] == "PASS" for r in thermal_rows)}
            if window:
                partial.update(summarize_samples(window))
            (OUT / "thermal_envelope.json").write_text(json.dumps(partial, indent=2) + "\n")
        (OUT / "runtime_error.json").write_text(json.dumps({"error": str(error),
            "phase": phase,
            "abort": state["abort"], "model_pid": state["model_pid"],
            "gpu_layers_requested": args.gpu_layers,
            "batch_size": args.batch_size,
            "reachability_attempts": len(rows), "thermal_attempts": len(thermal_rows)}, indent=2) + "\n")
        print(json.dumps({"error": str(error), "abort": state["abort"]}), flush=True)
        raise
    finally:
        stop.set()
        watcher.join(timeout=10)
        if shim:
            shim.terminate()
            shim.wait(timeout=10)
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if state["model_pid"]:
            stop_owned(state["model_pid"])
        try:
            (OUT / "model_server.log").write_text(remote(f"cat {REMOTE_LOG}", timeout=30))
        except Exception:
            pass


if __name__ == "__main__":
    main()
