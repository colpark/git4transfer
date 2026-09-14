"""Four authorized, unscored Stage 3h diagnostic cells only."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import threading
import time
from pathlib import Path

import pilot_run
import stage3d_runtime as host
from stage3f_pilot_cell import inspect_trace, model_responses
from stage3g_run import baseline, owned
from stage3h_validity import FRACTION, controls, response_breach, session_windows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3h_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SHIM = ROOT / "benchmark-mcp/pilot_responses_shim.py"
CATALOG = ROOT / "benchmark-mcp/stage3g_model_catalog.json"
MODEL30 = "/home/aid1/models/stage3g/Qwen3-30B-A3B-Q4_K_M.gguf"
CAP = 4096


def start_model(model: str) -> int:
    if model == "7b":
        host.REMOTE_LOG = "/tmp/stage3h_qwen7b_20260914.log"
        return host.start_model(99, 128)
    if host.remote("ss -ltn '( sport = :18080 )' | tail -n +2"):
        raise RuntimeError("node 11 model port occupied")
    size = int(host.remote(f"stat -c %s {MODEL30}"))
    if size != 18556685824:
        raise RuntimeError("30B checkpoint size mismatch")
    import shlex
    args = [host.LLAMA, "-m", MODEL30, "--host", "127.0.0.1", "--port", "18080",
            "--ctx-size", "32768", "--n-gpu-layers", "99", "--threads", "2",
            "--threads-batch", "2", "--batch-size", "128", "--parallel", "1",
            "--jinja", "--no-webui"]
    return int(host.remote("nohup " + shlex.join(args) +
                           " > /tmp/stage3h_qwen30b_20260914.log 2>&1 < /dev/null & echo $!"))


def trace_details(path: Path, run_out: Path) -> dict:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.startswith("{")]
    attempts = []
    receipt_variant = {}
    for event in events:
        item = event.get("item", {})
        if item.get("type") != "mcp_tool_call":
            continue
        if event.get("type") == "item.started":
            attempts.append(item)
        if event.get("type") != "item.completed":
            continue
        result = item.get("result") or {}
        try:
            body = result.get("structured_content") or json.loads(result["content"][0]["text"])
        except (ValueError, KeyError, IndexError, TypeError):
            continue
        receipt = body.get("receipt", {})
        artifact = Path(receipt.get("artifact_path", "/__missing__"))
        if artifact.is_file():
            try:
                data = json.loads(artifact.read_text())
                args = data.get("args", {})
                if receipt.get("call_id") == data.get("receipt", {}).get("call_id"):
                    variant = args.get("variant")
                    if variant is None and args.get("position") and args.get("mutant") and args.get("wt"):
                        variant = f"{args['wt']}{args['position']}{args['mutant']}"
                    receipt_variant[receipt["call_id"]] = variant
            except (ValueError, OSError):
                pass
    submitted = run_out / "submissions/pilot_item.json"
    answer = json.loads(submitted.read_text()).get("answer") if submitted.is_file() else None
    considered = set()
    attempted_forms = []
    for item in attempts:
        args = item.get("arguments", {})
        if isinstance(args, str):
            try:
                args = json.loads(args)
            except ValueError:
                args = {}
        if item.get("tool") in ("blosum_score", "conservation", "pssm_score", "esm2_likelihood",
                                "esm_if", "screen_variant_classical", "screen_variant_fm"):
            attempted_forms.append({"tool": item.get("tool"),
                "form": "both" if args.get("variant") and any(args.get(k) is not None for k in ("wt", "position", "mutant"))
                else "variant" if args.get("variant") else "decomposed" if any(args.get(k) is not None for k in ("wt", "position", "mutant"))
                else "sequence_only" if item.get("tool") == "esm_if" else "missing",
                "variant": args.get("variant"), "mutant": args.get("mutant")})
        variant = args.get("variant")
        if variant and re.fullmatch(r"[ACDEFGHIKLMNPQRSTVWY][1-9][0-9]*[ACDEFGHIKLMNPQRSTVWY]", variant):
            considered.add(variant)
        elif args.get("wt") and args.get("position") and args.get("mutant") and len(str(args["mutant"])) == 1:
            considered.add(f"{args['wt']}{args['position']}{args['mutant']}")
    depths = []
    variant_specific = []
    if isinstance(answer, dict):
        for section in ("selected", "rejected", "ranking"):
            for entry in answer.get(section, []):
                if isinstance(entry, dict) and isinstance(entry.get("mutant"), str):
                    considered.add(entry["mutant"])
        for entry in answer.get("selected", []):
            validation = entry.get("validation", [])
            depths.append(len({e.get("category") for e in validation if isinstance(e, dict) and e.get("category")}))
            cited = list(entry.get("evidence", [])) + [e.get("call_id") for e in validation if isinstance(e, dict)]
            variant_specific.append(any(receipt_variant.get(cid) == entry.get("mutant") for cid in cited))
    submit_calls = [item for item in attempts if item.get("tool") == "submit_answer"]
    return {"submission": "accepted" if submitted.is_file() else "rejected" if submit_calls else "absent",
            "candidates_considered_lower_bound": len(considered), "considered_variants": sorted(considered),
            "validation_categories_per_pick": depths, "pick_has_variant_specific_evidence": variant_specific,
            "argument_forms_attempted": attempted_forms,
            "receipt_variant_map": receipt_variant}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("model", choices=("7b", "30b"))
    parser.add_argument("mode", choices=("unguided", "guided"))
    opts = parser.parse_args()
    if not json.loads((OUT / "schema_controls.json").read_text())["checks"]["pass"]:
        raise SystemExit("schema controls must pass before model cells")
    selection = json.loads((OUT / "diagnostic_item.json").read_text())
    if selection["n_remaining"] != 140 or selection["n_usable"] < 1:
        raise SystemExit("MSA sweep/diagnostic item not valid")
    run_out = OUT / f"cell_{opts.model}_{opts.mode}"
    if run_out.exists():
        raise SystemExit(f"refusing duplicate diagnostic cell {run_out}")
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("model or shim port occupied")
    run_out.mkdir(parents=True)
    model_name = "Qwen3-30B-A3B-Q4_K_M" if opts.model == "30b" else "qwen2.5-7b-instruct-q4_k_m"
    slug = "stage3g-qwen30b" if opts.model == "30b" else "stage2b-qwen7b"
    model_pid = None
    tunnel = shim = process = None
    shim_log = None
    stop = threading.Event()
    state = {"abort": None, "sensors": [], "response_checks": [], "session_checks": []}
    monitor = None
    try:
        model_pid = start_model(opts.model)
        if not owned(model_pid, "30" if opts.model == "30b" else "7b"):
            raise RuntimeError("model process identity check failed")
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N", "-L",
                                   "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(stop, timeout_s=300 if opts.model == "30b" else 180)
        placement = {"host": host.HOST, "model": model_name, "quantization": "Q4_K_M",
                     "context": 32768, "sensors_initial": host.sample(),
                     "memory_csv": host.remote("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits")}
        (run_out / "placement.json").write_text(json.dumps(placement, indent=2) + "\n")
        repeats = [baseline(model_name) for _ in range(3)]
        baseline_tps = statistics.median(row["tps"] for row in repeats)
        checks = controls()
        (run_out / "baseline.json").write_text(json.dumps({"repeats": repeats, "median_tps": baseline_tps,
            "threshold_tps": FRACTION * baseline_tps, "window_active_generation_s": 60,
            "controls": checks}, indent=2) + "\n")
        if not all(checks.values()):
            raise RuntimeError("validity controls failed")
        shim_dir = run_out / "shim"
        shim_dir.mkdir()
        shim_log = (run_out / "shim_server.log").open("w")
        allowed = ",".join("mcp__rescue_" + name for name in pilot_run.ALL_SERVERS)
        shim = subprocess.Popen([str(PY), str(SHIM), "--port", "18081", "--allow", allowed,
                                 "--output", str(shim_dir), "--seed", "1", "--temperature", "0.2",
                                 "--max-tokens", str(CAP), "--model", model_name], cwd=ROOT,
                                stdout=shim_log, stderr=subprocess.STDOUT)
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
                    with (run_out / "reported_sensors.jsonl").open("a") as handle:
                        handle.write(json.dumps(sample) + "\n")
                except Exception as exc:
                    state.setdefault("sensor_errors", []).append(str(exc))
                for response in model_responses(shim_dir):
                    if response["response"] in checked:
                        continue
                    checked.add(response["response"])
                    breach = response_breach(response["generation_tokens"], response["generation_s"], baseline_tps)
                    state["response_checks"].append({**response, "breach": breach})
                    state["session_checks"] = session_windows(state["response_checks"], baseline_tps)
                    if breach is True or any(row["breach"] for row in state["session_checks"]):
                        state["abort"] = "response" if breach is True else "session"
                        if process and process.poll() is None:
                            process.terminate()
                        return
        monitor = threading.Thread(target=watch, daemon=True)
        monitor.start()
        prompt = (OUT / "diagnostic_prompt.txt").read_text()
        cell = {"arm": "3", "mode": opts.mode, "sample": 1, "assay_id": selection["assay_id"]}
        cmd = pilot_run.command(cell, run_out)
        cmd[cmd.index("stage2b-qwen7b")] = slug
        cmd[-1:-1] = ["-c", f'model_catalog_json="{CATALOG}"']
        started = time.monotonic()
        process = subprocess.Popen(cmd, cwd=ROOT, text=True, stdin=subprocess.PIPE,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            stdout, stderr = process.communicate(input=prompt, timeout=1200)
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
        forms = []
        for cid in calls["receipt_ids"]:
            for server in ("classical", "predictive", "generative"):
                artifact = ROOT / f"results/benchmark/stage2_2026-09-12/artifacts/{server}/{cid.split(':')[-1]}.json"
                if artifact.is_file():
                    form = json.loads(artifact.read_text()).get("receipt", {}).get("input_form")
                    if form:
                        forms.append(form)
        cap_hits = [path.name for path in shim_dir.glob("shim_*_raw_model.json")
                    if (raw := json.loads(path.read_text())).get("choices", [{}])[0].get("finish_reason") == "length"
                    and raw.get("usage", {}).get("completion_tokens", 0) >= CAP]
        result = {"model": model_name, "mode": opts.mode, "assay_id": selection["assay_id"],
                  "wall_s": time.monotonic() - started, "prompt_tokens": sum(r["prompt_tokens"] for r in responses),
                  "generation_tokens": sum(r["generation_tokens"] for r in responses),
                  "response_cap": CAP, "cap_hits": cap_hits, "exit_code": process.returncode,
                  "timed_out": timed_out, "stop_reason": state["abort"], "calls": calls,
                  "fm_attempted": sum(calls["attempted"].get(s, 0) for s in ("predictive", "generative")),
                  "fm_usable": sum(calls["succeeded"].get(s, 0) for s in ("predictive", "generative")),
                  "argument_forms_with_receipts": forms, "response_checks": state["response_checks"],
                  "session_checks": state["session_checks"], "session_gate": "BREACH" if state["abort"] else "PASS" if state["session_checks"] else "UNDEMONSTRATED",
                  "baseline_tps": baseline_tps, "threshold_tps": FRACTION * baseline_tps,
                  "peak_gpu_c": max((s["gpu_c"] for s in state["sensors"]), default=None),
                  "peak_cpu_c": max((max(s["cpu_zone0_c"], s["cpu_zone4_c"]) for s in state["sensors"]), default=None),
                  "peak_gpu_power_w": max((s["gpu_power_w"] for s in state["sensors"]), default=None),
                  "peak_gpu_util_pct": max((s["gpu_util_pct"] for s in state["sensors"]), default=None),
                  "min_mem_available_gib": min((s["mem_available_gib"] for s in state["sensors"]), default=None),
                  "sensor_errors": state.get("sensor_errors", []), **details}
        (run_out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps({"model": opts.model, "mode": opts.mode, "wall_s": round(result["wall_s"], 1),
                          "submission": result["submission"], "fm_usable": result["fm_usable"],
                          "session_gate": result["session_gate"]}), flush=True)
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
        if model_pid and owned(model_pid, "30" if opts.model == "30b" else "7b"):
            host.remote(f"kill -TERM {model_pid}")


if __name__ == "__main__":
    main()
