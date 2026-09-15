"""Resume-time context calibration and sequential B4 supervisor."""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from stage4step2e_run import command as b4_command
from stage4step3_run import OUT, ROOT, observed_context, row_for, run_process, sha, verify_precall_freeze


def main() -> None:
    verify_precall_freeze()
    row = row_for("cmp_001")
    contract = ROOT / row["contract_path"]
    run = OUT / "runs/b4_context_calibration_2026-09-15"
    prompt = "Unscored label-free resume context calibration. Do not call any tool. Reply with the single word ok."
    meta = run_process(run, b4_command("gpt-5.6-sol", run, contract), prompt=prompt,
        cwd=ROOT, env={**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONHASHSEED": "0"},
        timeout=600)
    if meta["timed_out"] or meta["exit_code"] != 0:
        raise SystemExit("resume context calibration failed; no B4 comparison item launched")
    context = observed_context(run / "trace.jsonl")
    calibration = OUT / "context_calibration_2026-09-15.json"
    calibration.write_text(json.dumps({"model": "gpt-5.6-sol", "stable_context": context,
        "trace_sha256": sha(run / "trace.jsonl"), "labels_opened": False}, sort_keys=True, indent=2) + "\n")
    requirements_path = OUT / "release_requirements.json"
    requirements = json.loads(requirements_path.read_text())
    prior = requirements["expected_stable_context"]
    requirements["expected_stable_context"] = context
    requirements["resume_context_calibration"] = "context_calibration_2026-09-15.json"
    requirements["resume_context_changed"] = prior != context
    requirements["labels_opened"] = False
    requirements_path.write_text(json.dumps(requirements, sort_keys=True, indent=2) + "\n")
    amendment = OUT / "comparison_release_resume_freeze.json"
    amendment.write_text(json.dumps({
        "frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "reason": "execution resumed on 2026-09-15 before any B4 comparison item or label opening",
        "original_release_freeze_sha256": sha(OUT / "comparison_release_freeze.json"),
        "resume_context_calibration_sha256": sha(calibration),
        "release_requirements_sha256": sha(requirements_path),
        "supervisor_sha256": sha(Path(__file__)),
        "labels_opened": False,
        "b4_comparison_items_started_before_amendment": 0,
    }, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"resume_release_freeze_sha256": sha(amendment),
                      "context_changed": prior != context}), flush=True)
    from stage4step3_run import b4_cell
    for index in range(1, 11):
        try:
            b4_cell(f"cmp_{index:03d}")
        except BaseException as exc:
            print(json.dumps({"cell": f"cmp_{index:03d}", "supervisor_error": f"{type(exc).__name__}: {exc}"}), flush=True)


if __name__ == "__main__":
    main()
