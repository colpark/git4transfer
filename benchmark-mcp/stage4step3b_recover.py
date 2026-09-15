"""Post-hoc Stage 4 Step 3b recovery using frozen B4 traces only.

The only gate normalization is the one literal cosmetic heading delta proven
in gate_diagnosis.md.  This program has no model-call path.  Its evaluator
opens only the ten assay members already authorized and opened in Step 3.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pilot_score import full_ranking
from stage3_evaluate import label_map, precision_at_10, spearman
from stage3_w1 import RAW
from stage4step2e_contract import ContractError, load_contract, ranking_scores, validate_answer, validate_artifact
from stage4step3_validate import audit_trace_pairs, result_receipt, rollout_path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/benchmark/stage4step3_2026-09-14"
DEST = ROOT / "results/benchmark/stage4step3b_2026-09-15"
ITEMS = tuple(f"cmp_{index:03d}" for index in range(1, 11))
RECOVER = ("cmp_004", "cmp_008", "cmp_009")
BEFORE = ("cmp_002", "cmp_003", "cmp_005", "cmp_006", "cmp_007", "cmp_010")
AFTER = tuple(item for item in ITEMS if item != "cmp_001")
ARMS = ("floor_c", "floor_m", "b4")
ARM_NAMES = {"floor_c": "Floor C", "floor_m": "Floor M", "b4": "B4"}
HEADING_VARIANTS = {"# Destructive actions", "# Destructive Actions"}
HEADING_CANONICAL = "# Destructive Actions"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def items() -> list[dict]:
    rows = read_jsonl(SOURCE / "blind_item_manifest_internal.jsonl")
    if [row["neutral_item_id"] for row in rows] != list(ITEMS):
        raise RuntimeError("ten-item manifest changed")
    return rows


def extract_context(trace: Path) -> dict:
    events = read_jsonl(trace)
    thread_ids = {event.get("thread_id") for event in events if event.get("type") == "thread.started"}
    if len(thread_ids) != 1:
        raise RuntimeError(f"{trace}: expected one thread id")
    rollout_file = rollout_path(next(iter(thread_ids)))
    rollout = read_jsonl(rollout_file)
    session = next(event["payload"] for event in rollout if event.get("type") == "session_meta")
    world = next(event["payload"]["state"] for event in rollout if event.get("type") == "world_state")
    turn = next(event["payload"] for event in rollout if event.get("type") == "turn_context")
    users: list[str] = []
    developers: list[str] = []
    for event in rollout:
        payload = event.get("payload") or {}
        if (event.get("type") == "response_item" and payload.get("type") == "message"
                and payload.get("role") in {"user", "developer"}):
            text = "".join(part.get("text", "") for part in payload.get("content", [])
                           if isinstance(part, dict))
            (users if payload["role"] == "user" else developers).append(text)
    return {
        "thread_id": next(iter(thread_ids)),
        "rollout_file": rollout_file,
        "rollout_sha256": sha(rollout_file),
        "base": (session.get("base_instructions") or {}).get("text", ""),
        "developers": developers,
        "users": users,
        "cli_version": session.get("cli_version"),
        "approval_policy": turn.get("approval_policy"),
        "sandbox_type": (turn.get("sandbox_policy") or {}).get("type"),
        "world": world,
    }


def normalize_base(text: str) -> str:
    lines = text.splitlines(keepends=True)
    normalized: list[str] = []
    for line in lines:
        ending = "\n" if line.endswith("\n") else ""
        body = line[:-1] if ending else line
        normalized.append((HEADING_CANONICAL if body in HEADING_VARIANTS else body) + ending)
    return "".join(normalized)


def gate_view(context: dict) -> dict:
    return {
        "normalized_base_instructions_sha256": sha_text(normalize_base(context["base"])),
        "developer_message_sha256": [sha_text(text) for text in context["developers"]],
        "cli_version": context["cli_version"],
        "sandbox_type": context["sandbox_type"],
        "approval_policy": context["approval_policy"],
    }


def gate_accepts(received: dict, reference: dict) -> bool:
    return gate_view(received) == gate_view(reference)


def calibration_contexts() -> tuple[dict, dict]:
    original = extract_context(SOURCE / "runs/b4_context_calibration/trace.jsonl")
    active = extract_context(SOURCE / "runs/b4_context_calibration_2026-09-15/trace.jsonl")
    original_pin = json.loads((SOURCE / "context_calibration.json").read_text())["stable_context"]
    active_pin = json.loads((SOURCE / "context_calibration_2026-09-15.json").read_text())["stable_context"]
    for context, pin in ((original, original_pin), (active, active_pin)):
        observed = {
            "base_instructions_sha256": sha_text(context["base"]),
            "developer_message_sha256": [sha_text(text) for text in context["developers"]],
            "cli_version": context["cli_version"],
            "sandbox_type": context["sandbox_type"],
            "approval_policy": context["approval_policy"],
        }
        if observed != pin:
            raise RuntimeError("calibration text does not reproduce its recorded raw fingerprint")
    return original, active


def write_controls() -> None:
    target = DEST / "gate_controls.json"
    if target.exists():
        raise SystemExit(f"refusing to replace {target}")
    original, active = calibration_contexts()
    checks: dict[str, bool] = {}
    checks["positive_proven_heading_delta_passes"] = gate_accepts(original, active)

    changed = dict(original)
    changed["base"] = original["base"].replace(
        "Be cautious with commands or API calls", "Be permissive with commands or API calls", 1)
    checks["must_fire_instruction_sentence_change"] = not gate_accepts(changed, active)

    changed = dict(original)
    changed["developers"] = [*original["developers"]]
    changed["developers"][0] += "\nBehaviour-changing control."
    checks["must_fire_developer_message_change"] = not gate_accepts(changed, active)

    for key, value in (("cli_version", "0.154.1"), ("sandbox_type", "workspace-write"),
                       ("approval_policy", "on-request")):
        changed = dict(original)
        changed[key] = value
        checks[f"must_fire_{key}_change"] = not gate_accepts(changed, active)

    body = {
        "created_at_utc": now(),
        "labels_opened_during_controls": False,
        "model_calls": 0,
        "normalization": {
            "base_instructions": (
                "Canonicalize only an exact whole-line Markdown H1 equal to "
                "'# Destructive actions' or '# Destructive Actions' as '# Destructive Actions'."
            ),
            "developer_messages": "Identity; ordered messages and bytes are unchanged.",
            "runtime_controls": "Exact equality; no normalization.",
            "all_other_base_text": "Identity; bytes are unchanged.",
        },
        "checks": checks,
        "all_pass": all(checks.values()),
    }
    if not body["all_pass"]:
        raise RuntimeError("repaired stable-context gate controls failed")
    DEST.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps(body, sort_keys=True))


def freeze() -> None:
    amendment = DEST / "posthoc_gate_amendment.json"
    freeze_path = DEST / "recovery_freeze.json"
    if amendment.exists() or freeze_path.exists():
        raise SystemExit("refusing to replace post-hoc amendment or recovery freeze")
    controls = json.loads((DEST / "gate_controls.json").read_text())
    if controls.get("all_pass") is not True:
        raise SystemExit("gate controls are not passing")
    diagnosis = (DEST / "gate_diagnosis.md").read_text()
    if "**COSMETIC**" not in diagnosis:
        raise SystemExit("Task 1 did not authorize the cosmetic branch")
    completed = json.loads((SOURCE / "completed_evaluation_manifest.json").read_text())
    authorized = completed["authorized_labels_opened"]
    expected = [row["internal_assay_id"] for row in items()]
    if authorized != expected or completed.get("other_135_labels_opened") is not False:
        raise SystemExit("prior label-opening scope cannot be verified")
    frozen_runs = {}
    for item in RECOVER:
        run = SOURCE / "runs/b4" / item
        historical = json.loads((run / "mechanical_integrity.json").read_text())
        if historical.get("failure_stage") != "stable_context_gate":
            raise SystemExit(f"{item}: historical disposition changed")
        if historical.get("trace_sha256") != sha(run / "trace.jsonl"):
            raise SystemExit(f"{item}: historical trace hash mismatch")
        frozen_runs[item] = {
            "trace_sha256": sha(run / "trace.jsonl"),
            "submission_sha256": sha(run / "submissions" / f"{item}.json"),
            "meta_sha256": sha(run / "meta.json"),
        }
    amendment_body = {
        "amended_at_utc": now(),
        "classification": "COSMETIC",
        "post_hoc": True,
        "reason": (
            "The raw base-instructions gate rejected three completed cells solely because the Markdown "
            "heading '# Destructive Actions' differed in capitalization from '# Destructive actions'. "
            "Task 1 established that all instruction sentences, developer messages, tools/grants, and "
            "runtime controls were unchanged."
        ),
        "named_threat": (
            "The agent receives behaviour-affecting instructions, tools/grants, or runtime controls that "
            "differ across cells, so B4 is not one arm."
        ),
        "permitted_change": "Stable-context gate normalization only.",
        "normalization_spec": controls["normalization"],
        "model_predictions_rerun_or_changed": False,
        "model_calls": 0,
        "contract_changed": False,
        "scorer_changed": False,
        "prompts_changed": False,
        "arm_definitions_changed": False,
        "item_list_changed": False,
        "authorized_ten_labels_previously_opened": authorized,
        "other_135_labels_opened": False,
        "frozen_source_runs": frozen_runs,
        "gate_diagnosis_sha256": sha(DEST / "gate_diagnosis.md"),
        "gate_controls_sha256": sha(DEST / "gate_controls.json"),
    }
    amendment.write_text(json.dumps(amendment_body, sort_keys=True, indent=2) + "\n")

    dependencies = [
        Path(__file__),
        ROOT / "benchmark-mcp/stage4step3b_gate_diagnose.py",
        ROOT / "benchmark-mcp/stage4step3_validate.py",
        ROOT / "benchmark-mcp/stage4step2e_contract.py",
        ROOT / "benchmark-mcp/stage3_evaluate.py",
        ROOT / "benchmark-mcp/pilot_score.py",
        SOURCE / "context_calibration.json",
        SOURCE / "context_calibration_2026-09-15.json",
        SOURCE / "blind_item_manifest_internal.jsonl",
        SOURCE / "blind_floor_c.jsonl",
        SOURCE / "blind_floor_m.jsonl",
        SOURCE / "blind_b4.jsonl",
        SOURCE / "completed_evaluation_manifest.json",
        DEST / "gate_diagnosis.md",
        DEST / "gate_controls.json",
        amendment,
    ]
    freeze_body = {
        "frozen_at_utc": now(),
        "post_hoc": True,
        "labels_already_opened_for_exact_ten_item_set": True,
        "other_135_labels_opened": False,
        "model_calls": 0,
        "files": {str(path.relative_to(ROOT)): sha(path) for path in dependencies},
    }
    freeze_path.write_text(json.dumps(freeze_body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"amendment_sha256": sha(amendment),
                      "recovery_freeze_sha256": sha(freeze_path)}, sort_keys=True))


def verify_freeze() -> dict:
    path = DEST / "recovery_freeze.json"
    frozen = json.loads(path.read_text())
    if frozen.get("post_hoc") is not True or frozen.get("model_calls") != 0:
        raise RuntimeError("invalid recovery freeze state")
    for relative, digest in frozen["files"].items():
        if sha(ROOT / relative) != digest:
            raise RuntimeError(f"recovery freeze dependency mismatch: {relative}")
    return frozen


def validate_one(item: str, reference: dict) -> dict:
    row = next(row for row in items() if row["neutral_item_id"] == item)
    run = SOURCE / "runs/b4" / item
    meta = json.loads((run / "meta.json").read_text())
    if meta.get("timed_out") or meta.get("exit_code") != 0:
        raise RuntimeError(f"{item}: process was not a completed successful run")
    historical = json.loads((run / "mechanical_integrity.json").read_text())
    if historical.get("failure_stage") != "stable_context_gate":
        raise RuntimeError(f"{item}: not an authorized context-gate recovery")
    if historical.get("trace_sha256") != sha(run / "trace.jsonl"):
        raise RuntimeError(f"{item}: trace changed since fail-closed decision")

    prompt = ROOT / row["b4_prompt_path"]
    contract_path = ROOT / row["contract_path"]
    if sha(prompt) != row["b4_prompt_sha256"] or sha(contract_path) != row["contract_sha256"]:
        raise RuntimeError(f"{item}: frozen prompt or contract changed")
    launch = json.loads((run / "launch.json").read_text())
    if sha(prompt) != launch.get("prompt_sha256"):
        raise RuntimeError(f"{item}: launch prompt hash mismatch")

    context = extract_context(run / "trace.jsonl")
    if not context["users"] or context["users"][-1] != prompt.read_text():
        raise RuntimeError(f"{item}: received prompt differs from frozen prompt")
    if not gate_accepts(context, reference):
        raise RuntimeError(f"{item}: normalized stable-context threat gate fired")
    world = context["world"]
    requirements = json.loads((SOURCE / "release_requirements.json").read_text())
    expected_model = requirements.get("immutable_model_id")
    if expected_model:
        if world.get("model") != expected_model:
            raise RuntimeError(f"{item}: immutable model mismatch")
    elif requirements.get("moving_alias_panel_waiver") is not True:
        raise RuntimeError("no immutable model identity or panel waiver")
    if world.get("apps_instructions") is not False:
        raise RuntimeError(f"{item}: apps unexpectedly enabled")
    if (world.get("orchestrator_skills") or {}).get("enabled") is not False:
        raise RuntimeError(f"{item}: orchestrator skills unexpectedly enabled")

    events = read_jsonl(run / "trace.jsonl")
    try:
        paired = audit_trace_pairs(events)
    except ContractError as exc:
        raise RuntimeError(f"{item}: {exc}") from exc
    submission_path = run / "submissions" / f"{item}.json"
    submission = json.loads(submission_path.read_text())
    starts = [event["item"] for event in events if event.get("type") == "item.started"
              and event.get("item", {}).get("type") == "mcp_tool_call"
              and event["item"].get("tool") == "submit_answer"]
    if len(starts) != 1 or starts[0].get("arguments", {}).get("answer") != submission.get("answer"):
        raise RuntimeError(f"{item}: frozen trace submission differs from stored answer")
    if paired["submission"].get("status") != "completed":
        raise RuntimeError(f"{item}: submit_answer was not completed")

    contract = load_contract(contract_path)
    verdict = validate_answer(submission.get("answer"), contract, run / "artifacts")
    if verdict != submission.get("validation") or verdict.get("accepted") is not True:
        raise RuntimeError(f"{item}: stored contract verdict is not reproducible")
    answer = submission["answer"]
    if re.search(r"\b(?:not|no)\b[^.]{0,100}\bmeasured\b",
                 answer["method_summary"].lower()) is None:
        raise RuntimeError(f"{item}: method summary omits no-measured-outcome limitation")

    artifact_receipts: dict[str, dict] = {}
    artifact_rows = []
    for path in sorted((run / "artifacts").glob("*/*.json")):
        body = json.loads(path.read_text())
        try:
            success = validate_artifact(body, path, contract, require_success=False)
        except ContractError as exc:
            raise RuntimeError(f"{item}: {exc}") from exc
        receipt = body["receipt"]
        artifact_receipts[receipt["call_id"]] = receipt
        artifact_rows.append({"call_id": receipt["call_id"], "successful": success,
                              "path": str(path), "sha256": sha(path)})
    completed_science = {key: value for key, value in paired["completed"].items()
                         if value.get("tool") != "submit_answer"}
    trace_receipts = {result_receipt(value).get("call_id"): result_receipt(value)
                      for value in completed_science.values()
                      if isinstance(result_receipt(value), dict)}
    if len(trace_receipts) != len(completed_science) or trace_receipts != artifact_receipts:
        raise RuntimeError(f"{item}: trace and artifact receipts differ")
    if len(artifact_receipts) != len(contract["candidates"]):
        raise RuntimeError(f"{item}: incomplete candidate receipt coverage")

    return {
        "neutral_item_id": item,
        "validated_at_utc": now(),
        "post_hoc_gate_repair": True,
        "accepted": True,
        "labels_opened_during_validation": False,
        "model_calls": 0,
        "thread_id": context["thread_id"],
        "trace_sha256": sha(run / "trace.jsonl"),
        "rollout_sha256": context["rollout_sha256"],
        "submission_sha256": sha(submission_path),
        "prompt_sha256": sha(prompt),
        "contract_sha256": verdict["contract_sha256"],
        "normalized_stable_context": gate_view(context),
        "raw_base_instructions_sha256": sha_text(context["base"]),
        "start_completion_pairs": len(paired["started"]),
        "science_receipt_count": len(artifact_receipts),
        "artifacts": artifact_rows,
        "checks": {
            "historical_trace_hash_unchanged": True,
            "received_prompt_byte_identical": True,
            "normalized_context_threat_absent": True,
            "runtime_controls_exact": True,
            "model_identity_or_waiver_valid": True,
            "apps_and_orchestrator_skills_disabled": True,
            "trace_pairs_complete": True,
            "stored_answer_equals_frozen_trace_argument": True,
            "contract_verdict_reproducible": True,
            "all_candidate_receipts_resolve_and_match_trace": True,
            "proxy_limit_explicit": True,
        },
    }


def validate() -> None:
    verify_freeze()
    validation_dir = DEST / "validation"
    if validation_dir.exists():
        raise SystemExit("refusing to replace Step 3b validation decisions")
    _, active = calibration_contexts()
    decisions = {item: validate_one(item, active) for item in RECOVER}
    validation_dir.mkdir(parents=True)
    for item, decision in decisions.items():
        (validation_dir / f"{item}.json").write_text(
            json.dumps(decision, sort_keys=True, indent=2) + "\n")
    summary = {
        "validated_at_utc": now(),
        "post_hoc": True,
        "model_calls": 0,
        "labels_opened_during_validation": False,
        "recovered": list(RECOVER),
        "coverage_before": {"scorable": 6, "attempted": 10},
        "coverage_after": {"scorable": 9, "attempted": 10},
        "decisions": {item: {"accepted": True, "sha256": sha(validation_dir / f"{item}.json")}
                      for item in RECOVER},
        "recovery_freeze_sha256": sha(DEST / "recovery_freeze.json"),
    }
    (DEST / "validation_summary.json").write_text(
        json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))


def assemble_blind() -> None:
    verify_freeze()
    target = DEST / "blind_bundle_manifest.json"
    blind_path = DEST / "blind_b4.jsonl"
    if target.exists() or blind_path.exists():
        raise SystemExit("refusing to replace Step 3b blind bundle")
    validation = json.loads((DEST / "validation_summary.json").read_text())
    if validation.get("recovered") != list(RECOVER):
        raise SystemExit("recovery validation is incomplete")
    old_rows = {row["neutral_item_id"]: row for row in read_jsonl(SOURCE / "blind_b4.jsonl")}
    if tuple(item for item in ITEMS if old_rows[item]["status"] == "SCORABLE") != BEFORE:
        raise SystemExit("prior B4 coverage set changed")
    new_rows = []
    for item in ITEMS:
        row = old_rows[item]
        if item in RECOVER:
            decision = json.loads((DEST / "validation" / f"{item}.json").read_text())
            if decision.get("accepted") is not True:
                raise SystemExit(f"{item}: repaired validation did not pass")
            submission = json.loads((SOURCE / "runs/b4" / item / "submissions" / f"{item}.json").read_text())
            row = {
                "neutral_item_id": item,
                "arm": "b4",
                "status": "SCORABLE",
                "coverage_failure_reason": "",
                "answer": submission["answer"],
                "post_hoc_recovery": True,
                "validation_sha256": sha(DEST / "validation" / f"{item}.json"),
            }
        new_rows.append(row)
    blind_path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in new_rows))
    if tuple(row["neutral_item_id"] for row in new_rows if row["status"] == "SCORABLE") != AFTER:
        raise RuntimeError("post-repair B4 coverage set is not exactly nine items")
    manifest = {
        "assembled_at_utc": now(),
        "post_hoc": True,
        "predictions_were_frozen_before_original_label_open": True,
        "bundle_assembled_after_exact_ten_labels_were_previously_opened": True,
        "model_predictions_rerun_or_changed": False,
        "model_calls": 0,
        "items": list(ITEMS),
        "other_135_labels_opened": False,
        "coverage": {"before": {"scorable": 6, "attempted": 10},
                     "after": {"scorable": 9, "attempted": 10}},
        "predictions": {
            "floor_c": {"path": str((SOURCE / "blind_floor_c.jsonl").relative_to(ROOT)),
                        "sha256": sha(SOURCE / "blind_floor_c.jsonl")},
            "floor_m": {"path": str((SOURCE / "blind_floor_m.jsonl").relative_to(ROOT)),
                        "sha256": sha(SOURCE / "blind_floor_m.jsonl")},
            "b4": {"path": str(blind_path.relative_to(ROOT)), "sha256": sha(blind_path)},
        },
        "prior_blind_b4_sha256": sha(SOURCE / "blind_b4.jsonl"),
        "prior_completed_evaluation_manifest_sha256": sha(SOURCE / "completed_evaluation_manifest.json"),
        "posthoc_gate_amendment_sha256": sha(DEST / "posthoc_gate_amendment.json"),
        "recovery_freeze_sha256": sha(DEST / "recovery_freeze.json"),
        "validation_summary_sha256": sha(DEST / "validation_summary.json"),
        "validator_decisions": {item: sha(DEST / "validation" / f"{item}.json") for item in RECOVER},
        "scorer_sha256": sha(Path(__file__)),
        "metric_implementation_sha256": sha(ROOT / "benchmark-mcp/stage3_evaluate.py"),
    }
    target.write_text(json.dumps(manifest, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"blind_bundle_sha256": sha(target), "b4_coverage": "9/10"}, sort_keys=True))


def verify_blind() -> dict:
    verify_freeze()
    manifest = json.loads((DEST / "blind_bundle_manifest.json").read_text())
    if manifest.get("items") != list(ITEMS) or manifest.get("model_calls") != 0:
        raise RuntimeError("invalid Step 3b blind manifest")
    for record in manifest["predictions"].values():
        if sha(ROOT / record["path"]) != record["sha256"]:
            raise RuntimeError(f"blind prediction hash mismatch: {record['path']}")
    dependencies = {
        "prior_blind_b4_sha256": SOURCE / "blind_b4.jsonl",
        "prior_completed_evaluation_manifest_sha256": SOURCE / "completed_evaluation_manifest.json",
        "posthoc_gate_amendment_sha256": DEST / "posthoc_gate_amendment.json",
        "recovery_freeze_sha256": DEST / "recovery_freeze.json",
        "validation_summary_sha256": DEST / "validation_summary.json",
        "scorer_sha256": Path(__file__),
        "metric_implementation_sha256": ROOT / "benchmark-mcp/stage3_evaluate.py",
    }
    for key, path in dependencies.items():
        if sha(path) != manifest[key]:
            raise RuntimeError(f"blind dependency hash mismatch: {key}")
    for item, digest in manifest["validator_decisions"].items():
        if sha(DEST / "validation" / f"{item}.json") != digest:
            raise RuntimeError(f"validator decision hash mismatch: {item}")
    return manifest


def load_floor(path: Path) -> dict[str, dict[str, float]]:
    result: dict[str, dict[str, float]] = defaultdict(dict)
    for row in read_jsonl(path):
        result[row["neutral_item_id"]][row["mutant"]] = float(row["score"])
    return result


def evaluate() -> None:
    manifest = verify_blind()
    rows_path = DEST / "evaluation_rows.csv"
    integrity_path = DEST / "evaluation_integrity.json"
    if rows_path.exists() or integrity_path.exists():
        raise SystemExit("refusing to repeat Step 3b label evaluation")
    item_rows = items()
    authorized = [row["internal_assay_id"] for row in item_rows]
    prior = json.loads((SOURCE / "completed_evaluation_manifest.json").read_text())
    if prior["authorized_labels_opened"] != authorized or prior.get("other_135_labels_opened") is not False:
        raise RuntimeError("authorized label scope differs from original evaluation")
    floors = {
        "floor_c": load_floor(SOURCE / "blind_floor_c.jsonl"),
        "floor_m": load_floor(SOURCE / "blind_floor_m.jsonl"),
    }
    b4_rows = {row["neutral_item_id"]: row for row in read_jsonl(DEST / "blind_b4.jsonl")}
    old = {(row["arm"], row["neutral_item_id"]): row
           for row in csv.DictReader((SOURCE / "comparison_rows.csv").open())}
    output = []
    opened_members = []
    with zipfile.ZipFile(RAW) as archive:
        for item in item_rows:
            neutral = item["neutral_item_id"]
            contract = json.loads((ROOT / item["contract_path"]).read_text())
            candidates = set(contract["candidates"])
            assay = item["internal_assay_id"]
            truth = label_map(archive, assay, candidates)
            opened_members.append(f"DMS_ProteinGym_substitutions/{assay}.csv")
            if set(truth) != candidates:
                raise RuntimeError(f"{neutral}: authorized label coverage incomplete")
            for arm in ARMS:
                status = "SCORABLE"
                reason = ""
                if arm in floors:
                    ranking = floors[arm][neutral]
                else:
                    record = b4_rows[neutral]
                    status = record["status"]
                    reason = record["coverage_failure_reason"]
                    ranking = ranking_scores(record["answer"]) if status == "SCORABLE" else None
                if status == "SCORABLE" and (ranking is None or set(ranking) != candidates
                                               or not all(math.isfinite(value) for value in ranking.values())):
                    raise RuntimeError(f"{arm}/{neutral}: blind ranking is incomplete")
                p10 = precision_at_10(ranking, truth) if ranking is not None else None
                rho = spearman(ranking, truth) if ranking is not None else None
                if ranking is not None and rho is None:
                    raise RuntimeError(f"{arm}/{neutral}: Spearman undefined")
                row = {
                    "neutral_item_id": neutral,
                    "assay_id": assay,
                    "published_quartile": item["published_quartile"],
                    "arm": arm,
                    "n_candidates": len(candidates),
                    "chance_p_at_10": 10 / len(candidates),
                    "status": status,
                    "coverage_failure_reason": reason,
                    "precision_at_10": "" if p10 is None else p10,
                    "spearman": "" if rho is None else rho,
                }
                prior_row = old.get((arm, neutral))
                if prior_row and prior_row["status"] == "SCORABLE":
                    if (abs(float(prior_row["precision_at_10"]) - float(p10)) > 1e-12
                            or abs(float(prior_row["spearman"]) - float(rho)) > 1e-12):
                        raise RuntimeError(f"{arm}/{neutral}: scorer no longer reproduces frozen result")
                output.append(row)
    with rows_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    integrity = {
        "evaluated_at_utc": now(),
        "post_hoc": True,
        "blind_bundle_sha256": sha(DEST / "blind_bundle_manifest.json"),
        "blind_hashes_verified_before_this_label_read": True,
        "labels_were_already_opened_in_original_step3_evaluation": True,
        "authorized_label_members_opened_by_this_scorer": opened_members,
        "authorized_label_count": len(opened_members),
        "other_135_labels_opened_by_this_scorer": False,
        "rows_sha256": sha(rows_path),
        "model_calls": 0,
        "reproduced_previously_scorable_rows": True,
        "source_label_archive_sha256_from_prior_frozen_evaluation": (
            json.loads((SOURCE / "comprehensive_summary.json").read_text())["provenance"]["label_archive_sha256"]
        ),
    }
    integrity_path.write_text(json.dumps(integrity, sort_keys=True, indent=2) + "\n")
    recovered = [row for row in output if row["arm"] == "b4" and row["neutral_item_id"] in RECOVER]
    print(json.dumps({"blind_bundle_sha256": manifest and sha(DEST / "blind_bundle_manifest.json"),
                      "recovered": recovered, "rows_sha256": sha(rows_path)}, sort_keys=True))


def load_evaluation() -> dict[tuple[str, str], dict]:
    rows = {(row["arm"], row["neutral_item_id"]): row
            for row in csv.DictReader((DEST / "evaluation_rows.csv").open())}
    if set(rows) != {(arm, item) for arm in ARMS for item in ITEMS}:
        raise RuntimeError("Step 3b evaluation row set is incomplete")
    return rows


def metric_mean(rows: dict, arm: str, subset: tuple[str, ...], metric: str) -> float:
    values = [float(rows[arm, item][metric]) for item in subset]
    return statistics.mean(values)


def write_gate_reflection() -> None:
    controls = json.loads((DEST / "gate_controls.json").read_text())
    text = f"""# Stable-context gate reflection

