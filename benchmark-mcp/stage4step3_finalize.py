"""Blind assembly and one-shot label evaluation for the ten-item comparison."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import statistics
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from pilot_score import full_ranking, selected_mutants
from stage3_evaluate import label_map, precision_at_10, spearman
from stage3_w1 import RAW
from stage4step2e_contract import ranking_scores
from stage4step3_prompt import parse_answer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
S3 = ROOT / "results/benchmark/stage3_2026-09-13"
ARMS = ("floor_c", "floor_m", "b1", "b2", "b4")
LABELS = {"floor_c": "Floor C", "floor_m": "Floor M (B3)", "b1": "B1", "b2": "B2", "b4": "B4"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def items() -> list[dict]:
    return [json.loads(x) for x in (OUT / "blind_item_manifest_internal.jsonl").read_text().splitlines()]


def claude_text(path: Path) -> str:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    init = next((e for e in events if e.get("type") == "system" and e.get("subtype") == "init"), {})
    if init.get("tools") != [] or init.get("mcp_servers") != [] or init.get("memory_paths") is not None:
        raise ValueError("B1 model-side grant was not empty and isolated")
    for event in events:
        message = event.get("message")
        blocks = message.get("content", []) if isinstance(message, dict) else []
        if any(isinstance(block, dict) and block.get("type") == "tool_use" for block in blocks):
            raise ValueError("B1 emitted a tool call despite the empty grant")
    result = next((e for e in reversed(events) if e.get("type") == "result"), {})
    text = result.get("result")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("B1 result text is missing")
    return text


def prompt_answer(arm: str, row: dict, audit: dict) -> tuple[dict | None, str]:
    neutral = row["neutral_item_id"]
    run = OUT / f"runs/{arm}/{neutral}"
    meta_path = run / "meta.json"
    if not meta_path.is_file():
        marker = run / "interrupted.json"
        return None, (json.loads(marker.read_text()).get("reason") if marker.is_file()
                      else "run did not reach a terminal record")
    meta = json.loads(meta_path.read_text())
    if meta.get("timed_out") or meta.get("exit_code") not in (None, 0) or meta.get("error"):
        return None, meta.get("error") or f"process exit={meta.get('exit_code')} timed_out={meta.get('timed_out')}"
    try:
        text = claude_text(run / "trace.jsonl") if arm == "b1" else (run / "answer.txt").read_text()
        answer = parse_answer(text, tuple(json.loads((ROOT / row["contract_path"]).read_text())["candidates"]), neutral)
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        return None, str(exc)
    decision = audit.get(f"{arm}/{neutral}")
    if not isinstance(decision, dict) or decision.get("accepted") is not True:
        return None, (decision or {}).get("reason", "blind content audit missing or rejected")
    return answer, ""


def b4_answer(row: dict, audit: dict) -> tuple[dict | None, str]:
    neutral = row["neutral_item_id"]
    run = OUT / f"runs/b4/{neutral}"
    if not (run / "meta.json").is_file():
        return None, "B4 run did not reach a terminal record"
    meta = json.loads((run / "meta.json").read_text())
    if meta.get("timed_out") or meta.get("exit_code") != 0:
        return None, f"process exit={meta.get('exit_code')} timed_out={meta.get('timed_out')}"
    if not (run / "mechanical_integrity.json").is_file():
        error = (run / "validator_stderr.txt").read_text().strip() if (run / "validator_stderr.txt").is_file() else ""
        return None, "mechanical integrity failure" + (f": {error}" if error else "")
    decision = audit.get(f"b4/{neutral}")
    if not isinstance(decision, dict) or decision.get("accepted") is not True:
        return None, (decision or {}).get("reason", "blind content audit missing or rejected")
    submission = run / "submissions" / f"{neutral}.json"
    if not submission.is_file():
        return None, "accepted submission file missing"
    return json.loads(submission.read_text())["answer"], ""


def assemble_blind() -> None:
    target = OUT / "blind_bundle_manifest.json"
    if target.exists():
        raise SystemExit("blind bundle already exists")
    audit_path = OUT / "blind_content_audit.json"
    if not audit_path.is_file():
        raise SystemExit("blind content audit is required")
    audit = json.loads(audit_path.read_text())["decisions"]
    item_rows = items()
    ids = {r["internal_assay_id"] for r in item_rows}
    source_rows = [r for r in csv.DictReader((S3 / "floor_predictions_blind.csv").open())
                   if r["assay_id"] in ids]
    if {r["assay_id"] for r in source_rows} != ids or any("DMS_score" in r for r in source_rows):
        raise SystemExit("frozen floor extraction is incomplete or label-bearing")
    floor_outputs = {"floor_c": [], "floor_m": []}
    internal_to_neutral = {r["internal_assay_id"]: r["neutral_item_id"] for r in item_rows}
    for source in source_rows:
        for arm, field in (("floor_c", "floor_c_score"), ("floor_m", "floor_m_score")):
            floor_outputs[arm].append({"neutral_item_id": internal_to_neutral[source["assay_id"]],
                                       "mutant": source["mutant"], "score": source[field]})
    for arm in ("floor_c", "floor_m"):
        path = OUT / f"blind_{arm}.jsonl"
        path.write_text("".join(json.dumps(x, sort_keys=True) + "\n" for x in floor_outputs[arm]))
    for arm in ("b1", "b2", "b4"):
        records = []
        for row in item_rows:
            answer, reason = (b4_answer(row, audit) if arm == "b4" else prompt_answer(arm, row, audit))
            records.append({"neutral_item_id": row["neutral_item_id"], "arm": arm,
                            "status": "SCORABLE" if answer is not None else "COVERAGE FAILURE",
                            "coverage_failure_reason": reason, "answer": answer})
        (OUT / f"blind_{arm}.jsonl").write_text(
            "".join(json.dumps(x, sort_keys=True) + "\n" for x in records))
    paths = {arm: OUT / f"blind_{arm}.jsonl" for arm in ARMS}
    body = {"items": [r["neutral_item_id"] for r in item_rows], "arms": list(ARMS),
            "predictions": {arm: {"path": str(path.relative_to(ROOT)), "sha256": sha(path)}
                            for arm, path in paths.items()},
            "content_audit_sha256": sha(audit_path),
            "precall_freeze_sha256": sha(OUT / "precall_freeze.json"),
            "comparison_release_freeze_sha256": sha(OUT / "comparison_release_freeze.json"),
            "comparison_release_resume_freeze_sha256": sha(OUT / "comparison_release_resume_freeze.json"),
            "stage3_evaluator_sha256": sha(ROOT / "benchmark-mcp/stage3_evaluate.py"),
            "stage4step3_finalize_sha256": sha(Path(__file__)),
            "labels_opened": False}
    target.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"blind_bundle_sha256": sha(target),
                      "coverage": {arm: sum(json.loads(x)["status"] == "SCORABLE" for x in paths[arm].read_text().splitlines())
                                   if arm in {"b1", "b2", "b4"} else 10 for arm in ARMS}}, sort_keys=True))


def verify_blind() -> dict:
    frozen = json.loads((OUT / "blind_bundle_manifest.json").read_text())
    if frozen.get("labels_opened") is not False or frozen.get("items") != [f"cmp_{i:03d}" for i in range(1, 11)]:
        raise SystemExit("blind manifest scope/state is invalid")
    for record in frozen["predictions"].values():
        if sha(ROOT / record["path"]) != record["sha256"]:
            raise SystemExit("blind prediction hash mismatch")
    for key, path in (("content_audit_sha256", OUT / "blind_content_audit.json"),
                      ("precall_freeze_sha256", OUT / "precall_freeze.json"),
                      ("comparison_release_freeze_sha256", OUT / "comparison_release_freeze.json"),
                      ("comparison_release_resume_freeze_sha256", OUT / "comparison_release_resume_freeze.json"),
                      ("stage3_evaluator_sha256", ROOT / "benchmark-mcp/stage3_evaluate.py"),
                      ("stage4step3_finalize_sha256", Path(__file__))):
        if sha(path) != frozen[key]:
            raise SystemExit(f"blind frozen dependency mismatch: {key}")
    return frozen


def load_floor(arm: str) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = defaultdict(dict)
    for line in (OUT / f"blind_{arm}.jsonl").read_text().splitlines():
        row = json.loads(line)
        out[row["neutral_item_id"]][row["mutant"]] = float(row["score"])
    return out


def evaluate() -> None:
    target = OUT / "comparison_rows.csv"
    if target.exists():
        raise SystemExit("labels have already been evaluated")
    frozen = verify_blind()
    item_rows = items()
    agents = {arm: {r["neutral_item_id"]: r for r in map(json.loads, (OUT / f"blind_{arm}.jsonl").read_text().splitlines())}
              for arm in ("b1", "b2", "b4")}
    floors = {arm: load_floor(arm) for arm in ("floor_c", "floor_m")}
    output = []
    with zipfile.ZipFile(RAW) as archive:
        for item in item_rows:
            neutral, assay = item["neutral_item_id"], item["internal_assay_id"]
            contract = json.loads((ROOT / item["contract_path"]).read_text())
            candidates = set(contract["candidates"])
            truth = label_map(archive, assay, candidates)
            if set(truth) != candidates:
                raise SystemExit(f"label coverage incomplete for {neutral}")
            for arm in ARMS:
                status, reason, ranking = "SCORABLE", "", None
                if arm in floors:
                    ranking = floors[arm][neutral]
                else:
                    record = agents[arm][neutral]
                    status, reason = record["status"], record["coverage_failure_reason"]
                    if status == "SCORABLE":
                        answer = record["answer"]
                        ranking = ranking_scores(answer) if arm == "b4" else full_ranking(answer, candidates)
                if status == "SCORABLE" and (ranking is None or set(ranking) != candidates or
                                              not all(math.isfinite(v) for v in ranking.values())):
                    status, reason, ranking = "COVERAGE FAILURE", "complete finite ranking unavailable", None
                p10 = precision_at_10(ranking, truth) if ranking is not None else None
                rho = spearman(ranking, truth) if ranking is not None else None
                if ranking is not None and rho is None:
                    status, reason = "COVERAGE FAILURE", "Spearman undefined for constant ranking"
                    p10 = rho = None
                output.append({"neutral_item_id": neutral, "assay_id": assay, "published_quartile": item["published_quartile"],
                    "arm": arm, "n_candidates": len(candidates), "chance_p_at_10": 10 / len(candidates),
                    "status": status, "coverage_failure_reason": reason,
                    "precision_at_10": "" if p10 is None else p10,
                    "spearman": "" if rho is None else rho})
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader(); writer.writerows(output)
    integrity = {"blind_bundle_sha256": sha(OUT / "blind_bundle_manifest.json"),
                 "blind_hashes_verified_before_label_open": True,
                 "labels_exposed_for": [x["internal_assay_id"] for x in item_rows],
                 "other_135_labels_opened": False, "rows_sha256": sha(target)}
    (OUT / "evaluation_integrity.json").write_text(json.dumps(integrity, sort_keys=True, indent=2) + "\n")
    report(output)


def cell(row: dict, metric: str) -> str:
    return (f"{float(row[metric]):.3f} (chance P@10 {float(row['chance_p_at_10']):.3f})"
            if row["status"] == "SCORABLE" else f"COVERAGE FAILURE: {row['coverage_failure_reason']} (chance P@10 {float(row['chance_p_at_10']):.3f})")


def report(rows: list[dict]) -> None:
    lookup = {(r["neutral_item_id"], r["arm"]): r for r in rows}
    item_rows = items()
    lines = ["# Ten-item comparison", "", "Spearman is the preregistered primary metric; precision at ten is secondary. Coverage failures are not scored as zeros.", "",
             "## Spearman", "", "| Item | Quartile | " + " | ".join(LABELS[a] for a in ARMS) + " |",
             "|---|:---:|" + "---:|" * len(ARMS)]
    for item in item_rows:
        neutral = item["neutral_item_id"]
        lines.append(f"| {neutral} | {item['published_quartile']} | " + " | ".join(cell(lookup[neutral, a], "spearman") for a in ARMS) + " |")
    lines += ["", "## Precision at ten", "", "| Item | Quartile | " + " | ".join(LABELS[a] for a in ARMS) + " |",
              "|---|:---:|" + "---:|" * len(ARMS)]
    for item in item_rows:
        neutral = item["neutral_item_id"]
        lines.append(f"| {neutral} | {item['published_quartile']} | " + " | ".join(cell(lookup[neutral, a], "precision_at_10") for a in ARMS) + " |")
    lines += ["", "## Preregistered conditional summaries", "",
              "| Arm | Scorable coverage | Mean Spearman (scorable denominator) | Mean P@10 (scorable denominator) |",
              "|---|---:|---:|---:|"]
    summary = {}
    for arm in ARMS:
        valid = [r for r in rows if r["arm"] == arm and r["status"] == "SCORABLE"]
        n = len(valid)
        rho = statistics.mean(float(r["spearman"]) for r in valid) if valid else None
        p10 = statistics.mean(float(r["precision_at_10"]) for r in valid) if valid else None
        summary[arm] = {"scorable": n, "attempted": 10, "mean_spearman": rho, "mean_precision_at_10": p10}
        lines.append(f"| {LABELS[arm]} | {n}/10 | " + (f"{rho:.3f} (n={n})" if rho is not None else "UNAVAILABLE (n=0)") + " | " + (f"{p10:.3f} (n={n})" if p10 is not None else "UNAVAILABLE (n=0)") + " |")
    lines += ["", "These ten items were selected by a frozen stratified rule for this comparison. They do not estimate performance on the other 135 items. The arms differ in model family and tool access, so the table does not isolate a causal effect of foundation-model tools. B4 uses a moving model alias and generic sequence/backbone evidence that can be misaligned with the declared assay endpoint; those limitations were prospectively accepted and remain part of the interpretation.", ""]
    (OUT / "comparison.md").write_text("\n".join(lines))
    (OUT / "comparison_summary.json").write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"assemble-blind", "evaluate"}:
        raise SystemExit("usage: stage4step3_finalize.py {assemble-blind|evaluate}")
    assemble_blind() if sys.argv[1] == "assemble-blind" else evaluate()
