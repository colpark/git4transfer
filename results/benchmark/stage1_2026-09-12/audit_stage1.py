#!/usr/bin/env python3
"""Stage 1 metadata-only denominator audit; no model or GPU calls."""

from __future__ import annotations

import csv
import io
import json
import re
import subprocess
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
CDHIT = ROOT / "biology-stack/cd-hit/cd-hit"
PG = Path("/tmp/ProteinGym_stage1/reference_files/DMS_substitutions.csv")
MEGA = Path("/tmp/stage1_megascale_processed.zip")
MEGA_PDB = Path("/tmp/stage1_megascale_afpdb.zip")


def write_csv(name: str, rows: list[dict], fields: list[str]) -> None:
    with (OUT / name).open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def cluster(seqs: dict[str, str], stem: str) -> tuple[dict[str, int], dict]:
    fasta = OUT / f"{stem}_sequences.fasta"
    with fasta.open("w") as handle:
        for key, seq in seqs.items():
            handle.write(f">{key}\n{seq}\n")
        # Positive control: exact duplicate must join its original cluster.
        first = next(iter(seqs))
        handle.write(f">CONTROL_DUPLICATE\n{seqs[first]}\n")
    target = OUT / f"{stem}_cluster"
    command = [str(CDHIT), "-i", str(fasta), "-o", str(target), "-c", "0.5",
               "-n", "3", "-g", "1", "-G", "0", "-aS", "0.8", "-d", "0",
               "-T", "1", "-M", "1024", "-l", "10"]
    subprocess.run(command, check=True, text=True, capture_output=True)
    mapping: dict[str, int] = {}
    current = -1
    for line in Path(f"{target}.clstr").read_text().splitlines():
        if line.startswith(">Cluster "):
            current = int(line.split()[-1])
        else:
            match = re.search(r">(.+?)\.\.\.", line)
            if match:
                mapping[match.group(1)] = current
    first = next(iter(seqs))
    assert mapping.pop("CONTROL_DUPLICATE") == mapping[first], "duplicate control failed"
    assert set(mapping) == set(seqs), "clustering lost a unit"
    return mapping, {"command": command, "duplicate_control": "PASS",
                     "raw": len(seqs), "clusters": len(set(mapping.values()))}


def w1() -> dict:
    rows = list(csv.DictReader(PG.open(newline="")))
    assert len(rows) == 217 and len({r["DMS_id"] for r in rows}) == 217
    assert all(set(r["target_seq"]) <= set("ACDEFGHIKLMNPQRSTVWY") for r in rows)
    seqs = {r["DMS_id"]: r["target_seq"] for r in rows}
    clustered, control = cluster(seqs, "w1")
    assert clustered["A0A140D2T1_ZIKV_Sourisseau_2019"] != clustered["A4_HUMAN_Seuma_2022"], "unrelated-sequence control failed"
    control["unrelated_sequence_control"] = "PASS"
    result = [{
        "assay_id": r["DMS_id"], "cluster_50": clustered[r["DMS_id"]],
        "sequence_length": len(r["target_seq"]),
        "assay_size_total_mutants": int(r["DMS_total_number_mutants"]),
        "assay_size_single_mutants": int(r["DMS_number_single_mutants"]),
        "taxon": r["taxon"], "organism": r["source_organism"],
        "publication_year": int(r["year"]),
        "pre_2025_publication": int(r["year"]) < 2025,
        "post_2025_publication": int(r["year"]) > 2025,
        "source_version": r["ProteinGym_version"],
    } for r in rows]
    write_csv("w1_assays.csv", result, list(result[0]))
    return {**control, "taxa": dict(Counter(r["taxon"] for r in rows)),
            "years": dict(sorted(Counter(int(r["year"]) for r in rows).items())),
            "post_2025_assays": sum(int(r["year"]) > 2025 for r in rows),
            "pre_2025_clusters": len({clustered[r["DMS_id"]] for r in rows if int(r["year"]) < 2025})}


