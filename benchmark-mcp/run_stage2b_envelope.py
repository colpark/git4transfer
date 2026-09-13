"""Node-11 GPU-placement thermal envelope with an exact-model safety stop."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

MODEL = "qwen2.5-7b-gpu8-32k:stage2b"
HOST = "192.168.100.11"
REMOTE_CLI = "/home/aid1/stage2_ollama/bin/ollama"
OUT = Path(__file__).resolve().parents[1] / "results/benchmark/stage2b_2026-09-12"
OUT.mkdir(parents=True, exist_ok=True)


def remote(command: str) -> str:
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
                             HOST, command], capture_output=True, text=True, timeout=15)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or f"remote exit {result.returncode}")
    return result.stdout.strip()


def sample() -> dict:
    script = ("nvidia-smi --query-gpu=utilization.gpu,temperature.gpu,power.draw "
              "--format=csv,noheader,nounits; "
              "for zone_dir in /sys/class/thermal/thermal_zone0 "
              "/sys/class/thermal/thermal_zone4; do read -r value < \"$zone_dir/temp\"; "
              "printf '%s\\n' \"$value\"; done; "
              "awk '/^MemAvailable:/ {print $2}' /proc/meminfo")
    lines = remote(script).splitlines()
    gpu_util, gpu_c, power_w = (part.strip() for part in lines[0].split(","))
    return {"gpu_util_pct": float(gpu_util), "gpu_c": float(gpu_c),
            "gpu_power_w": float(power_w), "cpu_zone0_c": int(lines[1]) / 1000,
            "cpu_zone4_c": int(lines[2]) / 1000,
            "mem_available_gib": round(int(lines[3]) / 1024**2, 3)}


def generate_loop(stop: threading.Event, state: dict) -> None:
    request_body = json.dumps({"model": MODEL,
                               "prompt": "List distinct integers from 1 to 100, one per line.",
                               "stream": False, "keep_alive": "30m",
                               "options": {"num_predict": 128, "temperature": 0}}).encode()
    while not stop.is_set():
        request = urllib.request.Request(f"http://{HOST}:11434/api/generate",
                                         request_body,
                                         {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.load(response)
            state["requests"] += 1
            state["eval_tokens"] += int(result.get("eval_count", 0))
            if not result.get("done"):
                state["errors"].append("incomplete generate response")
                stop.set()
        except Exception as error:
            state["errors"].append(str(error))
            stop.set()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    initial_placement = remote(f"{REMOTE_CLI} ps")
    if MODEL not in initial_placement or "CPU/GPU" not in initial_placement:
        raise SystemExit("GPU placement not verified; no thermal run")
    stop = threading.Event()
    state = {"requests": 0, "eval_tokens": 0, "errors": []}
    worker = threading.Thread(target=generate_loop, args=(stop, state), daemon=True)
    start = time.monotonic()
    worker.start()
    rows = []
    abort_reason = None
    try:
        while time.monotonic() - start < args.minutes * 60 and not stop.is_set():
            record = sample()
            record["elapsed_s"] = round(time.monotonic() - start, 2)
            record["requests_completed"] = state["requests"]
            rows.append(record)
            print(json.dumps(record), flush=True)
            if record["gpu_util_pct"] > 90:
                abort_reason = "GPU utilization exceeded 90%"
            elif record["gpu_c"] >= 80:
                abort_reason = "GPU reached 80 C"
            elif max(record["cpu_zone0_c"], record["cpu_zone4_c"]) >= 85:
                abort_reason = "CPU thermal zone reached 85 C"
            if abort_reason:
                stop.set()
                remote(f"{REMOTE_CLI} stop {MODEL}")
                break
            time.sleep(5)
    except Exception as error:
        abort_reason = f"monitor failed: {error}"
        stop.set()
        remote(f"{REMOTE_CLI} stop {MODEL}")
    stop.set()
    worker.join(timeout=15)
    elapsed = round(time.monotonic() - start, 2)
    if state["errors"] and not abort_reason:
        abort_reason = "; ".join(state["errors"])
    sample_path = OUT / f"{args.name}_samples.csv"
    with sample_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"model": MODEL, "model_host": HOST, "server": "Ollama 0.24.0",
               "precision": "Q4_K_M", "context": 32768, "gpu_layers": 8,
               "cpu_threads": 2, "placement": initial_placement,
               "requested_minutes": args.minutes, "elapsed_s": elapsed,
               "requests": state["requests"], "eval_tokens": state["eval_tokens"],
               "errors": state["errors"], "abort_reason": abort_reason,
               "completed": abort_reason is None and elapsed >= args.minutes * 60,
               "max_gpu_util_pct": max(row["gpu_util_pct"] for row in rows),
               "max_gpu_c": max(row["gpu_c"] for row in rows),
               "max_cpu_c": max(max(row["cpu_zone0_c"], row["cpu_zone4_c"])
                                for row in rows),
               "min_mem_available_gib": min(row["mem_available_gib"] for row in rows),
               "samples_csv": str(sample_path)}
    (OUT / f"{args.name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    if abort_reason:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
