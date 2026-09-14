"""Label-safe Stage 4 pilot selection and prompt freeze; run only after Stage 3d gate."""

from __future__ import annotations

import csv
import hashlib
import json
import random
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from stage3_w1 import AA, a2m_records

ROOT = Path(__file__).resolve().parents[1]
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
STRUCTURES = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures"
OUT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
STEM1 = ("You have a protein and candidate single substitutions. Your assay queue accepts ten. "
         "Choose ten variants, rank them, and state what evidence supports each choice and "
         "what would overturn it. Report variants you considered and rejected. Do not claim "
         "a measured assay outcome.")
STEM2 = ("Given a protein and candidate single substitutions, select ten for a limited assay "
         "queue. Rank the ten; explain the evidence for each, what would change your choice, "
         "and which candidates you considered but rejected. Do not claim a measured assay outcome.")
CONTRACT = """

Submit exactly one answer through the mounted record channel, using item_id
`pilot_item`. The answer object must contain `selected`: exactly ten entries,
each with `rank` (1–10), `mutant`, `basis`, `evidence` (receipt ID array),
`validation` (array of {category, call_id}), and `would_overturn`.
Include `rejected`: an array of {mutant, reason}, empty only if none were
rejected. If possible, include `ranking`: one {mutant, score} entry per
supplied candidate, with larger predicted scores better. The scores are your predictions, not
measured fitness. Every cited receipt must come from a successful tool call
in this run. If you cannot support a site/variant, say so; do not invent data.
Submit only when finished. Do not claim an assay result.
""".strip("\n")
FORCED = ("Each submitted candidate must carry validation from at least three distinct "
          "categories: structural, energetic, and sequence or geometric. A second call "
          "to the same tool with different arguments does not count.")