## (a) Named failure prevented

**Threat:** The agent receives behaviour-affecting instructions, a different tool list or grant, or different sandbox/approval controls on different cells, so the nominal B4 arm is not one arm and its results are not comparable.

The raw hash is only a proxy for this threat. The stop condition should be: **stop when the normalized received contexts differ in any behaviour-affecting instruction, ordered developer message, tool/grant content, CLI identity, sandbox type, or approval policy.**

## (b) Did a fourth developer hash constitute the failure?

No fourth developer-message hash exists in the three cells. `developer_message_sha256` is an ordered array of three simultaneously received developer messages, not three alternative permitted variants. Every cell exactly matched all three values in order. The only mismatch used by the active validator was the base-instructions SHA-256. Its complete diff was one heading-capitalization character and did not instantiate the named threat.

## (c) Why three rather than one?

The record shows three distinct developer-message layers: (1) skills and permission instructions, (2) `/root` team-agent instructions, and (3) the multi-agent delegation restriction. `stage4step3_run.py` collects every received developer message and hashes the resulting ordered list. No record states a rationale for the number three, and no record describes the hashes as alternatives. Therefore the reason for “three permitted variants” is **not recorded because that configuration did not exist**.

## (d) Normalized context

Yes, the gate should compare the instruction-bearing quantity after an exact, reviewable normalization. For this recovery the normalization is deliberately narrow:

