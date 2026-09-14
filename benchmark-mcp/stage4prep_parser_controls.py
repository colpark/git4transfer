"""Synthetic must-pass/must-fail controls for the frozen prompt-only parser."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from stage4prep_promptonly import parse_answer

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4prep_2026-09-14"
CANDIDATES = tuple(f"A{index}C" for index in range(1, 101))


def valid_answer() -> dict:
    names = list(CANDIDATES)
    return {"item_id": "pilot_item",
            "selected": [{"rank": rank, "mutant": variant, "basis": "synthetic",
                          "evidence": [], "validation": [], "would_overturn": "synthetic"}
                         for rank, variant in enumerate(names[:10], 1)],
            "rejected": [{"mutant": variant, "reason": "synthetic"} for variant in names[10:]],
            "ranking": [{"mutant": variant, "score": 100 - index}
                        for index, variant in enumerate(names)]}


def main() -> None:
    cases = {}
    good = valid_answer()
    parse_answer(json.dumps(good), CANDIDATES)
    cases["valid_100"] = "PASS"
    tests = {"malformed_json": "{not-json"}
    altered = copy.deepcopy(good)
    altered["selected"].pop()
    tests["nine_picks"] = altered
    altered = copy.deepcopy(good)
    altered["selected"].append(copy.deepcopy(altered["selected"][-1]))
    tests["eleven_picks"] = altered
    altered = copy.deepcopy(good)
    altered["selected"][1]["mutant"] = altered["selected"][0]["mutant"]
    tests["duplicate_pick"] = altered
    altered = copy.deepcopy(good)
    altered["selected"][0]["evidence"] = ["call_id:invented"]
    tests["invented_receipt"] = altered
    altered = copy.deepcopy(good)
    altered["ranking"].pop()
    tests["incomplete_ranking"] = altered
    for name, test in tests.items():
        try:
            parse_answer(test if isinstance(test, str) else json.dumps(test), CANDIDATES)
        except ValueError:
            cases[name] = "PASS: rejected"
        else:
            cases[name] = "FAIL: accepted"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "parser_controls.json").write_text(json.dumps(cases, indent=2) + "\n")
    print(json.dumps(cases, indent=2))
    if any(not value.startswith("PASS") for value in cases.values()):
        raise SystemExit("parser control failed")


if __name__ == "__main__":
    main()
