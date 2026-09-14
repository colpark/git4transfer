"""Predictive W1/W2 MCP backends; model workers are isolated subprocesses."""

from __future__ import annotations

import json
import subprocess

from common import ROOT, require_sequence

TORCH_PY = ROOT / "E1/.venv/bin/python"


def esm2_likelihood(sequence: str, position: int, mutant: str) -> dict:
    sequence = require_sequence(sequence)
    mutant = require_sequence(mutant)
    if len(sequence) > 1022 or len(mutant) != 1 or not 1 <= position <= len(sequence):
        raise ValueError("ESM-2 requires <=1022 residues, one mutant amino acid, valid position")
    if not TORCH_PY.is_file():
        raise RuntimeError("Torch worker environment unavailable")
    arguments = {"sequence": sequence, "position": position, "mutant": mutant}
    process = subprocess.run([str(TORCH_PY), str(ROOT / "benchmark-mcp/esm2_worker.py")],
                             input=json.dumps(arguments), text=True, capture_output=True, timeout=90)
    if process.returncode:
        raise RuntimeError(f"ESM-2 worker exited {process.returncode}: {process.stderr[-500:]}")
    return json.loads(process.stdout)


def esmfold(sequence: str, seed: int = 0) -> dict:
    sequence = require_sequence(sequence, min_len=5)
    if len(sequence) > 600 or not 0 <= seed <= 2**31-1:
        raise ValueError("ESMFold requires 5–600 residues and a nonnegative 31-bit seed")
    arguments = {"sequence": sequence, "seed": seed}
    process = subprocess.run([str(TORCH_PY), str(ROOT / "benchmark-mcp/esmfold_worker.py")],
                             input=json.dumps(arguments), text=True, capture_output=True, timeout=115)
    if process.returncode:
        raise RuntimeError(f"ESMFold worker exited {process.returncode}: {process.stderr[-500:]}")
    return json.loads(process.stdout)