1. Split base instructions into lines without otherwise changing bytes.
2. Canonicalize an exact whole line equal to `# Destructive actions` or `# Destructive Actions` to `# Destructive Actions`.
3. Leave every other base-instruction byte unchanged.
4. Leave every developer-message byte and its ordered position unchanged.
5. Compare `cli_version`, `sandbox_type`, and `approval_policy` by exact equality.
6. Hash the canonical object formed from the normalized base hash, ordered raw developer hashes, and those three exact runtime controls.

No general case-folding, whitespace deletion, path stripping, or regular-expression removal is allowed: those operations could hide a changed tool path or instruction. Session/thread IDs and timestamps were never part of this gate object; `turn_context.cwd` was also not included. If a future stable instruction field embeds a run-varying value, it must first be structurally named and shown by a must-fire control not to carry instruction content before being added to normalization.

## (e) Control status

The original gate shipped with **no context mutation control** in `test_stage4step2e.py`; its tests cover answer contracts, trace pairing, bound inputs, checkpoints, and tool surfaces. Therefore the original context gate was **not checked**, not passed. The later live rejection is an incident, not a prospective control.

The repaired gate ships with one positive cosmetic control and five must-fire controls. All {len(controls['checks'])} passed: a changed instruction sentence, developer message, CLI version, sandbox type, and approval policy each fire the repaired gate. See `gate_controls.json`.
"""
    (DEST / "gate_reflection.md").write_text(text)


def b2_counts() -> list[dict]:
    result = []
    for item in ITEMS:
        candidates = set(json.loads((SOURCE / "contracts" / f"{item}.json").read_text())["candidates"])
        answer = json.loads((SOURCE / "runs/b2" / item / "answer.txt").read_text())
        selected = answer.get("selected") if isinstance(answer, dict) else None
        names = [entry.get("mutant") for entry in selected if isinstance(entry, dict)] if isinstance(selected, list) else []
        result.append({"item": item, "count": len({name for name in names if name in candidates})})
    return result


def write_b2_contract() -> None:
    audit = json.loads((SOURCE / "blind_content_audit.json").read_text())["decisions"]
    counts = b2_counts()
    failure_rows = "\n".join(
        f"| {row['item']} | {audit['b2/' + row['item']]['reason'].removeprefix('structured-answer validation failed: ValueError: ')} | {row['count']} |"
        for row in counts
    )
    text = f"""# B2 contract diagnosis

