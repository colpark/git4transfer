"""Frozen prompt-only W1 contract and deterministic, label-free parser."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass

VARIANT = re.compile(r"^[ACDEFGHIKLMNPQRSTVWY][1-9][0-9]*[ACDEFGHIKLMNPQRSTVWY]$")
WITHHOLD_FM = "Do not use foundation models."


@dataclass(frozen=True)
class ParsedAnswer:
    selected: tuple[str, ...]
    rejected: tuple[str, ...]
    ranking: tuple[tuple[str, float], ...]


def candidates_from_source_prompt(source_prompt: str) -> tuple[str, ...]:
    section = source_prompt.split("Candidate variants:\n", 1)
    if len(section) != 2:
        raise ValueError("source prompt has no candidate section")
    candidates = tuple(part.strip() for part in section[1].strip().split(","))
    if len(candidates) < 10 or len(set(candidates)) != len(candidates):
        raise ValueError("source candidate list is too short or duplicated")
    if any(not VARIANT.fullmatch(variant) for variant in candidates):
        raise ValueError("source candidate list contains malformed variants")
    return candidates


def build_prompt(source_prompt: str, with_fm_instruction: bool) -> str:
    candidates_from_source_prompt(source_prompt)
    stem = source_prompt.strip()
    condition = "\n\n" + WITHHOLD_FM if with_fm_instruction else ""
    contract = (
        "\n\nReturn one plain JSON object, with no Markdown fence or extra text. "
        "This is a prediction, not an assay result. Use exactly these keys: "
        "item_id, selected, rejected, ranking. Set item_id to pilot_item. "
        "selected must contain exactly ten unique objects with rank 1 through 10 in order, "
        "mutant, basis, evidence, validation, and would_overturn. "
        "The evidence and validation arrays must be empty because no tools are available; "
        "describe reasoning in basis, never invent a receipt. "
        "rejected must contain every other candidate exactly once, each as an object with "
        "mutant and reason. ranking must contain every supplied candidate exactly once, "
        "each as an object with mutant and finite numeric score, in descending predicted "
        "score order. The first ten ranking mutants must match selected ranks 1 through 10. "
        "If two scores tie, order their mutants lexicographically. "
        "Do not claim that predicted scores are measured fitness."
    )
    return stem + condition + contract + "\n"


def parse_answer(text: str, candidates: tuple[str, ...]) -> ParsedAnswer:
    try:
        answer = json.loads(text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError("answer is not one plain JSON object") from exc
    if not isinstance(answer, dict) or set(answer) != {"item_id", "selected", "rejected", "ranking"}:
        raise ValueError("answer has wrong top-level contract")
    if answer["item_id"] != "pilot_item":
        raise ValueError("item_id must be pilot_item")
    selected = answer["selected"]
    rejected = answer["rejected"]
    ranking = answer["ranking"]
    if not isinstance(selected, list) or len(selected) != 10:
        raise ValueError("selected must contain exactly ten picks")
    if not isinstance(rejected, list) or len(rejected) != len(candidates) - 10:
        raise ValueError("rejected must be the candidate complement")
    if not isinstance(ranking, list) or len(ranking) != len(candidates):
        raise ValueError("ranking must include every candidate")
    selected_names = []
    for rank, pick in enumerate(selected, 1):
        if not isinstance(pick, dict) or set(pick) != {
            "rank", "mutant", "basis", "evidence", "validation", "would_overturn"
        }:
            raise ValueError("selected entry has wrong fields")
        if type(pick["rank"]) is not int or pick["rank"] != rank:
            raise ValueError("selected ranks must be 1 through 10 in order")
        if not isinstance(pick["mutant"], str) or pick["mutant"] not in candidates:
            raise ValueError("selected mutant is not a supplied candidate")
        if not isinstance(pick["basis"], str) or not pick["basis"].strip():
            raise ValueError("selected basis must be nonempty")
        if not isinstance(pick["would_overturn"], str) or not pick["would_overturn"].strip():
            raise ValueError("selected would_overturn must be nonempty")
        if pick["evidence"] != [] or pick["validation"] != []:
            raise ValueError("prompt-only answer must not cite tool receipts")
        selected_names.append(pick["mutant"])
    if len(set(selected_names)) != 10:
        raise ValueError("selected picks contain a duplicate")
    rejected_names = []
    for entry in rejected:
        if not isinstance(entry, dict) or set(entry) != {"mutant", "reason"}:
            raise ValueError("rejected entry has wrong fields")
        if not isinstance(entry["mutant"], str) or entry["mutant"] not in candidates:
            raise ValueError("rejected mutant is not a supplied candidate")
        if not isinstance(entry["reason"], str) or not entry["reason"].strip():
            raise ValueError("rejected reason must be nonempty")
        rejected_names.append(entry["mutant"])
    if set(rejected_names) != set(candidates) - set(selected_names) or len(set(rejected_names)) != len(rejected_names):
        raise ValueError("rejected does not equal the unique nonselected candidates")
    rows = []
    for entry in ranking:
        if not isinstance(entry, dict) or set(entry) != {"mutant", "score"}:
            raise ValueError("ranking entry has wrong fields")
        mutant, score = entry["mutant"], entry["score"]
        if mutant not in candidates or type(score) not in (int, float) or not math.isfinite(score):
            raise ValueError("ranking mutant or score invalid")
        rows.append((mutant, float(score)))
    if len({mutant for mutant, _ in rows}) != len(candidates):
        raise ValueError("ranking has duplicate or missing candidates")
    if rows != sorted(rows, key=lambda row: (-row[1], row[0])):
        raise ValueError("ranking is not descending with lexical tie break")
    if [mutant for mutant, _ in rows[:10]] != selected_names:
        raise ValueError("selected ranks disagree with full ranking")
    return ParsedAnswer(tuple(selected_names), tuple(rejected_names), tuple(rows))
