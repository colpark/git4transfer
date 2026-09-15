"""Prepare the prospective B4 v3 remediation package without model or labels."""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from pathlib import Path

import stage4step2e_record_server as record_server
import stage4step2e_server as item_server
from stage4step2e_contract import POLICY_ID, canonical_sha, file_sha

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2e_2026-09-14"
OLD = ROOT / "results/benchmark/stage4step2b_2026-09-14"
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
STEP2D = ROOT / "results/benchmark/stage4step2d_2026-09-14"
SOURCE_PROMPT = OLD / "prompts/ENVZ_ECOLI_Ghose_2023.txt"
SOURCE_FASTA = OLD / "reference_fastas/ENVZ_ECOLI_Ghose_2023.fasta"
SOURCE_PDB = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures/ENVZ_ECOLI.pdb"
EXPECTED = {"prompt": "574386437dfa249cd541cc69ac4e55296b4d0ccbbf09a8bc3c92a1a8c0d2a6ed",
            "fasta": "19d734fe12acab48cf018738026505c6a9474629a8b5e74abddcf9e414d7a1d5",
            "pdb": "31c6d4bc27a7c380fbd4108438a235afbf13b0e337279caaa020aac2349c6f41"}


def write_once(path: Path, text: str) -> None:
    if path.exists():
        raise SystemExit(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def tool_surface() -> dict:
    tools = {}
    dummy = {"candidates": [], "sequence": "", "input_sha256": {}, "chain": "A"}
    for server_name, mcp in (
        ("record", record_server.build(OUT, contract={})),
        ("classical", item_server.make_classical(OUT, dummy, {"msa": None})),
        ("fm", item_server.make_fm(OUT, dummy, {})),
        ("structure", item_server.make_structure(OUT, dummy, {})),
    ):
        for name, tool in mcp._tool_manager._tools.items():
            tools[f"mcp__b4v3_{server_name}__{name}"] = {
                "description": tool.description, "parameters": tool.parameters}
    return {"manifest_version": 1, "item_bound_mcp": dict(sorted(tools.items())),
            "known_platform_residual_names": ["apply_patch", "list_mcp_resource_templates",
                "list_mcp_resources", "read_mcp_resource", "view_image"],
            "audit_semantics": "local MCP schemas are frozen; all observed calls and start/completion pairs fail closed"}


def endpoint_registry() -> tuple[list[dict], list[dict], dict]:
    cohort = list(csv.DictReader((OLD / "cohort_145.csv").open()))
    metadata = {r["DMS_id"]: r for r in csv.DictReader((STAGE3 / "input/DMS_substitutions.csv").open())}
    records, visible, missing, optional_unknown = [], [], [], []
    for ordinal, row in enumerate(sorted(cohort, key=lambda x: x["assay_id"]), 1):
        source = metadata[row["assay_id"]]
        internal_endpoint = {
            "phenotype_field": source["raw_DMS_phenotype_name"].strip(),
            "direction": "higher values preferred" if source["raw_DMS_directionality"].strip() == "1" else "lower values preferred",
            "measurement_assay": source["selection_assay"].strip(),
            "selection_method": source["selection_type"].strip(),
            "functional_class": source["coarse_selection_type"].strip(),
            "molecule_context": source["molecule_name"].strip(),
            "construct_region": source["region_mutated"].strip(),
            "label_free": True,
        }
        core = ("phenotype_field", "direction", "functional_class", "construct_region")
        absent = sorted(k for k in core if not internal_endpoint[k])
        if not internal_endpoint["measurement_assay"] and not internal_endpoint["selection_method"]:
            absent.append("measurement_assay_or_selection_method")
        if absent:
            missing.append({"neutral_item_id": f"item_{ordinal:03d}", "missing": absent})
        unknown = sorted(k for k in ("measurement_assay", "selection_method") if not internal_endpoint[k])
        if unknown:
            optional_unknown.append({"neutral_item_id": f"item_{ordinal:03d}", "not_reported": unknown})
        model_endpoint = {
            "phenotype_field": internal_endpoint["phenotype_field"],
            "direction": internal_endpoint["direction"],
            "measurement_assay": internal_endpoint["measurement_assay"] or "NOT_REPORTED_IN_SOURCE_METADATA",
            "selection_method": internal_endpoint["selection_method"] or "NOT_REPORTED_IN_SOURCE_METADATA",
            "functional_class": internal_endpoint["functional_class"],
            "molecule_context": internal_endpoint["functional_class"].lower() + " assay target",
            "construct_region": internal_endpoint["construct_region"], "label_free": True,
            "mechanistic_limit": "generic sequence/backbone plausibility is not a causal assay model",
        }
        records.append({"neutral_item_id": f"item_{ordinal:03d}",
                        "internal_assay_id": row["assay_id"], "endpoint": internal_endpoint,
                        "endpoint_sha256": canonical_sha(internal_endpoint)})
        visible.append({"neutral_item_id": f"item_{ordinal:03d}", "endpoint": model_endpoint,
                        "endpoint_sha256": canonical_sha(model_endpoint)})
    readiness = {"items": len(records), "complete_metadata_items": len(records) - len(missing),
                 "incomplete_metadata_items": len(missing), "missing": missing,
                 "optional_fields_not_reported": optional_unknown,
                 "label_fields_read": False,
                 "note": "Internal assay IDs are never included in model-visible prompts."}
    return records, visible, readiness


def main() -> None:
    for key, path in (("prompt", SOURCE_PROMPT), ("fasta", SOURCE_FASTA), ("pdb", SOURCE_PDB)):
        if not path.is_file() or file_sha(path) != EXPECTED[key]:
            raise SystemExit(f"source {key} is missing or changed")
    old = SOURCE_PROMPT.read_text()
    sequence = old.split("Protein sequence:\n", 1)[1].split("\n\n", 1)[0].strip()
    candidates = old.split("Candidate variants:\n", 1)[1].splitlines()[0].split(", ")
    if len(candidates) != 100 or len(set(candidates)) != 100:
        raise SystemExit("fixture candidates changed")
    inputs = OUT / "fixture_inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    fasta, pdb = inputs / "item_fixture.fasta", inputs / "item_fixture.pdb"
    if fasta.exists() or pdb.exists():
        raise SystemExit("fixture inputs already exist")
    shutil.copyfile(SOURCE_FASTA, fasta)
    pdb.write_text("HEADER    NEUTRAL REFERENCE STRUCTURE\n" + SOURCE_PDB.read_text())
    endpoint = {"phenotype_field": "mean_on", "direction": "higher values preferred",
                "measurement_assay": "fluorescent reporter", "selection_method": "FACS",
                "functional_class": "Activity", "molecule_context": "kinase signaling protein",
                "construct_region": "residues 1-60 of the supplied construct", "label_free": True,
                "mechanistic_limit": "generic plausibility tools do not directly model reporter-state regulation"}
    contract_body = {"schema_version": 2, "neutral_item_id": "item_fixture",
        "status": "PROSPECTIVE_FIXTURE_ONLY_NO_RERUN_AUTHORIZED", "policy_id": POLICY_ID,
        "endpoint": endpoint, "endpoint_sha256": canonical_sha(endpoint), "sequence": sequence,
        "candidates": candidates, "candidate_count": len(candidates),
        "fasta_path": str(fasta.resolve()), "pdb_path": str(pdb.resolve()), "chain": "A",
        "input_sha256": {"sequence": hashlib.sha256(sequence.encode()).hexdigest(),
                         "fasta": file_sha(fasta), "pdb": file_sha(pdb)}}
    envelope = {**contract_body, "contract_sha256": canonical_sha(contract_body)}
    write_once(OUT / "fixture_contract.json", json.dumps(envelope, sort_keys=True, indent=2) + "\n")
    surface = tool_surface()
    write_once(OUT / "tool_surface_manifest.json", json.dumps(surface, sort_keys=True, indent=2) + "\n")
    prompt = f"""B4 v3 prospective adaptive policy. This fixture is for parser and boundary tests only; no model rerun is authorized.

Neutral item: item_fixture
Declared label-free endpoint context:
{json.dumps(endpoint, sort_keys=True)}

Rank every supplied candidate for the declared endpoint. The available evidence tools are item-bound: callers provide only a candidate variant. They do not accept a sequence, path, structure, MSA, endpoint identifier, or label. Generic plausibility evidence is not a measured assay outcome and may be mechanistically misaligned; disclose the adaptive rule in method_summary.

Candidate variants:
{', '.join(candidates)}

Call submit_answer exactly once with only an answer object. The answer has exactly five keys: policy_id, method_summary, selected, rejected, ranking. policy_id is {POLICY_ID}. selected is exactly the first ten ranked variants; rejected is every remaining variant in rank order. ranking contains every candidate once with consecutive integer rank, mutant, one or more real evidence_call_ids, and rationale. Every row requires its own successful score_variant_fm receipt. Do not copy or supply any cryptographic hash. Invalid output is a COVERAGE FAILURE, never a zero.
"""
    write_once(OUT / "fixture_prompt.txt", prompt)
    registry, visible_registry, readiness = endpoint_registry()
    write_once(OUT / "endpoint_registry_145_internal.jsonl",
               "".join(json.dumps(row, sort_keys=True) + "\n" for row in registry))
    write_once(OUT / "endpoint_registry_145_model_visible.jsonl",
               "".join(json.dumps(row, sort_keys=True) + "\n" for row in visible_registry))
    write_once(OUT / "endpoint_readiness.json", json.dumps(readiness, sort_keys=True, indent=2) + "\n")
    context = json.loads((STEP2D / "runs/item_001/coverage_failure_context.json").read_text())
    requirements = {
        "cohort_authorized": False, "batch_one_open": False, "b1_ruling": "OUTSTANDING",
        "immutable_model_id": None, "moving_alias_observed": "gpt-5.6-sol",
        "moving_alias_panel_waiver": False,
        "expected_stable_context": {
            "base_instructions_sha256": context["base_instructions_sha256"],
            "developer_message_sha256": context["developer_message_sha256"],
            "cli_version": context["cli_version"], "approval_policy": "never",
            "sandbox_type": "read-only"},
        "v3_context_calibration_captured": False,
        "exact_started_completed_pairing_required": True,
        "human_content_audit_before_blind_export": True,
        "identifier_policy": "model-visible prompts use neutral item IDs and omit sequence, paths, DMS IDs, authors, years, publications, and protein IDs",
        "irreducible_candidate_pattern_recognition": "REQUIRES_PANEL_ACCEPTANCE",
        "platform_catalog_residual_visibility": "REQUIRES_PANEL_ACCEPTANCE",
        "assay_proxy_alignment_limit": "REQUIRES_PANEL_ACCEPTANCE",
        "endpoint_metadata_complete": readiness["incomplete_metadata_items"] == 0,
        "release_rule": "all boolean conditions and external decisions must pass before any cohort model call",
    }
    write_once(OUT / "release_requirements.json", json.dumps(requirements, sort_keys=True, indent=2) + "\n")
    model_catalog = json.loads((Path.home() / ".codex/models_cache.json").read_text())
    model_row = next(r for r in model_catalog.get("models", []) if r.get("slug") == "gpt-5.6-sol")
    model_identity = {"requested_slug": "gpt-5.6-sol", "catalog_record": model_row,
                      "immutable_backend_revision_exposed": False,
                      "cohort_effect": "hard block unless an immutable ID is supplied or the panel records a waiver"}
    write_once(OUT / "model_identity.json", json.dumps(model_identity, sort_keys=True, indent=2) + "\n")
    remediation = """# Stage 4 step 2e: prospective B4 v3 remediation

This package was created after the permanently sealed ENVZ calibration and cannot reinterpret or replace that coverage failure or its post-hoc diagnostic. No model or label was opened while creating it.

B4 v3 removes the model-copied endpoint and contract hashes that caused an irrelevant Step 2d rejection. The record server attaches those identities. Scientific tools are item-bound facades: the model supplies only a frozen candidate identifier; sequence, FASTA, PDB, chain, MSA, and checkpoint inputs remain inside the hashed server. Model-visible prompts omit sequences, paths, assay IDs, protein IDs, authors, years, and publications. Candidate patterns may still be recognizable and require an explicit panel decision.

The trace validator requires a one-to-one match between every MCP start and completion, identical server/tool/arguments across each pair, an exact allowlist, exact trace/artifact receipt equality, stable received-context equality, and exact model identity or a recorded panel waiver. The long-hash acknowledgement is gone. Human prose review remains mandatory before any blind prediction export.

Endpoint metadata for all 145 cohort items is registered from label-free ProteinGym metadata. Core endpoint fields and at least one of measurement assay or selection method are mandatory; optional omissions remain explicitly `NOT_REPORTED_IN_SOURCE_METADATA`. A separate model-visible registry removes source assay/protein identifiers and generalizes molecule names. This improves target specification but does not make generic sequence/backbone plausibility a causal model of an assay.

The release gate currently denies every cohort call because B1 is outstanding, batch one is closed, no immutable backend revision is exposed, the v3 context has not been captured on a non-benchmark calibration fixture, and the panel has not accepted candidate-pattern recognition, residual platform-tool visibility, or assay-proxy misalignment. These are enforced blockers rather than warnings. Changing a decision requires a new prospective freeze.
"""
    write_once(OUT / "remediation.md", remediation)
    provenance = {"source_step2d_freeze_sha256": file_sha(STEP2D / "freeze_hashes.json"),
                  "fixture_only": True, "rerun_authorized": False, "labels_opened": False,
                  "model_calls": 0, "source_sha256": EXPECTED,
                  "fixture_sha256": {"fasta": file_sha(fasta), "pdb": file_sha(pdb),
                                      "contract": file_sha(OUT / "fixture_contract.json"),
                                      "prompt": file_sha(OUT / "fixture_prompt.txt")}}
    write_once(OUT / "provenance.json", json.dumps(provenance, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"prepared": True, "cohort_items": len(registry),
                      "endpoint_incomplete": readiness["incomplete_metadata_items"],
                      "model_calls": 0, "labels_opened": False}, sort_keys=True))


if __name__ == "__main__":
    main()