## (a) Is the complement requirement explicit?

Yes. Every B2 comparison prompt contains these exact lines:

> “rejected contains every other candidate exactly once, each as an object with exactly mutant and reason.”

The same response paragraph also says:

> “selected contains exactly ten unique objects in rank order”

Thus the exact-set-difference requirement is explicit in the arm prompt, although the parser's diagnostic wording (“candidate complement”) is more compact than the prompt.

## (b) Valid unique picks independent of contract acceptance

| Cell | First strict rejection | Valid unique selected mutants in candidate set |
|---|---|---:|
{failure_rows}

Nine answers contain 10 valid unique picks. `cmp_004` contains 9 because one selected mutant is outside its supplied candidate set. These counts do not make the answers contract-valid and are not scores.

## (c) Precision-only extraction path

It did **not** fire. The three-item smoke's `stage4step2b_run.py` parsed raw JSON first, then called `pilot_score.selected_mutants(answer, candidates)` independently of strict `parse_answer` acceptance; that preserved P@10 whenever ten ranked, unique, in-candidate selections existed.

In Step 3, `stage4step3_finalize.prompt_answer` calls the strict `stage4step3_prompt.parse_answer` first. Any exception returns `(None, reason)`. Blind assembly then writes a whole-answer `COVERAGE FAILURE`, and the scorer never calls `selected_mutants`; it only calls `full_ranking` after strict acceptance. Therefore B2 is 0/10 measured coverage even though nine cells have a ten-pick set. This is a design/measurement failure, not a zero accuracy result. Per instruction, neither contract nor scorer is changed here.
"""
    (DEST / "b2_contract.md").write_text(text)


def write_metric_primacy() -> None:
    text = """# Metric primacy discrepancy

