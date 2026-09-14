"""Stage 4 W1 pilot executor; blind answers only, no label access."""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import threading
import time
from pathlib import Path

import stage3d_runtime as host
from stage3d_watchdog import classify

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
STAGE3D = ROOT / "results/benchmark/stage3d_2026-09-13"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SERVER = ROOT / "benchmark-mcp/server.py"
RECORD = ROOT / "benchmark-mcp/pilot_record_server.py"
SHIM = ROOT / "benchmark-mcp/pilot_responses_shim.py"
ALL_SERVERS = ("record", "classical", "lit", "analysis", "predictive", "generative", "physics")
GRANTS = {"1": ("record",), "2": ("record", "classical", "lit"),
          "3": ALL_SERVERS, "3F": ALL_SERVERS, "3L": ALL_SERVERS}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze(selection: dict, frozen: dict) -> None:
    expected = {"selection_sha256": OUT / "selection.json",
                "preselection_freeze_sha256": OUT / "preselection_freeze.json",
                "preregistration_sha256": OUT / "preregistration.md",
                "selection_csv_sha256": OUT / "selection.csv",
                "schedule_sha256": OUT / "run_schedule.json",
                "source_floor_scores_sha256": ROOT / "results/benchmark/stage3_2026-09-13/floor_item_scores.csv",
                "source_prompt_manifest_sha256": ROOT / "results/benchmark/stage3_2026-09-13/prompt_manifest.jsonl",
                "prompt_template_code_sha256": ROOT / "benchmark-mcp/pilot_prepare.py",
                "scoring_code_sha256": ROOT / "benchmark-mcp/pilot_score.py",
                "stage3_evaluator_sha256": ROOT / "benchmark-mcp/stage3_evaluate.py",
                "stage3_floor_code_sha256": ROOT / "benchmark-mcp/stage3_w1.py",
                "runner_code_sha256": ROOT / "benchmark-mcp/pilot_run.py",
                "pilot_shim_sha256": SHIM,
                "record_mount_sha256": RECORD}
    for key, path in expected.items():
        if digest(path) != frozen[key]:
            raise SystemExit(f"frozen {key} mismatch: {path}")
    for item in selection["items"]:
        if digest(Path(item["homolog_fasta_path"])) != item["homolog_fasta_sha256"]:
            raise SystemExit("frozen homolog FASTA hash mismatch")
        if digest(Path(item["reference_pdb_path"])) != item["reference_pdb_sha256"]:
            raise SystemExit("frozen reference PDB hash mismatch")
        if digest(Path(item["source_pdb_path"])) != item["source_pdb_sha256"]:
            raise SystemExit("source reference PDB hash mismatch")
        for prompt in item["prompt_files"].values():
            if digest(Path(prompt["path"])) != prompt["sha256"]:
                raise SystemExit("frozen prompt hash mismatch")


def gate_check() -> None:
    controls = json.loads((STAGE3D / "watchdog_controls.json").read_text())
    envelope = json.loads((STAGE3D / "thermal_envelope.json").read_text())
    ladder = list(csv.DictReader((STAGE3D / "reachability.csv").open()))
    if not controls["all_pass"] or controls["thresholds"]["gpu_tlimit_margin_c"] != 10:
        raise SystemExit("Stage 3d amended watchdog control gate not passed")
    if len(ladder) != 8 or [int(row["server_count"]) for row in ladder] != list(range(1, 9)):
        raise SystemExit("Stage 3d remount ladder not complete")
    if any(row["verdict"] != "PASS" for row in ladder):
        raise SystemExit("Stage 3d remount ladder has a non-PASS")
    if envelope.get("thirty_minute_envelope_pass") is not True:
        raise SystemExit("Stage 3d full-grant thermal envelope did not pass")


