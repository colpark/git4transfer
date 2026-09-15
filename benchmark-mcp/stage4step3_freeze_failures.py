"""Write explicit fail-closed mechanical decisions for context-gate failures."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    audit_path = OUT / "blind_content_audit.json"
    audit = json.loads(audit_path.read_text())["decisions"]
    written = []
    for neutral in ("cmp_004", "cmp_008", "cmp_009"):
        run = OUT / "runs/b4" / neutral
        target = run / "mechanical_integrity.json"
        if target.exists():
            raise SystemExit(f"refusing to replace decision for {neutral}")
        decision = audit[f"b4/{neutral}"]
        if decision.get("accepted") is not False or decision.get("reason") != (
                "stable received context differs from prospective gate"):
            raise SystemExit(f"audit does not bind expected context failure for {neutral}")
        body = {
            "structural_and_receipt_integrity_passed": False,
            "broad_integrity_passed": False,
            "human_content_audit_required": True,
            "labels_opened": False,
            "evaluation_authorized": False,
            "failure_stage": "stable_context_gate",
            "failure_reason": decision["reason"],
            "trace_sha256": sha(run / "trace.jsonl"),
            "blind_content_audit_sha256": sha(audit_path),
            "validator_repair_amendment_sha256": sha(OUT / "validator_repair_amendment.json"),
        }
        target.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
        written.append({"neutral_item_id": neutral, "decision_sha256": sha(target)})
    manifest = {
        "labels_opened": False,
        "purpose": "Explicit fail-closed decisions so blind assembly preserves the substantive context-gate reason.",
        "decisions": written,
    }
    target = OUT / "mechanical_failure_decisions.json"
    target.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"written": written, "manifest_sha256": sha(target)}, sort_keys=True))


if __name__ == "__main__":
    main()
