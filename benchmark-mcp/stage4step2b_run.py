"""Sealed-only, label-blind Stage 4 step-2b model calls and blind-file assembly."""

from __future__ import annotations

import argparse
import csv
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
from stage3ic_run import ORDER, command as codex_command
from stage4prep_promptonly import candidates_from_source_prompt, parse_answer
from pilot_score import full_ranking, selected_mutants

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2b_2026-09-14"
S3 = ROOT / "results/benchmark/stage3_2026-09-13"
S1 = ROOT / "results/benchmark/stage4step1_2026-09-14"
PREP = ROOT / "results/benchmark/stage4prep_2026-09-14"
SEALS = ("AACC1_PSEAI_Dandage_2018", "ARGR_ECOLI_Tsuboyama_2023_1AOY", "ENVZ_ECOLI_Ghose_2023")
DISALLOWED = ("Task,Bash,CronCreate,CronDelete,CronList,DesignSync,Edit,EnterWorktree,"
              "ExitWorktree,ListAgents,Monitor,NotebookEdit,PushNotification,Read,"
              "RemoteTrigger,ReportFindings,ScheduleWakeup,SendMessage,Skill,TaskOutput,"
              "TaskStop,ToolSearch,WebFetch,WebSearch,Workflow,Write,Glob,Grep,"
              "ListMcpResourcesTool,ReadMcpResourceDirTool,ReadMcpResourceTool")
CLAUDE_CWD = Path("/tmp/b1probe_step2b")
QWEN_MODEL = "Qwen3-30B-A3B-Q4_K_M"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest() -> dict[str, dict]:
    rows = {row["assay_id"]: row for line in (OUT / "sealed_prompt_manifest.jsonl").open()
            if (row := json.loads(line))}
    if set(rows) != set(SEALS):
        raise SystemExit("sealed manifest mismatch")
    for row in rows.values():
        if sha(ROOT / row["prompt_path"]) != row["prompt_sha256"]:
            raise SystemExit("sealed prompt hash mismatch")
    return rows


