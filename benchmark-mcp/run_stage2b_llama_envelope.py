"""Final serving-layer thermal envelope under the exact full-remount request."""

from __future__ import annotations

import argparse
import csv
import json
import threading
import time
import urllib.request
from pathlib import Path

from run_stage2b_envelope import OUT, remote, sample

REQUEST = OUT / "shim_remount/shim_013_forwarded.json"
URL = "http://127.0.0.1:18080/v1/chat/completions"


def server_pid() -> int:
    lines = remote("ps -eo pid,args").splitlines()
    matches = [line for line in lines if
               "/home/aid1/stage2b_llama.cpp/build/bin/llama-server -m " in line
               and "--port 18080" in line and "--no-webui" in line]
    if len(matches) != 1:
        raise RuntimeError(f"expected exactly one Stage 2b llama-server, found {len(matches)}")
    return int(matches[0].strip().split()[0])


def generate_loop(stop: threading.Event, state: dict) -> None:
    body = REQUEST.read_bytes()
    while not stop.is_set():
        request = urllib.request.Request(URL, body, {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                result = json.load(response)
            state["requests"] += 1
            state["eval_tokens"] += int(result.get("usage", {}).get("completion_tokens", 0))
            if not result.get("choices"):
                state["errors"].append("no choices in backend response")
                stop.set()
        except Exception as error:
            state["errors"].append(str(error))
            stop.set()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minutes", type=float, required=True)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not REQUEST.is_file():
        raise SystemExit("full-remount request missing")
    pid = server_pid()
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
                remote(f"kill -TERM {pid}")
                break
            time.sleep(5)
    except Exception as error:
        abort_reason = f"monitor failed: {error}"
        stop.set()
        remote(f"kill -TERM {pid}")
    stop.set()
    worker.join(timeout=15)
    elapsed = round(time.monotonic() - start, 2)
    if state["errors"] and not abort_reason:
        abort_reason = "; ".join(state["errors"])
    csv_path = OUT / f"{args.name}_samples.csv"
    with csv_path.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    summary = {"model": "Qwen2.5-7B-Instruct Q4_K_M",
               "server": "llama.cpp 4a899373", "model_host": "192.168.100.11",
               "agent_host": "192.168.100.10", "context": 32768,
               "gpu_layers": 8, "cpu_threads": 2,
               "workload": str(REQUEST), "requested_minutes": args.minutes,
               "elapsed_s": elapsed, "requests": state["requests"],
               "eval_tokens": state["eval_tokens"], "errors": state["errors"],
               "abort_reason": abort_reason,
               "completed": abort_reason is None and elapsed >= args.minutes * 60,
               "max_gpu_util_pct": max(row["gpu_util_pct"] for row in rows),
               "max_gpu_c": max(row["gpu_c"] for row in rows),
               "max_cpu_c": max(max(row["cpu_zone0_c"], row["cpu_zone4_c"])
                                for row in rows),
               "min_mem_available_gib": min(row["mem_available_gib"] for row in rows),
               "samples_csv": str(csv_path)}
    (OUT / f"{args.name}.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    if abort_reason:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
