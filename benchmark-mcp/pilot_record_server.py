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
    permitted = tuple((ROOT / f"results/benchmark/{stage}").resolve() for stage in
                      ("stage4pilot_2026-09-13", "stage3f_2026-09-14", "stage3g_2026-09-14"))
    if not any(parent in out.parents for parent in permitted):
        raise SystemExit("record output must be inside an explicit pilot/probe directory")
    out.mkdir(parents=True, exist_ok=True)
    record.OUT = out
    common.ARTIFACTS = out / "artifacts"
    common.CACHE = out / "cache"
    asyncio.run(make_record(args.presentation).run_stdio_async())


if __name__ == "__main__":
    main()
