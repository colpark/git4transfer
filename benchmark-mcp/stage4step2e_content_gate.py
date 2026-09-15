"""Human-bound content gate before a B4 v3 blind prediction can be exported."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from stage4step2e_contract import load_contract, ranking_scores


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()
    run, contract = Path(args.run).resolve(), load_contract(Path(args.contract).resolve())
    audit_path = run / "human_content_audit.json"
    required = {"authorship", "auditor", "decision", "trace_sha256", "submission_sha256",
                "mechanical_integrity_sha256", "prose_claims_supported_by_receipts",
                "no_measured_outcome_claims", "no_fabricated_files_calls_or_receipts", "notes"}
    if not audit_path.is_file():
        raise SystemExit("human_content_audit.json is required; an automated agent must not create it")
    audit = json.loads(audit_path.read_text())
    if set(audit) != required or audit.get("authorship") != "human" or not audit.get("auditor"):
        raise SystemExit("human content audit schema/authorship is invalid")
    if audit.get("decision") != "APPROVE_UNSCORED_EXPORT":
        raise SystemExit("human content audit did not approve unscored export")
    expected = {"trace_sha256": sha(run / "trace.jsonl"),
                "submission_sha256": sha(run / "submissions" / f"{contract['neutral_item_id']}.json"),
                "mechanical_integrity_sha256": sha(run / "mechanical_integrity.json")}
    if any(audit.get(k) != v for k, v in expected.items()):
        raise SystemExit("human audit is not bound to the current run")
    for field in ("prose_claims_supported_by_receipts", "no_measured_outcome_claims",
                  "no_fabricated_files_calls_or_receipts"):
        if audit.get(field) is not True:
            raise SystemExit(f"human content audit failed: {field}")
    if not isinstance(audit.get("notes"), str):
        raise SystemExit("human audit notes must be prose")
    blind = run / "blind_prediction.json"
    if blind.exists() or (run / "content_integrity.json").exists():
        raise SystemExit("refusing to overwrite content-gated export")
    submission = json.loads((run / "submissions" / f"{contract['neutral_item_id']}.json").read_text())
    answer = submission["answer"]
    payload = {"neutral_item_id": contract["neutral_item_id"], "policy_id": contract["policy_id"],
               "answer": answer, "rank_scores": ranking_scores(answer), "scored": False,
               "evaluation_authorized": False, "human_content_audit_sha256": sha(audit_path)}
    blind.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    result = {"content_export_passed": True, "scored": False, "evaluation_authorized": False,
              "blind_prediction_sha256": sha(blind), "human_content_audit_sha256": sha(audit_path)}
    (run / "content_integrity.json").write_text(json.dumps(result, sort_keys=True, indent=2) + "\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
