"""No-label MCP controls for rebuilt retrieval→MSA→classical scoring surface."""

import asyncio
import json
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3g_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SERVER = ROOT / "benchmark-mcp/server.py"
QUERY = "MLRSSNDVTQQGSRPKTKLGGSSMGIIRTCRLGPDQVKSMRAALDLFGREFGDVATYSQHQPDSDYLGNLLRSKTFIALAAFDQEAVVGALAAYVLPKFEQPRSEIYIYDLAVSGEHRRQGIATALINLLKHEANALGAYVIYVQADYGDDPAVALYTKLGIREEVMHFDIDPSTAT"
FASTA = ROOT / "results/benchmark/stage4pilot_2026-09-13/reference_fastas/item02_homologs.fasta"
TEST_QUERY = "ACDEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"
TEST_FASTA = ROOT / "benchmark-mcp/fixtures/stage3g_msa_positive.fasta"


def body(response):
    return response.structured_content or json.loads(response.content[0].text)


def resolves(value):
    path = Path(value["receipt"]["artifact_path"])
    return path.is_file() and json.loads(path.read_text())["receipt"]["call_id"] == value["receipt"]["call_id"]


async def classical_call(mode, name, arguments):
    params = StdioServerParameters(command=str(PY), args=[str(SERVER), "--server", "classical",
        "--presentation", mode], cwd=ROOT)
    async with Client(params, raise_exceptions=True, read_timeout_seconds=150) as client:
        return body(await client.call_tool(name, arguments))


async def listed(mode):
    result = []
    for server in ("classical", "analysis", "predictive", "generative", "physics", "lit"):
        params = StdioServerParameters(command=str(PY), args=[str(SERVER), "--server", server,
            "--presentation", mode], cwd=ROOT)
        async with Client(params, raise_exceptions=True, read_timeout_seconds=150) as client:
            tools = (await client.list_tools()).tools
            result.extend({"server": server, "name": tool.name, "description": tool.description,
                           "input_schema": tool.input_schema} for tool in tools)
    return result


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "unguided_surface_tools.json").write_text(json.dumps(await listed("unguided"), indent=2) + "\n")
    (OUT / "guided_surface_tools.json").write_text(json.dumps(await listed("guided"), indent=2) + "\n")
    request = {"sequence": TEST_QUERY, "reference_fasta": str(TEST_FASTA), "max_hits": 10}
    aligned = await classical_call("unguided", "blast_msa", request)
    one = await classical_call("unguided", "conservation",
                               {"query": TEST_QUERY, "msa": [TEST_QUERY], "position": 3})
    good = await classical_call("unguided", "pssm_score",
                                {"query": TEST_QUERY, "msa": aligned["result"]["msa"],
                                 "position": 3, "mutant": "E"})
    guided = await classical_call("guided", "screen_variant_classical",
                                  {**request, "position": 3, "mutant": "E"})
    bad = await classical_call("guided", "screen_variant_classical",
                               {**request, "position": 3, "mutant": "D3E"})
    item_msa = await classical_call("unguided", "blast_msa",
                                    {"sequence": QUERY, "reference_fasta": str(FASTA), "max_hits": 100})
    checks = {"blast_msa": aligned, "one_sequence_conservation": one,
              "pssm_from_msa": good, "guided_classical": guided, "bad_mutant_guided": bad,
              "item02_msa": item_msa}
    expected_rows = [TEST_QUERY, "ACEEFGHIKLMNPQRSTVWYACDEFGHIKLMNPQRSTVWY"]
    checks["pass"] = bool(aligned.get("result", {}).get("msa") == expected_rows and resolves(aligned)
        and one.get("result") is None and one.get("error")
        and good.get("result", {}).get("delta_bits") == 0.0 and resolves(good)
        and abs(guided.get("result", {}).get("conservation", {}).get("conservation", -1)
                - 0.7686217868402409) < 1e-9 and resolves(guided)
        and bad.get("result") is None and bad.get("error")
        and item_msa.get("result") is None and item_msa.get("error"))
    (OUT / "surface_controls.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps({"pass": checks["pass"], "msa_depth": aligned.get("result", {}).get("depth"),
                      "unguided_tool_count": len(json.loads((OUT / "unguided_surface_tools.json").read_text())),
                      "guided_tool_count": len(json.loads((OUT / "guided_surface_tools.json").read_text()))}), flush=True)
    if not checks["pass"]:
        raise SystemExit("surface controls failed")


if __name__ == "__main__":
    asyncio.run(main())
