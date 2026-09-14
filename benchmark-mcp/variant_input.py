"""Resolve a biological variant string without hiding conflicting arguments."""

from __future__ import annotations

import re

AA_PATTERN = r"^[ACDEFGHIKLMNPQRSTVWY]$"
VARIANT_PATTERN = r"^[ACDEFGHIKLMNPQRSTVWY][1-9][0-9]*[ACDEFGHIKLMNPQRSTVWY]$"


def resolve_variant(*, variant: str | None = None, wt: str | None = None,
                    position: int | None = None, mutant: str | None = None,
                    sequence: str | None = None, require_mutant: bool = True) -> dict:
    """Return canonical fields plus the agent's input form; do not infer a mutant."""
    supplied = {"wt": wt, "position": position, "mutant": mutant}
    if variant is not None:
        if not re.fullmatch(VARIANT_PATTERN, variant):
            raise ValueError("variant must look like G52L (one-letter WT, one-based position, one-letter mutant)")
        parsed = re.fullmatch(r"([A-Z])([1-9][0-9]*)([A-Z])", variant)
        assert parsed is not None
        canonical = {"wt": parsed[1], "position": int(parsed[2]), "mutant": parsed[3]}
        for key, value in supplied.items():
            if value is not None and value != canonical[key]:
                raise ValueError(f"conflicting variant {variant}: supplied {key}={value!r}, expected {canonical[key]!r}")
        form = "both" if any(value is not None for value in supplied.values()) else "variant"
    else:
        canonical = dict(supplied)
        form = "decomposed"
    for key in ("wt", "mutant"):
        value = canonical[key]
        if value is not None and not re.fullmatch(AA_PATTERN, value):
            raise ValueError(f"{key} must be one amino-acid letter (e.g. G), not a variant such as G52L; use variant='G52L'")
    if require_mutant and canonical["mutant"] is None:
        raise ValueError("supply mutant as one letter or variant such as G52L")
    if sequence is not None and canonical["position"] is not None:
        pos = canonical["position"]
        if not 1 <= pos <= len(sequence):
            raise ValueError(f"position {pos} outside sequence of length {len(sequence)}")
        actual_wt = sequence[pos - 1]
        if canonical["wt"] is not None and canonical["wt"] != actual_wt:
            raise ValueError(f"variant WT {canonical['wt']} conflicts with sequence residue {actual_wt} at position {pos}")
        canonical["wt"] = actual_wt
    if canonical["position"] is None and sequence is not None:
        raise ValueError("supply position or variant such as G52L")
    return {**canonical, "input_form": form}
