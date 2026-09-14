"""Re-register 146 W1 assays and the current tool surface; never read labels."""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from stage3ic_run import ORDER, ROOT, TOOLS
from stage4prep_promptonly import build_prompt, candidates_from_source_prompt

OUT = ROOT / "results/benchmark/stage4prep_2026-09-14"
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
PILOT = ROOT / "results/benchmark/stage4pilot_2026-09-13"
SEALED = {"AACC1_PSEAI_Dandage_2018", "ARGR_ECOLI_Tsuboyama_2023_1AOY"}
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SERVER = ROOT / "benchmark-mcp/server.py"
RECORD = ROOT / "benchmark-mcp/pilot_record_server.py"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_new(path: Path, content: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite frozen output {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def build_cohort() -> dict[str, dict]:
    floor = list(csv.DictReader((STAGE3 / "floor_item_scores.csv").open()))
    by_assay = {}
    for row in floor:
        by_assay.setdefault(row["assay_id"], {})[row["floor"]] = row
    eligible = {assay: pair for assay, pair in by_assay.items()
                if pair.get("C", {}).get("status") == "EVALUABLE"
                and pair.get("M", {}).get("status") == "EVALUABLE"}
    if len(eligible) != 148 or not SEALED <= set(eligible):
        raise SystemExit("frozen 148-item floor set or sealed ids differ")
    pilot = {row["assay_id"]: row["pilot_item"]
             for row in csv.DictReader((PILOT / "selection.csv").open())}
    if len(pilot) != 8 or pilot["AACC1_PSEAI_Dandage_2018"] != "2":
        raise SystemExit("pilot selection does not match ruling")
    source_rows = {row["assay_id"]: row for row in
                   csv.DictReader((STAGE3 / "cohort.csv").open()) if row["assay_id"]}
    manifest = {row["assay_id"]: row for line in (STAGE3 / "prompt_manifest.jsonl").open()
                if (row := json.loads(line))}
    fields = ("assay_id", "cluster_50", "candidate_count", "sequence_length", "pilot_item")
    path = OUT / "cohort_146.csv"
    if path.exists():
        raise SystemExit("cohort_146.csv already exists")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for assay in sorted(set(eligible) - SEALED):
            source = source_rows[assay]
            writer.writerow({"assay_id": assay, "cluster_50": eligible[assay]["M"]["cluster_50"],
                             "candidate_count": eligible[assay]["M"]["n_candidates"],
                             "sequence_length": source["sequence_length"],
                             "pilot_item": pilot.get(assay, "")})
    if sum(1 for _ in csv.DictReader(path.open())) != 146:
        raise SystemExit("cohort size is not 146")
    prompt_rows = []
    for assay in sorted(set(eligible) - SEALED):
        source = manifest[assay]["prompt"]
        n = len(candidates_from_source_prompt(source))
        if n != int(eligible[assay]["M"]["n_candidates"]):
            raise SystemExit(f"candidate count mismatch for {assay}")
        prompt_rows.append({"assay_id": assay,
                            "source_prompt_sha256": hashlib.sha256(source.encode()).hexdigest(),
                            "promptonly_with_instruction_sha256": hashlib.sha256(build_prompt(source, True).encode()).hexdigest(),
                            "promptonly_without_instruction_sha256": hashlib.sha256(build_prompt(source, False).encode()).hexdigest(),
                            "candidate_count": n})
    write_new(OUT / "prompt_manifest_146.jsonl",
              "".join(json.dumps(row, sort_keys=True) + "\n" for row in prompt_rows))
    for assay in sorted(SEALED):
        source = manifest[assay]["prompt"]
        for condition, with_instruction in (("a", True), ("b", False)):
            write_new(OUT / f"promptonly_{assay}_{condition}.txt",
                      build_prompt(source, with_instruction))
    return eligible


async def surface(mode: str) -> list[dict]:
    rows = []
    for server in ORDER:
        if server == "record":
            args = [str(RECORD), "--out", str(OUT / "surface_record"),
                    "--presentation", mode]
        else:
            args = [str(SERVER), "--server", server, "--presentation", mode]
        params = StdioServerParameters(command=str(PY), args=args, cwd=ROOT)
        async with Client(params, raise_exceptions=True, read_timeout_seconds=150) as client:
            for tool in (await client.list_tools()).tools:
                rows.append({"server": server, "name": tool.name,
                             "description": tool.description, "input_schema": tool.input_schema,
                             "in_unguided_grant": tool.name in TOOLS[server]})
    return rows


def freeze() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if (OUT / "freeze_hashes.json").exists():
        raise SystemExit("replacement freeze already exists")
    build_cohort()
    for mode in ("unguided", "guided"):
        rows = asyncio.run(surface(mode))
        write_new(OUT / f"surface_{mode}.json", json.dumps(rows, indent=2) + "\n")
        if mode == "unguided" and sum(row["in_unguided_grant"] for row in rows) != 18:
            raise SystemExit("unguided model grant is not 18 functions")
    named = {
        "preregistration": OUT / "preregistration.md",
        "cohort_146": OUT / "cohort_146.csv",
        "freeze_builder": ROOT / "benchmark-mcp/stage4prep_freeze.py",
        "floor_scores": STAGE3 / "floor_item_scores.csv",
        "source_prompt_manifest": STAGE3 / "prompt_manifest.jsonl",
        "prompt_manifest_146": OUT / "prompt_manifest_146.jsonl",
        "prompt_template_original": ROOT / "benchmark-mcp/pilot_prepare.py",
        "prompt_template_promptonly": ROOT / "benchmark-mcp/stage4prep_promptonly.py",
        "promptonly_parser_controls": ROOT / "benchmark-mcp/stage4prep_parser_controls.py",
        "scoring_code": ROOT / "benchmark-mcp/pilot_score.py",
        "evaluator": ROOT / "benchmark-mcp/stage3_evaluate.py",
        "floor_code": ROOT / "benchmark-mcp/stage3_w1.py",
        "legacy_runner": ROOT / "benchmark-mcp/pilot_run.py",
        "frontier_control_runner": ROOT / "benchmark-mcp/stage3id_run.py",
        "qwen_prep_runner": ROOT / "benchmark-mcp/stage4prep_qwen.py",
        "response_shim": ROOT / "benchmark-mcp/pilot_responses_shim.py",
        "record_mount": ROOT / "benchmark-mcp/pilot_record_server.py",
        "session_validity_gate": ROOT / "benchmark-mcp/stage3h_validity.py",
        "server_tool_schemas_and_descriptions": ROOT / "benchmark-mcp/server.py",
        "current_unguided_surface": OUT / "surface_unguided.json",
        "current_guided_surface": OUT / "surface_guided.json",
        "served_model_catalog": ROOT / "benchmark-mcp/stage3g_model_catalog.json",
        "sealed_aacc1_prompt_a": OUT / "promptonly_AACC1_PSEAI_Dandage_2018_a.txt",
        "sealed_aacc1_prompt_b": OUT / "promptonly_AACC1_PSEAI_Dandage_2018_b.txt",
        "sealed_argr_prompt_a": OUT / "promptonly_ARGR_ECOLI_Tsuboyama_2023_1AOY_a.txt",
        "sealed_argr_prompt_b": OUT / "promptonly_ARGR_ECOLI_Tsuboyama_2023_1AOY_b.txt",
    }
    for server in ("classical", "analysis", "predictive", "generative", "physics",
                   "lit", "record", "common", "variant_input"):
        named[f"mcp_impl_{server}"] = ROOT / f"benchmark-mcp/{server}.py"
    if not all(path.is_file() for path in named.values()):
        raise SystemExit("a freeze target is missing")
    frozen = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "supersedes": "results/benchmark/stage4pilot_2026-09-13/freeze_hashes.json",
              "cohort_count": 146,
              "sealed_items": sorted(SEALED),
              "sha256": {key: {"path": str(path.relative_to(ROOT)), "digest": digest(path)}
                         for key, path in named.items()}}
    write_new(OUT / "freeze_hashes.json", json.dumps(frozen, indent=2) + "\n")
    print(json.dumps({"cohort": 146, "hash_targets": len(named),
                      "surface_unguided": len(json.loads((OUT / "surface_unguided.json").read_text())),
                      "surface_guided": len(json.loads((OUT / "surface_guided.json").read_text()))}))


if __name__ == "__main__":
    freeze()