## Governing order

**Precision at ten is primary; Spearman is secondary.** The governing dated amendment is `results/benchmark/stage3b_2026-09-13/preregistration_v2.md`, which states:

> “where its metric order conflicts, this dated amendment controls subsequent reporting.”

and:

> “**Primary decision metric:** precision@10, macro-averaged across independent 50%-identity clusters. Print each item's chance baseline `10/n_candidates` beside its precision@10 and report `lift = precision@10 − 10/n_candidates` ... **Secondary:** per-item Spearman rho and its macro-average.”

The subsequent Stage 4 preparation preregistration confirms rather than changes that order:

> “Primary decision metric remains P@10, with per-item chance and lift; Spearman is secondary only for a complete, valid numeric ranking.”

## Drift

`comparison_10_prereg.md` later says, “The primary accuracy metric is per-item Spearman correlation ... Precision at ten is secondary,” and `comparison.md` repeats it. No recorded amendment identifies a metric-order change, gives a reason, marks it post-result, or supersedes the Stage 3b controlling clause. The Step 3 execution amendment even says `primary_metrics_changed: false`. Therefore this is **drift**, not an effective amendment.

On the six originally scorable paired B4 items, the metrics illustrate why the controlling order matters: B4 minus Floor M is **−0.033 P@10 (n=6)** but **+0.022 Spearman (n=6)**. The governing primary sentence is therefore that B4 trails Floor M by 0.033 in paired mean P@10 on those six items; the opposite-sign Spearman result is secondary.
"""
    (DEST / "metric_primacy.md").write_text(text)


def subset_table(rows: dict, subset: tuple[str, ...], title: str) -> list[str]:
    lines = [f"## {title}", "", f"Common B4-scorable set: {', '.join(subset)} (`n={len(subset)}` for every aggregate cell).", "",
             "### Item-level paired values", "",
             "| Item | Floor C P@10 (n=1) | Floor M P@10 (n=1) | B4 P@10 (n=1) | Floor C Spearman (n=1) | Floor M Spearman (n=1) | B4 Spearman (n=1) |",
             "|---|---:|---:|---:|---:|---:|---:|"]
    for item in subset:
        lines.append("| " + item + " | " + " | ".join(
            f"{float(rows[arm, item][metric]):.3f}"
            for metric in ("precision_at_10", "spearman") for arm in ARMS
        ) + " |")
    lines.extend(["", "### Paired-set means", "",
                  "| Arm | Mean P@10 | Mean Spearman |", "|---|---:|---:|"])
    for arm in ARMS:
        lines.append(f"| {ARM_NAMES[arm]} | {metric_mean(rows, arm, subset, 'precision_at_10'):.3f} (n={len(subset)}) | "
                     f"{metric_mean(rows, arm, subset, 'spearman'):.3f} (n={len(subset)}) |")
    for baseline in ("floor_m", "floor_c"):
        lines.append(
            f"| B4 − {ARM_NAMES[baseline]} | "
            f"{metric_mean(rows, 'b4', subset, 'precision_at_10') - metric_mean(rows, baseline, subset, 'precision_at_10'):+.3f} (n={len(subset)}) | "
            f"{metric_mean(rows, 'b4', subset, 'spearman') - metric_mean(rows, baseline, subset, 'spearman'):+.3f} (n={len(subset)}) |"
        )
    lines.append("")
    return lines


def write_paired_comparison() -> None:
    rows = load_evaluation()
    lines = [
        "# Paired comparison on B4-scorable items",
        "",
        "P@10 is primary and appears first; Spearman is secondary. Every cross-arm summary uses one "
        "common B4-scorable item set, and `n` is printed in every aggregate cell. Coverage failures "
        "are excluded rather than scored as zero. No unequal-denominator arm aggregate is reported.",
        "",
    ]
    lines.extend(subset_table(rows, BEFORE, "Before gate recovery"))
    lines.extend(subset_table(rows, AFTER, "After gate recovery"))
    (DEST / "paired_comparison.md").write_text("\n".join(lines))


def write_recovery() -> None:
    rows = load_evaluation()
    recovered = "\n".join(
        f"| {item} | {float(rows['b4', item]['precision_at_10']):.3f} | "
        f"{float(rows['b4', item]['chance_p_at_10']):.3f} | "
        f"{float(rows['b4', item]['spearman']):.3f} |"
        for item in RECOVER
    )
    text = f"""# B4 stable-context recovery

