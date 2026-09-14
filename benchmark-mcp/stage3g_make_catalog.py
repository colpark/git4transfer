"""Mechanically preserve Stage 3f's model instructions in registered metadata."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/benchmark/stage3f_2026-09-14/pilot_001/shim/shim_001_request.json"
TARGET = ROOT / "benchmark-mcp/stage3g_model_catalog.json"
source = json.loads(SOURCE.read_text())
instructions = source["instructions"]
assert instructions.startswith("You are a coding agent running in the Codex CLI")
catalog = json.loads(TARGET.read_text())
for model in catalog["models"]:
    model["base_instructions"] = instructions
TARGET.write_text(json.dumps(catalog, indent=2, ensure_ascii=False) + "\n")
print(json.dumps({"source": str(SOURCE), "target": str(TARGET),
                  "instruction_bytes": len(instructions.encode()),
                  "instruction_sha256": hashlib.sha256(instructions.encode()).hexdigest()}))
