"""Read-only account-plan and Codex rate-window probe via the signed-in app server."""

from __future__ import annotations

import json
import select
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4prep_2026-09-14"


def send(process: subprocess.Popen, message: dict) -> None:
    assert process.stdin is not None
    process.stdin.write(json.dumps(message, separators=(",", ":")) + "\n")
    process.stdin.flush()


def receive_id(process: subprocess.Popen, target: int, timeout: float = 30) -> dict:
    assert process.stdout is not None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        ready, _, _ = select.select([process.stdout], [], [], min(1, deadline - time.monotonic()))
        if not ready:
            continue
        line = process.stdout.readline()
        if not line:
            raise RuntimeError("app-server closed before reply")
        message = json.loads(line)
        if message.get("id") == target:
            return message
    raise TimeoutError(f"app-server did not answer request {target}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(["codex", "app-server", "--stdio"], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               text=True, bufsize=1, cwd=ROOT)
    try:
        send(process, {"method": "initialize", "id": 1, "params": {"clientInfo": {
            "name": "stage4prep_readonly_audit", "title": "Stage 4 Preparation Audit", "version": "1.0"}}})
        initialized = receive_id(process, 1)
        if "error" in initialized:
            raise RuntimeError(initialized["error"])
        send(process, {"method": "initialized", "params": {}})
        methods = ("account/read", "account/rateLimits/read", "account/usage/read")
        results = {}
        for request_id, method in enumerate(methods, 2):
            send(process, {"method": method, "id": request_id, "params": {}})
            response = receive_id(process, request_id)
            results[method] = response.get("result") if "result" in response else {"error": response.get("error")}
        account = results.get("account/read") or {}
        rates = results.get("account/rateLimits/read") or {}
        usage = results.get("account/usage/read") or {}
        safe = {
            "observed_at_utc": datetime.now(timezone.utc).isoformat(),
            "account": {"authMode": account.get("authMode"), "planType": account.get("planType"),
                        "error": account.get("error")},
            "rateLimits": rates.get("rateLimits"),
            "rateLimitsByLimitId": rates.get("rateLimitsByLimitId"),
            "rateLimitReachedType": rates.get("rateLimitReachedType"),
            "rateLimits_error": rates.get("error"),
            "usage_summary": usage.get("summary"),
            "usage_error": usage.get("error"),
        }
        (OUT / "account_limits.json").write_text(json.dumps(safe, indent=2) + "\n")
        print(json.dumps(safe, indent=2))
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


if __name__ == "__main__":
    main()
