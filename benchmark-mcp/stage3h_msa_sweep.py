"""Label-free BLAST→MSA coverage audit of the 140 non-pilot W1 items."""

from __future__ import annotations

import csv
import json
import statistics
import zipfile
from pathlib import Path

import classical
from pilot_prepare import CONTRACT, STEM1, STEM2
from stage3_w1 import AA, a2m_records

ROOT = Path(__file__).resolve().parents[1]
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
OUT = ROOT / "results/benchmark/stage3h_2026-09-14"
PILOT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
STRUCTURES = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pilot = {row["assay_id"] for row in json.loads((PILOT / "selection.json").read_text())["items"]}
    manifest = {row["assay_id"]: row for line in (STAGE3 / "prompt_manifest.jsonl").open()
                if (row := json.loads(line))}
    remaining = sorted(set(manifest) - pilot)
    if len(pilot) != 8 or len(remaining) != 140:
        raise SystemExit(f"expected 8 discarded and 140 remaining; got {len(pilot)} and {len(remaining)}")
    metadata = {row["DMS_id"]: row for row in csv.DictReader((STAGE3 / "input/DMS_substitutions.csv").open())}
    fastas = OUT / "audit_fastas"
    fastas.mkdir(exist_ok=True)
    rows = []
    with zipfile.ZipFile(STAGE3 / "input/DMS_msa_files.zip") as archive:
        for index, assay in enumerate(remaining, 1):
            source_prompt = manifest[assay]["prompt"]
            sequence = source_prompt.split("\n\nProtein sequence:\n", 1)[1].split("\n\nCandidate variants:\n", 1)[0].strip()
            member = "DMS_msa_files/" + metadata[assay]["MSA_filename"]
            fasta = fastas / f"{index:03d}.fasta"
            lines = []
            for ordinal, (_, a2m) in enumerate(a2m_records(archive.open(member))):
                homolog = "".join(char.upper() for char in a2m if char.isalpha())
                if len(homolog) >= 50 and set(homolog) <= AA:
                    lines += [f">homolog_{ordinal:04d}", homolog]
                if len(lines) >= 400 or sum(map(len, lines)) >= 5_000_000:
                    break
            if not lines:
                row = {"assay_id": assay, "status": "NO_REFERENCE_ROWS", "usable_homologs": 0,
                       "blast_hits": 0, "query_length": len(sequence), "reference_rows": 0,
                       "error": "no canonical homolog FASTA entries", "reference_fasta": ""}
            else:
                fasta.write_text("\n".join(lines) + "\n")
                try:
                    result = classical.blast_msa(sequence, str(fasta), max_hits=100)
                    row = {"assay_id": assay, "status": "USABLE", "usable_homologs": result["depth"] - 1,
                           "blast_hits": len(result["search_hits"]), "query_length": len(sequence),
                           "reference_rows": len(lines)//2, "error": "", "reference_fasta": str(fasta)}
                except Exception as exc:
                    # Preserve a missing/invalid MSA as zero; never relax the 80% coverage rule.
                    row = {"assay_id": assay, "status": "NO_USABLE_MSA" if isinstance(exc, ValueError) else "ERROR",
                           "usable_homologs": 0, "blast_hits": "", "query_length": len(sequence),
                           "reference_rows": len(lines)//2, "error": f"{type(exc).__name__}: {exc}",
                           "reference_fasta": str(fasta)}
            rows.append(row)
            with (OUT / "msa_coverage.csv").open("w", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=list(rows[0]), lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)
            if index % 10 == 0 or index == len(remaining):
                print(json.dumps({"done": index, "usable": sum(r["status"] == "USABLE" for r in rows)}), flush=True)
    usable = [row for row in rows if row["status"] == "USABLE"]
    if usable:
        counts = sorted(row["usable_homologs"] for row in usable)
        median = statistics.median(counts)
        choice = min(usable, key=lambda row: (abs(row["usable_homologs"] - median), row["assay_id"]))
        assay = choice["assay_id"]
        source = manifest[assay]["prompt"]
        old_stem, rest = source.split("\n\nProtein sequence:\n", 1)
        if old_stem != STEM1:
            raise RuntimeError("source prompt stem differs from frozen Stage 3")
        pdb = STRUCTURES / metadata[assay]["pdb_file"]
        if not pdb.is_file():
            raise RuntimeError(f"missing label-free reference structure: {pdb}")
        # Exact frozen Stage 4 text: same alternating stem rule, reference pointers, contract.
        prompt = STEM1 + "\n\nProtein sequence:\n" + rest
        prompt += "\n\nReference homolog FASTA for retrieval: " + choice["reference_fasta"]
        prompt += "\nReference structure PDB for geometric evaluation: " + str(pdb)
        prompt += "\n\n" + CONTRACT + "\n"
        (OUT / "diagnostic_prompt.txt").write_text(prompt)
        chosen = {"assay_id": assay, "usable_homologs": choice["usable_homologs"],
                  "median_usable_homologs": median, "reference_fasta": choice["reference_fasta"],
                  "reference_pdb": str(pdb), "n_remaining": len(rows), "n_usable": len(usable)}
        (OUT / "diagnostic_item.json").write_text(json.dumps(chosen, indent=2) + "\n")
        print(json.dumps({"selected": chosen}), flush=True)
    else:
        print(json.dumps({"selected": None, "reason": "no usable MSA among 140"}), flush=True)


if __name__ == "__main__":
    main()
