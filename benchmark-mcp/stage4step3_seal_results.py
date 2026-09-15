"""Seal the completed primary and exploratory evaluation artifacts."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
TARGET = OUT / "completed_evaluation_manifest.json"
FILES = (
    "validator_repair_amendment.json",
    "mechanical_validation_summary.json",
    "mechanical_failure_decisions.json",
    "blind_content_audit.json",
    "evaluation_execution_amendment.json",
    "blind_bundle_manifest.json",
    "blind_floor_c.jsonl",
    "blind_floor_m.jsonl",
    "blind_b1.jsonl",
    "blind_b2.jsonl",
    "blind_b4.jsonl",
    "comparison_rows.csv",
    "comparison_summary.json",
    "comparison.md",
    "evaluation_integrity.json",
    "comprehensive_metric_rows.csv",
    "comprehensive_summary.json",
    "comprehensive_report.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if TARGET.exists():
        raise SystemExit("completed evaluation manifest already exists")
    missing = [name for name in FILES if not (OUT / name).is_file()]
    if missing:
        raise SystemExit("missing evaluation artifacts: " + ", ".join(missing))
    integrity = json.loads((OUT / "evaluation_integrity.json").read_text())
    if integrity.get("other_135_labels_opened") is not False:
        raise SystemExit("unexpected label scope")
    body = {
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "COMPLETE_WITH_DISCLOSED_PROTOCOL_DEVIATIONS",
        "authorized_labels_opened": integrity["labels_exposed_for"],
        "other_135_labels_opened": False,
        "model_predictions_rerun": False,
        "files": {name: sha(OUT / name) for name in FILES},
        "analysis_code": {
            "validator_repair": sha(ROOT / "benchmark-mcp/stage4step3_validate_repair.py"),
            "blind_audit": sha(ROOT / "benchmark-mcp/stage4step3_blind_audit.py"),
            "frozen_primary_evaluator": sha(ROOT / "benchmark-mcp/stage4step3_finalize.py"),
            "comprehensive_evaluator": sha(ROOT / "benchmark-mcp/stage4step3_comprehensive.py"),
        },
    }
    TARGET.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"manifest": str(TARGET), "sha256": sha(TARGET)}, sort_keys=True))


if __name__ == "__main__":
    main()
