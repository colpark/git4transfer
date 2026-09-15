"""Isolated label-free retry of the interrupted Stage 4 B4 cmp_001 cell."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from stage4step2e_contract import ContractError, load_contract, validate_answer, validate_artifact
from stage4step2e_run import command as b4_command
from stage4step3_validate import audit_trace_pairs, result_receipt
from stage4step3b_recover import extract_context, gate_accepts, gate_view, calibration_contexts


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/benchmark/stage4step3_2026-09-14"
DEST = ROOT / "results/benchmark/stage4step3c_retry_2026-09-15"
RUN = DEST / "runs/b4/cmp_001"
CONTRACT = SOURCE / "contracts/cmp_001.json"
PROMPT = SOURCE / "prompts/b4/cmp_001.txt"
ORIGINAL = SOURCE / "runs/b4/cmp_001"
MODEL = "gpt-5.6-sol"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_events(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def prepare() -> None:
    target = DEST / "retry_prereg.json"
    if target.exists() or RUN.exists():
        raise SystemExit("cmp_001 retry is already registered or attempted")
    original_meta = json.loads((ORIGINAL / "meta.json").read_text())
    if (original_meta.get("exit_code") != 1 or original_meta.get("timed_out") is not False
            or (ORIGINAL / "submissions/cmp_001.json").exists()):
        raise SystemExit("original interrupted-cell state changed")
    body = {
        "registered_at_utc": now(),
        "purpose": "One label-free diagnostic retry of B4 cmp_001 after platform biological-risk interruption.",
        "disposition": "Separate retry; not incorporated into frozen Step 3b coverage or scores without a panel ruling.",
        "neutral_item_id": "cmp_001",
        "arm": "B4",
        "model_alias": MODEL,
        "sandbox": "read-only",
        "approval_policy": "never",
        "reasoning_effort": "high",
        "web_search": "disabled",
        "labels_opened_for_retry": False,
        "model_calls_authorized": 1,
        "prompt_sha256": sha(PROMPT),
        "contract_sha256": sha(CONTRACT),
        "original_trace_sha256": sha(ORIGINAL / "trace.jsonl"),
        "original_meta_sha256": sha(ORIGINAL / "meta.json"),
        "runner_sha256": sha(Path(__file__)),
        "b4_command_code_sha256": sha(ROOT / "benchmark-mcp/stage4step2e_run.py"),
        "contract_code_sha256": sha(ROOT / "benchmark-mcp/stage4step2e_contract.py"),
        "context_gate_code_sha256": sha(ROOT / "benchmark-mcp/stage4step3b_recover.py"),
        "stop": "Stop after label-free structural/context validation; do not GT-score or alter Step 3b.",
    }
    DEST.mkdir(parents=True)
    target.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"retry_prereg_sha256": sha(target)}, sort_keys=True))


def verify_prereg() -> dict:
    prereg = json.loads((DEST / "retry_prereg.json").read_text())
    checks = {
        PROMPT: prereg["prompt_sha256"],
        CONTRACT: prereg["contract_sha256"],
        ORIGINAL / "trace.jsonl": prereg["original_trace_sha256"],
        ORIGINAL / "meta.json": prereg["original_meta_sha256"],
        Path(__file__): prereg["runner_sha256"],
        ROOT / "benchmark-mcp/stage4step2e_run.py": prereg["b4_command_code_sha256"],
        ROOT / "benchmark-mcp/stage4step2e_contract.py": prereg["contract_code_sha256"],
        ROOT / "benchmark-mcp/stage4step3b_recover.py": prereg["context_gate_code_sha256"],
    }
    for path, digest in checks.items():
        if sha(path) != digest:
            raise RuntimeError(f"retry prereg dependency changed: {path}")
    return prereg


def run() -> None:
    verify_prereg()
    if RUN.exists():
        raise SystemExit("refusing a second cmp_001 retry")
    load_contract(CONTRACT)
    command = b4_command(MODEL, RUN, CONTRACT)
    RUN.mkdir(parents=True)
    prompt = PROMPT.read_text()
    (RUN / "launch.json").write_text(json.dumps({
        "command": command,
        "cwd": str(ROOT),
        "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
        "contract_sha256": sha(CONTRACT),
        "retry_prereg_sha256": sha(DEST / "retry_prereg.json"),
        "labels_opened": False,
    }, sort_keys=True, indent=2) + "\n")
    started = time.monotonic()
    try:
        process = subprocess.run(
            command,
            input=prompt,
            text=True,
            capture_output=True,
            cwd=ROOT,
            env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0"},
            timeout=5400,
        )
        stdout, stderr = process.stdout, process.stderr
        exit_code, timed_out = process.returncode, False
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or "", exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode(errors="replace")
        exit_code, timed_out = None, True
    (RUN / "trace.jsonl").write_text(stdout)
    (RUN / "stderr.txt").write_text(stderr)
    meta = {
        "completed_at_utc": now(),
        "wall_s": round(time.monotonic() - started, 3),
        "exit_code": exit_code,
        "timed_out": timed_out,
        "model_call_attempted": True,
        "model_call_count": 1,
        "labels_opened": False,
    }
    (RUN / "meta.json").write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n")
    print(json.dumps(meta, sort_keys=True), flush=True)


def validate() -> None:
    verify_prereg()
    target = DEST / "retry_result.json"
    if target.exists():
        raise SystemExit("retry result already exists")
    meta = json.loads((RUN / "meta.json").read_text())
    trace = RUN / "trace.jsonl"
    events = read_events(trace)
    fm_started = sum(event.get("type") == "item.started"
                     and event.get("item", {}).get("tool") == "score_variant_fm" for event in events)
    fm_completed = sum(event.get("type") == "item.completed"
                       and event.get("item", {}).get("tool") == "score_variant_fm"
                       and event.get("item", {}).get("status") == "completed" for event in events)
    terminal_errors = [event for event in events if event.get("type") in {"error", "turn.failed"}]
    result = {
        "validated_at_utc": now(),
        "neutral_item_id": "cmp_001",
        "separate_retry_not_step3b": True,
        "labels_opened": False,
        "model_call_count": 1,
        "process": meta,
        "trace_sha256": sha(trace),
        "fm_started": fm_started,
        "fm_completed": fm_completed,
        "artifact_count": len(list((RUN / "artifacts/fm").glob("*.json"))),
        "terminal_errors": terminal_errors,
        "complete_submission": False,
        "contract_valid": False,
        "same_normalized_context_as_active_b4": None,
    }
    if meta.get("exit_code") == 0 and not meta.get("timed_out"):
        try:
            pairs = audit_trace_pairs(events)
            context = extract_context(trace)
            _, active = calibration_contexts()
            result["received_context"] = gate_view(context)
            result["same_normalized_context_as_active_b4"] = gate_accepts(context, active)
            submission_path = RUN / "submissions/cmp_001.json"
            if not submission_path.is_file() or pairs["submission"].get("status") != "completed":
                raise RuntimeError("completed process lacks completed recorded submission")
            submission = json.loads(submission_path.read_text())
            contract = load_contract(CONTRACT)
            verdict = validate_answer(submission.get("answer"), contract, RUN / "artifacts")
            if verdict != submission.get("validation") or verdict.get("accepted") is not True:
                raise RuntimeError("stored submission verdict is not reproducible")
            artifact_receipts = {}
            for path in sorted((RUN / "artifacts").glob("*/*.json")):
                body = json.loads(path.read_text())
                validate_artifact(body, path, contract, require_success=True)
                artifact_receipts[body["receipt"]["call_id"]] = body["receipt"]
            completed_science = {key: value for key, value in pairs["completed"].items()
                                 if value.get("tool") != "submit_answer"}
            trace_receipts = {result_receipt(value).get("call_id"): result_receipt(value)
                              for value in completed_science.values()
                              if isinstance(result_receipt(value), dict)}
            if trace_receipts != artifact_receipts or len(artifact_receipts) != len(contract["candidates"]):
                raise RuntimeError("trace/artifact receipt coverage is not complete")
            result.update({
                "complete_submission": True,
                "contract_valid": True,
                "submission_sha256": sha(submission_path),
                "science_receipt_count": len(artifact_receipts),
                "validation_error": None,
            })
        except (ContractError, KeyError, OSError, RuntimeError, StopIteration, ValueError) as exc:
            result["validation_error"] = f"{type(exc).__name__}: {exc}"
    else:
        result["validation_error"] = "process did not complete successfully"
    target.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in (
        "complete_submission", "contract_valid", "same_normalized_context_as_active_b4",
        "fm_started", "fm_completed", "artifact_count", "validation_error")}, sort_keys=True))


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {"prepare", "run", "validate"}:
        raise SystemExit("usage: stage4step3c_retry_cmp001.py {prepare|run|validate}")
    {"prepare": prepare, "run": run, "validate": validate}[sys.argv[1]]()


if __name__ == "__main__":
    main()
