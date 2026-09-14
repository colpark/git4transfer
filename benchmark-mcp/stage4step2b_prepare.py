"""Label-blind sealed prompt materialization and 145-item registry."""

from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

from pilot_prepare import CONTRACT
from stage3_w1 import AA, a2m_records

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2b_2026-09-14"
S3 = ROOT / "results/benchmark/stage3_2026-09-13"
S1 = ROOT / "results/benchmark/stage4step1_2026-09-14"
PREP = ROOT / "results/benchmark/stage4prep_2026-09-14"
STRUCTURES = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures"
NEW_SEAL = "ENVZ_ECOLI_Ghose_2023"
SEALED = ("AACC1_PSEAI_Dandage_2018", "ARGR_ECOLI_Tsuboyama_2023_1AOY", NEW_SEAL)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def main() -> None:
    rows = list(csv.DictReader((PREP / "cohort_146.csv").open()))
    if len(rows) != 146 or sum(row["assay_id"] == NEW_SEAL for row in rows) != 1:
        raise SystemExit("146-item source or third seal mismatch")
    floor = [row for row in csv.DictReader((S3 / "floor_item_scores.csv").open())
             if row["floor"] == "M" and row["assay_id"] in {r["assay_id"] for r in rows}]
    if min(floor, key=lambda r: float(r["rho"]))["assay_id"] != NEW_SEAL:
        raise SystemExit("third seal is not the lowest published Floor M rho")
    cohort = OUT / "cohort_145.csv"
    if cohort.exists():
        raise SystemExit("cohort_145 already materialized")
    cohort.parent.mkdir(parents=True, exist_ok=True)
    with cohort.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(row for row in rows if row["assay_id"] != NEW_SEAL)
    if sum(1 for _ in csv.DictReader(cohort.open())) != 145:
        raise SystemExit("cohort count is not 145")
    prompts = {row["assay_id"]: row["prompt"] for line in (S3 / "prompt_manifest.jsonl").open()
               if (row := json.loads(line))}
    metadata = {row["DMS_id"]: row for row in csv.DictReader((S3 / "input/DMS_substitutions.csv").open())}
    manifest = []
    with zipfile.ZipFile(S3 / "input/DMS_msa_files.zip") as archive:
        for assay in SEALED:
            if assay == "ARGR_ECOLI_Tsuboyama_2023_1AOY":
                source = S1.parent / "stage3h_2026-09-14/diagnostic_prompt.txt"
                prompt = source.read_text()
                if len(prompt.encode()) != 2023:
                    raise SystemExit("ARGR prompt no longer matches accepted Step 1 prompt")
                fasta = ROOT / "results/benchmark/stage3h_2026-09-14/audit_fastas/012.fasta"
                pdb = STRUCTURES / "ARGR_ECOLI.pdb"
            else:
                member = "DMS_msa_files/" + metadata[assay]["MSA_filename"]
                lines = []
                for ordinal, (_, a2m) in enumerate(a2m_records(archive.open(member))):
                    sequence = "".join(char.upper() for char in a2m if char.isalpha())
                    if len(sequence) >= 50 and set(sequence) <= AA:
                        lines.extend((f">homolog_{ordinal:04d}", sequence))
                    if len(lines) >= 400 or sum(map(len, lines)) >= 5_000_000:
                        break
                if not lines:
                    raise SystemExit(f"no homolog reference for {assay}")
                fasta = OUT / "reference_fastas" / f"{assay}.fasta"
                write_once(fasta, "\n".join(lines) + "\n")
                pdb = STRUCTURES / metadata[assay]["pdb_file"]
                prompt = (prompts[assay] + "\n\nReference homolog FASTA for retrieval: " + str(fasta) +
                          "\nReference structure PDB for geometric evaluation: " + str(pdb) +
                          "\n\n" + CONTRACT + "\n")
            if not fasta.is_file() or not pdb.is_file():
                raise SystemExit(f"missing prompt reference for {assay}")
            path = OUT / "prompts" / f"{assay}.txt"
            write_once(path, prompt)
            n = len(prompts[assay].split("Candidate variants:\n", 1)[1].strip().split(", "))
            manifest.append({"assay_id": assay, "prompt_path": str(path.relative_to(ROOT)),
                             "prompt_sha256": sha(path), "prompt_bytes": len(path.read_bytes()),
                             "candidate_count": n,
                             "fasta_path": str(fasta.relative_to(ROOT)), "fasta_sha256": sha(fasta),
                             "pdb_path": str(pdb.relative_to(ROOT)), "pdb_sha256": sha(pdb)})
    write_once(OUT / "sealed_prompt_manifest.jsonl",
               "".join(json.dumps(row, sort_keys=True) + "\n" for row in manifest))
    write_once(OUT / "empty_mcp.json", json.dumps({"mcpServers": {}}, indent=2) + "\n")
    print(json.dumps({"sealed": list(SEALED), "cohort": 145,
                      "prompt_bytes": {r["assay_id"]: r["prompt_bytes"] for r in manifest}}))


if __name__ == "__main__":
    main()