## Disposition

Task 1 returned **COSMETIC**, so the additive post-hoc normalization was authorized. The validator and scorer ran over the existing `cmp_004`, `cmp_008`, and `cmp_009` traces/submissions. No model prediction was rerun or changed.

The gate repair canonicalizes only the proven Markdown heading capitalization. Developer messages remain byte-exact and ordered; CLI version, sandbox type, and approval policy remain exact. The original fail-closed decisions remain on disk unchanged. New validation decisions are under `validation/` and are tied to `posthoc_gate_amendment.json` and `recovery_freeze.json`.

## Coverage

| State | B4 scorable coverage |
|---|---:|
| Before | 6/10 |
| After | 9/10 |

`cmp_001` remains a coverage failure because its model process exited 1. It was not rerun.

## Recovered results

| Cell | P@10 | Chance P@10 | Spearman |
|---|---:|---:|---:|
{recovered}

## Audit trail

- Post-hoc amendment SHA-256: `{sha(DEST / 'posthoc_gate_amendment.json')}`
- Recovery freeze SHA-256: `{sha(DEST / 'recovery_freeze.json')}`
- Validation summary SHA-256: `{sha(DEST / 'validation_summary.json')}`
- Blind bundle SHA-256: `{sha(DEST / 'blind_bundle_manifest.json')}`
- Evaluation rows SHA-256: `{sha(DEST / 'evaluation_rows.csv')}`
- The bundle was assembled post-hoc after these exact ten labels had already opened in Step 3; recovered predictions are nevertheless proven unchanged from their pre-label frozen traces. This limitation is recorded, not relabeled as prospective blinding.
- This scorer opened exactly the same ten authorized archive members and none of the other 135.
"""
    (DEST / "recovery.md").write_text(text)


def write_finding() -> None:
    rows = load_evaluation()
    before_p10 = metric_mean(rows, "b4", BEFORE, "precision_at_10") - metric_mean(rows, "floor_m", BEFORE, "precision_at_10")
    before_rho = metric_mean(rows, "b4", BEFORE, "spearman") - metric_mean(rows, "floor_m", BEFORE, "spearman")
    after_p10 = metric_mean(rows, "b4", AFTER, "precision_at_10") - metric_mean(rows, "floor_m", AFTER, "precision_at_10")
    after_rho = metric_mean(rows, "b4", AFTER, "spearman") - metric_mean(rows, "floor_m", AFTER, "spearman")
    text = f"""# Finding: the raw context hash discarded valid B4 cells

