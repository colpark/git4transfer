"""Freeze the validator repair and bind it to the completed blind runs."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
ORIGINAL = ROOT / "benchmark-mcp/stage4step3_validate.py"
REPAIRED = ROOT / "benchmark-mcp/stage4step3_validate_repair.py"
TARGET = OUT / "validator_repair_amendment.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if TARGET.exists():
        raise SystemExit("validator repair amendment already exists")
    forbidden = [OUT / "blind_bundle_manifest.json", OUT / "comparison_rows.csv",
                 OUT / "evaluation_integrity.json"]
    if any(path.exists() for path in forbidden):
        raise SystemExit("label-stage artifacts already exist; refusing pre-label amendment")

    freeze = json.loads((OUT / "precall_freeze.json").read_text())
    frozen_hashes = {Path(row["path"]).resolve(): row["sha256"] for row in freeze["files"]}
    if frozen_hashes.get(ORIGINAL.resolve()) != sha(ORIGINAL):
        raise SystemExit("original validator no longer matches the pre-call freeze")

    runs = {}
    for index in range(1, 11):
        neutral = f"cmp_{index:03d}"
        run = OUT / "runs/b4" / neutral
        prompt = OUT / "prompts/b4" / f"{neutral}.txt"
        contract = OUT / "contracts" / f"{neutral}.json"
        launch = json.loads((run / "launch.json").read_text())
        if "prompt_path" in launch or launch.get("prompt_sha256") != sha(prompt):
            raise SystemExit(f"repair premise does not hold for {neutral}")
        meta = json.loads((run / "meta.json").read_text())
        record = {
            "run": str(run.relative_to(ROOT)),
            "exit_code": meta.get("exit_code"),
            "timed_out": meta.get("timed_out"),
            "launch_sha256": sha(run / "launch.json"),
            "trace_sha256": sha(run / "trace.jsonl"),
            "prompt_path": str(prompt.relative_to(ROOT)),
            "prompt_sha256": sha(prompt),
            "contract_path": str(contract.relative_to(ROOT)),
            "contract_sha256": sha(contract),
        }
        submission = run / "submissions" / f"{neutral}.json"
        record["submission_sha256"] = sha(submission) if submission.is_file() else None
        runs[neutral] = record

    body = {
        "amended_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorization": "User explicitly requested the auditable validator repair and subsequent sealed-label evaluation on 2026-09-15.",
        "defect": "The runner froze prompt_sha256 but omitted prompt_path from launch.json; the original validator raised KeyError before substantive validation.",
        "scope": "Post-run metadata repair only; no model calls, predictions, prompts, contracts, traces, submissions, artifacts, or labels are changed.",
        "repair": "A separate validator requires --prompt-path and verifies it against the launch's frozen prompt_sha256 before applying the original substantive checks.",
        "original_validator_path": str(ORIGINAL.relative_to(ROOT)),
        "original_validator_sha256": sha(ORIGINAL),
        "repaired_validator_path": str(REPAIRED.relative_to(ROOT)),
        "repaired_validator_sha256": sha(REPAIRED),
        "precall_freeze_sha256": sha(OUT / "precall_freeze.json"),
        "model_runs_complete_sha256": sha(OUT / "background/model_runs_complete.json"),
        "labels_opened_before_amendment": False,
        "model_calls_rerun": False,
        "runs": runs,
    }
    TARGET.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"amendment": str(TARGET), "sha256": sha(TARGET),
                      "runs_bound": len(runs)}, sort_keys=True))


if __name__ == "__main__":
    main()
