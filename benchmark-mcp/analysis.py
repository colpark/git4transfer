"""W1/W2 sequence and structure comparison tools."""

from __future__ import annotations

import re
import subprocess

from common import ROOT, reference_path
from classical import seq_identity

TMALIGN = ROOT / "benchmark-mcp/bin/TMalign"


def tmalign(pdb_a: str, pdb_b: str) -> dict:
    a, b = reference_path(pdb_a), reference_path(pdb_b)
    if not TMALIGN.is_file():
        raise RuntimeError("TM-align executable is not installed")
    process = subprocess.run([str(TMALIGN), str(a), str(b)], capture_output=True,
                             text=True, timeout=90)
    if process.returncode:
        raise RuntimeError(f"TM-align exited {process.returncode}: {process.stderr[-300:]}")
    scores = [float(value) for value in re.findall(r"TM-score=\s*([0-9.]+)", process.stdout)]
    if len(scores) != 2:
        raise ValueError("TM-align did not return both normalized TM-scores")
    rmsd = re.search(r"RMSD=\s*([0-9.]+)", process.stdout)
    aligned = re.search(r"Aligned length=\s*(\d+)", process.stdout)
    return {"tm_score_by_structure_1": scores[0], "tm_score_by_structure_2": scores[1],
            "rmsd_A": float(rmsd.group(1)) if rmsd else None,
            "aligned_length": int(aligned.group(1)) if aligned else None,
            "source": "pylelab/USalign TMalign.cpp fcb0f9d921415a2095bc509975db7fc1e968af1d"}