def command(cell: dict, run_out: Path) -> list[str]:
    mode, grant = cell["mode"], GRANTS[cell["arm"]]
    args = ["codex", "exec", "--json", "--ignore-user-config", "--skip-git-repo-check",
            "-m", "stage2b-qwen7b", "-s", "read-only", "-c", 'approval_policy="never"',
            "-c", 'model_provider="stage4pilot_llama"',
            "-c", 'model_providers.stage4pilot_llama={name="Stage 4 pilot llama.cpp",'
            'base_url="http://127.0.0.1:18081/v1",wire_api="responses"}',
            "-c", "model_context_window=32768", "-c", "model_auto_compact_token_limit=30000"]
    for name in grant:
        if name == "record":
            config = (f'mcp_servers.rescue_record={{command="{PY}",args=["{RECORD}",'
                      f'"--out","{run_out}","--presentation","{mode}"],'
                      'default_tools_approval_mode="approve",startup_timeout_sec=30,'
                      'tool_timeout_sec=150}')
        else:
            config = (f'mcp_servers.rescue_{name}={{command="{PY}",args=["{SERVER}",'
                      f'"--server","{name}","--presentation","{mode}"],'
                      'default_tools_approval_mode="approve",startup_timeout_sec=30,'
                      'tool_timeout_sec=150}')
        args += ["-c", config]
    return args + ["-"]


def run_cell(cell: dict, item: dict, state: dict) -> dict:
    run_out = OUT / "runs" / cell["run_id"]
    run_out.mkdir(parents=True, exist_ok=True)
    prompt_file = Path(item["prompt_files"][cell["arm"]]["path"])
    prompt = prompt_file.read_text()
    shim_dir = run_out / "shim"
    shim_dir.mkdir(exist_ok=True)
    allowed = ",".join("mcp__rescue_" + name for name in ALL_SERVERS)
    shim_log = (run_out / "shim_server.log").open("w")
    shim = subprocess.Popen([str(PY), str(SHIM), "--port", "18081", "--allow", allowed,
                             "--output", str(shim_dir), "--seed", str(cell["sample"]),
                             "--temperature", "0.2", "--max-tokens", "3072"],
                            cwd=ROOT, stdout=shim_log, stderr=subprocess.STDOUT)
    try:
        deadline = time.monotonic() + 20
        while not host.port_open(18081) and time.monotonic() < deadline and not state["abort"]:
            time.sleep(0.2)
        if not host.port_open(18081):
            raise RuntimeError("pilot response shim failed to start")
        started = time.monotonic()
        process = subprocess.Popen(command(cell, run_out), cwd=ROOT, text=True,
                                   stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE)
        state["active_agent"] = process
        try:
            stdout, stderr = process.communicate(input=prompt, timeout=900)
            timed_out = False
        except subprocess.TimeoutExpired:
            process.terminate()
            stdout, stderr = process.communicate(timeout=15)
            timed_out = True
        finally:
            state["active_agent"] = None
        wall_s = round(time.monotonic() - started, 3)
        trace = run_out / "trace.jsonl"
        trace.write_text(stdout)
        (run_out / "stderr.txt").write_text(stderr)
        submission = run_out / "submissions/pilot_item.json"
        try:
            body = json.loads(submission.read_text()) if submission.is_file() else None
            answer = body.get("answer") if isinstance(body, dict) else None
        except (ValueError, OSError):
            answer = None
        interrupted = bool(state["abort"]) or timed_out
        status = ("UNDEMONSTRATED" if interrupted
                  else "COMPLETED" if process.returncode == 0 and isinstance(answer, dict)
                  else "FAILED")
        usage = []
        for path in sorted(shim_dir.glob("shim_*_parsed.json")):
            try:
                usage.append(json.loads(path.read_text()).get("backend_usage", {}))
            except (ValueError, OSError):
                pass
        return {**cell, "status": status, "wall_s": wall_s,
                "exit_code": process.returncode,
                "stop_reason": state["abort"] or ("timeout_900s" if timed_out else None),
                "answer": answer, "trace_path": str(trace),
                "submission_path": str(submission) if submission.is_file() else None,
                "model_request_count": len(usage),
                "max_prompt_tokens": max((u.get("prompt_tokens", 0) for u in usage), default=0),
                "max_completion_tokens": max((u.get("completion_tokens", 0) for u in usage), default=0)}
    finally:
        shim.terminate()
        shim.wait(timeout=10)
        shim_log.close()


