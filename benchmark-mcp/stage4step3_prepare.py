"""Prepare the label-free ten-item comparison inputs exactly once."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

from stage4step2e_contract import POLICY_ID, canonical_sha, file_sha
from stage4step3_prompt import prompt as prompt_only

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
S1 = ROOT / "results/benchmark/stage4step1_2026-09-14"
S2E = ROOT / "results/benchmark/stage4step2e_2026-09-14"
S3 = ROOT / "results/benchmark/stage3_2026-09-13"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, text: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def parse_source_prompt(path: Path) -> tuple[str, tuple[str, ...]]:
    text = path.read_text()
    try:
        sequence = text.split("Protein sequence:\n", 1)[1].split("\n\n", 1)[0].strip()
        candidates = tuple(text.split("Candidate variants:\n", 1)[1].splitlines()[0].split(", "))
    except (IndexError, ValueError) as exc:
        raise SystemExit(f"malformed label-free source prompt: {path}") from exc
    if len(candidates) != 100 or len(set(candidates)) != 100:
        raise SystemExit(f"expected 100 unique candidates: {path}")
    return sequence, candidates


def b4_prompt(neutral_id: str, endpoint: dict, candidates: tuple[str, ...]) -> str:
    return f"""B4 v3 prospective adaptive policy for the ten-item comparison.

Rank every supplied candidate for the declared endpoint. The available evidence tools are item-bound: callers provide only a candidate variant. They do not accept a sequence, path, structure, MSA, endpoint identifier, or label. Generic plausibility evidence is not a measured assay outcome and may be mechanistically misaligned; disclose the adaptive rule in method_summary.

Neutral item: {neutral_id}
Declared label-free endpoint context:
{json.dumps(endpoint, sort_keys=True)}

Candidate variants:
{', '.join(candidates)}

Call submit_answer exactly once with only an answer object. The answer has exactly five keys: policy_id, method_summary, selected, rejected, ranking. policy_id is {POLICY_ID}. selected is exactly the first ten ranked variants; rejected is every remaining variant in rank order. ranking contains every candidate once with consecutive integer rank, mutant, one or more real evidence_call_ids, and rationale. Every row requires its own successful score_variant_fm receipt. Do not copy or supply any cryptographic hash. Invalid output is a COVERAGE FAILURE, never a zero.
"""


def main() -> None:
    selection = json.loads((OUT / "comparison_10_selection.json").read_text())
    ids = selection["items"]
    if len(ids) != 10 or len(set(ids)) != 10:
        raise SystemExit("selection is not ten unique items")
    manifests = {row["assay_id"]: row for line in (S1 / "prompt_manifest_146_executable.jsonl").open()
                 if (row := json.loads(line))}
    internal = {row["internal_assay_id"]: row for line in (S2E / "endpoint_registry_145_internal.jsonl").open()
                if (row := json.loads(line))}
    visible = {row["neutral_item_id"]: row for line in (S2E / "endpoint_registry_145_model_visible.jsonl").open()
               if (row := json.loads(line))}
    records = []
    for ordinal, assay in enumerate(ids, 1):
        neutral = f"cmp_{ordinal:03d}"
        source = manifests.get(assay)
        endpoint_link = internal.get(assay)
        if source is None or endpoint_link is None:
            raise SystemExit(f"missing label-free manifest data for {assay}")
        endpoint = visible[endpoint_link["neutral_item_id"]]["endpoint"]
        source_prompt = ROOT / source["prompt_path"]
        source_fasta = ROOT / source["fasta_path"]
        source_pdb = ROOT / source["pdb_path"]
        for key, path in (("prompt", source_prompt), ("fasta", source_fasta), ("pdb", source_pdb)):
            expected = source[f"{key}_sha256"]
            if not path.is_file() or sha(path) != expected:
                raise SystemExit(f"source {key} missing or changed for {assay}")
        sequence, candidates = parse_source_prompt(source_prompt)
        item = OUT / "inputs" / neutral
        fasta, pdb = item / "reference.fasta", item / "reference.pdb"
        if item.exists():
            raise SystemExit(f"comparison input already exists: {neutral}")
        item.mkdir(parents=True)
        shutil.copyfile(source_fasta, fasta)
        original_pdb = source_pdb.read_text()
        pdb.write_text(original_pdb if original_pdb.startswith("HEADER") else
                       "HEADER    NEUTRAL REFERENCE STRUCTURE\n" + original_pdb)
        body = {
            "schema_version": 2,
            "neutral_item_id": neutral,
            "status": "TEN_ITEM_COMPARISON_LABEL_FREE",
            "policy_id": POLICY_ID,
            "endpoint": endpoint,
            "endpoint_sha256": canonical_sha(endpoint),
            "sequence": sequence,
            "candidates": list(candidates),
            "candidate_count": len(candidates),
            "fasta_path": str(fasta.resolve()),
            "pdb_path": str(pdb.resolve()),
            "chain": "A",
            "input_sha256": {
                "sequence": hashlib.sha256(sequence.encode()).hexdigest(),
                "fasta": file_sha(fasta),
                "pdb": file_sha(pdb),
            },
        }
        contract = {**body, "contract_sha256": canonical_sha(body)}
        contract_path = OUT / "contracts" / f"{neutral}.json"
        po_path = OUT / "prompts" / "prompt_only" / f"{neutral}.txt"
        b4_path = OUT / "prompts" / "b4" / f"{neutral}.txt"
        write_once(contract_path, json.dumps(contract, sort_keys=True, indent=2) + "\n")
        write_once(po_path, prompt_only(neutral, endpoint, candidates))
        write_once(b4_path, b4_prompt(neutral, endpoint, candidates))
        records.append({
            "neutral_item_id": neutral,
            "internal_assay_id": assay,
            "published_quartile": "Q1" if ordinal <= 3 else "Q2" if ordinal <= 6 else "Q3" if ordinal <= 8 else "Q4",
            "candidate_count": len(candidates),
            "contract_path": str(contract_path.relative_to(ROOT)),
            "contract_sha256": sha(contract_path),
            "prompt_only_path": str(po_path.relative_to(ROOT)),
            "prompt_only_sha256": sha(po_path),
            "b4_prompt_path": str(b4_path.relative_to(ROOT)),
            "b4_prompt_sha256": sha(b4_path),
            "fasta_sha256": sha(fasta),
            "pdb_sha256": sha(pdb),
            "source_manifest_sha256": sha(S1 / "prompt_manifest_146_executable.jsonl"),
            "label_fields_read": False,
        })
    write_once(OUT / "blind_item_manifest_internal.jsonl",
               "".join(json.dumps(x, sort_keys=True) + "\n" for x in records))
    public = [{k: v for k, v in row.items() if k != "internal_assay_id"} for row in records]
    write_once(OUT / "blind_item_manifest_model_visible.jsonl",
               "".join(json.dumps(x, sort_keys=True) + "\n" for x in public))
    write_once(OUT / "empty_mcp.json", json.dumps({"mcpServers": {}}, indent=2) + "\n")
    print(json.dumps({"prepared": len(records), "labels_opened": False,
                      "manifest_sha256": sha(OUT / "blind_item_manifest_internal.jsonl")}, sort_keys=True))


if __name__ == "__main__":
    main()
