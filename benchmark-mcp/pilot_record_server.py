"""Per-run record mount without changing the certified record tool contract."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import record
import common
from common import ROOT
from server import make_record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--presentation", choices=("guided", "unguided"), required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    pilot = (ROOT / "results/benchmark/stage4pilot_2026-09-13").resolve()
    if pilot not in out.parents:
        raise SystemExit("record output must be inside the Stage 4 pilot directory")
    out.mkdir(parents=True, exist_ok=True)
    record.OUT = out
    common.ARTIFACTS = out / "artifacts"
    common.CACHE = out / "cache"
    asyncio.run(make_record(args.presentation).run_stdio_async())


if __name__ == "__main__":
    main()
