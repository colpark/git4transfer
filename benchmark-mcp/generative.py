"""ESM-IF1 MCP backend."""

from __future__ import annotations

import json
import subprocess

from common import ROOT

TORCH_PY = ROOT / "E1/.venv/bin/python"


def esm_if(pdb_path: str, chain: str, sequence: str) -> dict:
    if not TORCH_PY.is_file():
        raise RuntimeError("Torch worker environment unavailable")
    arguments = {"pdb_path": pdb_path, "chain": chain, "sequence": sequence}
    process = subprocess.run([str(TORCH_PY), str(ROOT / "benchmark-mcp/esm_if_worker.py")],
                             input=json.dumps(arguments), text=True, capture_output=True, timeout=110)
    if process.returncode:
        raise RuntimeError(f"ESM-IF1 worker exited {process.returncode}: {process.stderr[-500:]}")
    return json.loads(process.stdout)
