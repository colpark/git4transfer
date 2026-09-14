"""Frozen Stage 4 pilot evaluator: only this module reads DMS_score labels."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path

from stage3_evaluate import label_map, spearman

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
ARMS = ("1", "2", "3", "3F", "3L")
MODES = ("unguided", "guided")
ARM_SERVERS = {"1": ("rescue_record",),
               "2": ("rescue_record", "rescue_classical", "rescue_lit"),
               "3": ("rescue_record", "rescue_classical", "rescue_lit", "rescue_analysis",
                     "rescue_predictive", "rescue_generative", "rescue_physics")}
ARM_SERVERS["3F"] = ARM_SERVERS["3"]
ARM_SERVERS["3L"] = ARM_SERVERS["3"]
CALL_ID_RE = re.compile(r"call_id:[A-Za-z0-9_-]+")
TOOL_CATEGORY = {
    "mmseqs_search": "sequence", "blast_search": "sequence",
    "pssm_score": "sequence", "conservation": "sequence",
    "motif_scan": "sequence", "blosum_score": "sequence",
    "screen_variant_classical": "sequence", "seq_identity": "sequence",
    "esm2_likelihood": "sequence", "hbond_geometry": "geometric",
    "tmalign": "structural", "dssp": "structural",
    "esmfold": "structural", "esm_if": "structural",
    "pyrosetta_ddg": "energetic", "openmm_delta_energy": "energetic",
    "pubmed_search": "literature",
}


def successful_receipts(trace_path: str) -> tuple[dict[str, str], dict[str, tuple[int, int]]]:
    valid: dict[str, str] = {}
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    path = Path(trace_path)
    if not path.is_file():
        return valid, {}
    events = []
    for line in path.read_text().splitlines():
        if line.startswith("{"):
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    for event in events:
        item = event.get("item", {})
        if item.get("type") != "mcp_tool_call":
            continue
        server = item.get("server", "unknown")
        if item.get("status") == "in_progress":
            counts[server][0] += 1
        if item.get("status") != "completed":
            continue
        try:
            result = item["result"]
            body = json.loads(result["content"][0]["text"])
            receipt = body["receipt"]
            artifact = Path(receipt["artifact_path"])
            if (body.get("error") is None and artifact.is_file()
                    and json.loads(artifact.read_text())["receipt"]["call_id"]
                    == receipt["call_id"]):
                valid[receipt["call_id"]] = TOOL_CATEGORY.get(item.get("tool"), "nonvalidation")
                counts[server][1] += 1
        except (KeyError, IndexError, TypeError, ValueError, OSError):
            pass
    return valid, {key: tuple(value) for key, value in counts.items()}


def selected_mutants(answer: dict, candidates: set[str]) -> list[str] | None:
    selected = answer.get("selected")
    if not isinstance(selected, list) or len(selected) != 10:
        return None
    try:
        ranked = sorted(selected, key=lambda entry: entry["rank"])
        mutants = [entry["mutant"] for entry in ranked]
        if [entry["rank"] for entry in ranked] != list(range(1, 11)):
            return None
        if len(set(mutants)) != 10 or not set(mutants) <= candidates:
            return None
        return mutants
    except (KeyError, TypeError, ValueError):
        return None


def full_ranking(answer: dict, candidates: set[str]) -> dict[str, float] | None:
    rows = answer.get("ranking")
    if not isinstance(rows, list) or len(rows) != len(candidates):
        return None
    try:
        scores = {row["mutant"]: float(row["score"]) for row in rows}
    except (KeyError, TypeError, ValueError):
        return None
    if (len(scores) != len(candidates) or set(scores) != candidates
            or not all(math.isfinite(v) for v in scores.values())):
        return None
    return scores


def agent_message_refs(trace_path: str) -> set[str]:
    path = Path(trace_path)
    if not path.is_file():
        return set()
    refs = set()
    for line in path.read_text().splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            refs.update(CALL_ID_RE.findall(item.get("text", "")))
    return refs


def native_capability_used(trace_path: str) -> bool:
    path = Path(trace_path)
    if not path.is_file():
        return False
    for line in path.read_text().splitlines():
        if not line.startswith("{"):
            continue
        try:
            item = json.loads(line).get("item", {})
        except ValueError:
            continue
        if item.get("type") in {"command_execution", "file_change", "web_search"}:
            return True
    return False


def cited_and_depth(answer: dict, valid: dict[str, str],
                    extra_refs: set[str] | None = None) -> tuple[int, int, float | None]:
    cited: set[str] = set(CALL_ID_RE.findall(json.dumps(answer)))
    cited.update(extra_refs or set())
    depths: list[int] = []
    for selected in answer.get("selected", []) if isinstance(answer.get("selected"), list) else []:
        if not isinstance(selected, dict):
            continue
        for ref in selected.get("evidence", []) if isinstance(selected.get("evidence"), list) else []:
            if isinstance(ref, str):
                cited.add(ref)
        categories = set()
        validation = selected.get("validation", [])
        for entry in validation if isinstance(validation, list) else []:
            if isinstance(entry, dict) and isinstance(entry.get("call_id"), str):
                ref = entry["call_id"]
                cited.add(ref)
                claimed = entry.get("category")
                if (ref in valid and valid[ref] != "nonvalidation" and isinstance(claimed, str)
                        and claimed.strip().lower() == valid[ref]):
                    categories.add(valid[ref])
        depths.append(len(categories))
    return len(cited), sum(ref not in valid for ref in cited), statistics.mean(depths) if depths else None


def summarize(rows: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for row in rows:
        groups[row["arm"]].append(row)
    output = []
    for arm in ARMS:
        data = groups[arm]
        by_item = defaultdict(list)
        for row in data:
            by_item[row["assay_id"]].append(row)
        def macro(field: str) -> float | None:
            values = [statistics.mean([r[field] for r in group if r[field] is not None])
                      for group in by_item.values() if any(r[field] is not None for r in group)]
            return statistics.mean(values) if values else None
        durations = [r["wall_s"] for r in data
                     if r["wall_s"] is not None and r["status"] == "COMPLETED"]
        all_durations = [r["wall_s"] for r in data if r["wall_s"] is not None]
        output.append({"arm": arm, "runs_attempted": len(data),
                       "runs_completed": sum(r["status"] == "COMPLETED" for r in data),
                       "runs_interrupted": sum(r["status"] == "UNDEMONSTRATED" for r in data),
                       "runs_valid_p_at_10": sum(r["p_at_10"] is not None for r in data),
                       "wall_median_s": statistics.median(durations) if durations else None,
                       "wall_min_s": min(durations) if durations else None,
                       "wall_max_s": max(durations) if durations else None,
                       "attempt_wall_median_s": statistics.median(all_durations)
                       if all_durations else None,
                       "p_at_10_macro": macro("p_at_10"),
                       "rho_macro": macro("rho"),
                       "depth_macro": macro("evaluation_depth"),
                       "rejected_empty_rate": statistics.mean(
                           r["rejected_empty"] for r in data if r["status"] == "COMPLETED")
                           if any(r["status"] == "COMPLETED" for r in data) else None,
                       "fabricated_citations": sum(r["fabricated_citations"] for r in data),
                       "cited_receipts": sum(r["cited_receipts"] for r in data),
                       "runs_with_fabrication": sum(r["fabricated_citations"] > 0 for r in data),
                       "out_of_grant_runs": sum(r["out_of_grant"] for r in data),
                       "pilot_chance_p_at_10": macro("chance_p_at_10"),
                       "pilot_floor_c_p_at_10": macro("floor_c_p_at_10"),
                       "pilot_released_floor_m_p_at_10": macro("floor_m_p_at_10"),
                       "global_chance_reference": 0.103,
                       "global_frozen_floor_c_reference": 0.176,
                       "global_released_floor_m_reference": 0.218,
                       "marked_pilot": True})
    return output


def main() -> None:
    frozen = json.loads((OUT / "freeze_hashes.json").read_text())
    for key, path in (("scoring_code_sha256", Path(__file__)),
                      ("preselection_freeze_sha256", OUT / "preselection_freeze.json"),
                      ("preregistration_sha256", OUT / "preregistration.md"),
                      ("stage3_evaluator_sha256", ROOT / "benchmark-mcp/stage3_evaluate.py"),
                      ("stage3_floor_code_sha256", ROOT / "benchmark-mcp/stage3_w1.py"),
                      ("selection_sha256", OUT / "selection.json"),
                      ("selection_csv_sha256", OUT / "selection.csv")):
        if hashlib.sha256(path.read_bytes()).hexdigest() != frozen[key]:
            raise SystemExit(f"frozen {key} mismatch; labels remain sealed")
    blind = OUT / "answers_blind.jsonl"
    expected = (OUT / "answers_blind.sha256").read_text().strip()
    actual = hashlib.sha256(blind.read_bytes()).hexdigest()
    if actual != expected:
        raise SystemExit("blind answer hash mismatch; labels remain sealed")
    records = [json.loads(line) for line in blind.read_text().splitlines() if line.strip()]
    if len(records) != 240:
        raise SystemExit(f"expected 240 recorded runs, found {len(records)}; labels remain sealed")
    selection = json.loads((OUT / "selection.json").read_text())
    selected_ids = {item["assay_id"] for item in selection["items"]}
    selected_floors = {item["assay_id"]: item for item in selection["items"]}
    expected_keys = {(assay, arm, mode, sample)
                     for assay in selected_ids for arm in ARMS for mode in MODES
                     for sample in (1, 2, 3)}
    keys = [(r["assay_id"], r["arm"], r["mode"], r["sample"]) for r in records]
    if len(set(keys)) != 240 or set(keys) != expected_keys:
        raise SystemExit("run identity mismatch; labels remain sealed")
    candidates = defaultdict(set)
    for row in csv.DictReader((STAGE3 / "candidates_blind.csv").open()):
        if row["assay_id"] in selected_ids:
            candidates[row["assay_id"]].add(row["mutant"])
    scored, call_rates = [], defaultdict(lambda: [0, 0])
    with zipfile.ZipFile(STAGE3 / "input/DMS_ProteinGym_substitutions.zip") as archive:
        labels = {assay: label_map(archive, assay, mutants)
                  for assay, mutants in candidates.items()}
        control_assay = next((item["assay_id"] for item in selection["items"]
                              if abs(item["floor_c_rho"]) > 0.01), None)
        if control_assay is None:
            raise RuntimeError("no nonzero frozen Floor C item for label control")
        floor_c_control = {row["mutant"]: float(row["floor_c_score"])
                           for row in csv.DictReader((STAGE3 / "floor_predictions_blind.csv").open())
                           if row["assay_id"] == control_assay}
        normal = spearman(floor_c_control, labels[control_assay])
        inverted = spearman(floor_c_control,
                            {key: -value for key, value in labels[control_assay].items()})
        label_controls = {"blind_answer_sha256_unchanged":
                          hashlib.sha256(blind.read_bytes()).hexdigest() == actual,
                          "sign_inversion_changes_rho": normal is not None and inverted is not None
                          and normal != inverted and abs(normal + inverted) < 1e-10,
                          "control_assay": control_assay,
                          "normal_rho": normal, "inverted_rho": inverted}
        label_controls["all_pass"] = (label_controls["blind_answer_sha256_unchanged"]
                                       and label_controls["sign_inversion_changes_rho"])
        (OUT / "pilot_label_controls.json").write_text(json.dumps(label_controls, indent=2) + "\n")
        if not label_controls["all_pass"]:
            raise RuntimeError("pilot label controls failed")
        for run in records:
            assay, arm = run["assay_id"], run["arm"]
            answer = run.get("answer") if isinstance(run.get("answer"), dict) else {}
            valid_receipts, counts = successful_receipts(run.get("trace_path", ""))
            out_of_grant = (any(server not in ARM_SERVERS[arm] for server in counts)
                            or native_capability_used(run.get("trace_path", "")))
            for server, (attempted, succeeded) in counts.items():
                call_rates[(arm, server)][0] += attempted
                call_rates[(arm, server)][1] += succeeded
            mutants = (selected_mutants(answer, candidates[assay])
                       if run["status"] == "COMPLETED" and not out_of_grant else None)
            true_top = {key for key, _ in sorted(labels[assay].items(),
                        key=lambda pair: (-pair[1], pair[0]))[:10]}
            p_at_10 = len(set(mutants) & true_top) / 10 if mutants is not None else None
            predicted = (full_ranking(answer, candidates[assay])
                         if run["status"] == "COMPLETED" and not out_of_grant else None)
            rho = spearman(predicted, labels[assay]) if predicted is not None else None
            cited, fabricated, depth = cited_and_depth(
                answer, valid_receipts, agent_message_refs(run.get("trace_path", "")))
            rejected = answer.get("rejected")
            scored.append({"run_id": run["run_id"], "assay_id": assay,
                           "arm": arm, "mode": run["mode"], "sample": run["sample"],
                           "status": run["status"], "wall_s": run.get("wall_s"),
                           "out_of_grant": out_of_grant,
                           "p_at_10": p_at_10, "rho": rho,
                           "chance_p_at_10": 10 / len(candidates[assay]),
                           "floor_c_p_at_10": selected_floors[assay]["floor_c_p_at_10"],
                           "floor_m_p_at_10": selected_floors[assay]["floor_m_p_at_10"],
                           "rejected_empty": not isinstance(rejected, list) or len(rejected) == 0,
                           "rejected_missing": not isinstance(rejected, list),
                           "evaluation_depth": depth, "cited_receipts": cited,
                           "fabricated_citations": fabricated})
    summaries = summarize(scored)
    for filename, rows in (("pilot_run_scores.csv", scored), ("pilot_arm_summary.csv", summaries)):
        with (OUT / filename).open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
    with (OUT / "pilot_tool_rates.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["arm", "server", "attempted", "succeeded", "rate"])
        writer.writeheader()
        for arm in ARMS:
            for server in ARM_SERVERS[arm]:
                attempted, succeeded = call_rates[(arm, server)]
                writer.writerow({"arm": arm, "server": server, "attempted": attempted,
                                 "succeeded": succeeded,
                                 "rate": succeeded / attempted if attempted else ""})
    span = json.loads((OUT / "pilot_run_span.json").read_text())
    duty = span.get("duty_cycle")
    medians = {row["arm"]: row["wall_median_s"] for row in summaries}
    projection = {"pilot_duty_cycle": duty,
                  "duty_cycle_definition": span.get("duty_cycle_definition"),
                  "headline_1776_runs_hours": None,
                  "subset_900_runs_hours": None,
                  "basis": "per-arm pilot median active wall time divided by measured pilot duty cycle"}
    if duty and all(isinstance(medians[arm], (int, float)) for arm in ARMS):
        projection["headline_1776_runs_hours"] = round(
            888 * (medians["2"] + medians["3"]) / duty / 3600, 2)
        projection["subset_900_runs_hours"] = round(
            180 * sum(medians.values()) / duty / 3600, 2)
    (OUT / "pilot_projection.json").write_text(json.dumps(projection, indent=2) + "\n")
    print(json.dumps({"blind_sha256": actual, "runs": len(scored), "arms": summaries}, indent=2))


if __name__ == "__main__":
    main()
