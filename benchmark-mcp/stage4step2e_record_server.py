"""Per-run strict B4 v3 submission server."""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from stage4step2e_contract import canonical_sha, load_contract, normalize_contract, validate_answer


def build(out: Path, contract_path: Path | None = None, *, contract: dict | None = None) -> MCPServer:
    mcp = MCPServer("b4-v3-record", version="2.0.0")
    if contract is None:
        if contract_path is None:
            raise ValueError("contract_path or contract is required")
        contract = load_contract(contract_path)
    elif contract:
        contract = normalize_contract(contract)

    @mcp.tool(name="submit_answer")
    def submit_answer(answer: dict) -> dict:
        """Submit the one item-bound final answer. Item and endpoint identities are attached by this server, not copied by the model."""
        item_id = contract["neutral_item_id"]
        verdict = validate_answer(answer, contract, out / "artifacts")
        target = out / "submissions" / f"{item_id}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            raise ValueError("this item already has a submission")
        target.write_text(json.dumps({"item_id": item_id,
                                     "contract_sha256": canonical_sha(contract),
                                     "endpoint_sha256": contract["endpoint_sha256"],
                                     "answer": answer, "validation": verdict},
                                     sort_keys=True, indent=2, allow_nan=False) + "\n")
        return {**verdict, "item_id": item_id, "submission_path": str(target)}

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()
    out, contract = Path(args.out).resolve(), Path(args.contract).resolve()
    out.mkdir(parents=True, exist_ok=True)
    asyncio.run(build(out, contract).run_stdio_async())


if __name__ == "__main__":
    main()
