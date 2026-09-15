"""Negative controls for the prospective B4 v3 remediation."""

from __future__ import annotations

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from stage4step2e_contract import (ContractError, ESM2_MODEL, ESM2_REVISION,
    ESM_IF_MODEL, ESM_IF_SHA256, POLICY_ID, canonical_sha, expected_bound_args,
    validate_answer)
from stage4step2e_prepare import tool_surface
from stage4step2e_validate import audit_trace_pairs


class ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.artifacts = root / "artifacts"
        sequence = "A" * 100
        self.contract = {"schema_version": 2, "neutral_item_id": "item_test",
            "policy_id": POLICY_ID, "status": "test", "sequence": sequence,
            "candidates": [f"A{i}C" for i in range(1, 101)], "candidate_count": 100,
            "fasta_path": str(root / "item.fasta"), "pdb_path": str(root / "item.pdb"),
            "chain": "A", "endpoint": {"field": "test"}, "endpoint_sha256": "e" * 64,
            "input_sha256": {"sequence": hashlib.sha256(sequence.encode()).hexdigest(),
                             "fasta": "f" * 64, "pdb": "p" * 64}}
        ids = []
        for i, variant in enumerate(self.contract["candidates"], 1):
            call_id = f"call_id:{i:032x}"
            args = expected_bound_args("score_variant_fm", variant, self.contract)
            path = self.artifacts / "fm" / f"{i:032x}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = json.dumps({"server": "fm", "tool": "score_variant_fm", "args": args},
                                 sort_keys=True, separators=(",", ":"), allow_nan=False)
            receipt = {"call_id": call_id, "tool": "score_variant_fm",
                       "args_hash": hashlib.sha256(payload.encode()).hexdigest(),
                       "runtime_s": 1.0, "artifact_path": str(path), "cache_hit": False}
            result = {"esm2": {"model": ESM2_MODEL, "revision": ESM2_REVISION,
                                "delta_log_probability": -float(i)},
                      "esm_if": {"model": ESM_IF_MODEL, "checkpoint_sha256": ESM_IF_SHA256,
                                 "mean_log_likelihood": -float(i)}}
            path.write_text(json.dumps({"server": "fm", "args": args, "result": result,
                                        "error": None, "receipt": receipt}) + "\n")
            ids.append(call_id)
        ranking = [{"rank": i, "mutant": v, "evidence_call_ids": [ids[i - 1]],
                    "rationale": "item-bound FM evidence"}
                   for i, v in enumerate(self.contract["candidates"], 1)]
        self.answer = {"policy_id": POLICY_ID,
            "method_summary": "Adaptive ordering based on item-bound label-free FM evidence.",
            "selected": self.contract["candidates"][:10],
            "rejected": self.contract["candidates"][10:], "ranking": ranking}

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_valid_without_model_copied_hash(self) -> None:
        self.assertTrue(validate_answer(self.answer, self.contract, self.artifacts)["accepted"])

    def test_model_supplied_hash_is_rejected(self) -> None:
        bad = copy.deepcopy(self.answer); bad["endpoint_sha256"] = "e" * 64
        with self.assertRaisesRegex(ContractError, "schema"):
            validate_answer(bad, self.contract, self.artifacts)

    def test_selected_must_be_ranking_slice(self) -> None:
        bad = copy.deepcopy(self.answer); bad["selected"][0], bad["selected"][1] = bad["selected"][1], bad["selected"][0]
        with self.assertRaisesRegex(ContractError, "slices"):
            validate_answer(bad, self.contract, self.artifacts)

    def test_boolean_rank_rejected(self) -> None:
        bad = copy.deepcopy(self.answer); bad["ranking"][0]["rank"] = True
        with self.assertRaisesRegex(ContractError, "rank"):
            validate_answer(bad, self.contract, self.artifacts)

    def test_wrong_bound_sequence_hash_rejected(self) -> None:
        path = next((self.artifacts / "fm").glob("*.json")); body = json.loads(path.read_text())
        body["args"]["sequence_sha256"] = "0" * 64; path.write_text(json.dumps(body))
        with self.assertRaisesRegex(ContractError, "bound arguments"):
            validate_answer(self.answer, self.contract, self.artifacts)

    def test_wrong_checkpoint_rejected(self) -> None:
        path = next((self.artifacts / "fm").glob("*.json")); body = json.loads(path.read_text())
        body["result"]["esm_if"]["checkpoint_sha256"] = "0" * 64; path.write_text(json.dumps(body))
        with self.assertRaisesRegex(ContractError, "checkpoint"):
            validate_answer(self.answer, self.contract, self.artifacts)


class TracePairTests(unittest.TestCase):
    def events(self) -> list[dict]:
        args = {"variant": "A1C"}
        return [{"type": "item.started", "item": {"id": "1", "type": "mcp_tool_call",
                 "server": "b4v3_fm", "tool": "score_variant_fm", "arguments": args}},
                {"type": "item.completed", "item": {"id": "1", "type": "mcp_tool_call",
                 "server": "b4v3_fm", "tool": "score_variant_fm", "arguments": args}},
                {"type": "item.started", "item": {"id": "2", "type": "mcp_tool_call",
                 "server": "b4v3_record", "tool": "submit_answer", "arguments": {"answer": {}}}},
                {"type": "item.completed", "item": {"id": "2", "type": "mcp_tool_call",
                 "server": "b4v3_record", "tool": "submit_answer", "arguments": {"answer": {}}}}]

    def test_exact_pairs_pass(self) -> None:
        self.assertEqual(len(audit_trace_pairs(self.events())["started"]), 2)

    def test_unmatched_start_rejected(self) -> None:
        with self.assertRaisesRegex(ContractError, "unmatched"):
            audit_trace_pairs(self.events()[:-1])

    def test_changed_arguments_rejected(self) -> None:
        events = self.events(); events[1]["item"]["arguments"] = {"variant": "A2C"}
        with self.assertRaisesRegex(ContractError, "arguments changed"):
            audit_trace_pairs(events)

    def test_unknown_tool_rejected(self) -> None:
        events = self.events(); events[0]["item"]["tool"] = "read_file"
        with self.assertRaisesRegex(ContractError, "outside allowlist"):
            audit_trace_pairs(events)


class SurfaceTests(unittest.TestCase):
    def test_model_cannot_supply_item_inputs(self) -> None:
        surface = tool_surface()["item_bound_mcp"]
        self.assertEqual(set(surface["mcp__b4v3_record__submit_answer"]["parameters"]["properties"]), {"answer"})
        for name, row in surface.items():
            properties = set(row["parameters"].get("properties", {}))
            self.assertFalse(properties & {"sequence", "pdb_path", "fasta_path", "chain", "msa", "endpoint_sha256"}, name)


if __name__ == "__main__":
    unittest.main()