15 September 2026. The stable-context incident was a proxy-gate failure, not evidence that three cells ran a different arm. `cmp_004`, `cmp_008`, and `cmp_009` received the original pinned base instructions, all three ordered developer messages, Codex CLI 0.154.0, read-only sandboxing, and approval `never`. The active gate had silently substituted a later base hash whose complete textual difference was `# Destructive Actions` versus `# Destructive actions`. No instruction sentence, tool list, grant, or runtime control changed. Classification: **COSMETIC**.

The post-hoc repair canonicalizes only that exact heading and preserves every other byte. Its must-fire controls reject a changed instruction sentence, developer message, CLI version, sandbox, and approval policy. All controls passed. The validator then reproduced each frozen prompt, contract verdict, trace/submission identity, 100 candidate-bound receipts, model/waiver condition, disabled app/skill state, and explicit proxy limitation. B4 coverage rose from **6/10 to 9/10** without a model call. `cmp_001` remains a process-exit coverage failure.

On the original common six items, B4 minus Floor M is {before_p10:+.3f} mean P@10 (`n=6`) and {before_rho:+.3f} mean Spearman (`n=6`). On the recovered common nine, it is {after_p10:+.3f} mean P@10 (`n=9`) and {after_rho:+.3f} mean Spearman (`n=9`). P@10 is the governing primary metric: the Stage 3b amendment says its order controls subsequent reporting, and no later recorded amendment changes it. The Step 3 Spearman-first statement drifted. All performance summaries here are paired on the same item set; no unequal-denominator aggregate is used.

