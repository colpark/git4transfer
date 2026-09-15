"""Strict item-bound contract for prospective B4 v3.

The model never supplies paths, sequences, chains, endpoint hashes, or contract
hashes. Servers attach those identities and this module verifies them.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

POLICY_ID = "b4_v3_adaptive_item_bound_endpoint_v1"
CALL_ID = re.compile(r"call_id:[0-9a-f]{32}")
VARIANT = re.compile(r"([ACDEFGHIKLMNPQRSTVWY])(\d+)([ACDEFGHIKLMNPQRSTVWY])")
ALLOWED_TOOLS = {"score_variant_classical", "score_variant_fm", "structure_context"}
FM_TOOL = "score_variant_fm"
ESM2_MODEL = "facebook/esm2_t33_650M_UR50D"
ESM2_REVISION = "08e4846e537177426273712802403f7ba8261b6c"
ESM_IF_MODEL = "esm_if1_gvp4_t16_142M_UR50"
ESM_IF_SHA256 = "be4ba36edec22a9bfaa4946ff6b2815f1f19d8a3d7e0eada8b796d5a0eae9fd4"


class ContractError(ValueError):
    """An invalid answer or receipt is a coverage failure."""


def canonical_sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize_contract(contract: dict) -> dict:
    """Return the hashed body and reject a missing or mismatched envelope hash."""
    body = dict(contract)
    embedded = body.pop("contract_sha256", None)
    if embedded is not None and embedded != canonical_sha(body):
        raise ContractError("contract envelope digest mismatch")
    return body


def load_contract(path: Path) -> dict:
    raw = json.loads(path.read_text())
    if "contract_sha256" not in raw:
        raise ContractError("contract envelope digest is missing")
    return normalize_contract(raw)


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def parse_candidate(variant: str, contract: dict) -> tuple[int, str]:
    if not isinstance(variant, str) or variant not in set(contract["candidates"]):
        raise ContractError("variant is outside the frozen candidate set")
    match = VARIANT.fullmatch(variant)
    if match is None:
        raise ContractError("candidate variant syntax is invalid")
    position, mutant = int(match[2]), match[3]
    sequence = contract["sequence"]
    if not 1 <= position <= len(sequence) or sequence[position - 1] != match[1]:
        raise ContractError("candidate conflicts with the server-bound sequence")
    return position, mutant


def expected_bound_args(tool: str, variant: str | None, contract: dict) -> dict:
    base = {"contract_sha256": canonical_sha(contract)}
    hashes = contract["input_sha256"]
    if tool == "score_variant_classical":
        parse_candidate(variant, contract)
        return {**base, "variant": variant, "sequence_sha256": hashes["sequence"],
                "fasta_sha256": hashes["fasta"]}
    if tool == "score_variant_fm":
        parse_candidate(variant, contract)
        return {**base, "variant": variant, "sequence_sha256": hashes["sequence"],
                "pdb_sha256": hashes["pdb"], "chain": contract["chain"]}
    if tool == "structure_context":
        if variant is not None:
            raise ContractError("structure_context is item-wide")
        return {**base, "pdb_sha256": hashes["pdb"], "chain": contract["chain"]}
    raise ContractError(f"tool outside B4 v3 contract: {tool}")


def validate_result(tool: str, result: object) -> None:
    if not isinstance(result, dict):
        raise ContractError(f"{tool} result must be an object")
    if tool == "score_variant_classical":
        if (not _finite(result.get("pssm_delta_bits"))
                or not _finite(result.get("conservation"))
                or not _finite(result.get("blosum62"))
                or type(result.get("msa_depth")) is not int or result["msa_depth"] < 2
                or not isinstance(result.get("msa_sha256"), str)):
            raise ContractError("classical result schema/value is invalid")
    elif tool == "score_variant_fm":
        e2, eif = result.get("esm2"), result.get("esm_if")
        if (not isinstance(e2, dict) or e2.get("model") != ESM2_MODEL
                or e2.get("revision") != ESM2_REVISION
                or not _finite(e2.get("delta_log_probability"))
                or not isinstance(eif, dict) or eif.get("model") != ESM_IF_MODEL
                or eif.get("checkpoint_sha256") != ESM_IF_SHA256
                or not _finite(eif.get("mean_log_likelihood"))):
            raise ContractError("FM result model/checkpoint/schema/value is invalid")
    elif tool == "structure_context":
        if (result.get("backend") != "mkdssp_4.2.2"
                or type(result.get("residue_count")) is not int
                or result["residue_count"] < 1):
            raise ContractError("structure result schema/value is invalid")
    else:
        raise ContractError(f"result uses tool outside contract: {tool}")


def validate_artifact(body: dict, path: Path, contract: dict, *, require_success: bool = True) -> bool:
    receipt = body.get("receipt") or {}
    call_id, tool = receipt.get("call_id"), receipt.get("tool")
    if not isinstance(call_id, str) or not CALL_ID.fullmatch(call_id):
        raise ContractError(f"invalid artifact call id: {path}")
    if tool not in ALLOWED_TOOLS:
        raise ContractError(f"artifact tool outside contract: {tool}")
    if Path(receipt.get("artifact_path", "")).resolve() != path.resolve():
        raise ContractError(f"artifact path mismatch: {call_id}")
    args = body.get("args") or {}
    if args != expected_bound_args(tool, args.get("variant"), contract):
        raise ContractError(f"server-bound arguments mismatch: {call_id}")
    payload = json.dumps({"server": body.get("server"), "tool": tool, "args": args},
                         sort_keys=True, separators=(",", ":"), allow_nan=False)
    if hashlib.sha256(payload.encode()).hexdigest() != receipt.get("args_hash"):
        raise ContractError(f"artifact argument hash mismatch: {call_id}")
    successful = body.get("error") is None and body.get("result") is not None
    if not successful:
        if require_success:
            raise ContractError(f"unsuccessful artifact cannot support an answer: {call_id}")
        return False
    validate_result(tool, body["result"])
    return True


def receipt_index(root: Path, contract: dict) -> dict[str, dict]:
    found: dict[str, dict] = {}
    for path in sorted(root.glob("*/*.json")):
        body = json.loads(path.read_text())
        call_id = (body.get("receipt") or {}).get("call_id")
        if call_id in found:
            raise ContractError(f"duplicate receipt id: {call_id}")
        if validate_artifact(body, path, contract, require_success=False):
            found[call_id] = body
    return found


def validate_answer(answer: dict, contract: dict, artifact_root: Path) -> dict:
    if not isinstance(answer, dict):
        raise ContractError("answer must be one object")
    required = {"policy_id", "method_summary", "selected", "rejected", "ranking"}
    if set(answer) != required or answer.get("policy_id") != POLICY_ID:
        raise ContractError("answer schema or policy identifier is invalid")
    if not isinstance(answer["method_summary"], str) or not 20 <= len(answer["method_summary"]) <= 4000:
        raise ContractError("method_summary must contain 20-4000 characters")
    candidates = contract["candidates"]
    if len(candidates) < 10 or len(set(candidates)) != len(candidates):
        raise ContractError("frozen candidate registry is invalid")
    selected, rejected, ranking = answer["selected"], answer["rejected"], answer["ranking"]
    if not isinstance(selected, list) or len(selected) != 10:
        raise ContractError("selected must contain exactly ten variants")
    if not isinstance(rejected, list) or len(rejected) != len(candidates) - 10:
        raise ContractError("rejected must contain every remaining variant")
    if not isinstance(ranking, list) or len(ranking) != len(candidates):
        raise ContractError("ranking must cover every candidate")
    receipts = receipt_index(artifact_root, contract)
    ranked: list[str] = []
    cited: set[str] = set()
    for expected_rank, row in enumerate(ranking, 1):
        if not isinstance(row, dict) or set(row) != {"rank", "mutant", "evidence_call_ids", "rationale"}:
            raise ContractError(f"ranking row {expected_rank} schema is invalid")
        if type(row["rank"]) is not int or row["rank"] != expected_rank:
            raise ContractError(f"ranking row {expected_rank} rank is invalid")
        mutant = row["mutant"]
        parse_candidate(mutant, contract)
        if not isinstance(row["rationale"], str) or not 1 <= len(row["rationale"]) <= 1000:
            raise ContractError(f"ranking row {expected_rank} rationale is invalid")
        ids = row["evidence_call_ids"]
        if not isinstance(ids, list) or not ids or any(not isinstance(x, str) for x in ids):
            raise ContractError(f"ranking row {expected_rank} receipts are invalid")
        has_fm = False
        for call_id in ids:
            body = receipts.get(call_id)
            if body is None:
                raise ContractError(f"ranking row {expected_rank} cites a missing receipt")
            args, tool = body["args"], body["receipt"]["tool"]
            if args.get("variant") == mutant and tool == FM_TOOL:
                has_fm = True
            elif args.get("variant") not in (None, mutant):
                raise ContractError(f"ranking row {expected_rank} cites another candidate")
            cited.add(call_id)
        if not has_fm:
            raise ContractError(f"ranking row {expected_rank} lacks item-bound FM evidence")
        ranked.append(mutant)
    if len(set(ranked)) != len(candidates) or set(ranked) != set(candidates):
        raise ContractError("ranking is not a unique candidate permutation")
    if selected != ranked[:10] or rejected != ranked[10:]:
        raise ContractError("selected/rejected must be exact ranking slices")
    return {"accepted": True, "policy_id": POLICY_ID, "candidate_count": len(candidates),
            "ranking_complete": True, "unique_cited_receipts": len(cited),
            "answer_sha256": canonical_sha(answer), "contract_sha256": canonical_sha(contract),
            "endpoint_sha256": contract["endpoint_sha256"]}


def ranking_scores(answer: dict) -> dict[str, float]:
    n = len(answer["ranking"])
    return {row["mutant"]: float(n + 1 - row["rank"]) for row in answer["ranking"]}
