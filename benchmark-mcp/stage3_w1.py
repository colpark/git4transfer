"""Label-blind W1 item preparation and preregistered mechanical floor scores.

The `prepare` and `score` commands never access DMS_score. `evaluate` lives in a
separate module so labels cannot leak into predictor code through imports.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import sys
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from Bio.Align import substitution_matrices

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3_2026-09-13"
INPUT = OUT / "input"
REF = INPUT / "DMS_substitutions.csv"
STAGE1 = ROOT / "results/benchmark/stage1_2026-09-12/w1_assays.csv"
RAW = INPUT / "DMS_ProteinGym_substitutions.zip"
MSAS = INPUT / "DMS_msa_files.zip"
SCORES = INPUT / "zero_shot_substitutions_scores.zip"
AA = set("ACDEFGHIKLMNPQRSTVWY")
MUTANT = re.compile(r"^([ACDEFGHIKLMNPQRSTVWY])(\d+)([ACDEFGHIKLMNPQRSTVWY])$")
BLOSUM62 = substitution_matrices.load("BLOSUM62")


def write_csv(path: Path, rows: list[dict], fields: list[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def a2m_records(handle):
    header = None
    pieces = []
    for line in io.TextIOWrapper(handle, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if header is not None:
                yield header, "".join(pieces)
            header, pieces = line[1:], []
        else:
            pieces.append(line)
    if header is not None:
        yield header, "".join(pieces)


def a2m_columns(sequence: str) -> str:
    return "".join(char for char in sequence if char.isupper() or char == "-")


def msa_counts(meta: dict, archive: zipfile.ZipFile) -> tuple[dict[int, Counter], dict]:
    member = "DMS_msa_files/" + meta["MSA_filename"]
    if member not in archive.namelist():
        raise ValueError("MSA member missing")
    records = a2m_records(archive.open(member))
    try:
        _, query = next(records)
    except StopIteration as error:
        raise ValueError("empty MSA") from error
    start, end = int(meta["MSA_start"]), int(meta["MSA_end"])
    target = meta["target_seq"]
    query_residues = "".join(char.upper() for char in query if char.isalpha())
    if query_residues != target[start - 1:end]:
        raise ValueError("A2M query does not match reference target interval")
    aligned_query = a2m_columns(query)
    positions = {}
    target_offset = 0
    column = 0
    for char in query:
        if char.isalpha():
            if char.isupper():
                if char not in AA:
                    raise ValueError("noncanonical A2M query residue")
                positions[start + target_offset] = column
                column += 1
            target_offset += 1
        elif char == "-":
            column += 1
        elif char != ".":
            raise ValueError("unsupported A2M query character")
    if column != len(aligned_query) or target_offset != end - start + 1:
        raise ValueError("A2M query coordinate mapping mismatch")
    selected_columns = sorted(set(positions.values()))
    if not selected_columns:
        raise ValueError("no uppercase A2M query columns")
    counts = {position: Counter() for position in positions}
    full_coverage_rows = 0
    total_rows = 0
    invalid_rows = 0
    def add_row(sequence: str) -> None:
        nonlocal full_coverage_rows, total_rows, invalid_rows
        aligned = a2m_columns(sequence)
        if len(aligned) != len(aligned_query) or set(aligned) - AA - {"-"}:
            invalid_rows += 1
            return
        total_rows += 1
        non_gap = sum(aligned[index] != "-" for index in selected_columns)
        if non_gap / len(selected_columns) >= 0.8:
            full_coverage_rows += 1
        for position, index in positions.items():
            residue = aligned[index]
            if residue != "-":
                counts[position][residue] += 1

    add_row(query)
    for _, sequence in records:
        add_row(sequence)
    if full_coverage_rows < 2:
        raise ValueError("fewer than two >=80%-coverage MSA rows")
    return counts, {"msa_rows": total_rows, "full_coverage_rows": full_coverage_rows,
                    "invalid_rows_excluded": invalid_rows,
                    "query_aligned_columns": len(selected_columns),
                    "query_insertion_residues": len(query_residues) - len(positions),
                    "scorable_positions": sum(sum(c.values()) >= 2 for c in counts.values()),
                    "msa_member": member}


def eligible_mutants(meta: dict, counts: dict[int, Counter], archive: zipfile.ZipFile) -> tuple[list[dict], dict]:
    member = "DMS_ProteinGym_substitutions/" + meta["DMS_filename"]
    if member not in archive.namelist():
        raise ValueError("DMS member missing")
    seen = set()
    selected = []
    rejection = Counter()
    with io.TextIOWrapper(archive.open(member), encoding="utf-8") as handle:
        reader = csv.reader(handle)
        header = next(reader)
        index = header.index("mutant")
        for row in reader:
            code = row[index]
            if code in seen:
                rejection["duplicate"] += 1
                continue
            seen.add(code)
            match = MUTANT.fullmatch(code)
            if not match:
                rejection["not_single_canonical"] += 1
                continue
            wt, index_s, alt = match.groups()
            position = int(index_s)
            sequence = meta["target_seq"]
            if not 1 <= position <= len(sequence) or sequence[position - 1] != wt or wt == alt:
                rejection["wt_or_position_mismatch"] += 1
                continue
            column = counts.get(position)
            if column is None or sum(column.values()) < 2:
                rejection["no_msa_column"] += 1
                continue
            depth = sum(column.values())
            def bit(residue: str) -> float:
                return math.log2(20 * (column[residue] + 1) / (depth + 20))
            selected.append({"mutant": code, "position": position, "wt": wt,
                             "alt": alt, "msa_depth": depth,
                             "pssm_delta_bits": bit(alt) - bit(wt),
                             "blosum62": int(BLOSUM62[wt, alt])})
    selected.sort(key=lambda x: (hashlib.sha256(
        f'{meta["DMS_id"]}|{x["mutant"]}'.encode()).hexdigest(), x["mutant"]))
    return selected[:100], {"eligible_before_hash_limit": len(selected),
                            "selected": min(100, len(selected)),
                            "rejections": dict(rejection), "raw_member": member}


def prepare() -> None:
    metadata = {row["DMS_id"]: row for row in csv.DictReader(REF.open())}
    stage1 = list(csv.DictReader(STAGE1.open()))
    clusters = defaultdict(list)
    for row in stage1:
        clusters[int(row["cluster_50"])].append(row)
    assert len(clusters) == 174
    cohort, candidates, qc = [], [], []
    with zipfile.ZipFile(RAW) as raw, zipfile.ZipFile(MSAS) as msas:
        for cluster in sorted(clusters):
            options = sorted((row["assay_id"] for row in clusters[cluster]
                              if 50 <= int(row["sequence_length"]) <= 1000
                              and metadata[row["assay_id"]]["MSA_filename"]),
                             key=str)
            record = {"cluster_50": cluster, "assay_id": options[0] if options else "",
                      "status": "", "reason": "", "candidate_count": 0,
                      "sequence_length": ""}
            if not options:
                record.update(status="UNAVAILABLE", reason="no_50_to_1000_aa_assay_with_msa")
                cohort.append(record)
                continue
            meta = metadata[options[0]]
            record["sequence_length"] = len(meta["target_seq"])
            try:
                columns, stats = msa_counts(meta, msas)
                variants, details = eligible_mutants(meta, columns, raw)
                if len(variants) < 20:
                    raise ValueError("fewer than 20 eligible single substitutions")
                record.update(status="ELIGIBLE", candidate_count=len(variants))
                for variant in variants:
                    candidates.append({"cluster_50": cluster, "assay_id": options[0],
                                       **variant})
                qc.append({"cluster_50": cluster, "assay_id": options[0],
                           **stats, **{key: details[key] for key in
                                     ("eligible_before_hash_limit", "selected", "raw_member")}})
            except (ValueError, KeyError, IndexError, UnicodeError) as error:
                record.update(status="UNAVAILABLE", reason=str(error))
            cohort.append(record)
            if cluster % 20 == 0:
                print(json.dumps({"cluster": cluster, "eligible": sum(
                    row["status"] == "ELIGIBLE" for row in cohort)}), flush=True)
    write_csv(OUT / "cohort.csv", cohort, list(cohort[0]))
    write_csv(OUT / "candidates_blind.csv", candidates, list(candidates[0]))
    write_csv(OUT / "msa_qc.csv", qc, list(qc[0]))
    summary = {"clusters_inherited": len(clusters), "eligible_clusters": sum(
        row["status"] == "ELIGIBLE" for row in cohort),
        "excluded_reasons": dict(Counter(row["reason"] for row in cohort
                                         if row["status"] != "ELIGIBLE")),
        "candidate_rows": len(candidates),
        "model_calls": 0, "gpu_hours": 0}
    (OUT / "prepare_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    hashes = {str(path): sha256_file(path) for path in (REF, STAGE1, RAW, MSAS, SCORES)}
    (OUT / "input_hashes.json").write_text(json.dumps(hashes, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


def percentiles(values: dict[str, float]) -> dict[str, float]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    n = len(ordered)
    if n == 1:
        return {ordered[0][0]: 0.5}
    result = {}
    offset = 0
    while offset < n:
        end = offset + 1
        while end < n and ordered[end][1] == ordered[offset][1]:
            end += 1
        rank = ((offset + end - 1) / 2) / (n - 1)
        result.update({key: rank for key, _ in ordered[offset:end]})
        offset = end
    return result


def finite(value: str) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def allowed_score_fields(fields: list[str], indices: dict[str, int]) -> dict:
    """Read exactly the published model fields; no assay-label field is indexed."""
    return {"esm2": finite(fields[indices["ESM2_650M"]]),
            "esm_if1": finite(fields[indices["ESM-IF1"]])}


def floor_m_available(selected: set[str], esm2: dict[str, float]) -> bool:
    return bool(selected) and set(esm2) == selected


def score() -> None:
    candidates = defaultdict(list)
    for row in csv.DictReader((OUT / "candidates_blind.csv").open()):
        candidates[row["assay_id"]].append(row)
    predictions, coverage = [], []
    with zipfile.ZipFile(SCORES) as archive:
        for assay_id, variants in sorted(candidates.items()):
            selected = {row["mutant"] for row in variants}
            member = assay_id + ".csv"
            if member not in archive.namelist():
                coverage.append({"assay_id": assay_id, "floor_m": "UNAVAILABLE",
                                 "reason": "score_member_missing", "esm2_missing": len(variants),
                                 "esm_if1_missing": len(variants)})
                model_scores = {}
            else:
                model_scores = {}
                with io.TextIOWrapper(archive.open(member), encoding="utf-8") as handle:
                    reader = csv.reader(handle)
                    header = next(reader)
                    # Explicit allowlist; never index DMS_score or DMS_score_bin.
                    allowed = {name: header.index(name) for name in
                               ("mutant", "ESM2_650M", "ESM-IF1")}
                    for fields in reader:
                        key = fields[allowed["mutant"]]
                        if key in selected:
                            model_scores[key] = allowed_score_fields(fields, allowed)
            pssm = percentiles({row["mutant"]: float(row["pssm_delta_bits"])
                                for row in variants})
            blosum = percentiles({row["mutant"]: float(row["blosum62"])
                                 for row in variants})
            c_score = {key: (pssm[key] + blosum[key]) / 2 for key in selected}
            c_rank = percentiles(c_score)
            esm2 = {key: data["esm2"] for key, data in model_scores.items()
                    if data["esm2"] is not None}
            esm_if1 = {key: data["esm_if1"] for key, data in model_scores.items()
                       if data["esm_if1"] is not None}
            all_esm2 = floor_m_available(selected, esm2)
            e2_rank = percentiles(esm2) if esm2 else {}
            if_rank = percentiles(esm_if1) if esm_if1 else {}
            coverage.append({"assay_id": assay_id,
                             "floor_m": "EVALUABLE" if all_esm2 else "UNAVAILABLE",
                             "reason": "" if all_esm2 else "esm2_missing",
                             "esm2_missing": len(selected) - len(esm2),
                             "esm_if1_missing": len(selected) - len(esm_if1)})
            for row in variants:
                key = row["mutant"]
                components = [c_rank[key], e2_rank[key]] if all_esm2 else []
                if all_esm2 and key in if_rank:
                    components.append(if_rank[key])
                predictions.append({"cluster_50": row["cluster_50"],
                                    "assay_id": assay_id, "mutant": key,
                                    "floor_c_score": c_score[key],
                                    "floor_m_score": sum(components)/len(components)
                                    if components else "",
                                    "floor_m_components": len(components),
                                    "esm_if1_present": key in if_rank})
            print(json.dumps({"assay": assay_id, "m": all_esm2,
                              "missing_esm2": len(selected) - len(esm2)}), flush=True)
    write_csv(OUT / "floor_predictions_blind.csv", predictions, list(predictions[0]))
    write_csv(OUT / "floor_coverage.csv", coverage, list(coverage[0]))
    print(json.dumps({"items": len(candidates),
                      "floor_m_evaluable": sum(row["floor_m"] == "EVALUABLE"
                                                for row in coverage),
                      "predictions": len(predictions)}))


if __name__ == "__main__":
    {"prepare": prepare, "score": score}[sys.argv[1]]()
