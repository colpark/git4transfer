"""Unscored task-contract/receipt audit; never reads assay labels."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3h_2026-09-14"


def audit(run_out: Path) -> dict:
    result = json.loads((run_out / "result.json").read_text())
    path = run_out / "submissions/pilot_item.json"
    answer = json.loads(path.read_text())["answer"] if path.is_file() else None
    accepted_ids = set(result["calls"]["receipt_ids"])
    if answer is None:
        return {"cell": run_out.name, "submission": "absent", "contract_valid": False,
                "reason": "no answer submitted", "cited_ids": [], "invalid_citations": []}
    selected = answer.get("selected") if isinstance(answer, dict) else None
    selected = selected if isinstance(selected, list) else []
    ranks = [entry.get("rank") for entry in selected if isinstance(entry, dict)]
    cites = []
    malformed = []
    for entry in selected:
        if not isinstance(entry, dict):
            malformed.append("selected entry is not an object")
            continue
        if not isinstance(entry.get("mutant"), str) or not isinstance(entry.get("basis"), str) or not isinstance(entry.get("would_overturn"), str):
            malformed.append("selected entry missing mutant, basis or would_overturn string")
        if not isinstance(entry.get("evidence"), list) or not isinstance(entry.get("validation"), list):
            malformed.append("selected entry evidence/validation must be arrays")
        cites.extend(x for x in entry.get("evidence", []) if isinstance(x, str))
        cites.extend(x.get("call_id") for x in entry.get("validation", []) if isinstance(x, dict))
    invalid = sorted({str(cid) for cid in cites if cid not in accepted_ids})
    rank_valid = len(ranks) == 10 and all(isinstance(rank, int) for rank in ranks) and sorted(ranks) == list(range(1, 11))
    valid = len(selected) == 10 and rank_valid and not malformed and not invalid
    return {"cell": run_out.name, "submission": "accepted_by_record", "contract_valid": valid,
            "selected_count": len(selected), "rank_sequence_valid": rank_valid,
            "malformed": malformed, "cited_ids": sorted(set(map(str, cites))),
            "invalid_citations": invalid, "valid_receipt_count": len(accepted_ids)}


def main() -> None:
    rows = [audit(OUT / f"cell_{model}_{mode}") for model in ("7b", "30b")
            for mode in ("unguided", "guided")]
    (OUT / "contract_audit.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(json.dumps([{key: row.get(key) for key in ("cell", "submission", "contract_valid",
                                                  "selected_count", "invalid_citations")} for row in rows]))


if __name__ == "__main__":
    main()
