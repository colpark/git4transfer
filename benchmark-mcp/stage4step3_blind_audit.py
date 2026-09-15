"""Create the pre-label coverage/content audit and execution amendment.

This is explicitly an automated audit.  It does not impersonate the human
audit requested by the prospective release requirements.  The substitution is
recorded as a protocol deviation authorized by the user's instruction to
complete the sealed-label evaluation.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from stage4step2e_contract import load_contract, validate_answer
from stage4step3_finalize import claude_text, items
from stage4step3_prompt import parse_answer
from stage4step3_run import observed_context


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
AUDIT = OUT / "blind_content_audit.json"
SUMMARY = OUT / "mechanical_validation_summary.json"
AMENDMENT = OUT / "evaluation_execution_amendment.json"
FORBIDDEN_PROMPT_ONLY_CLAIMS = re.compile(
    r"(?i)(?:\b(?:i|we)\s+(?:read|opened|observed|measured|queried|used)\b"
    r"|\baccording to (?:the )?(?:pdb|fasta|file|database)\b"
    r"|\b(?:tool|receipt|file)\s+(?:showed|returned|indicated)\b)"
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reject(reason: str, checks: dict | None = None) -> dict:
    return {"accepted": False, "reason": reason, "checks": checks or {}}


def approve(reason: str, checks: dict) -> dict:
    return {"accepted": True, "reason": reason, "checks": checks}


def prompt_only_decision(arm: str, row: dict) -> dict:
    neutral = row["neutral_item_id"]
    run = OUT / "runs" / arm / neutral
    meta_path = run / "meta.json"
    if not meta_path.is_file():
        marker = run / "interrupted.json"
        detail = json.loads(marker.read_text()).get("reason") if marker.is_file() else "missing terminal record"
        return reject(f"run unavailable: {detail}")
    meta = json.loads(meta_path.read_text())
    if meta.get("timed_out") or meta.get("exit_code") not in (None, 0) or meta.get("error"):
        return reject(meta.get("error") or
                      f"process exit={meta.get('exit_code')} timed_out={meta.get('timed_out')}")
    try:
        text = claude_text(run / "trace.jsonl") if arm == "b1" else (run / "answer.txt").read_text()
        contract = json.loads((ROOT / row["contract_path"]).read_text())
        answer = parse_answer(text, tuple(contract["candidates"]), neutral)
    except Exception as exc:  # Freeze the exact parser outcome as coverage, not a retry.
        return reject(f"structured-answer validation failed: {type(exc).__name__}: {exc}")
    prose = " ".join(
        [entry["basis"] + " " + entry["would_overturn"] for entry in answer["selected"]]
        + [entry["reason"] for entry in answer["rejected"]]
    )
    forbidden = sorted({match.group(0).lower()
                        for match in FORBIDDEN_PROMPT_ONLY_CLAIMS.finditer(prose)})
    if forbidden:
        return reject("prompt-only prose implies unavailable evidence",
                      {"forbidden_terms": forbidden})
    return approve("schema-valid prompt-only prediction with no evidence/tool/file claims", {
        "structured_answer_valid": True,
        "candidate_count": len(contract["candidates"]),
        "empty_evidence_and_validation_arrays": True,
        "forbidden_claim_terms": [],
    })


def b4_decision(row: dict, expected_context: dict) -> tuple[dict, dict]:
    neutral = row["neutral_item_id"]
    run = OUT / "runs/b4" / neutral
    meta = json.loads((run / "meta.json").read_text())
    status = {"exit_code": meta.get("exit_code"), "timed_out": meta.get("timed_out")}
    if meta.get("timed_out") or meta.get("exit_code") != 0:
        return reject(f"process exit={meta.get('exit_code')} timed_out={meta.get('timed_out')}") , status

    context = observed_context(run / "trace.jsonl")
    status["observed_context"] = context
    status["context_matches_gate"] = context == expected_context
    if context != expected_context:
        return reject("stable received context differs from prospective gate",
                      {"expected": expected_context, "observed": context}), status

    mechanical = run / "mechanical_integrity.json"
    if not mechanical.is_file():
        return reject("repaired mechanical validation decision missing"), status
    decision = json.loads(mechanical.read_text())
    if decision.get("structural_and_receipt_integrity_passed") is not True:
        return reject("repaired mechanical validation did not pass"), status

    contract = load_contract(ROOT / row["contract_path"])
    submission_path = run / "submissions" / f"{neutral}.json"
    submission = json.loads(submission_path.read_text())
    verdict = validate_answer(submission.get("answer"), contract, run / "artifacts")
    if verdict != submission.get("validation"):
        return reject("submission validation is not reproducible"), status
    answer = submission["answer"]
    method = answer["method_summary"].lower()
    if re.search(r"\b(?:not|no)\b[^.]{0,100}\bmeasured\b", method) is None:
        return reject("method summary lacks an explicit no-measured-outcome limitation"), status

    return approve("mechanically valid item-bound prediction; prose identifies proxy limits", {
        "mechanical_integrity_sha256": sha(mechanical),
        "submission_sha256": sha(submission_path),
        "trace_sha256": sha(run / "trace.jsonl"),
        "structured_answer_revalidated": True,
        "every_rank_has_variant-bound_fm_receipt": True,
        "trace_tools_within_allowlist": True,
        "no_measured_outcome_claim": True,
        "proxy_limit_explicit": True,
    }), status


def main() -> None:
    if any(path.exists() for path in (AUDIT, SUMMARY, AMENDMENT,
                                      OUT / "blind_bundle_manifest.json",
                                      OUT / "comparison_rows.csv")):
        raise SystemExit("audit/amendment or label-stage artifacts already exist")

    requirements = json.loads((OUT / "release_requirements.json").read_text())
    expected_context = requirements["expected_stable_context"]
    decisions: dict[str, dict] = {}
    mechanical: dict[str, dict] = {}
    for row in items():
        neutral = row["neutral_item_id"]
        decisions[f"b1/{neutral}"] = prompt_only_decision("b1", row)
        decisions[f"b2/{neutral}"] = prompt_only_decision("b2", row)
        decisions[f"b4/{neutral}"], mechanical[neutral] = b4_decision(row, expected_context)

    audit_body = {
        "authorship": "automated_agent",
        "audit_type": "blind_prelabel_content_and_coverage_audit",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "labels_opened_during_audit": False,
        "human_audit_substitution": True,
        "protocol_deviation": "The prospective human-content-audit requirement was not met; an automated audit was used on the user's explicit instruction to complete evaluation.",
        "checks": {
            "prompt_only": "Frozen parser validity plus rejection of unavailable evidence/tool/file claims.",
            "b4": "Repaired mechanical validation, frozen context equality, answer/receipt revalidation, allowlisted traces, and explicit proxy/no-measured-outcome language.",
        },
        "decisions": decisions,
    }
    AUDIT.write_text(json.dumps(audit_body, sort_keys=True, indent=2) + "\n")

    summary_body = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "labels_opened": False,
        "validator_repair_amendment_sha256": sha(OUT / "validator_repair_amendment.json"),
        "b4": mechanical,
        "automated_audit_accepted": [n for n in sorted(mechanical)
                                     if decisions[f"b4/{n}"]["accepted"]],
        "coverage": {
            arm: sum(decisions[f"{arm}/cmp_{i:03d}"]["accepted"] for i in range(1, 11))
            for arm in ("b1", "b2", "b4")
        },
    }
    SUMMARY.write_text(json.dumps(summary_body, sort_keys=True, indent=2) + "\n")

    amendment_body = {
        "amended_at_utc": datetime.now(timezone.utc).isoformat(),
        "authorization": "User explicitly requested comprehensive sealed-label evaluation and the validator repair on 2026-09-15.",
        "labels_opened_before_amendment": False,
        "model_predictions_rerun_or_changed": False,
        "primary_metrics_changed": False,
        "primary_metrics": ["per-item Spearman correlation", "precision at 10"],
        "exploratory_metrics_postspecified": True,
        "exploratory_metrics": [
            "Kendall tau-b", "Pearson correlation", "precision at 5", "precision at 20",
            "NDCG at 10", "reciprocal rank of the true-best candidate", "top-1 hit",
            "top-5 overlap", "normalized best-in-top-10 regret", "bootstrap intervals",
            "paired win/tie/loss and paired mean differences",
        ],
        "protocol_deviations": [
            "A repaired validator was added because frozen launch records omitted prompt_path.",
            "Three successful-process B4 runs failed the frozen base-instruction context hash and are coverage failures.",
            "The required human content audit was replaced by a disclosed automated audit under the user's instruction.",
        ],
        "supersedes_prelabel_audit": (
            "blind_content_audit_v1.json" if (OUT / "blind_content_audit_v1.json").is_file()
            else None
        ),
        "supersedes_execution_amendment": (
            "evaluation_execution_amendment_v1.json"
            if (OUT / "evaluation_execution_amendment_v1.json").is_file() else None
        ),
        "validator_repair_amendment_sha256": sha(OUT / "validator_repair_amendment.json"),
        "mechanical_validation_summary_sha256": sha(SUMMARY),
        "blind_content_audit_sha256": sha(AUDIT),
        "frozen_primary_evaluator_sha256": sha(ROOT / "benchmark-mcp/stage4step3_finalize.py"),
        "frozen_stage3_evaluator_sha256": sha(ROOT / "benchmark-mcp/stage3_evaluate.py"),
    }
    AMENDMENT.write_text(json.dumps(amendment_body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"coverage": summary_body["coverage"],
                      "audit_sha256": sha(AUDIT), "amendment_sha256": sha(AMENDMENT)},
                     sort_keys=True))


if __name__ == "__main__":
    main()
