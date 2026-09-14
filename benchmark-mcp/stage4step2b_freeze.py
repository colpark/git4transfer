"""Hash the amended, sealed-only smoke surface before any Step-2b model call."""

from __future__ import annotations

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from stage4prep_freeze import surface

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2b_2026-09-14"
STEP1 = ROOT / "results/benchmark/stage4step1_2026-09-14"
S3 = ROOT / "results/benchmark/stage3_2026-09-13"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if (OUT / "freeze_hashes.json").exists():
        raise SystemExit("replacement freeze already exists")
    if (OUT / "runs").exists():
        raise SystemExit("model runs already exist; freeze was not preregistered")
    prior = json.loads((STEP1 / "freeze_hashes.json").read_text())
    for key, path in (("scoring_code", ROOT / "benchmark-mcp/pilot_score.py"),
                      ("evaluator_unchanged", ROOT / "benchmark-mcp/stage3_evaluate.py"),
                      ("floor_code", ROOT / "benchmark-mcp/stage3_w1.py")):
        if sha(path) != prior["sha256"][key]["digest"]:
            raise SystemExit(f"Step 1 scorer/evaluator/floor code changed: {key}")
    manifest = [json.loads(line) for line in (OUT / "sealed_prompt_manifest.jsonl").read_text().splitlines()]
    if len(manifest) != 3:
        raise SystemExit("sealed prompt manifest must contain exactly three items")
    for row in manifest:
        for kind in ("prompt", "fasta", "pdb"):
            if sha(ROOT / row[f"{kind}_path"]) != row[f"{kind}_sha256"]:
                raise SystemExit(f"sealed {kind} hash mismatch: {row['assay_id']}")
    for mode in ("unguided", "guided"):
        path = OUT / f"surface_{mode}.json"
        if path.exists():
            raise SystemExit("tool surface already materialized")
        rows = asyncio.run(surface(mode))
        path.write_text(json.dumps(rows, indent=2) + "\n")
        if mode == "unguided" and len(rows) != 18:
            raise SystemExit("unguided full grant must have exactly 18 MCP functions")
    targets = {
        "prereg_amendment": OUT / "prereg_amendment.md",
        "sealed_register": OUT / "sealed_register.md",
        "cohort_145": OUT / "cohort_145.csv",
        "sealed_prompt_manifest": OUT / "sealed_prompt_manifest.jsonl",
        "empty_mcp_config": OUT / "empty_mcp.json",
        "step1_freeze": STEP1 / "freeze_hashes.json",
        "step1_scoring_prereg": STEP1 / "scoring_prereg.md",
        "source_manifest": S3 / "prompt_manifest.jsonl",
        "published_floor_scores": S3 / "floor_item_scores.csv",
        "published_blind_floor_predictions": S3 / "floor_predictions_blind.csv",
        "prepare_code": ROOT / "benchmark-mcp/stage4step2b_prepare.py",
        "freeze_code": ROOT / "benchmark-mcp/stage4step2b_freeze.py",
        "runner_and_blind_assembly_code": ROOT / "benchmark-mcp/stage4step2b_run.py",
        "one_shot_smoke_evaluation_code": ROOT / "benchmark-mcp/stage4step2b_eval.py",
        "unchanged_scorer": ROOT / "benchmark-mcp/pilot_score.py",
        "unchanged_stage3_evaluator": ROOT / "benchmark-mcp/stage3_evaluate.py",
        "unchanged_floor_code": ROOT / "benchmark-mcp/stage3_w1.py",
        "frozen_promptonly_parser": ROOT / "benchmark-mcp/stage4prep_promptonly.py",
        "step1_prompt_template_code": ROOT / "benchmark-mcp/stage4step1_prepare.py",
        "step1_full_grant_runner": ROOT / "benchmark-mcp/stage3ic_run.py",
        "record_mount": ROOT / "benchmark-mcp/pilot_record_server.py",
        "mcp_schema_and_descriptions": ROOT / "benchmark-mcp/server.py",
        "surface_unguided": OUT / "surface_unguided.json",
        "surface_guided": OUT / "surface_guided.json",
        "qwen_host_runner": ROOT / "benchmark-mcp/stage3g_run.py",
        "qwen_runtime": ROOT / "benchmark-mcp/stage3d_runtime.py",
    }
    for name in ("classical", "analysis", "predictive", "generative", "physics", "lit", "record", "common", "variant_input"):
        targets[f"mcp_impl_{name}"] = ROOT / f"benchmark-mcp/{name}.py"
    if any(not path.is_file() for path in targets.values()):
        raise SystemExit("freeze target missing")
    freeze = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
              "status": "SMOKE_ONLY_PANEL_RULING_PENDING", "scorable_cohort_count": 145,
              "sealed_items": [row["assay_id"] for row in manifest],
              "supersedes": "results/benchmark/stage4step1_2026-09-14/freeze_hashes.json",
              "wording_repair_only": True,
              "sha256": {key: {"path": str(path.relative_to(ROOT)), "digest": sha(path)}
                         for key, path in targets.items()}}
    (OUT / "freeze_hashes.json").write_text(json.dumps(freeze, indent=2) + "\n")
    print(json.dumps({"targets": len(targets), "sealed": len(manifest),
                      "freeze_sha256": sha(OUT / "freeze_hashes.json")}))


if __name__ == "__main__":
    main()
