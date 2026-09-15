"""One-shot, label-free runners for the ten-item comparison."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import threading
import time
import urllib.request
from pathlib import Path

import stage3d_runtime as host
from stage3g_run import MODEL30, owned, start_model
from stage4step2e_contract import load_contract
from stage4step2e_run import command as b4_command

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
QWEN_MODEL = "Qwen3-30B-A3B-Q4_K_M"
CLAUDE_CWD = Path("/tmp/b1_stage4step3")
DISALLOWED = ("Task,Bash,CronCreate,CronDelete,CronList,DesignSync,Edit,EnterWorktree,"
              "ExitWorktree,ListAgents,Monitor,NotebookEdit,PushNotification,Read,"
              "RemoteTrigger,ReportFindings,ScheduleWakeup,SendMessage,Skill,TaskOutput,"
              "TaskStop,ToolSearch,WebFetch,WebSearch,Workflow,Write,Glob,Grep,"
              "ListMcpResourcesTool,ReadMcpResourceDirTool,ReadMcpResourceTool")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_precall_freeze() -> None:
    freeze = json.loads((OUT / "precall_freeze.json").read_text())
    failures = []
    for record in freeze["files"]:
        path = Path(record["path"])
        if not path.is_file() or sha(path) != record["sha256"]:
            failures.append(str(path))
    if failures:
        raise SystemExit("precall freeze mismatch: " + ", ".join(failures))
    if freeze.get("labels_opened") is not False or freeze.get("model_calls_before_freeze") != 0:
        raise SystemExit("invalid precall freeze state")


def rows() -> list[dict]:
    return [json.loads(line) for line in (OUT / "blind_item_manifest_internal.jsonl").read_text().splitlines()]


def row_for(neutral_id: str) -> dict:
    found = [row for row in rows() if row["neutral_item_id"] == neutral_id]
    if len(found) != 1:
        raise SystemExit("unknown or duplicate neutral item")
    return found[0]


def run_process(run: Path, cmd: list[str], *, prompt: str | None, cwd: Path,
                env: dict[str, str] | None, timeout: int) -> dict:
    if run.exists():
        raise SystemExit(f"refusing to retry {run}")
    run.mkdir(parents=True)
    (run / "launch.json").write_text(json.dumps({"command": cmd, "cwd": str(cwd),
        "prompt_sha256": hashlib.sha256((prompt or "").encode()).hexdigest(),
        "labels_opened": False}, sort_keys=True, indent=2) + "\n")
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True,
                              cwd=cwd, env=env, timeout=timeout)
        stdout, stderr, code, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr, code, timed_out = exc.stdout or "", exc.stderr or "", None, True
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
    (run / "trace.jsonl").write_text(stdout)
    (run / "stderr.txt").write_text(stderr)
    meta = {"wall_s": round(time.monotonic() - started, 3), "exit_code": code,
            "timed_out": timed_out, "model_call_attempted": True, "labels_opened": False}
    (run / "meta.json").write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"run": str(run.relative_to(OUT)), **meta}), flush=True)
    return meta


def claude_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    env["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] = "1"
    return env


def claude_cmd(prompt: str) -> list[str]:
    return ["claude", "-p", prompt, "--model", "claude-opus-5", "--strict-mcp-config",
            "--mcp-config", str(OUT / "empty_mcp.json"), "--disallowedTools", DISALLOWED,
            "--output-format", "stream-json", "--verbose"]


def b1_grant() -> None:
    verify_precall_freeze()
    CLAUDE_CWD.mkdir(parents=True, exist_ok=True)
    prompt = "Reply with the single word: ok"
    run_process(OUT / "runs/b1_grant", claude_cmd(prompt), prompt=None,
                cwd=CLAUDE_CWD, env=claude_env(), timeout=300)


def b1_cell(neutral_id: str) -> None:
    verify_precall_freeze()
    row = row_for(neutral_id)
    prompt = (ROOT / row["prompt_only_path"]).read_text()
    run_process(OUT / f"runs/b1/{neutral_id}", claude_cmd(prompt), prompt=None,
                cwd=CLAUDE_CWD, env=claude_env(), timeout=2400)


def qwen_request(payload: dict, timeout: int) -> dict:
    req = urllib.request.Request("http://127.0.0.1:18080/v1/chat/completions",
                                 json.dumps(payload).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.load(response)


def b2_all() -> None:
    verify_precall_freeze()
    targets = [(row, OUT / f"runs/b2/{row['neutral_item_id']}") for row in rows()]
    if any(path.exists() for _, path in targets) or (OUT / "runs/b2_grant").exists():
        raise SystemExit("B2 was already attempted; retry forbidden")
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("model/shim port occupied; do not replace a server")
    model_pid = None
    tunnel = None
    try:
        model_pid = start_model("30")
        if not owned(model_pid, "30"):
            raise RuntimeError("Qwen3 30B placement could not be verified")
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N", "-L",
                                   "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(threading.Event(), timeout_s=300)
        grant = OUT / "runs/b2_grant"
        grant.mkdir(parents=True)
        preflight = {"model": QWEN_MODEL, "messages": [{"role": "user", "content": "Reply ok"}],
                     "temperature": 0.2, "seed": 1, "max_tokens": 32, "stream": False}
        (grant / "forwarded_request.json").write_text(json.dumps(preflight, indent=2) + "\n")
        response = qwen_request(preflight, 180)
        (grant / "response.json").write_text(json.dumps(response, indent=2) + "\n")
        if response.get("choices", [{}])[0].get("message", {}).get("tool_calls"):
            raise RuntimeError("B2 grant response included tool calls")
        (grant / "placement.json").write_text(json.dumps({"host": host.HOST,
            "checkpoint": MODEL30, "quantization": "Q4_K_M", "context": 32768,
            "sensors": host.sample()}, sort_keys=True, indent=2) + "\n")
        for row, run in targets:
            run.mkdir(parents=True)
            prompt = (ROOT / row["prompt_only_path"]).read_text()
            payload = {"model": QWEN_MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.2, "seed": 1, "max_tokens": 16384, "stream": False}
            (run / "forwarded_request.json").write_text(json.dumps(payload, indent=2) + "\n")
            started = time.monotonic()
            try:
                raw = qwen_request(payload, 1200)
                error = None
            except Exception as exc:
                raw, error = {}, f"{type(exc).__name__}: {exc}"
            answer = raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
            (run / "raw_response.json").write_text(json.dumps(raw, indent=2) + "\n")
            (run / "answer.txt").write_text(answer)
            meta = {"wall_s": round(time.monotonic() - started, 3), "error": error,
                    "usage": raw.get("usage"), "finish_reason": raw.get("choices", [{}])[0].get("finish_reason"),
                    "post_sensors": host.sample(), "model_call_attempted": True, "labels_opened": False}
            (run / "meta.json").write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n")
            print(json.dumps({"run": f"b2/{row['neutral_item_id']}", "answer_bytes": len(answer.encode()), **meta}), flush=True)
    finally:
        if tunnel is not None:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if model_pid is not None and owned(model_pid, "30"):
            host.remote(f"kill -TERM {model_pid}")


def rollout_path(thread_id: str) -> Path:
    found = list((Path.home() / ".codex/sessions").rglob(f"*{thread_id}.jsonl"))
    if len(found) != 1:
        raise RuntimeError(f"expected one rollout for {thread_id}, found {len(found)}")
    return found[0]


def observed_context(trace_path: Path) -> dict:
    events = [json.loads(line) for line in trace_path.read_text().splitlines() if line.strip()]
    thread_ids = {x.get("thread_id") for x in events if x.get("type") == "thread.started"}
    if len(thread_ids) != 1:
        raise RuntimeError("context calibration lacks one thread id")
    rollout = [json.loads(line) for line in rollout_path(next(iter(thread_ids))).read_text().splitlines() if line.strip()]
    session = next(x["payload"] for x in rollout if x.get("type") == "session_meta")
    turn = next(x["payload"] for x in rollout if x.get("type") == "turn_context")
    developers = []
    for event in rollout:
        payload = event.get("payload") or {}
        if event.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") == "developer":
            text = "".join(x.get("text", "") for x in payload.get("content", []) if isinstance(x, dict))
            developers.append(text)
    base = (session.get("base_instructions") or {}).get("text", "")
    return {"base_instructions_sha256": hashlib.sha256(base.encode()).hexdigest(),
            "developer_message_sha256": [hashlib.sha256(x.encode()).hexdigest() for x in developers],
            "cli_version": session.get("cli_version"), "approval_policy": turn.get("approval_policy"),
            "sandbox_type": (turn.get("sandbox_policy") or {}).get("type")}


def b4_calibrate() -> None:
    verify_precall_freeze()
    row = rows()[0]
    contract = ROOT / row["contract_path"]
    run = OUT / "runs/b4_context_calibration"
    prompt = "Unscored label-free context calibration. Do not call any tool. Reply with the single word ok."
    meta = run_process(run, b4_command("gpt-5.6-sol", run, contract), prompt=prompt,
                       cwd=ROOT, env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0"},
                       timeout=600)
    if meta["timed_out"] or meta["exit_code"] != 0:
        raise SystemExit("B4 context calibration failed")
    context = observed_context(run / "trace.jsonl")
    target = OUT / "context_calibration.json"
    if target.exists():
        raise SystemExit("context calibration decision already exists")
    target.write_text(json.dumps({"model": "gpt-5.6-sol", "stable_context": context,
        "trace_sha256": sha(run / "trace.jsonl"), "labels_opened": False}, sort_keys=True, indent=2) + "\n")
    print(json.dumps(context, sort_keys=True))


def b4_cell(neutral_id: str) -> None:
    verify_precall_freeze()
    row = row_for(neutral_id)
    run = OUT / f"runs/b4/{neutral_id}"
    contract_path, prompt_path = ROOT / row["contract_path"], ROOT / row["b4_prompt_path"]
    if sha(contract_path) != row["contract_sha256"] or sha(prompt_path) != row["b4_prompt_sha256"]:
        raise SystemExit("B4 contract or prompt changed")
    requirements = json.loads((OUT / "release_requirements.json").read_text())
    if requirements.get("comparison_release") is not True:
        raise SystemExit("ten-item B4 release is not authorized")
    load_contract(contract_path)
    prompt = prompt_path.read_text()
    meta = run_process(run, b4_command(requirements["moving_alias_observed"], run, contract_path),
                       prompt=prompt, cwd=ROOT,
                       env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0"},
                       timeout=5400)
    if not meta["timed_out"] and meta["exit_code"] == 0:
        validator = ROOT / "benchmark-mcp/stage4step3_validate.py"
        proc = subprocess.run([str(ROOT / "benchmark-mcp/.venv/bin/python"), str(validator),
                               "--run", str(run), "--contract", str(contract_path)],
                              cwd=ROOT, text=True, capture_output=True)
        (run / "validator_stdout.txt").write_text(proc.stdout)
        (run / "validator_stderr.txt").write_text(proc.stderr)
        if proc.returncode:
            print(json.dumps({"run": str(run.relative_to(OUT)), "validator_failure": proc.stderr.strip()}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("b1-grant", "b1", "b2-all", "b4-calibrate", "b4"))
    parser.add_argument("neutral_id", nargs="?")
    args = parser.parse_args()
    if args.mode == "b1-grant":
        b1_grant()
    elif args.mode == "b1":
        b1_cell(args.neutral_id)
    elif args.mode == "b2-all":
        b2_all()
    elif args.mode == "b4-calibrate":
        b4_calibrate()
    else:
        b4_cell(args.neutral_id)


if __name__ == "__main__":
    main()
