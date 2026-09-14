"""One-shot, unscored matched ARGR controls; never imports labels or evaluators."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

from stage3ic_run import ORDER, ROOT, command

OUT = ROOT / "results/benchmark/stage4step1_2026-09-14"
PREP = ROOT / "results/benchmark/stage4prep_2026-09-14"
PROMPT = ROOT / "results/benchmark/stage3h_2026-09-14/diagnostic_prompt.txt"
OLD_CONFIG = ROOT / "results/benchmark/stage4prepd_2026-09-14/rescue_seven.json"
CLAUDE_CWD = Path("/tmp/b4probe")
ALLOWED = ",".join("mcp__rescue_" + name for name in ORDER)
DISALLOWED = ("Task,Bash,CronCreate,CronDelete,CronList,DesignSync,Edit,EnterWorktree,"
              "ExitWorktree,ListAgents,Monitor,NotebookEdit,PushNotification,Read,"
              "RemoteTrigger,ReportFindings,ScheduleWakeup,SendMessage,Skill,TaskOutput,"
              "TaskStop,ToolSearch,WebFetch,WebSearch,Workflow,Write,Glob,Grep,"
              "ListMcpResourcesTool,ReadMcpResourceDirTool,ReadMcpResourceTool")


def run_once(name: str, cmd: list[str], *, prompt: str | None, cwd: Path,
             env: dict[str, str] | None = None, timeout: int = 2400) -> None:
    trace = OUT / f"{name}.jsonl"
    stderr = OUT / f"{name}.err"
    wall = OUT / f"{name}.meta.json"
    if any(p.exists() for p in (trace, stderr, wall)):
        raise SystemExit(f"refusing to retry or overwrite {name}")
    start = time.monotonic()
    try:
        proc = subprocess.run(cmd, input=prompt, text=True, capture_output=True,
                              cwd=cwd, env=env, timeout=timeout)
        exit_code = proc.returncode
        timed_out = False
        out, err = proc.stdout, proc.stderr
    except subprocess.TimeoutExpired as exc:
        exit_code = None
        timed_out = True
        out = exc.stdout or b""
        err = exc.stderr or b""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
    trace.write_text(out)
    stderr.write_text(err)
    wall.write_text(json.dumps({"wall_s": round(time.monotonic()-start, 3),
                                "exit_code": exit_code, "timed_out": timed_out}, indent=2)+"\n")
    print(json.dumps({"run": name, "exit_code": exit_code, "timed_out": timed_out,
                      "wall_s": round(time.monotonic()-start, 3)}), flush=True)


def codex_preflight() -> None:
    record_out = PREP / "step1_codex_preflight_record"
    if record_out.exists():
        raise SystemExit("Codex preflight record directory already exists")
    prompt = ("Unscored grant audit. From the actual ALL_TOOLS catalog, use the code executor "
              "to print exactly one JSON object with catalog_names: ALL_TOOLS.map(x=>x.name), "
              "catalog_bytes: UTF-8 bytes of JSON.stringify(ALL_TOOLS). Do not call an MCP tool.")
    run_once("codex_grant", command(ORDER, record_out), prompt=prompt, cwd=ROOT, timeout=300)


def codex_cell() -> None:
    record_out = PREP / "step1_codex_cell_record"
    if record_out.exists():
        raise SystemExit("Codex cell record directory already exists")
    run_once("codex_cell", command(ORDER, record_out), prompt=PROMPT.read_text(), cwd=ROOT)


def claude_config() -> Path:
    path = OUT / "rescue_seven_matched.json"
    if path.exists():
        return path
    config = json.loads(OLD_CONFIG.read_text())
    args = config["mcpServers"]["rescue_record"]["args"]
    args[args.index("--out")+1] = str(PREP / "step1_claude_cell_record")
    path.write_text(json.dumps(config, indent=2)+"\n")
    return path


def claude_command(prompt: str) -> list[str]:
    return ["claude", "-p", prompt, "--model", "claude-opus-5", "--strict-mcp-config",
            "--mcp-config", str(claude_config()), "--allowedTools", ALLOWED,
            "--disallowedTools", DISALLOWED, "--output-format", "stream-json", "--verbose"]


def claude_env() -> dict[str, str]:
    env = dict(os.environ)
    env.pop("ANTHROPIC_API_KEY", None)
    env["CLAUDE_CODE_DISABLE_AUTO_MEMORY"] = "1"
    env["CLAUDE_CODE_DISABLE_CLAUDE_MDS"] = "1"
    return env


def claude_preflight() -> None:
    CLAUDE_CWD.mkdir(parents=True, exist_ok=True)
    run_once("claude_grant", claude_command("Reply with the single word: ok"),
             prompt=None, cwd=CLAUDE_CWD, env=claude_env(), timeout=300)


def claude_usage(which: str) -> None:
    if which not in ("before", "after"):
        raise SystemExit("usage must be before|after")
    # Slash command is local and costs no model turn.
    run_once("claude_usage_"+which,
             ["claude", "-p", "/usage", "--output-format", "json"],
             prompt=None, cwd=CLAUDE_CWD, env=claude_env(), timeout=120)


def claude_cell() -> None:
    record_out = PREP / "step1_claude_cell_record"
    # The model-side grant preflight starts the same record server and creates
    # this directory. Only a prior submission would mean a cell was attempted.
    if (record_out / "submissions" / "pilot_item.json").exists():
        raise SystemExit("Claude cell submission already exists")
    run_once("claude_cell", claude_command(PROMPT.read_text()),
             prompt=None, cwd=CLAUDE_CWD, env=claude_env())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("codex_preflight", "codex_cell", "claude_preflight",
                                         "claude_cell", "claude_usage_before", "claude_usage_after"))
    mode = parser.parse_args().mode
    if mode.startswith("claude_usage_"):
        claude_usage(mode.removeprefix("claude_usage_"))
    else:
        globals()[mode]()
