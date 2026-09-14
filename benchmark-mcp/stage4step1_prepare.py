"""Label-blind Stage 4 step 1 prompt materialization and superseding freeze."""

from __future__ import annotations

import asyncio
import csv
import difflib
import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pilot_prepare import CONTRACT
from stage3_w1 import AA, a2m_records
from stage4prep_freeze import surface

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step1_2026-09-14"
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
PREP = ROOT / "results/benchmark/stage4prep_2026-09-14"
STRUCTURES = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures"
ARGR = "ARGR_ECOLI_Tsuboyama_2023_1AOY"
SEALED = {ARGR, "AACC1_PSEAI_Dandage_2018"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_once(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite frozen output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def source_prompts() -> dict[str, str]:
    return {row["assay_id"]: row["prompt"]
            for line in (STAGE3 / "prompt_manifest.jsonl").open()
            if (row := json.loads(line))}


def prompt_diff(source: str, actual: str) -> None:
    if not actual.startswith(source):
        raise SystemExit("actual Codex prompt is not source stem plus appendage")
    diff = "".join(difflib.unified_diff(source.splitlines(keepends=True),
                                        actual.splitlines(keepends=True),
                                        fromfile="A: stage3 manifest ARGR (973 bytes)",
                                        tofile="B: Codex B4 actual (2023 bytes)"))
    content = ("# Exact ARGR prompt audit\n\n"
               f"A: {len(source.encode())} UTF-8 bytes; SHA-256 `{hashlib.sha256(source.encode()).hexdigest()}`. "
               f"B: {len(actual.encode())} bytes; SHA-256 `{hashlib.sha256(actual.encode()).hexdigest()}`. "
               f"B starts with A byte-for-byte and appends {len(actual.encode())-len(source.encode())} bytes.\n\n"
               "## A — Stage 3 hashed source manifest (full)\n\n```text\n" + source +
               "\n```\n\n## B — prompt the Codex B4 cell actually received (full)\n\n```text\n" +
               actual + "\n```\n\n## Unified diff\n\n```diff\n" + diff + "```\n\n"
               "## Exactly what B adds\n\n"
               "- A local reference homolog FASTA path: `results/benchmark/stage3h_2026-09-14/audit_fastas/012.fasta`.\n"
               "- A local reference structure PDB path: `results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures/ARGR_ECOLI.pdb`.\n"
               "- An instruction to submit exactly once through the mounted record channel with `item_id=pilot_item`.\n"
               "- Required `selected` array: exactly ten entries with `rank`, `mutant`, `basis`, receipt-ID `evidence`, categorical `validation`, and `would_overturn`.\n"
               "- Required `rejected` array and optional full candidate `ranking` of `{mutant, score}` with larger predicted score better.\n"
               "- Receipt provenance, no invented data, no measured-assay claim, and submit-only-when-finished instructions.\n\n"
               "## Runner audit and freeze finding\n\n"
               "`benchmark-mcp/pilot_run.py:run_cell` reads `item['prompt_files'][arm]['path']` and sends **that file's bytes** to `codex exec` on stdin. "
               "`benchmark-mcp/pilot_prepare.py` writes those files by appending per-item FASTA/PDB paths and the record contract to the Stage 3 manifest stem; it also alternates two opening stems. "
               "`benchmark-mcp/stage3id_run.py` imports `PROMPT` from `stage3ic_run.py`, where it points to the 2,023-byte diagnostic file, and passes its text to Codex. "
               "Thus the hashed Stage 3 `prompt_manifest.jsonl` **does not match the prompt the runner sends**. It was a source artifact, not the executable prompt. "
               "The Stage 4 pilot selection separately hashed its eight enriched prompt files, but the Stage 4-prep 146-item manifest hashes source and prompt-only variants, not 146 enriched executable prompts. "
               "The prior 146 freeze therefore described the wrong artifact for full-MCP arms and **FAILED** as an executable-prompt freeze; it is superseded here, not deemed satisfied.\n")
    write_once(OUT / "prompt_diff.md", content)


def materialize(prompts: dict[str, str]) -> None:
    cohort = list(csv.DictReader((PREP / "cohort_146.csv").open()))
    if len(cohort) != 146 or SEALED & {r["assay_id"] for r in cohort}:
        raise SystemExit("cohort count or seal mismatch")
    metadata = {r["DMS_id"]: r for r in csv.DictReader((STAGE3 / "input/DMS_substitutions.csv").open())}
    records = []
    with zipfile.ZipFile(STAGE3 / "input/DMS_msa_files.zip") as archive:
        for row in cohort:
            assay = row["assay_id"]
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
            if not pdb.is_file():
                raise SystemExit(f"missing structure for {assay}: {pdb}")
            prompt = (prompts[assay] + "\n\nReference homolog FASTA for retrieval: " + str(fasta) +
                      "\nReference structure PDB for geometric evaluation: " + str(pdb) +
                      "\n\n" + CONTRACT + "\n")
            path = OUT / "prompts" / f"{assay}.txt"
            write_once(path, prompt)
            records.append({"assay_id": assay, "prompt_path": str(path.relative_to(ROOT)),
                            "prompt_sha256": sha(path), "prompt_bytes": len(path.read_bytes()),
                            "fasta_path": str(fasta.relative_to(ROOT)), "fasta_sha256": sha(fasta),
                            "pdb_path": str(pdb.relative_to(ROOT)), "pdb_sha256": sha(pdb),
                            "candidate_count": int(row["candidate_count"])})
    write_once(OUT / "prompt_manifest_146_executable.jsonl",
               "".join(json.dumps(r, sort_keys=True) + "\n" for r in records))


def aggregate_floors() -> None:
    allowed = {r["assay_id"] for r in csv.DictReader((PREP / "cohort_146.csv").open())}
    rows = list(csv.DictReader((STAGE3 / "floor_item_scores.csv").open()))
    if len(rows) != 296 or len(allowed) != 146:
        raise SystemExit("floor/cohort cardinality changed")
    from statistics import mean
    data = {}
    for cohort_name, subset in (("148_published_set", rows),
                                ("146_matched_set", [r for r in rows if r["assay_id"] in allowed])):
        data[cohort_name] = {}
        for floor in ("C", "M"):
            group = [r for r in subset if r["floor"] == floor and r["status"] == "EVALUABLE"]
            expected = 148 if cohort_name.startswith("148") else 146
            if len(group) != expected:
                raise SystemExit(f"{cohort_name} {floor} has {len(group)} evaluable rows")
            data[cohort_name][floor] = {
                "n": len(group), "mean_spearman": mean(float(r["rho"]) for r in group),
                "mean_precision_at_10": mean(float(r["precision_at_10"]) for r in group),
                "mean_per_item_chance_at_10": mean(10/int(r["n_candidates"]) for r in group),
                "mean_lift_over_chance": mean(float(r["precision_at_10"])-10/int(r["n_candidates"]) for r in group),
            }
    write_once(OUT / "floors_146.json", json.dumps(data, indent=2) + "\n")
    report = ["# Published floors, restricted to the matched 146", "",
              "Aggregate-only arithmetic on the already published `floor_item_scores.csv`; no label file, evaluator, or sealed-item score was opened. The 148 values are preserved, not overwritten.", "",
              "| Set | Floor | n | P@10 | Chance P@10 | Lift | Spearman |", "|---|---|---:|---:|---:|---:|---:|"]
    for label, group in data.items():
        for floor, d in group.items():
            report.append(f"| {label} | {floor} | {d['n']} | {d['mean_precision_at_10']:.6f} | {d['mean_per_item_chance_at_10']:.6f} | {d['mean_lift_over_chance']:+.6f} | {d['mean_spearman']:.6f} |")
    report += ["", "The two sealed items are excluded only in the 146 rows. These floor aggregates do not authorize scoring either matched control cell."]
    write_once(OUT / "floors_146.md", "\n".join(report) + "\n")


def freeze() -> None:
    for mode in ("unguided", "guided"):
        rows = asyncio.run(surface(mode))
        write_once(OUT / f"surface_{mode}.json", json.dumps(rows, indent=2) + "\n")
    targets = {
        "preregistration": PREP / "preregistration.md",
        "prompt_ruling": OUT / "prompt_ruling.md", "scoring_prereg": OUT / "scoring_prereg.md",
        "prompt_diff": OUT / "prompt_diff.md",
        "prompt_template_and_freeze_code": ROOT / "benchmark-mcp/stage4step1_prepare.py",
        "chosen_sealed_prompt": ROOT / "results/benchmark/stage3h_2026-09-14/diagnostic_prompt.txt",
        "source_prompt_manifest": STAGE3 / "prompt_manifest.jsonl",
        "executable_prompt_manifest_146": OUT / "prompt_manifest_146_executable.jsonl",
        "cohort_146": PREP / "cohort_146.csv", "published_floor_scores": STAGE3 / "floor_item_scores.csv",
        "floors_146_aggregates": OUT / "floors_146.json",
        "scoring_code": ROOT / "benchmark-mcp/pilot_score.py",
        "evaluator_unchanged": ROOT / "benchmark-mcp/stage3_evaluate.py",
        "floor_code": ROOT / "benchmark-mcp/stage3_w1.py",
        "legacy_stage4_runner": ROOT / "benchmark-mcp/pilot_run.py",
        "pilot_prompt_template_code": ROOT / "benchmark-mcp/pilot_prepare.py",
        "record_mount": ROOT / "benchmark-mcp/pilot_record_server.py",
        "tool_schema_and_description": ROOT / "benchmark-mcp/server.py",
        "surface_unguided": OUT / "surface_unguided.json",
        "surface_guided": OUT / "surface_guided.json",
    }
    for server in ("classical", "analysis", "predictive", "generative", "physics", "lit", "record", "common", "variant_input"):
        targets[f"mcp_impl_{server}"] = ROOT / f"benchmark-mcp/{server}.py"
    for code in ("stage3ic_run", "stage3id_run", "stage4prep_qwen", "stage4prep_promptonly", "stage4prep_parser_controls", "pilot_responses_shim", "stage3h_validity"):
        targets[f"code_{code}"] = ROOT / f"benchmark-mcp/{code}.py"
    if any(not p.is_file() for p in targets.values()):
        raise SystemExit("freeze target missing")
    manifest = OUT / "prompt_manifest_146_executable.jsonl"
    for row in map(json.loads, manifest.read_text().splitlines()):
        for kind in ("prompt", "fasta", "pdb"):
            if sha(ROOT / row[f"{kind}_path"]) != row[f"{kind}_sha256"]:
                raise SystemExit(f"materialized {kind} mismatch: {row['assay_id']}")
    frozen = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "PROVISIONAL_PANEL_RULING_PENDING", "cohort_count": 146,
              "supersedes": ["results/benchmark/stage4pilot_2026-09-13/freeze_hashes.json",
                             "results/benchmark/stage4prep_2026-09-14/freeze_hashes.json"],
              "sealed_items": sorted(SEALED),
              "sha256": {k: {"path": str(p.relative_to(ROOT)), "digest": sha(p)} for k, p in targets.items()}}
    write_once(OUT / "freeze_hashes.json", json.dumps(frozen, indent=2) + "\n")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    prompts = source_prompts()
    source = prompts[ARGR]
    actual = (ROOT / "results/benchmark/stage3h_2026-09-14/diagnostic_prompt.txt").read_text()
    if len(source.encode()) != 973 or len(actual.encode()) != 2023:
        raise SystemExit("ARGR prompt byte counts differ from panel finding")
    prompt_diff(source, actual)
    materialize(prompts)
    aggregate_floors()
    freeze()
    print(json.dumps({"prompt_A_bytes": 973, "prompt_B_bytes": 2023,
                      "cohort_prompts": 146, "freeze_sha256": sha(OUT / "freeze_hashes.json")}))


if __name__ == "__main__":
    main()
