"""Experimental unfolded-reference correction; not a certified W2 scorer.

The caller must supply a complete, source-pinned table in kJ/mol. No table is
bundled: importing Rosetta REU reference weights into Amber would be an
unvalidated force-field/units substitution. This module is deliberately not
mounted as an MCP tool until a MegaScale endpoint comparison passes criterion e.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")


def corrected_delta(
    folded_delta_kj_per_mol: float,
    wt_aa: str,
    mutant_aa: str,
    unfolded_reference_kj_per_mol: Mapping[str, float],
    reference_source: str,
) -> dict:
    """Return ΔU_folded − [u_ref(mutant) − u_ref(WT)], as a proxy only."""
    if not math.isfinite(folded_delta_kj_per_mol):
        raise ValueError("folded-state energy delta must be finite")
    if len(wt_aa) != 1 or wt_aa not in AMINO_ACIDS or len(mutant_aa) != 1 or mutant_aa not in AMINO_ACIDS:
        raise ValueError("WT and mutant must be canonical single amino acids")
    if set(unfolded_reference_kj_per_mol) != AMINO_ACIDS:
        raise ValueError("reference table must contain exactly 20 canonical amino acids")
    if not reference_source.strip():
        raise ValueError("reference source must be declared")
    table = {aa: float(value) for aa, value in unfolded_reference_kj_per_mol.items()}
    if not all(math.isfinite(value) for value in table.values()):
        raise ValueError("reference energies must be finite")
    unfolded_delta = table[mutant_aa] - table[wt_aa]
    return {
        "folded_delta_kj_per_mol": folded_delta_kj_per_mol,
        "unfolded_reference_delta_kj_per_mol": unfolded_delta,
        "corrected_delta_kj_per_mol": folded_delta_kj_per_mol - unfolded_delta,
        "reference_source": reference_source,
        "is_folding_ddg": False,
        "eligible_for_w2_scoring": False,
        "method": "unvalidated_per_amino_acid_unfolded_reference_proxy",
    }
