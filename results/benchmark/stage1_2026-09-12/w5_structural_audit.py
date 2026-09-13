#!/usr/bin/env python3
"""Read-only RCSB audit of exact-sequence Ca/REE cross-deposits."""

from __future__ import annotations

import csv
import json
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
META = ROOT / "E1-Metal-Binding-main/data/dataset_artifacts/ree_plip_2026-05-12_qa_rebuild/metadata/ree_binding_metadata.csv"
SEARCH = "https://search.rcsb.org/rcsbsearch/v2/query"
CORE = "https://data.rcsb.org/rest/v1/core/polymer_entity"


def search_ca(seq: str) -> dict:
    query = {
        "query": {"type": "group", "logical_operator": "and", "nodes": [
            {"type": "terminal", "service": "sequence", "parameters": {
                "sequence_type": "protein", "value": seq, "identity_cutoff": 1.0,
                "evalue_cutoff": 0.1}},
            {"type": "terminal", "service": "text", "parameters": {
                "attribute": "rcsb_nonpolymer_entity_container_identifiers.nonpolymer_comp_id",
                "operator": "exact_match", "value": "CA"}},
        ]},
        "return_type": "polymer_entity",
        "request_options": {"paginate": {"start": 0, "rows": 1000}},
    }
    for attempt in range(4):
        try:
            response = requests.post(SEARCH, json=query, timeout=30)
            if response.status_code == 204:
                return {"total_count": 0, "result_set": []}
            response.raise_for_status()
            payload = response.json()
            if payload["total_count"] > 1000:
                raise RuntimeError("pagination required")
            return payload
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.5 * (attempt + 1))
    raise AssertionError


def core_seq(entity: str) -> tuple[str, str]:
    pdb, entity_id = entity.split("_")
    for attempt in range(4):
        try:
            response = requests.get(f"{CORE}/{pdb}/{entity_id}", timeout=30)
            response.raise_for_status()
            return entity, response.json()["entity_poly"]["pdbx_seq_one_letter_code_can"]
        except Exception:
            if attempt == 3:
                raise
            time.sleep(0.5 * (attempt + 1))
    raise AssertionError


def main() -> None:
    rows = list(csv.DictReader(META.open(newline="")))
    by_sequence: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if len(row["sequence"]) >= 10:
            by_sequence[row["sequence"]].append(row)
    assert len(by_sequence) == 439
    with ThreadPoolExecutor(max_workers=8) as pool:
        responses = dict(zip(by_sequence, pool.map(search_ca, by_sequence)))
    candidates = sorted({
        hit["identifier"] for response in responses.values()
        for hit in response.get("result_set", [])
    })
    with ThreadPoolExecutor(max_workers=8) as pool:
        canonical = dict(pool.map(core_seq, candidates))
    out_rows = []
    for seq, source_rows in by_sequence.items():
        ca_entities = [
            hit["identifier"] for hit in responses[seq].get("result_set", [])
            if canonical[hit["identifier"]] == seq
        ]
        source_pdbs = sorted({row["pdb_id"] for row in source_rows})
        elements = sorted({row["element_code"] for row in source_rows
                           if row["element_code"] not in {"", "REE"}})
        for ca_entity in ca_entities:
            ca_pdb = ca_entity.split("_")[0]
            for source_pdb in source_pdbs:
                if ca_pdb == source_pdb:
                    continue
                source_elems = sorted({r["element_code"] for r in source_rows
                                       if r["pdb_id"] == source_pdb
                                       and r["element_code"] not in {"", "REE"}})
                for element in source_elems:
                    out_rows.append({
                        "evidence_type": "pdb_exact_sequence_ca_ree",
                        "protein_sequence_sha256": __import__("hashlib").sha256(seq.encode()).hexdigest(),
                        "ree_pdb": source_pdb, "ca_pdb": ca_pdb,
                        "ca_polymer_entity": ca_entity,
                        "element_a": "CA", "element_b": element,
                        "same_exact_polymer_sequence": True,
                        "selectivity_ground_truth": False,
                        "limitation": "separate deposits establish occupancy, not relative affinity",
                        "source": "https://search.rcsb.org/; https://data.rcsb.org/",
                    })
    out_rows.sort(key=lambda x:(x["element_b"],x["ree_pdb"],x["ca_pdb"],x["ca_polymer_entity"]))
    with (OUT / "w5_structural_pairs.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(out_rows[0]) if out_rows else [
            "evidence_type","protein_sequence_sha256","ree_pdb","ca_pdb","ca_polymer_entity",
            "element_a","element_b","same_exact_polymer_sequence","selectivity_ground_truth",
            "limitation","source"])
        writer.writeheader(); writer.writerows(out_rows)
    summary = {
        "source_ree_raw_chain_pairs": len({(r["pdb_id"],r["chain_id"]) for r in rows}),
        "unique_ree_sequences_at_least_10aa": len(by_sequence),
        "short_sequences_unsearchable": sorted({f"{r['pdb_id']}_{r['chain_id']}" for r in rows
                                                 if len(r["sequence"]) < 10}),
        "candidate_ca_entities": len(candidates),
        "exact_sequence_cross_deposit_rows": len(out_rows),
        "distinct_ree_ca_entry_pairs": len({(r["ree_pdb"],r["ca_pdb"]) for r in out_rows}),
        "distinct_exact_sequences": len({r["protein_sequence_sha256"] for r in out_rows}),
        "element_pair_contrasts": sorted({f"CA/{r['element_b']}" for r in out_rows}),
        "selectivity_ground_truth_pairs": 0,
        "positive_control_1NCZ_1TOP": any(r["ree_pdb"] == "1NCZ" and r["ca_pdb"] == "1TOP" for r in out_rows),
        "negative_control_same_entry_excluded": all(r["ree_pdb"] != r["ca_pdb"] for r in out_rows),
    }
    assert summary["positive_control_1NCZ_1TOP"]
    assert summary["negative_control_same_entry_excluded"]
    (OUT / "w5_structural_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
