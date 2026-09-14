"""One-shot sealed-only smoke evaluator; imports labels only after blind hashes verify."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import zipfile
from collections import defaultdict
from pathlib import Path

from pilot_score import full_ranking, selected_mutants
from stage3_evaluate import label_map, precision_at_10, spearman
from stage3_w1 import RAW

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2b_2026-09-14"
SEALED = ("AACC1_PSEAI_Dandage_2018", "ARGR_ECOLI_Tsuboyama_2023_1AOY", "ENVZ_ECOLI_Ghose_2023")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_blind() -> dict:
    frozen = json.loads((OUT / "blind_hashes.json").read_text())
    if tuple(frozen["sealed_items"]) != SEALED:
        raise SystemExit("blind sealed-item list mismatch")
    if sha(ROOT / "benchmark-mcp/stage3_evaluate.py") != frozen["evaluator_sha256"]:
        raise SystemExit("unchanged Stage 3 evaluator hash mismatch")
    if sha(ROOT / "benchmark-mcp/pilot_score.py") != frozen["scorer_sha256"]:
        raise SystemExit("frozen scorer hash mismatch")
    for arm, record in frozen["prediction_sha256"].items():
        path = ROOT / record["path"]
        if sha(path) != record["digest"]:
            raise SystemExit(f"blind prediction hash mismatch for {arm}")
    scorable = {r["assay_id"] for r in csv.DictReader((OUT / "cohort_145.csv").open())}
    if len(scorable) != 145 or scorable & set(SEALED):
        raise SystemExit("seals overlap the 145 scorable cohort")
    return frozen


def candidates() -> dict[str, set[str]]:
    prompt_rows = {r["assay_id"]: r for line in (OUT / "sealed_prompt_manifest.jsonl").open()
                   if (r := json.loads(line))}
    output = {}
    for assay in SEALED:
        row = prompt_rows[assay]
        prompt = (ROOT / row["prompt_path"]).read_text()
        names = set(prompt.split("Candidate variants:\n", 1)[1].splitlines()[0].split(", "))
        if len(names) != row["candidate_count"]:
            raise SystemExit("candidate count mismatch")
        output[assay] = names
    return output


def load_floor(arm: str) -> dict[str, dict[str, float]]:
    rows = defaultdict(dict)
    for row in csv.DictReader((OUT / f"blind_{arm}.csv").open()):
        rows[row["assay_id"]][row["mutant"]] = float(row["score"])
    return rows


def main() -> None:
    target = OUT / "smoke_eval_rows.csv"
    if target.exists():
        raise SystemExit("sealed smoke has already been scored; refusing a second evaluation")
    frozen = verify_blind()
    names = candidates()
    agents = {arm: {row["assay_id"]: row for line in (OUT / f"blind_{arm}.jsonl").open()
                    if (row := json.loads(line))} for arm in ("b1", "b2", "b4")}
    floors = {arm: load_floor(arm) for arm in ("b3", "floor_c")}
    if any(set(rows) != set(SEALED) for rows in (*agents.values(), *floors.values())):
        raise SystemExit("one blind arm does not cover exactly the three sealed items")
    output = []
    with zipfile.ZipFile(RAW) as archive:
        for assay in SEALED:
            truth = label_map(archive, assay, names[assay])
            if set(truth) != names[assay]:
                raise SystemExit(f"label coverage incomplete for sealed {assay}")
            true_top = {key for key, _ in sorted(truth.items(), key=lambda pair: (-pair[1], pair[0]))[:10]}
            for arm in ("b1", "b2", "b3", "b4", "floor_c"):
                chance = 10 / len(names[assay])
                if arm in floors:
                    ranking = floors[arm][assay]
                    if set(ranking) != names[assay] or not all(math.isfinite(v) for v in ranking.values()):
                        raise SystemExit("blind mechanical floor is incomplete")
                    p10 = precision_at_10(ranking, truth)
                    rho = spearman(ranking, truth)
                    parser_ok, parser_reason = True, ""
                    selected_ok, ranking_ok = True, True
                else:
                    row = agents[arm][assay]
                    answer = row.get("answer") if isinstance(row.get("answer"), dict) else {}
                    picks = selected_mutants(answer, names[assay])
                    ranking = full_ranking(answer, names[assay])
                    p10 = len(set(picks) & true_top) / 10 if picks is not None else None
                    rho = spearman(ranking, truth) if ranking is not None else None
                    parser_ok = bool(row["parser_accepted"])
                    parser_reason = row.get("parser_error") or ""
                    selected_ok, ranking_ok = picks is not None, ranking is not None
                output.append({"assay_id": assay, "arm": arm, "n_candidates": len(names[assay]),
                               "chance_p_at_10": chance,
                               "parser_accepted": parser_ok, "parser_rejection": parser_reason,
                               "ten_valid_unique_picks": selected_ok,
                               "complete_candidate_ranking": ranking_ok,
                               "precision_computable": p10 is not None,
                               "spearman_computable": rho is not None,
                               "precision_at_10": "" if p10 is None else p10,
                               "spearman": "" if rho is None else rho,
                               "precision_coverage_failure": p10 is None,
                               "spearman_coverage_failure": rho is None})
    # The mechanical rows must reproduce the published per-item values exactly.
    published = {(r["assay_id"], r["floor"]): r for r in
                 csv.DictReader((ROOT / "results/benchmark/stage3_2026-09-13/floor_item_scores.csv").open())
                 if r["assay_id"] in SEALED}
    floor_check = []
    for row in output:
        if row["arm"] not in ("b3", "floor_c"):
            continue
        historic = published[row["assay_id"], "M" if row["arm"] == "b3" else "C"]
        ok = (abs(float(row["precision_at_10"]) - float(historic["precision_at_10"])) < 1e-12 and
              abs(float(row["spearman"]) - float(historic["rho"])) < 1e-12)
        floor_check.append({"assay_id": row["assay_id"], "arm": row["arm"], "matches_published": ok})
    if not all(row["matches_published"] for row in floor_check):
        raise SystemExit("mechanical floor smoke differs from published Stage 3 values")
    with target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    (OUT / "evaluation_integrity.json").write_text(json.dumps({
        "scored_once": True, "blind_hashes_verified_before_label_open": True,
        "sealed_only": list(SEALED), "scorable_145_labels_opened": False,
        "stage3_evaluator_sha256": frozen["evaluator_sha256"],
        "mechanical_floor_checks": floor_check, "smoke_eval_rows_sha256": sha(target)}, indent=2) + "\n")
    print(json.dumps({"sealed_items": len(SEALED), "rows": len(output),
                      "mechanical_checks": len(floor_check), "all_mechanical_checks_pass": True}))


if __name__ == "__main__":
    main()
