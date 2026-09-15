"""Item-bound B4 v3 evidence servers.

Only a frozen candidate identifier is accepted from the model. Sequences,
paths, chains, checkpoints, and homolog inputs remain server-side.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
from collections import Counter
from pathlib import Path

from mcp.server.mcpserver import MCPServer

import classical
import common
import generative
import physics
import predictive
from stage4step2e_contract import (ESM_IF_MODEL, ESM_IF_SHA256, canonical_sha,
                                   expected_bound_args, file_sha, load_contract,
                                   parse_candidate)

ROOT = Path(__file__).resolve().parents[1]
IF_CHECKPOINT = Path.home() / ".cache/torch/hub/checkpoints/esm_if1_gvp4_t16_142M_UR50.pt"
CACHE_NAMESPACE = "b4v3_item-bound_esm2-08e4846e_if1-be4ba36e"


def configure(out: Path, contract_path: Path) -> tuple[dict, dict]:
    contract = load_contract(contract_path)
    for key, path_key in (("fasta", "fasta_path"), ("pdb", "pdb_path")):
        if file_sha(Path(contract[path_key])) != contract["input_sha256"][key]:
            raise SystemExit(f"frozen {key} input digest mismatch")
    if hashlib.sha256(contract["sequence"].encode()).hexdigest() != contract["input_sha256"]["sequence"]:
        raise SystemExit("frozen sequence digest mismatch")
    if not IF_CHECKPOINT.is_file() or file_sha(IF_CHECKPOINT) != ESM_IF_SHA256:
        raise SystemExit("ESM-IF1 checkpoint digest mismatch")
    common.OUT = out
    common.ARTIFACTS = out / "artifacts"
    common.CACHE = out / "cache" / CACHE_NAMESPACE
    state: dict = {"msa": None}
    return contract, state


def _variant_parts(variant: str, contract: dict) -> tuple[int, str]:
    try:
        return parse_candidate(variant, contract)
    except ValueError as exc:
        raise ValueError(str(exc)) from exc


def make_classical(out: Path, contract: dict, state: dict) -> MCPServer:
    mcp = MCPServer("b4-v3-item-classical", version="1.0.0")

    @mcp.tool(name="score_variant_classical")
    def score_variant_classical(variant: str) -> dict:
        """Item-bound PSSM, conservation, and BLOSUM62 evidence for one frozen candidate. No path, sequence, MSA, or assay label is accepted from the caller."""
        position, mutant = _variant_parts(variant, contract)
        args = expected_bound_args("score_variant_classical", variant, contract)

        def compute() -> dict:
            if state["msa"] is None:
                state["msa"] = classical.blast_msa(
                    contract["sequence"], contract["fasta_path"], max_hits=100)
            msa = state["msa"]
            pssm = classical.pssm_score(contract["sequence"], msa["msa"], position, mutant)
            conservation = classical.conservation(contract["sequence"], msa["msa"], position)
            blosum = classical.blosum_score(contract["sequence"][position - 1], mutant)
            msa_identity = {"query": msa["query"], "msa": msa["msa"]}
            return {"pssm_delta_bits": pssm["delta_bits"],
                    "conservation": conservation["conservation"],
                    "blosum62": blosum["score"], "msa_depth": msa["depth"],
                    "msa_sha256": canonical_sha(msa_identity),
                    "note": "Generic evolutionary evidence; not an assay outcome."}

        return common.emit("classical", "score_variant_classical", args, compute)

    return mcp


def make_fm(out: Path, contract: dict, state: dict) -> MCPServer:
    mcp = MCPServer("b4-v3-item-fm", version="1.0.0")

    @mcp.tool(name="score_variant_fm")
    def score_variant_fm(variant: str) -> dict:
        """Item-bound ESM-2 and ESM-IF1 evidence for one frozen candidate. No path, sequence, structure, chain, or assay label is accepted from the caller."""
        position, mutant = _variant_parts(variant, contract)
        args = expected_bound_args("score_variant_fm", variant, contract)

        def compute() -> dict:
            e2 = predictive.esm2_likelihood(contract["sequence"], position, mutant)
            changed = (contract["sequence"][:position - 1] + mutant
                       + contract["sequence"][position:])
            eif = generative.esm_if(contract["pdb_path"], contract["chain"], changed)
            if eif.get("model") != ESM_IF_MODEL or file_sha(IF_CHECKPOINT) != ESM_IF_SHA256:
                raise RuntimeError("ESM-IF1 checkpoint identity changed")
            eif = {**eif, "checkpoint_sha256": ESM_IF_SHA256,
                   "cache_namespace": CACHE_NAMESPACE}
            return {"esm2": e2, "esm_if": eif,
                    "note": "Generic sequence/backbone plausibility; not an assay outcome."}

        return common.emit("fm", "score_variant_fm", args, compute)

    return mcp


def make_structure(out: Path, contract: dict, state: dict) -> MCPServer:
    mcp = MCPServer("b4-v3-item-structure", version="1.0.0")

    @mcp.tool(name="structure_context")
    def structure_context() -> dict:
        """Item-bound DSSP context. The caller supplies no path or structure content."""
        args = expected_bound_args("structure_context", None, contract)

        def compute() -> dict:
            raw = physics.dssp(contract["pdb_path"])
            counts = Counter(row["secondary_structure"] for row in raw["residues"])
            return {"backend": raw["backend"], "residue_count": raw["residue_count"],
                    "secondary_structure_by_position":
                        {str(row["position"]): row["secondary_structure"] for row in raw["residues"]},
                    "secondary_structure_counts": dict(sorted(counts.items())),
                    "note": "Static reference-backbone context; not an assay outcome."}

        return common.emit("structure", "structure_context", args, compute)

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", choices=("classical", "fm", "structure"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--contract", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)
    contract, state = configure(out, Path(args.contract).resolve())
    makers = {"classical": make_classical, "fm": make_fm, "structure": make_structure}
    asyncio.run(makers[args.server](out, contract, state).run_stdio_async())


if __name__ == "__main__":
    main()
