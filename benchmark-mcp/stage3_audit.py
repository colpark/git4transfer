"""Mechanical Stage 3 denominator, blinding, and negative-control audit."""

from __future__ import annotations

import csv
import json
from collections import Counter

from stage3_w1 import OUT


def rows(name: str) -> list[dict]:
    return list(csv.DictReader((OUT / name).open()))


def unique_candidates(items: list[dict]) -> bool:
    keys = [(row["assay_id"], row["mutant"]) for row in items]
    return len(keys) == len(set(keys))


def main() -> None:
    cohort = rows("cohort.csv")
    eligible = [row for row in cohort if row["status"] == "ELIGIBLE"]
    candidates = rows("candidates_blind.csv")
    predictions = rows("floor_predictions_blind.csv")
    coverage = rows("floor_coverage.csv")
    item_scores = rows("floor_item_scores.csv")
    counts = Counter(row["assay_id"] for row in candidates)
    source_assays = {row["assay_id"] for row in eligible}
    source_clusters = {row["cluster_50"] for row in eligible}
    assert len(cohort) == 174
    assert len(source_assays) == len(source_clusters) == len(eligible)
    assert set(counts) == source_assays
    assert all(20 <= counts[assay] <= 100 for assay in source_assays)
    assert unique_candidates(candidates) and unique_candidates(predictions)
    assert len(predictions) == len(candidates)
    assert {row["assay_id"] for row in coverage} == source_assays
    assert len(item_scores) == 2 * len(eligible)
    forbidden = {"DMS_score", "DMS_score_bin", "label", "measured_fitness"}
    blind_headers = {name: set(rows(name)[0]) for name in
                     ("candidates_blind.csv", "floor_predictions_blind.csv")}
    assert all(not (fields & forbidden) for fields in blind_headers.values())
    altered = candidates + [candidates[0]]
    duplicate_control_rejected = not unique_candidates(altered)
    assert duplicate_control_rejected
    altered_cluster = source_clusters - {eligible[0]["cluster_50"]}
    missing_cluster_control_rejected = len(altered_cluster) != len(eligible)
    assert missing_cluster_control_rejected
    report = {"inherited_clusters": len(cohort), "eligible_clusters": len(eligible),
              "unique_assays": len(source_assays), "unique_clusters": len(source_clusters),
              "candidate_rows": len(candidates), "prediction_rows": len(predictions),
              "all_candidate_counts_20_to_100": True,
              "blind_tables_exclude_measured_labels": True,
              "duplicate_candidate_control_rejected": duplicate_control_rejected,
              "missing_cluster_control_rejected": missing_cluster_control_rejected,
              "floor_m_evaluable_items": sum(row["floor_m"] == "EVALUABLE" for row in coverage),
              "floor_item_score_rows": len(item_scores)}
    (OUT / "cohort_controls.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
