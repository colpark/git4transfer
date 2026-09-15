"""Fail-closed cohort release gate for B4 v3. No model or label access."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2e_2026-09-14"


def decision() -> dict:
    req = json.loads((OUT / "release_requirements.json").read_text())
    endpoints = json.loads((OUT / "endpoint_readiness.json").read_text())
    blockers = []
    if req.get("b1_ruling") != "APPROVED":
        blockers.append("B1_RULING_OUTSTANDING")
    if req.get("batch_one_open") is not True or req.get("cohort_authorized") is not True:
        blockers.append("COHORT_NOT_AUTHORIZED")
    immutable = req.get("immutable_model_id")
    if not immutable and req.get("moving_alias_panel_waiver") is not True:
        blockers.append("NO_IMMUTABLE_MODEL_ID_OR_PANEL_WAIVER")
    if req.get("irreducible_candidate_pattern_recognition") != "PANEL_ACCEPTED":
        blockers.append("PRETRAINED_RECOGNITION_RISK_NOT_ACCEPTED")
    if req.get("platform_catalog_residual_visibility") != "PANEL_ACCEPTED":
        blockers.append("PLATFORM_CATALOG_RESIDUALS_NOT_ACCEPTED")
    if req.get("assay_proxy_alignment_limit") != "PANEL_ACCEPTED":
        blockers.append("ASSAY_PROXY_ALIGNMENT_LIMIT_NOT_ACCEPTED")
    if endpoints.get("items") != 145 or endpoints.get("incomplete_metadata_items") != 0:
        blockers.append("ENDPOINT_REGISTRY_INCOMPLETE")
    stable = req.get("expected_stable_context") or {}
    required_context = {"base_instructions_sha256", "developer_message_sha256", "cli_version",
                        "approval_policy", "sandbox_type"}
    if set(stable) != required_context or not stable["base_instructions_sha256"]:
        blockers.append("STABLE_CONTEXT_GATE_INCOMPLETE")
    if req.get("v3_context_calibration_captured") is not True:
        blockers.append("V3_STABLE_CONTEXT_NOT_YET_CAPTURED")
    return {"cohort_release": not blockers, "blockers": blockers,
            "items": endpoints.get("items"), "labels_opened": False, "model_calls": 0}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("report", "enforce"))
    args = parser.parse_args()
    result = decision()
    print(json.dumps(result, sort_keys=True))
    if args.mode == "enforce" and not result["cohort_release"]:
        raise SystemExit("B4 v3 cohort release denied: " + ", ".join(result["blockers"]))


if __name__ == "__main__":
    main()