LOW_VARIETY = ("Each submitted candidate must carry at least six validation results "
               "drawn from no more than two categories.")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    gate_path = ROOT / "results/benchmark/stage3d_2026-09-13/thermal_envelope.json"
    if not gate_path.is_file():
        raise SystemExit("Stage 3d full-grant envelope is not on disk; pilot selection forbidden")
    gate = json.loads(gate_path.read_text())
    if gate.get("thirty_minute_envelope_pass") is not True:
        raise SystemExit("Stage 3d full-grant envelope has not passed; pilot selection forbidden")
    reach = list(csv.DictReader((ROOT / "results/benchmark/stage3d_2026-09-13/reachability.csv").open()))
    if len(reach) != 8 or any(row["verdict"] != "PASS" for row in reach):
        raise SystemExit("Stage 3d remount ladder incomplete; pilot selection forbidden")
    OUT.mkdir(parents=True, exist_ok=True)
    static = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "preregistration_sha256": sha256(OUT / "preregistration.md"),
              "source_floor_scores_sha256": sha256(STAGE3 / "floor_item_scores.csv"),
              "source_prompt_manifest_sha256": sha256(STAGE3 / "prompt_manifest.jsonl"),
              "prompt_template_code_sha256": sha256(Path(__file__)),
              "scoring_code_sha256": sha256(ROOT / "benchmark-mcp/pilot_score.py"),
              "stage3_evaluator_sha256": sha256(ROOT / "benchmark-mcp/stage3_evaluate.py"),
              "stage3_floor_code_sha256": sha256(ROOT / "benchmark-mcp/stage3_w1.py"),
              "runner_code_sha256": sha256(ROOT / "benchmark-mcp/pilot_run.py"),
              "pilot_shim_sha256": sha256(ROOT / "benchmark-mcp/pilot_responses_shim.py"),
              "record_mount_sha256": sha256(ROOT / "benchmark-mcp/pilot_record_server.py")}
    preselection = OUT / "preselection_freeze.json"
    if preselection.exists():
        raise SystemExit("preselection freeze already exists; refusing to redraw items")
    preselection.write_text(json.dumps(static, indent=2) + "\n")
    scores = list(csv.DictReader((STAGE3 / "floor_item_scores.csv").open()))
    by_assay: dict[str, dict] = {}
    for row in scores:
        by_assay.setdefault(row["assay_id"], {})[row["floor"]] = row
    eligible = [(float(pair["M"]["rho"]), assay)
                for assay, pair in by_assay.items()
                if pair.get("M", {}).get("status") == "EVALUABLE"
                and pair.get("C", {}).get("status") == "EVALUABLE"]
    eligible.sort(key=lambda pair: (pair[0], pair[1]))
    if len(eligible) != 148:
        raise SystemExit(f"expected 148 evaluable assays, found {len(eligible)}")
    rng = random.Random(42)
    chosen: list[tuple[int, str]] = []
    for quartile in range(4):
        group = eligible[quartile * 37:(quartile + 1) * 37]
        for assay in sorted(rng.sample([assay for _, assay in group], 2)):
            chosen.append((quartile + 1, assay))
    manifest = {row["assay_id"]: row for line in (STAGE3 / "prompt_manifest.jsonl").open()
                if (row := json.loads(line))}
    metadata = {row["DMS_id"]: row for row in
                csv.DictReader((STAGE3 / "input/DMS_substitutions.csv").open())}
    prompt_dir = OUT / "prompts"
    prompt_dir.mkdir(exist_ok=True)
    fasta_dir = OUT / "reference_fastas"
    fasta_dir.mkdir(exist_ok=True)
    structure_dir = OUT / "reference_pdbs"
    structure_dir.mkdir(exist_ok=True)
    records = []
    with zipfile.ZipFile(STAGE3 / "input/DMS_msa_files.zip") as msa_archive:
      for index, (quartile, assay) in enumerate(sorted(chosen, key=lambda x: x[1])):
        source = manifest[assay]["prompt"]
        old_stem, rest = source.split("\n\nProtein sequence:\n", 1)
        if old_stem != STEM1:
            raise SystemExit(f"unexpected frozen Stage 3 stem for {assay}")
        fasta = fasta_dir / f"item{index + 1:02d}_homologs.fasta"
        member = "DMS_msa_files/" + metadata[assay]["MSA_filename"]
        lines = []
        for ordinal, (_, a2m) in enumerate(a2m_records(msa_archive.open(member))):
            sequence = "".join(char.upper() for char in a2m if char.isalpha())
            if len(sequence) >= 50 and set(sequence) <= AA:
                lines += [f">homolog_{ordinal:04d}", sequence]
            if len(lines) >= 400 or sum(len(line) for line in lines) >= 5_000_000:
                break
        if not lines:
            raise SystemExit(f"no usable homolog FASTA entries for {assay}")
        fasta.write_text("\n".join(lines) + "\n")
        source_structure = STRUCTURES / metadata[assay]["pdb_file"]
        if not source_structure.is_file():
            raise SystemExit(f"missing label-free reference structure for {assay}")
        structure = structure_dir / f"item{index + 1:02d}.pdb"
        shutil.copyfile(source_structure, structure)
        base = (STEM1 if index % 2 == 0 else STEM2) + "\n\nProtein sequence:\n" + rest
        base += "\n\nReference homolog FASTA for retrieval: " + str(fasta)
        base += "\nReference structure PDB for geometric evaluation: " + str(structure)
        base += "\n\n" + CONTRACT + "\n"
        files = {}
        for arm, suffix in (("1", ""), ("2", ""), ("3", ""),
                            ("3F", "\n\n" + FORCED + "\n"),
                            ("3L", "\n\n" + LOW_VARIETY + "\n")):
            path = prompt_dir / f"item{index + 1:02d}_arm{arm}.txt"
            path.write_text(base + suffix)
            files[arm] = {"path": str(path), "sha256": sha256(path)}
        c, m = by_assay[assay]["C"], by_assay[assay]["M"]
        n = int(m["n_candidates"])
        records.append({"pilot_item": index + 1, "quartile": quartile,
                        "assay_id": assay, "cluster_50": m["cluster_50"],
                        "n_candidates": n, "chance_p_at_10": 10 / n,
                        "floor_c_p_at_10": float(c["precision_at_10"]),
                        "floor_c_rho": float(c["rho"]),
                        "floor_m_p_at_10": float(m["precision_at_10"]),
                        "floor_m_rho": float(m["rho"]),
                        "homolog_fasta_path": str(fasta),
                        "homolog_fasta_sha256": sha256(fasta),
                        "reference_pdb_path": str(structure),
                        "reference_pdb_sha256": sha256(structure),
                        "source_pdb_path": str(source_structure),
                        "source_pdb_sha256": sha256(source_structure),
                        "prompt_files": files})
    selection = OUT / "selection.json"
    selection.write_text(json.dumps({"seed": 42, "quartile_size": 37,
                                    "items": records}, indent=2) + "\n")
    selection_csv = OUT / "selection.csv"
    fields = ("pilot_item", "quartile", "assay_id", "cluster_50", "n_candidates",
              "chance_p_at_10", "floor_c_p_at_10", "floor_c_rho",
              "floor_m_p_at_10", "floor_m_rho")
    with selection_csv.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: record[key] for key in fields} for record in records)
    schedule = [{"item": item["pilot_item"], "assay_id": item["assay_id"],
                 "arm": arm, "mode": mode, "sample": sample}
                for item in records for arm in ("1", "2", "3", "3F", "3L")
                for mode in ("unguided", "guided") for sample in (1, 2, 3)]
    random.Random(42).shuffle(schedule)
    for index, cell in enumerate(schedule, 1):
        cell["run_id"] = f"pilot_{index:03d}"
    schedule_path = OUT / "run_schedule.json"
    schedule_path.write_text(json.dumps({"seed": 42, "runs": schedule}, indent=2) + "\n")
    freeze = {**static,
              "preselection_freeze_sha256": sha256(preselection),
              "selection_sha256": sha256(selection),
              "selection_csv_sha256": sha256(selection_csv),
              "schedule_sha256": sha256(schedule_path)}
    (OUT / "freeze_hashes.json").write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps({"selected": len(records), "selection_sha256": freeze["selection_sha256"]}))


if __name__ == "__main__":
    main()