def _pdb_sequence_for_1a0n() -> str:
    aa3 = {"ALA":"A","ARG":"R","ASN":"N","ASP":"D","CYS":"C","GLN":"Q",
           "GLU":"E","GLY":"G","HIS":"H","ILE":"I","LEU":"L","LYS":"K",
           "MET":"M","PHE":"F","PRO":"P","SER":"S","THR":"T","TRP":"W",
           "TYR":"Y","VAL":"V"}
    with zipfile.ZipFile(MEGA_PDB) as z:
        lines = z.read("AlphaFold_model_PDBs/1A0N.pdb").decode().splitlines()
    residues: dict[tuple[str, str], str] = {}
    for line in lines:
        if line.startswith("ATOM"):
            residues[(line[21], line[22:27])] = aa3.get(line[17:20], "X")
    seq = "".join(residues.values())
    assert seq == "VTLFVALYDYEARTEDDLSFHKGEKFQILNSSEGDWWEARSLTTGETGYIPSNYVAPV"
    return seq


def w2() -> dict:
    member = "Processed_K50_dG_datasets/Tsuboyama2023_Dataset2_Dataset3_20230416.csv"
    domains: dict[str, dict] = {}
    wt_rows: dict[str, dict] = {}
    mutation_counts: Counter[str] = Counter()
    usable_counts: Counter[str] = Counter()
    with zipfile.ZipFile(MEGA) as z, io.TextIOWrapper(z.open(member)) as stream:
        for row in csv.DictReader(stream):
            key = row["WT_name"]
            if key not in domains:
                domains[key] = {"domain_id": key, "wt_cluster_source": row["WT_cluster"]}
            mutation_counts[key] += 1
            if row["mut_type"] != "wt" and row["ddG_ML"] not in {"", "-"}:
                usable_counts[key] += 1
            if row["mut_type"] == "wt" and key not in wt_rows:
                wt_rows[key] = row
    assert len(domains) == 479 and len(wt_rows) == 478
    for key, data in domains.items():
        data["sequence"] = wt_rows[key]["aa_seq"] if key in wt_rows else _pdb_sequence_for_1a0n()
        data["origin"] = "natural" if data["wt_cluster_source"].isdigit() else "designed"
        data["total_rows"] = mutation_counts[key]
        data["usable_ddg_mutation_rows"] = usable_counts[key]
        data["sequence_source"] = "wt_row" if key in wt_rows else "released_AF2_PDB"
    seqs = {key: data["sequence"] for key, data in domains.items()}
    assert all(set(seq) <= set("ACDEFGHIKLMNPQRSTVWY") for seq in seqs.values())
    clustered, control = cluster(seqs, "w2")
    assert clustered["1A0N.pdb"] != clustered["EA|run2_0325_0005.pdb"], "unrelated-sequence control failed"
    control["unrelated_sequence_control"] = "PASS"
    result = [{
        "domain_id": key, "cluster_50": clustered[key], "origin": data["origin"],
        "sequence_length": len(data["sequence"]),
        "total_rows": data["total_rows"], "usable_ddg_mutation_rows": data["usable_ddg_mutation_rows"],
        "sequence_source": data["sequence_source"], "source_wt_cluster": data["wt_cluster_source"],
        "publication_year": 2023,
    } for key, data in sorted(domains.items())]
    write_csv("w2_domains.csv", result, list(result[0]))
    return {**control, "origin": dict(Counter(d["origin"] for d in domains.values())),
            "clusters_with_usable_ddg": len({clustered[k] for k in domains if usable_counts[k] > 0}),
            "domains_with_usable_ddg": sum(usable_counts[k] > 0 for k in domains),
            "missing_wt_row_domain": "1A0N.pdb"}


if __name__ == "__main__":
    summary = {"w1": w1(), "w2": w2(), "model_calls": 0, "gpu_hours": 0}
    (OUT / "sequence_audit.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
