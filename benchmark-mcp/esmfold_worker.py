"""Pinned ESMFold checkpoint worker; returns a PDB artifact, not a binding score."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import torch
from transformers import EsmForProteinFolding

ROOT = Path(__file__).resolve().parents[1]
MODEL = "facebook/esmfold_v1"
REVISION = "75a3841ee059df2bf4d56688166c8fb459ddd97a"
AA = set("ACDEFGHIKLMNPQRSTVWY")


def fold(sequence: str, seed: int = 0) -> dict:
    sequence = sequence.upper()
    if not 5 <= len(sequence) <= 600 or set(sequence) - AA:
        raise ValueError("ESMFold sequence must be 5–600 canonical residues")
    if not 0 <= seed <= 2**31-1:
        raise ValueError("seed must be a nonnegative 31-bit integer")
    torch.manual_seed(seed)
    model = EsmForProteinFolding.from_pretrained(MODEL, revision=REVISION).eval()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        model = model.cuda()
        model.esm = model.esm.half()
    with torch.inference_mode():
        pdb_text = model.infer_pdb(sequence)
    ca_lines = [line for line in pdb_text.splitlines()
                if line.startswith("ATOM") and line[12:16].strip() == "CA"]
    if len(ca_lines) != len(sequence):
        raise RuntimeError("ESMFold output CA count does not match sequence length")
    mean_bfactor = sum(float(line[60:66]) for line in ca_lines) / len(ca_lines)
    key = hashlib.sha256(f"{REVISION}:{sequence}:{seed}".encode()).hexdigest()
    path = ROOT / "results/benchmark/stage2_2026-09-12/model_artifacts/esmfold" / f"{key}.pdb"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(pdb_text)
    return {"sequence_length": len(sequence), "ca_count": len(ca_lines),
            "mean_ca_bfactor_as_written": mean_bfactor, "pdb_path": str(path),
            "model": MODEL, "revision": REVISION, "device": device, "seed": seed,
            "interpretation": "structure confidence only; not a binding or stability measurement"}


if __name__ == "__main__":
    print(json.dumps(fold(**json.load(sys.stdin)), allow_nan=False))