def run_once(name: str, cmd: list[str], *, stdin: str | None, cwd: Path,
             env: dict[str, str] | None = None, timeout: int = 2400) -> None:
    run = OUT / "runs" / name
    if run.exists():
        raise SystemExit(f"refusing to retry {name}")
    run.mkdir(parents=True)
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, input=stdin, text=True, capture_output=True,
                              cwd=cwd, env=env, timeout=timeout)
        out, err, code, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        out, err, code, timed_out = exc.stdout or b"", exc.stderr or b"", None, True
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
    (run / "trace.jsonl").write_text(out)
    (run / "stderr.txt").write_text(err)
    meta = {"wall_s": round(time.monotonic() - started, 3), "exit_code": code,
            "timed_out": timed_out, "model_call_attempted": True}
    (run / "meta.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(json.dumps({"run": name, **meta}), flush=True)


def codex_b1_grant() -> None:
    prompt = ("Unscored grant audit. Print the exact names in the actual ALL_TOOLS "
              "catalog as one JSON array. Do not call a mounted MCP tool.")
    run_once("b1_codex_grant", codex_command((), OUT / "runs/b1_codex_grant/record"),
             stdin=prompt, cwd=ROOT, timeout=300)


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
    CLAUDE_CWD.mkdir(parents=True, exist_ok=True)
    run_once("b1_claude_grant", claude_cmd("Reply with the single word: ok"),
             stdin=None, cwd=CLAUDE_CWD, env=claude_env(), timeout=300)


def b1_cell(assay: str) -> None:
    if assay not in SEALS:
        raise SystemExit("B1 only runs sealed items")
    row = manifest()[assay]
    run_once(f"b1_{assay}", claude_cmd((ROOT / row["prompt_path"]).read_text()),
             stdin=None, cwd=CLAUDE_CWD, env=claude_env(), timeout=1800)


def b4_grant() -> None:
    prompt = ("Unscored grant audit. From the actual ALL_TOOLS catalog, print one "
              "JSON object with catalog_names: ALL_TOOLS.map(x=>x.name), and "
              "catalog_bytes: UTF-8 bytes of JSON.stringify(ALL_TOOLS). "
              "Do not call an MCP tool.")
    record = OUT / "runs/b4_codex_grant/record"
    run_once("b4_codex_grant", codex_command(ORDER, record), stdin=prompt, cwd=ROOT, timeout=300)


def b4_cell(assay: str) -> None:
    if assay not in SEALS or assay == "ARGR_ECOLI_Tsuboyama_2023_1AOY":
        raise SystemExit("B4 ARGR is the already accepted Step 1 cell; no repeat")
    row = manifest()[assay]
    record = OUT / "runs" / f"b4_{assay}" / "record"
    run_once(f"b4_{assay}", codex_command(ORDER, record),
             stdin=(ROOT / row["prompt_path"]).read_text(), cwd=ROOT)


def b2_all() -> None:
    for assay in SEALS:
        if (OUT / "runs" / f"b2_{assay}").exists():
            raise SystemExit("B2 sealed cell already attempted; no retry")
    if host.port_open(18080) or host.port_open(18081):
        raise SystemExit("model/shim port occupied; do not replace a server")
    model_pid = None
    tunnel = None
    try:
        model_pid = start_model("30")
        if not owned(model_pid, "30"):
            raise RuntimeError("Qwen3 30B model placement could not be verified")
        tunnel = subprocess.Popen(["ssh", "-o", "BatchMode=yes", "-N", "-L",
                                   "18080:127.0.0.1:18080", host.HOST],
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        host.wait_model(threading.Event(), timeout_s=300)
        pre = OUT / "runs" / "b2_grant"
        pre.mkdir(parents=True)
        preflight = {"model": QWEN_MODEL, "messages": [{"role": "user", "content": "Reply ok"}],
                     "temperature": 0.2, "seed": 1, "max_tokens": 32, "stream": False}
        (pre / "forwarded_request.json").write_text(json.dumps(preflight, indent=2) + "\n")
        req = urllib.request.Request("http://127.0.0.1:18080/v1/chat/completions",
                                     json.dumps(preflight).encode(), {"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=180) as response:
            body = json.load(response)
        (pre / "response.json").write_text(json.dumps(body, indent=2) + "\n")
        if "tools" in preflight or body.get("choices", [{}])[0].get("message", {}).get("tool_calls"):
            raise RuntimeError("B2 direct model request/response is not tool-free")
        (pre / "placement.json").write_text(json.dumps({"host": host.HOST, "checkpoint": MODEL30,
                "quantization": "Q4_K_M", "context": 32768, "sensors": host.sample()}, indent=2) + "\n")
        for assay, row in manifest().items():
            run = OUT / "runs" / f"b2_{assay}"
            run.mkdir(parents=True)
            prompt = (ROOT / row["prompt_path"]).read_text()
            payload = {"model": QWEN_MODEL, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0.2, "seed": 1, "max_tokens": 16384, "stream": False}
            (run / "forwarded_request.json").write_text(json.dumps(payload, indent=2) + "\n")
            started = time.monotonic()
            try:
                req = urllib.request.Request("http://127.0.0.1:18080/v1/chat/completions",
                                             json.dumps(payload).encode(), {"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=1200) as response:
                    raw = json.load(response)
                error = None
            except Exception as exc:
                raw, error = {}, f"{type(exc).__name__}: {exc}"
            wall = time.monotonic() - started
            (run / "raw_response.json").write_text(json.dumps(raw, indent=2) + "\n")
            text = raw.get("choices", [{}])[0].get("message", {}).get("content") or ""
            (run / "answer.txt").write_text(text)
            (run / "meta.json").write_text(json.dumps({"wall_s": round(wall, 3),
                "model_call_attempted": True, "error": error,
                "usage": raw.get("usage"), "finish_reason": raw.get("choices", [{}])[0].get("finish_reason"),
                "post_sensors": host.sample()}, indent=2) + "\n")
            print(json.dumps({"run": f"b2_{assay}", "wall_s": round(wall, 3),
                              "error": error, "answer_bytes": len(text.encode())}), flush=True)
    finally:
        if tunnel is not None:
            tunnel.terminate()
            tunnel.wait(timeout=10)
        if model_pid is not None and owned(model_pid, "30"):
            host.remote(f"kill -TERM {model_pid}")


def claude_text(path: Path) -> str:
    events = [json.loads(line) for line in path.read_text().splitlines()]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    if init.get("tools") != [] or init.get("mcp_servers") != [] or init.get("memory_paths") is not None:
        raise RuntimeError("B1 Claude model-side grant not empty/isolated")
    if any(block.get("type") == "tool_use" for e in events
           for block in (e.get("message", {}).get("content", []) if isinstance(e.get("message"), dict) else [])
           if isinstance(block, dict)):
        raise RuntimeError("B1 used a tool despite empty catalog")
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    return result.get("result") if isinstance(result.get("result"), str) else ""


def codex_answer(assay: str) -> dict | None:
    path = ((S1.parent / "stage4prep_2026-09-14/step1_codex_cell_record/submissions/pilot_item.json")
            if assay == "ARGR_ECOLI_Tsuboyama_2023_1AOY" else
            OUT / "runs" / f"b4_{assay}" / "record/submissions/pilot_item.json")
    if not path.is_file():
        return None
    body = json.loads(path.read_text())
    return body.get("answer") if body.get("item_id") == "pilot_item" else None


def blind() -> None:
    data = manifest()
    for arm in ("b1", "b2", "b4"):
        path = OUT / f"blind_{arm}.jsonl"
        if path.exists():
            raise SystemExit(f"blind file already exists: {path}")
        lines = []
        for assay in SEALS:
            row = data[assay]
            candidates = tuple((ROOT / row["prompt_path"]).read_text().split("Candidate variants:\n", 1)[1].splitlines()[0].split(", "))
            if len(candidates) != row["candidate_count"]:
                raise SystemExit("candidate count mismatch")
            answer: dict | None = None
            text = ""
            parser_error = None
            parser_accepted = False
            if arm == "b1":
                raw = OUT / "runs" / f"b1_{assay}" / "trace.jsonl"
                if not raw.is_file():
                    raise SystemExit(f"B1 run missing for {assay}")
                text = claude_text(raw)
            elif arm == "b2":
                raw = OUT / "runs" / f"b2_{assay}" / "answer.txt"
                if not raw.is_file():
                    raise SystemExit(f"B2 run missing for {assay}")
                text = raw.read_text()
            else:
                answer = codex_answer(assay)
                if assay != "ARGR_ECOLI_Tsuboyama_2023_1AOY" and not (OUT / "runs" / f"b4_{assay}" / "trace.jsonl").is_file():
                    raise SystemExit(f"B4 run missing for {assay}")
            if arm != "b4":
                try:
                    answer = json.loads(text)
                    if not isinstance(answer, dict):
                        answer = None
                    parsed = parse_answer(text, candidates)
                    parser_accepted = True
                except (ValueError, TypeError) as exc:
                    parser_error = str(exc)
            else:
                parser_accepted = isinstance(answer, dict)
                if not parser_accepted:
                    parser_error = "record submission missing or not a JSON object"
            selected = selected_mutants(answer, set(candidates)) if isinstance(answer, dict) else None
            ranking = full_ranking(answer, set(candidates)) if isinstance(answer, dict) else None
            lines.append({"assay_id": assay, "arm": arm, "candidate_count": len(candidates),
                          "prompt_sha256": row["prompt_sha256"], "answer": answer,
                          "raw_text": text if arm != "b4" else None,
                          "parser_accepted": parser_accepted, "parser_error": parser_error,
                          "ten_valid_unique_picks": selected is not None,
                          "complete_ranking": ranking is not None})
        path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in lines))
    source = S3 / "floor_predictions_blind.csv"
    with source.open() as handle:
        reader = csv.DictReader(handle)
        if "DMS_score" in reader.fieldnames:
            raise SystemExit("source blind floor file contains labels")
        rows = [row for row in reader if row["assay_id"] in set(SEALS)]
    if len({row["assay_id"] for row in rows}) != 3:
        raise SystemExit("blind floor extraction missing a sealed item")
    for arm, field in (("b3", "floor_m_score"), ("floor_c", "floor_c_score")):
        path = OUT / f"blind_{arm}.csv"
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=("assay_id", "mutant", "score"))
            writer.writeheader()
            writer.writerows({"assay_id": row["assay_id"], "mutant": row["mutant"],
                              "score": row[field]} for row in rows)
    files = {arm: OUT / f"blind_{arm}.{ext}" for arm, ext in
             (("b1", "jsonl"), ("b2", "jsonl"), ("b3", "csv"), ("b4", "jsonl"), ("floor_c", "csv"))}
    target = OUT / "blind_hashes.json"
    if target.exists():
        raise SystemExit("blind hash file already exists")
    target.write_text(json.dumps({"sealed_items": list(SEALS),
        "prediction_sha256": {arm: {"path": str(path.relative_to(ROOT)), "digest": sha(path)}
                              for arm, path in files.items()},
        "evaluator_sha256": sha(ROOT / "benchmark-mcp/stage3_evaluate.py"),
        "scorer_sha256": sha(ROOT / "benchmark-mcp/pilot_score.py")}, indent=2) + "\n")
    print(json.dumps({"blind_files": {arm: sha(path) for arm, path in files.items()}}))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("b1_codex_grant", "b1_claude_grant", "b1", "b2_all",
                                         "b4_grant", "b4", "blind"))
    parser.add_argument("assay", nargs="?")
    args = parser.parse_args()
    if args.mode == "b1_codex_grant":
        codex_b1_grant()
    elif args.mode == "b1_claude_grant":
        b1_grant()
    elif args.mode == "b1":
        b1_cell(args.assay)
    elif args.mode == "b2_all":
        b2_all()
    elif args.mode == "b4_grant":
        b4_grant()
    elif args.mode == "b4":
        b4_cell(args.assay)
    else:
        blind()


if __name__ == "__main__":
    main()
