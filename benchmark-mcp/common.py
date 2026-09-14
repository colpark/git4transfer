"""Common response, receipt, and content-addressed cache for Stage 2 MCP."""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage2_2026-09-12"
ARTIFACTS = OUT / "artifacts"
CACHE = OUT / "cache"


def emit(server: str, tool: str, args: dict[str, Any], compute: Callable[[], Any]) -> dict:
    """Never silently substitute a failed computation for a result."""
    started = time.monotonic()
    serialized = json.dumps({"server": server, "tool": tool, "args": args}, sort_keys=True,
                            separators=(",", ":"), allow_nan=False)
    args_hash = hashlib.sha256(serialized.encode()).hexdigest()
    cache_path = CACHE / server / f"{args_hash}.json"
    cache_hit = cache_path.exists() and json.loads(cache_path.read_text()).get("error") is None
    if cache_hit:
        body = json.loads(cache_path.read_text())
    else:
        try:
            body = {"result": compute(), "error": None}
        except Exception as exc:
            body = {"result": None, "error": f"{type(exc).__name__}: {exc}"}
        if body["error"] is None:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(json.dumps(body, sort_keys=True, allow_nan=False) + "\n")
    call_id = f"call_id:{uuid.uuid4().hex}"
    artifact_path = ARTIFACTS / server / f"{call_id.split(':')[1]}.json"
    artifact_path.parent.mkdir(parents=True, exist_ok=True)
    receipt = {"call_id": call_id, "tool": tool, "args_hash": args_hash,
               "runtime_s": round(time.monotonic() - started, 6),
               "artifact_path": str(artifact_path), "cache_hit": cache_hit}
    response = {**body, "receipt": receipt}
    artifact_path.write_text(json.dumps({"server": server, "args": args, **response},
                                        sort_keys=True, indent=2, allow_nan=False) + "\n")
    return response


def require_sequence(sequence: str, min_len: int = 1) -> str:
    seq = sequence.upper()
    if len(seq) < min_len or len(seq) > 10000 or set(seq) - set("ACDEFGHIKLMNPQRSTVWY"):
        raise ValueError("sequence must contain 1–10000 canonical amino acids")
    return seq


def reference_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if not path.is_file() or ROOT not in path.parents or path.stat().st_size > 10_000_000:
        raise ValueError("reference FASTA must be an existing <=10 MB workspace file")
    return path
