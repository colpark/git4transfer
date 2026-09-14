"""Direct, unscored record and guided-composite positive/negative controls."""

import asyncio
import json
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3g_2026-09-14"
PY = ROOT / "benchmark-mcp/.venv/bin/python"
SEQUENCE = "MQIFVKTLTGKTITLEVEPSDTIENVKAKIQDKEGIPPDQQRLIFAGKQLEDGRTLSDYNIQKESTLHLVLRLRGG"


def body(response):
    return response.structured_content or json.loads(response.content[0].text)


def resolves(value):
    receipt = value["receipt"]
    path = Path(receipt["artifact_path"])
    return path.is_file() and json.loads(path.read_text())["receipt"]["call_id"] == receipt["call_id"]


async def main():
    OUT.mkdir(parents=True, exist_ok=True)
    checks = {}
    record_out = OUT / "record_preflight"
    record_params = StdioServerParameters(command=str(PY), args=[
        str(ROOT / "benchmark-mcp/pilot_record_server.py"), "--out", str(record_out),
        "--presentation", "guided"], cwd=ROOT)
    async with Client(record_params, raise_exceptions=True, read_timeout_seconds=30) as client:
        listed = await client.list_tools()
        good = body(await client.call_tool("log_note", {"item_id": "stage3g_preflight", "note": "record path check"}))
        bad = body(await client.call_tool("log_note", {"item_id": "stage3g_preflight", "note": ""}))
    checks["record"] = {"tools": [tool.name for tool in listed.tools], "valid_note": good,
                        "invalid_note": bad, "pass": {tool.name for tool in listed.tools} ==
                        {"submit_answer", "log_note"} and good.get("result") is not None and
                        resolves(good) and bad.get("result") is None and bool(bad.get("error"))}
    guided_tools = []
    for server in pilot_servers():
        if server == "record":
            tools = listed.tools
        else:
            params = StdioServerParameters(command=str(PY), args=[
                str(ROOT / "benchmark-mcp/server.py"), "--server", server,
                "--presentation", "guided"], cwd=ROOT)
            async with Client(params, raise_exceptions=True, read_timeout_seconds=180) as client:
                tools = (await client.list_tools()).tools
        guided_tools += [{"server": server, "name": tool.name, "description": tool.description,
                          "input_schema": tool.input_schema} for tool in tools]
    (OUT / "guided_after_tools.json").write_text(json.dumps(guided_tools, indent=2) + "\n")
    params = StdioServerParameters(command=str(PY), args=[
        str(ROOT / "benchmark-mcp/server.py"), "--server", "predictive",
        "--presentation", "guided"], cwd=ROOT)
    arguments = {"sequence": SEQUENCE, "position": 3, "mutant": "A",
                 "pdb_path": str(ROOT / "benchmark-mcp/fixtures/1ubq.pdb"), "chain": "A"}
    async with Client(params, raise_exceptions=True, read_timeout_seconds=300) as client:
        good = body(await client.call_tool("screen_variant_fm", arguments))
        bad = body(await client.call_tool("screen_variant_fm", {**arguments, "mutant": "!"}))
    checks["fm_composite"] = {"valid": good, "invalid": bad,
        "pass": good.get("result") is not None and resolves(good) and
        good["result"]["esm2_likelihood"]["model"] == "facebook/esm2_t33_650M_UR50D" and
        good["result"]["esm_if"]["model"] == "esm_if1_gvp4_t16_142M_UR50" and
        bad.get("result") is None and bool(bad.get("error"))}
    (OUT / "direct_controls.json").write_text(json.dumps(checks, indent=2) + "\n")
    print(json.dumps({"record_pass": checks["record"]["pass"],
                      "fm_composite_pass": checks["fm_composite"]["pass"],
                      "guided_tool_count": len(guided_tools)}), flush=True)
    if not all(check["pass"] for check in checks.values()):
        raise RuntimeError("direct controls failed")


def pilot_servers():
    return ("record", "classical", "lit", "analysis", "predictive", "generative", "physics")


if __name__ == "__main__":
    asyncio.run(main())
