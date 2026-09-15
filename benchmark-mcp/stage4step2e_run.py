"""One-shot B4 v3 cohort runner; release-gated and label-free."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

from stage4step2e_contract import canonical_sha, load_contract

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2e_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SERVER = ROOT / "benchmark-mcp/stage4step2e_server.py"
RECORD = ROOT / "benchmark-mcp/stage4step2e_record_server.py"
TOOLS = {"record": ("submit_answer",), "classical": ("score_variant_classical",),
         "fm": ("score_variant_fm",), "structure": ("structure_context",)}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mount(name: str, run: Path, contract: Path) -> str:
    code = RECORD if name == "record" else SERVER
    args = [str(code), "--out", str(run), "--contract", str(contract)]
    if name != "record":
        args[1:1] = ["--server", name]
    return (f"mcp_servers.b4v3_{name}={{command={json.dumps(str(PY))},"
            f"args={json.dumps(args)},enabled_tools={json.dumps(TOOLS[name])},"
            'default_tools_approval_mode="approve",startup_timeout_sec=60,tool_timeout_sec=900}')


def command(model: str, run: Path, contract: Path) -> list[str]:
    cmd = ["codex", "exec", "--json", "--ignore-user-config", "--ignore-rules",
           "--skip-git-repo-check", "-m", model, "-s", "read-only",
           "-c", 'approval_policy="never"', "-c", 'model_reasoning_effort="high"',
           "-c", 'web_search="disabled"', "-c", "tools.view_image=false"]
    for feature in ("shell_tool", "unified_exec", "multi_agent", "multi_agent_v2", "apps",
                    "browser_use", "computer_use", "image_generation", "goals", "plugins",
                    "remote_plugin", "code_mode"):
        cmd.extend(("--disable", feature))
    for name in ("record", "classical", "fm", "structure"):
        cmd.extend(("-c", mount(name, run, contract)))
    return cmd + ["-"]


def preflight(run: Path, contract_path: Path, prompt: Path) -> tuple[dict, str]:
    subprocess.run([str(PY), str(ROOT / "benchmark-mcp/stage4step2e_freeze.py"), "verify"],
                   cwd=ROOT, check=True)
    subprocess.run([str(PY), str(ROOT / "benchmark-mcp/stage4step2e_release_gate.py"), "enforce"],
                   cwd=ROOT, check=True)
    if run.exists():
        raise SystemExit("run path exists; retry forbidden")
    contract = load_contract(contract_path)
    if contract.get("status") != "COHORT_LABEL_FREE_UNSCORED_UNTIL_CONTENT_AUDIT":
        raise SystemExit("fixture or non-cohort contract cannot launch")
    if not prompt.is_file() or not prompt.read_text().strip():
        raise SystemExit("model-visible prompt is missing")
    requirements = json.loads((OUT / "release_requirements.json").read_text())
    model = requirements.get("immutable_model_id") or requirements.get("moving_alias_observed")
    return contract, model


def run_once(run: Path, contract_path: Path, prompt: Path) -> None:
    contract, model = preflight(run, contract_path, prompt)
    run.mkdir(parents=True)
    cmd = command(model, run, contract_path)
    launch = {"command": cmd, "cwd": str(ROOT), "model": model,
              "prompt_path": str(prompt.resolve()), "prompt_sha256": sha(prompt),
              "contract_path": str(contract_path.resolve()),
              "contract_sha256": canonical_sha(contract),
              "evaluation_authorized": False, "labels_opened": False}
    (run / "launch.json").write_text(json.dumps(launch, sort_keys=True, indent=2) + "\n")
    env = dict(os.environ)
    env.update({"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0"})
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, input=prompt.read_text(), text=True, capture_output=True,
                              cwd=ROOT, env=env, timeout=5400)
        timed_out, stdout, stderr, code = False, proc.stdout, proc.stderr, proc.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out, stdout, stderr, code = True, exc.stdout or "", exc.stderr or "", None
        if isinstance(stdout, bytes): stdout = stdout.decode(errors="replace")
        if isinstance(stderr, bytes): stderr = stderr.decode(errors="replace")
    (run / "trace.jsonl").write_text(stdout)
    (run / "stderr.txt").write_text(stderr)
    meta = {"wall_s": round(time.monotonic() - started, 3), "exit_code": code,
            "timed_out": timed_out, "model_call_attempted": True,
            "labels_opened": False, "evaluation_authorized": False}
    (run / "meta.json").write_text(json.dumps(meta, sort_keys=True, indent=2) + "\n")
    if timed_out or code != 0:
        raise SystemExit("cell failed; retry forbidden")
    subprocess.run([str(PY), str(ROOT / "benchmark-mcp/stage4step2e_validate.py"),
                    "--run", str(run), "--contract", str(contract_path)], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preflight", "run-once"))
    parser.add_argument("--run", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    values = (Path(args.run).resolve(), Path(args.contract).resolve(), Path(args.prompt).resolve())
    preflight(*values) if args.mode == "preflight" else run_once(*values)


if __name__ == "__main__":
    main()
