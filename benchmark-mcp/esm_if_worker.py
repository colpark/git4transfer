"""Pinned ESM-IF1 backbone-conditioned sequence likelihood worker."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import biotite.structure as bs
import torch

# fair-esm 2.0 imports the old Biotite API spelling. In Biotite 1.7.1 the
# corresponding peptide-backbone predicate was renamed; do not edit packages.
if not hasattr(bs, "filter_backbone"):
    bs.filter_backbone = bs.filter_peptide_backbone

import esm  # noqa: E402
from esm.inverse_folding.util import load_coords, score_sequence  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
MODEL = "esm_if1_gvp4_t16_142M_UR50"
AA = set("ACDEFGHIKLMNPQRSTVWY")


def score(pdb_path: str, chain: str, sequence: str) -> dict:
    path = Path(pdb_path).resolve()
    if ROOT not in path.parents or not path.is_file() or path.stat().st_size > 10_000_000:
        raise ValueError("PDB must be an existing <=10 MB workspace file")
    if path.suffix.lower() != ".pdb" or len(chain) != 1:
        raise ValueError("a PDB and one-character chain ID are required")
    sequence = sequence.upper()
    if not sequence or set(sequence) - AA:
        raise ValueError("sequence must contain canonical amino acids")
    coords, extracted = load_coords(str(path), chain)
    if len(coords) != len(sequence) or len(extracted) != len(sequence):
        raise ValueError("input sequence length must match the backbone")
    model, alphabet = esm.pretrained.esm_if1_gvp4_t16_142M_UR50()
    model.eval()
    with torch.inference_mode():
        full, with_coords = score_sequence(model, alphabet, coords, sequence)
    return {"sequence_length": len(sequence), "backbone_length": len(coords),
            "mean_log_likelihood": float(full),
            "mean_log_likelihood_with_coords": float(with_coords),
            "native_sequence_match": sequence == extracted,
            "model": MODEL, "device": "cpu", "pdb_path": str(path), "chain": chain,
            "interpretation": "backbone-conditioned sequence score; not a measured stability effect"}


if __name__ == "__main__":
    print(json.dumps(score(**json.load(sys.stdin)), allow_nan=False))
