"""Frozen prompt-only contract for the ten-item comparison."""

from __future__ import annotations

import json
import math
import re

VARIANT = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY][1-9][0-9]*[ACDEFGHIKLMNPQRSTVWY]$")


def parse_answer(text: str, candidates: tuple[str, ...], neutral_id: str) -> dict:
    try:
        answer = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("answer is not one plain JSON object") from exc
    if not isinstance(answer, dict) or set(answer) != {"item_id", "selected", "rejected", "ranking"}:
        raise ValueError("answer has wrong top-level contract")
    if answer["item_id"] != neutral_id:
        raise ValueError("item_id does not match the neutral item handle")
    selected, rejected, ranking = answer["selected"], answer["rejected"], answer["ranking"]
    if not isinstance(selected, list) or len(selected) != 10:
        raise ValueError("selected must contain exactly ten picks")
    if not isinstance(rejected, list) or len(rejected) != len(candidates) - 10:
        raise ValueError("rejected must be the candidate complement")
    if not isinstance(ranking, list) or len(ranking) != len(candidates):
        raise ValueError("ranking must include every candidate")
    selected_names = []
    for expected_rank, pick in enumerate(selected, 1):
        if not isinstance(pick, dict) or set(pick) != {
            "rank", "mutant", "basis", "evidence", "validation", "would_overturn"
        }:
            raise ValueError("selected entry has wrong fields")
        if type(pick["rank"]) is not int or pick["rank"] != expected_rank:
            raise ValueError("selected ranks must be consecutive")
        if pick["mutant"] not in candidates:
            raise ValueError("selected mutant is outside the candidate set")
        if not isinstance(pick["basis"], str) or not pick["basis"].strip():
            raise ValueError("selected basis is empty")
        if pick["evidence"] != [] or pick["validation"] != []:
            raise ValueError("prompt-only answer cites evidence or validation")
        if not isinstance(pick["would_overturn"], str) or not pick["would_overturn"].strip():
            raise ValueError("would_overturn is empty")
        selected_names.append(pick["mutant"])
    if len(set(selected_names)) != 10:
        raise ValueError("selected picks are duplicated")
    rejected_names = []
    for entry in rejected:
        if not isinstance(entry, dict) or set(entry) != {"mutant", "reason"}:
            raise ValueError("rejected entry has wrong fields")
        if entry["mutant"] not in candidates or not isinstance(entry["reason"], str) or not entry["reason"].strip():
            raise ValueError("rejected entry is invalid")
        rejected_names.append(entry["mutant"])
    if len(set(rejected_names)) != len(rejected_names) or set(rejected_names) != set(candidates) - set(selected_names):
        raise ValueError("rejected entries do not equal the candidate complement")
    rows = []
    for expected_rank, entry in enumerate(ranking, 1):
        if not isinstance(entry, dict) or set(entry) != {"rank", "mutant", "score"}:
            raise ValueError("ranking entry has wrong fields")
        if type(entry["rank"]) is not int or entry["rank"] != expected_rank:
            raise ValueError("ranking ranks must be consecutive")
        score = entry["score"]
        if entry["mutant"] not in candidates or type(score) not in (int, float) or not math.isfinite(score):
            raise ValueError("ranking mutant or score is invalid")
        rows.append((entry["mutant"], float(score)))
    if len({mutant for mutant, _ in rows}) != len(candidates):
        raise ValueError("ranking has duplicate or missing candidates")
    if rows != sorted(rows, key=lambda row: (-row[1], row[0])):
        raise ValueError("ranking is not descending with lexical tie break")
    if [mutant for mutant, _ in rows[:10]] != selected_names:
        raise ValueError("selected picks disagree with full ranking")
    return answer


def prompt(neutral_id: str, endpoint: dict, candidates: tuple[str, ...]) -> str:
    if len(candidates) < 10 or len(candidates) != len(set(candidates)):
        raise ValueError("invalid candidate set")
    if any(VARIANT.fullmatch(x) is None for x in candidates):
        raise ValueError("malformed candidate")
    return f"""Rank every supplied single-substitution candidate for the declared endpoint. This is a prediction, not a measured assay result. No scientific, filesystem, shell, retrieval, or web tools are available. Use only the endpoint description and candidate notation. Do not imply that you read a sequence, FASTA, PDB, file, tool result, database record, or measured value.

Neutral item: {neutral_id}
Declared label-free endpoint context:
{json.dumps(endpoint, sort_keys=True)}

Candidate variants:
{', '.join(candidates)}

Return one plain JSON object with no Markdown fence or extra text and exactly these keys: item_id, selected, rejected, ranking. Set item_id to {neutral_id}. selected contains exactly ten unique objects in rank order with exactly the keys rank, mutant, basis, evidence, validation, would_overturn. Ranks are integers 1 through 10. evidence and validation are empty arrays because no tools are available. rejected contains every other candidate exactly once, each as an object with exactly mutant and reason. ranking contains every candidate exactly once in predicted descending order, each with exactly rank, mutant, and a finite numeric score. Ranking ranks are consecutive integers starting at 1; its first ten mutants exactly match selected. Break tied scores by mutant lexicographic order. Never invent an observation, receipt, or assay result.
"""