def main() -> None:
    gate_check()
    selection = json.loads((OUT / "selection.json").read_text())
    schedule = json.loads((OUT / "run_schedule.json").read_text())["runs"]
    frozen = json.loads((OUT / "freeze_hashes.json").read_text())
    verify_freeze(selection, frozen)
    items = {item["assay_id"]: item for item in selection["items"]}
    blind = OUT / "answers_blind.jsonl"
    prior = [json.loads(line) for line in blind.read_text().splitlines()] if blind.exists() else []
    done = {row["run_id"] for row in prior}
    if len(done) != len(prior):
        raise SystemExit("duplicate run ID in blind log; stop for audit")
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("pilot model/shim port occupied; refusing to replace")
    initial = host.sample()
    if reason := classify(initial):
        raise SystemExit(f"unsafe initial state: {reason}")
    host.REMOTE_LOG = "/tmp/stage4pilot_llama_20260913.log"
    state = {"abort": None, "active_agent": None, "model_pid": None, "samples": []}
    stop = threading.Event()
    def watch() -> None:
        while not stop.is_set():
            try:
                sample = host.sample()
                state["samples"].append(sample)
                with (OUT / "watchdog_samples.jsonl").open("a") as handle:
                    handle.write(json.dumps(sample) + "\n")
                state["abort"] = classify(sample)
            except Exception as error:
                state["abort"] = f"sensor monitor failed: {error}"
            if state["abort"]:
                active = state["active_agent"]
                if active and active.poll() is None:
                    active.terminate()
                if state["model_pid"]:
                    try:
                        host.stop_owned(state["model_pid"])
                    except Exception:
                        pass
                stop.set()
                return
            stop.wait(2)
    watcher = threading.Thread(target=watch, daemon=True)
    watcher.start()
    tunnel = None
    try:
        state["model_pid"] = host.start_model(99, 128)
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N",
                                   "-L", "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(stop)
        pilot_start = time.monotonic()
        active_agent_s = 0.0
        for cell in schedule:
            if cell["run_id"] in done:
                continue
            if state["abort"]:
                break
            record = run_cell(cell, items[cell["assay_id"]], state)
            active_agent_s += record["wall_s"]
            with blind.open("a") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
                handle.flush()
            done.add(cell["run_id"])
            print(json.dumps({"run_id": cell["run_id"], "item": cell["item"],
                              "arm": cell["arm"], "mode": cell["mode"],
                              "sample": cell["sample"], "status": record["status"],
                              "wall_s": record["wall_s"], "completed_rows": len(done)}), flush=True)
            if state["abort"]:
                break
            latest = state["samples"][-1]
            cpu = max(latest["cpu_zone0_c"], latest["cpu_zone4_c"])
            delay = 15 if cpu >= 83.5 else 5 if cpu >= 82 else 0
            if delay:
                stop.wait(delay)
        pilot_elapsed_s = time.monotonic() - pilot_start
        (OUT / "pilot_run_span.json").write_text(json.dumps({
            "runs_in_this_session": len(done) - len(prior),
            "elapsed_s": round(pilot_elapsed_s, 2),
            "active_agent_s": round(active_agent_s, 2),
            "duty_cycle": round(active_agent_s / pilot_elapsed_s, 4) if pilot_elapsed_s else None,
            "duty_cycle_definition": "sum of agent-run wall times / session elapsed including thermal waits",
            "stop_reason": state["abort"]}, indent=2) + "\n")
        if len(done) == 240 and not state["abort"]:
            seal = digest(blind)
            (OUT / "answers_blind.sha256").write_text(seal + "\n")
            print(json.dumps({"pilot_runs_recorded": 240, "blind_sha256": seal}), flush=True)
        else:
            (OUT / "pilot_stop.json").write_text(json.dumps({"runs_recorded": len(done),
                "stop_reason": state["abort"], "complete": False}, indent=2) + "\n")
    except Exception as error:
        (OUT / "pilot_stop.json").write_text(json.dumps({
            "runs_recorded": len(done),
            "stop_reason": state["abort"] or f"{type(error).__name__}: {error}",
            "complete": False}, indent=2) + "\n")
        raise
    finally:
        stop.set()
        watcher.join(timeout=10)
        if tunnel:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if state["model_pid"]:
            host.stop_owned(state["model_pid"])
        try:
            (OUT / "model_server.log").write_text(host.remote(f"cat {host.REMOTE_LOG}", timeout=30))
        except Exception:
            pass


if __name__ == "__main__":
    main()
