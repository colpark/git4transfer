"""W1 measured-label evaluation, run only after blind floor predictions exist."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import random
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

from stage3_w1 import (OUT, RAW, REF, MSAS, write_csv, percentiles,
                       allowed_score_fields, msa_counts, eligible_mutants,
                       floor_m_available)


def spearman(a: dict[str, float], b: dict[str, float]) -> float | None:
    keys = sorted(a)
    if keys != sorted(b):
        raise ValueError("unequal candidate sets")
    ra, rb = percentiles(a), percentiles(b)
    mean_a = sum(ra.values()) / len(keys)
    mean_b = sum(rb.values()) / len(keys)
    cov = sum((ra[k] - mean_a) * (rb[k] - mean_b) for k in keys)
    var_a = sum((ra[k] - mean_a)**2 for k in keys)
    var_b = sum((rb[k] - mean_b)**2 for k in keys)
    return cov / math.sqrt(var_a * var_b) if var_a and var_b else None


def precision_at_10(predicted: dict[str, float], measured: dict[str, float]) -> float:
    top_pred = {key for key, _ in sorted(predicted.items(),
                key=lambda item: (-item[1], item[0]))[:10]}
    top_true = {key for key, _ in sorted(measured.items(),
                key=lambda item: (-item[1], item[0]))[:10]}
    return len(top_pred & top_true) / 10


def finite(value: str) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def label_map(archive: zipfile.ZipFile, assay: str, selected: set[str]) -> dict[str, float]:
    member = "DMS_ProteinGym_substitutions/" + assay + ".csv"
    labels = {}
    with io.TextIOWrapper(archive.open(member), encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        mutant_index = header.index("mutant")
        score_index = header.index("DMS_score")
        for row in reader:
            key = row[mutant_index]
            if key in selected and key not in labels:
                value = finite(row[score_index])
                if value is not None:
                    labels[key] = value
    return labels


def mean_interval(values: list[float], rng: random.Random) -> dict:
    if not values:
        return {"n": 0, "mean": None, "ci95": None}
    replicates = []
    for _ in range(2000):
        replicate = [values[rng.randrange(len(values))] for _ in values]
        replicates.append(sum(replicate) / len(replicate))
    replicates.sort()
    return {"n": len(values), "mean": sum(values) / len(values),
            "ci95": [replicates[49], replicates[1949]]}


def controls(predictions: list[dict], rows: list[dict]) -> dict:
    # Stage 2's must-fail pattern: labels are tampered, the prediction table
    # remains byte-identical, and the scorer's result must change.
    blind_path = OUT / "floor_predictions_blind.csv"
    original_hash = hashlib.sha256(blind_path.read_bytes()).hexdigest()
    nonzero = next((row for row in rows if row["floor"] == "C" and
                    row["rho"] not in {"", "0.0"}), None)
    if nonzero is None:
        raise AssertionError("no nonzero item for sign-inversion control")
    assay = nonzero["assay_id"]
    item = [row for row in predictions if row["assay_id"] == assay]
    pred = {row["mutant"]: float(row["floor_c_score"]) for row in item}
    with zipfile.ZipFile(RAW) as archive:
        labels = label_map(archive, assay, set(pred))
    normal, inverted = spearman(pred, labels), spearman(pred, {k: -v for k, v in labels.items()})
    assert normal is not None and inverted is not None and abs(normal + inverted) < 1e-10
    # The scoring field allowlist must ignore even an adversarial label value.
    header = ["mutant", "DMS_score", "ESM2_650M", "ESM-IF1"]
    idx = {name: header.index(name) for name in ("mutant", "ESM2_650M", "ESM-IF1")}
    before = allowed_score_fields(["A1V", "9999", "0.5", "0.2"], idx)
    after = allowed_score_fields(["A1V", "-9999", "0.5", "0.2"], idx)
    assert before == after
    # A missing MSA is a hard error; an absent ESM2 cannot yield Floor M.
    try:
        with zipfile.ZipFile(OUT / "input/DMS_msa_files.zip") as archive:
            msa_counts({"MSA_filename": "__missing__.a2m"}, archive)
    except ValueError:
        missing_msa_rejected = True
    else:
        missing_msa_rejected = False
    assert missing_msa_rejected
    missing_esm2_rejected = not floor_m_available({"A1V", "A1C"}, {"A1V": 0.5})
    assert missing_esm2_rejected
    metadata = {row["DMS_id"]: row for row in csv.DictReader(REF.open())}
    qc = list(csv.DictReader((OUT / "msa_qc.csv").open()))
    with zipfile.ZipFile(RAW) as raw, zipfile.ZipFile(MSAS) as msas:
        smallest = min(qc, key=lambda row: raw.getinfo(row["raw_member"]).file_size +
                       msas.getinfo(row["msa_member"]).file_size)
        meta = metadata[smallest["assay_id"]]
        columns, _ = msa_counts(meta, msas)
        original_candidates, _ = eligible_mutants(meta, columns, raw)
        member = smallest["raw_member"]
        with io.TextIOWrapper(raw.open(member), encoding="utf-8") as handle:
            table = list(csv.reader(handle))
        label_index = table[0].index("DMS_score")
        values = [row[label_index] for row in table[1:]]
        for row, replacement in zip(table[1:], reversed(values)):
            row[label_index] = replacement
        altered_csv = io.StringIO()
        csv.writer(altered_csv).writerows(table)
        altered_zip = io.BytesIO()
        with zipfile.ZipFile(altered_zip, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr(member, altered_csv.getvalue())
        with zipfile.ZipFile(io.BytesIO(altered_zip.getvalue())) as archive:
            altered_candidates, _ = eligible_mutants(meta, columns, archive)
    assert original_candidates == altered_candidates
    return {"blind_predictions_sha256": original_hash,
            "label_tamper_does_not_change_allowed_scores": before == after,
            "label_permutation_preserves_candidate_scores":
            original_candidates == altered_candidates,
            "sign_inversion_changes_rho": normal != inverted,
            "inverted_rho_sums_to_zero": abs(normal + inverted) < 1e-10,
            "missing_msa_rejected": missing_msa_rejected,
            "missing_esm2_rejected": missing_esm2_rejected,
            "control_assay": assay,
            "label_permutation_assay": smallest["assay_id"],
            "normal_rho": normal, "inverted_rho": inverted}


def main() -> None:
    blind = OUT / "floor_predictions_blind.csv"
    if not blind.is_file() or not (OUT / "floor_coverage.csv").is_file():
        raise SystemExit("blind floors must be written before measured-label evaluation")
    predictions = list(csv.DictReader(blind.open()))
    grouped = defaultdict(list)
    for row in predictions:
        grouped[row["assay_id"]].append(row)
    scores = []
    with zipfile.ZipFile(RAW) as archive:
        for assay, variants in sorted(grouped.items()):
            selected = {row["mutant"] for row in variants}
            labels = label_map(archive, assay, selected)
            complete = len(labels) == len(selected)
            for floor, column in (("C", "floor_c_score"), ("M", "floor_m_score")):
                predicted = {row["mutant"]: finite(row[column]) for row in variants}
                evaluable = complete and all(value is not None for value in predicted.values())
                rho = spearman(predicted, labels) if evaluable else None
                precision = precision_at_10(predicted, labels) if evaluable else None
                scores.append({"cluster_50": variants[0]["cluster_50"],
                               "assay_id": assay, "floor": floor,
                               "n_candidates": len(selected),
                               "status": "EVALUABLE" if evaluable else "UNAVAILABLE",
                               "reason": "" if evaluable else
                               ("label_missing" if not complete else "predictor_missing"),
                               "rho": rho if rho is not None else "",
                               "precision_at_10": precision if precision is not None else ""})
    write_csv(OUT / "floor_item_scores.csv", scores, list(scores[0]))
    checks = controls(predictions, scores)
    (OUT / "floor_controls.json").write_text(json.dumps(checks, indent=2) + "\n")
    summary = {"independent_units": len(grouped), "floors": {}, "paired": {},
               "zero_subject_llm_calls": True, "zero_new_fm_inference_calls": True}
    for floor in ("C", "M"):
        rows = [row for row in scores if row["floor"] == floor and row["status"] == "EVALUABLE"]
        summary["floors"][floor] = {
            "spearman": mean_interval([float(row["rho"]) for row in rows if row["rho"] != ""],
                                      random.Random(19)),
            "precision_at_10": mean_interval([float(row["precision_at_10"]) for row in rows],
                                             random.Random(19))}
    by_assay = defaultdict(dict)
    for row in scores:
        by_assay[row["assay_id"]][row["floor"]] = row
    paired = [pair for pair in by_assay.values()
              if all(pair.get(floor, {}).get("status") == "EVALUABLE" for floor in ("C", "M"))]
    for metric in ("rho", "precision_at_10"):
        differences = [float(pair["M"][metric]) - float(pair["C"][metric])
                       for pair in paired if pair["M"][metric] != "" and pair["C"][metric] != ""]
        summary["paired"]["M_minus_C_" + metric] = mean_interval(differences, random.Random(19))
    (OUT / "floor_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
