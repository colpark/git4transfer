"""Stage 3h label-free schema and native-variant MCP controls."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from variant_input import AA_PATTERN, resolve_variant

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3h_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SERVER = ROOT / "benchmark-mcp/server.py"
FIXTURE_FASTA = ROOT / "benchmark-mcp/fixtures/stage3g_msa_positive.fasta"
FIXTURE_PDB = ROOT / "benchmark-mcp/fixtures/1ubq.pdb"
Q = "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"
UBQ = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"


def body(response):
    if response.structured_content:
        return response.structured_content
    value = response.content[0].text
    try:
        return json.loads(value)
    except ValueError:
        return {"error": value}


def resolves(value):
    receipt = value.get("receipt", {})
    path = Path(receipt.get("artifact_path", "/__absent__"))
    return path.is_file() and json.loads(path.read_text())["receipt"]["call_id"] == receipt.get("call_id")


async def check(server, mode, cases):
    params = StdioServerParameters(command=str(PY), args=[str(SERVER), "--server", server,
                                    "--presentation", mode], cwd=ROOT)
    outcomes = {}
    async with Client(params, raise_exceptions=False, read_timeout_seconds=600) as client:
        listing = {tool.name: tool for tool in (await client.list_tools()).tools}
        for label, tool, args in cases:
            try:
                response = await client.call_tool(tool, args)
                value = body(response)
                outcomes[label] = {"tool": tool, "input": args, "response": value,
                                   "is_error": bool(response.is_error), "receipt_resolves": resolves(value)}
            except Exception as exc:
                outcomes[label] = {"tool": tool, "input": args, "exception": f"{type(exc).__name__}: {exc}",
                                   "is_error": True, "receipt_resolves": False}
        schema = {name: listing[name].input_schema for _, name, _ in cases}
    return schema, outcomes


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    direct = {
        "variant": resolve_variant(variant="G52L", sequence="A"*51+"G"+"A"*20),
        "both_agree": resolve_variant(variant="G52L", wt="G", position=52, mutant="L"),
    }
    try:
        resolve_variant(variant="G52L", wt="G", position=52, mutant="A")
        direct["conflict_rejected"] = False
    except ValueError as exc:
        direct["conflict_rejected"] = "conflicting variant" in str(exc)
        direct["conflict_message"] = str(exc)
    try:
        resolve_variant(position=52, mutant="G52L")
        direct["wrong_shape_rejected"] = False
    except ValueError as exc:
        direct["wrong_shape_rejected"] = "use variant" in str(exc)
        direct["wrong_shape_message"] = str(exc)
    classical_cases = [
        ("blosum_variant", "blosum_score", {"variant": "G52L"}),
        ("blosum_decomposed", "blosum_score", {"wt": "G", "position": 52, "mutant": "L"}),
        ("blosum_bad_shape", "blosum_score", {"wt": "G", "position": 52, "mutant": "G52L"}),
        ("blosum_conflict", "blosum_score", {"variant": "G52L", "mutant": "A"}),
        ("pssm_variant", "pssm_score", {"query": Q, "msa": [Q, Q], "variant": "D3E"}),
        ("conservation_variant", "conservation", {"query": Q, "msa": [Q, Q], "variant": "D3E"}),
        ("guided_variant", "screen_variant_classical", {"sequence": Q,
              "reference_fasta": str(FIXTURE_FASTA), "variant": "D3E"}),
    ]
    predictive_cases = [
        ("esm2_variant", "esm2_likelihood", {"sequence": Q, "variant": "D3E"}),
        ("fm_composite_variant", "screen_variant_fm", {"sequence": UBQ,
              "pdb_path": str(FIXTURE_PDB), "variant": "I3A"}),
    ]
    generative_cases = [
        ("esm_if_variant", "esm_if", {"sequence": UBQ, "pdb_path": str(FIXTURE_PDB),
              "chain": "A", "variant": "I3A"}),
    ]
    schemas = {}
    outcomes = {}
    for server, mode, cases in (("classical", "guided", classical_cases),
                                ("predictive", "guided", predictive_cases),
                                ("generative", "unguided", generative_cases)):
        schema, result = await check(server, mode, cases)
        schemas.update(schema)
        outcomes.update(result)
    positives = ("blosum_variant", "blosum_decomposed", "pssm_variant", "conservation_variant",
                 "guided_variant", "esm2_variant", "fm_composite_variant", "esm_if_variant")
    negatives = ("blosum_bad_shape", "blosum_conflict")
    patterns_ok = all("pattern" in json.dumps(schemas[name]) for name in
                      ("blosum_score", "pssm_score", "conservation", "screen_variant_classical",
                       "esm2_likelihood", "screen_variant_fm", "esm_if"))
    checks = {"positive_calls": {key: outcomes[key].get("response", {}).get("result") is not None
                                   and outcomes[key]["receipt_resolves"] for key in positives},
              "negative_calls": {key: outcomes[key]["is_error"] or
                                  outcomes[key].get("response", {}).get("result") is None for key in negatives},
              "bad_shape_names_pattern": AA_PATTERN in outcomes["blosum_bad_shape"].get("response", {}).get("error", ""),
              "conflict_names_values": "supplied mutant='A', expected 'L'" in
                                       outcomes["blosum_conflict"].get("response", {}).get("error", ""),
              "pattern_in_all_seven_schemas": patterns_ok,
              "direct_conflict_rejected": direct["conflict_rejected"],
              "direct_wrong_shape_rejected": direct["wrong_shape_rejected"],
              "receipt_input_forms": {key: outcomes[key].get("response", {}).get("receipt", {}).get("input_form")
                                      for key in positives}}
    checks["receipt_forms_correct"] = (checks["receipt_input_forms"]["blosum_variant"] == "variant"
        and checks["receipt_input_forms"]["blosum_decomposed"] == "decomposed"
        and all(checks["receipt_input_forms"][key] == "variant" for key in positives
                if key != "blosum_decomposed"))
    checks["pass"] = (all(checks["positive_calls"].values()) and all(checks["negative_calls"].values())
                       and patterns_ok and direct["conflict_rejected"] and direct["wrong_shape_rejected"]
                       and checks["bad_shape_names_pattern"] and checks["conflict_names_values"]
                       and checks["receipt_forms_correct"])
    (OUT / "schema_controls.json").write_text(json.dumps({"direct": direct, "schemas": schemas,
          "outcomes": outcomes, "checks": checks}, indent=2) + "\n")
    print(json.dumps({"pass": checks["pass"], "positive": checks["positive_calls"],
                      "negative": checks["negative_calls"], "patterns": patterns_ok}), flush=True)
    if not checks["pass"]:
        raise SystemExit("variant schema controls failed")


if __name__ == "__main__":
    asyncio.run(main())
