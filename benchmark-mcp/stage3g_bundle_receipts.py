"""Bundle external Stage 2 receipt artifacts used by the new Stage 3g probes."""

import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3g_2026-09-14"
PHASES = ("echo7_surface", "fm7_surface", "cell7_surface_unguided",
          "cell7_surface_guided", "echo30_surface", "cell30_surface_unguided")
paths = set()


def collect(value):
    if isinstance(value, dict):
        receipt = value.get("receipt")
        if isinstance(receipt, dict) and isinstance(receipt.get("artifact_path"), str):
            paths.add(Path(receipt["artifact_path"]).resolve())
        for child in value.values():
            collect(child)
    elif isinstance(value, list):
        for child in value:
            collect(child)


collect(json.loads((OUT / "surface_controls.json").read_text()))
for phase in PHASES:
    trace = OUT / phase / "trace.jsonl"
    for line in trace.read_text().splitlines():
        event = json.loads(line)
        item = event.get("item", {})
        if item.get("type") != "mcp_tool_call":
            continue
        for block in (item.get("result") or {}).get("content", []):
            if block.get("type") == "text":
                try:
                    collect(json.loads(block["text"]))
                except json.JSONDecodeError:
                    pass

manifest = []
for source in sorted(paths):
    if not source.is_file() or ROOT not in source.parents or source.stat().st_size > 5_000_000:
        raise RuntimeError(f"receipt artifact missing or outside workspace: {source}")
    if OUT in source.parents:
        bundled = source
    else:
        bundled = OUT / "receipt_mirror" / source.parent.name / source.name
        bundled.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, bundled)
    manifest.append({"original": str(source), "bundled": str(bundled.relative_to(OUT)),
                     "sha256": hashlib.sha256(source.read_bytes()).hexdigest()})
(OUT / "receipt_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps({"receipts": len(manifest), "mirrored": sum("receipt_mirror/" in x["bundled"] for x in manifest)}))
