"""Known-input, deliberately unmasked, invalid-input, and receipt controls."""

import asyncio
import json
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from predictive import ESM2_MODEL as MODEL, ESM2_REVISION as REVISION

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3f_2026-09-14"
SEQUENCE = "ACDEFGHIKLMNPQRSTVWY"
EXPECTED_MASKED = -0.16856098175048828  # independently measured pinned worker
UNMASKED_NEGATIVE = -3.5586464405059814  # independent forward without masking


async def main():
    params = StdioServerParameters(command=str(ROOT / "benchmark-mcp/.venv/bin/python"),
                                    args=[str(ROOT / "benchmark-mcp/server.py"), "--server", "predictive",
                                          "--presentation", "unguided"], cwd=ROOT)
    async with Client(params, raise_exceptions=True, read_timeout_seconds=650) as client:
        good = await client.call_tool("esm2_likelihood", {"sequence": SEQUENCE, "position": 1,
                                                            "mutant": "R"})
        bad = await client.call_tool("esm2_likelihood", {"sequence": SEQUENCE, "position": 1,
                                                           "mutant": "!"})
    good_body = good.structured_content or json.loads(good.content[0].text)
    bad_body = bad.structured_content or json.loads(bad.content[0].text)
    receipt = good_body["receipt"]
    artifact = Path(receipt["artifact_path"])
    saved = json.loads(artifact.read_text())
    score = good_body["result"]["delta_log_probability"]
    checks = {
        "known_input_matches_independent_score": abs(score - EXPECTED_MASKED) < 1e-5,
        "deliberately_unmasked_negative_differs": abs(score - UNMASKED_NEGATIVE) > 0.1,
        "invalid_input_returns_error": bad_body.get("result") is None and bool(bad_body.get("error")),
        "receipt_resolves": artifact.is_file() and saved["receipt"]["call_id"] == receipt["call_id"],
        "checkpoint_pinned": good_body["result"]["model"] == MODEL and
                             good_body["result"]["revision"] == REVISION,
    }
    output = {"sequence": SEQUENCE, "mutation": "A1R", "masked_mcp": score,
              "masked_independent": EXPECTED_MASKED, "unmasked_negative": UNMASKED_NEGATIVE,
              "bad_error": bad_body.get("error"), "receipt": receipt, "checks": checks}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "esm2_controls.json").write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps(output), flush=True)
    if not all(checks.values()):
        raise SystemExit("ESM-2 650M controls failed")


if __name__ == "__main__":
    asyncio.run(main())