B2 remains **unmeasured, not zero**. The complement requirement is explicit, but nine of ten answers contain ten valid unique selections (the tenth contains nine). The precision-only path that worked in the sealed smoke was not wired into the Step 3 scorer, which discards the whole answer when strict parsing fails. No B2 contract or scorer change is made here.

This is a post-hoc rescue after the ten authorized labels had already opened. The blind bundle was hashed before this evaluation read, and the recovered answers are byte-tied to traces frozen before label opening; that does not turn the amendment into a prospective one. Exactly those ten labels were read, none of the other 135. Stop here for panel rulings on normalization, B2 measurement design, and metric primacy.
"""
    (DEST / "finding.md").write_text(text)


def reports() -> None:
    verify_blind()
    integrity = json.loads((DEST / "evaluation_integrity.json").read_text())
    if integrity.get("other_135_labels_opened_by_this_scorer") is not False:
        raise RuntimeError("label scope is not clean")
    targets = [DEST / name for name in ("gate_reflection.md", "recovery.md", "b2_contract.md",
                                         "metric_primacy.md", "paired_comparison.md", "finding.md")]
    if any(path.exists() for path in targets):
        raise SystemExit("refusing to replace Step 3b reports")
    write_gate_reflection()
    write_recovery()
    write_b2_contract()
    write_metric_primacy()
    write_paired_comparison()
    write_finding()
    print(json.dumps({path.name: sha(path) for path in targets}, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("controls", "freeze", "validate", "assemble-blind", "evaluate", "reports"))
    args = parser.parse_args()
    actions = {
        "controls": write_controls,
        "freeze": freeze,
        "validate": validate,
        "assemble-blind": assemble_blind,
        "evaluate": evaluate,
        "reports": reports,
    }
    actions[args.mode]()


if __name__ == "__main__":
    main()
