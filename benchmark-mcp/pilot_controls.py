"""Pre-pilot must-fail controls for frozen answer parsing and receipt audits."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from pilot_score import cited_and_depth, full_ranking, selected_mutants, native_capability_used

OUT = Path(__file__).resolve().parents[1] / "results/benchmark/stage4pilot_2026-09-13"


def main() -> None:
    candidates = {f"A{i}V" for i in range(1, 21)}
    valid_selected = [{"rank": i, "mutant": f"A{i}V"} for i in range(1, 11)]
    valid_ranking = [{"mutant": f"A{i}V", "score": float(i)} for i in range(1, 21)]
    forged_answer = {"selected": [{"evidence": ["call_id:forged"],
                                    "validation": [{"category": "sequence",
                                                    "call_id": "call_id:real"}]}]}
    cited, fabricated, depth = cited_and_depth(forged_answer, {"call_id:real": "sequence"})
    wrong_category = {"selected": [{"validation": [{"category": "energetic",
                                                   "call_id": "call_id:real"}]}]}
    _, _, wrong_depth = cited_and_depth(wrong_category, {"call_id:real": "sequence"})
    with tempfile.TemporaryDirectory(prefix="pilot_grant_control_") as tmp:
        bad_trace = Path(tmp) / "bad.jsonl"
        clean_trace = Path(tmp) / "clean.jsonl"
        bad_trace.write_text(json.dumps({"item": {"type": "command_execution"}}) + "\n")
        clean_trace.write_text(json.dumps({"item": {"type": "agent_message"}}) + "\n")
        grant_control = native_capability_used(str(bad_trace)) and not native_capability_used(str(clean_trace))
    checks = {
        "valid_top_ten_accepted": selected_mutants({"selected": valid_selected}, candidates)
                                  == [f"A{i}V" for i in range(1, 11)],
        "duplicate_top_ten_rejected": selected_mutants(
            {"selected": valid_selected[:-1] + [{"rank": 10, "mutant": "A1V"}]},
            candidates) is None,
        "missing_top_ten_rejected": selected_mutants({"selected": valid_selected[:-1]},
                                                      candidates) is None,
        "complete_ranking_accepted": full_ranking({"ranking": valid_ranking}, candidates)
                                     is not None,
        "incomplete_ranking_rejected": full_ranking({"ranking": valid_ranking[:-1]},
                                                     candidates) is None,
        "forged_receipt_counted": cited == 2 and fabricated == 1 and depth == 1,
        "false_validation_category_rejected": wrong_depth == 0,
        "native_out_of_grant_detected": grant_control,
    }
    body = {"all_pass": all(checks.values()), "checks": checks}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "pilot_controls.json").write_text(json.dumps(body, indent=2) + "\n")
    if not body["all_pass"]:
        raise AssertionError("pilot answer/receipt controls failed")
    print(json.dumps(body))


if __name__ == "__main__":
    main()
