"""Pre-registered Stage 3c sensor classification; utilization is diagnostic only."""

from __future__ import annotations

import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3c_2026-09-13"
GPU_TEMP_C = 76.0
GPU_TLIMIT_MARGIN_C = 20.0
CPU_TEMP_C = 85.0
MEM_AVAILABLE_GIB = 20.0
GPU_POWER_W = 100.0
FIELDS = ("gpu_util_pct", "gpu_c", "gpu_tlimit_margin_c", "gpu_power_w",
          "cpu_zone0_c", "cpu_zone4_c", "mem_available_gib")


def classify(sample: dict) -> str | None:
    """Return an abort reason; never classify on GPU utilization."""
    try:
        values = {key: float(sample[key]) for key in FIELDS}
    except (KeyError, ValueError, TypeError) as error:
        return f"required sensor unreadable: {error}"
    if not all(math.isfinite(value) for value in values.values()):
        return "required sensor non-finite"
    if values["gpu_c"] >= GPU_TEMP_C:
        return f"GPU temperature >= {GPU_TEMP_C:g} C"
    if values["gpu_tlimit_margin_c"] <= GPU_TLIMIT_MARGIN_C:
        return f"GPU T.Limit margin <= {GPU_TLIMIT_MARGIN_C:g} C"
    if max(values["cpu_zone0_c"], values["cpu_zone4_c"]) >= CPU_TEMP_C:
        return f"CPU thermal zone >= {CPU_TEMP_C:g} C"
    if values["mem_available_gib"] < MEM_AVAILABLE_GIB:
        return f"available shared memory < {MEM_AVAILABLE_GIB:g} GiB"
    if values["gpu_power_w"] >= GPU_POWER_W:
        return f"GPU power draw >= {GPU_POWER_W:g} W"
    return None


def run_controls() -> dict:
    baseline = {"gpu_util_pct": 20, "gpu_c": 43,
                "gpu_tlimit_margin_c": 53, "gpu_power_w": 10,
                "cpu_zone0_c": 45, "cpu_zone4_c": 45,
                "mem_available_gib": 95}
    cases = {
        "safe_baseline_passes": (baseline, False),
        "gpu_utilization_100_passes": ({**baseline, "gpu_util_pct": 100}, False),
        "gpu_temperature_threshold_trips": ({**baseline, "gpu_c": 76}, True),
        "gpu_margin_threshold_trips": ({**baseline, "gpu_tlimit_margin_c": 20}, True),
        "cpu_zone0_threshold_trips": ({**baseline, "cpu_zone0_c": 85}, True),
        "cpu_zone4_threshold_trips": ({**baseline, "cpu_zone4_c": 85}, True),
        "memory_floor_trips": ({**baseline, "mem_available_gib": 19.9}, True),
        "power_threshold_trips": ({**baseline, "gpu_power_w": 100}, True),
        "unreadable_power_trips": ({**baseline, "gpu_power_w": "[N/A]"}, True),
        "missing_sensor_trips": ({key: value for key, value in baseline.items()
                                   if key != "gpu_tlimit_margin_c"}, True),
    }
    results = {name: (classify(payload) is not None) == should_trip
               for name, (payload, should_trip) in cases.items()}
    body = {"results": results, "all_pass": all(results.values()),
            "thresholds": {"gpu_temp_c": GPU_TEMP_C,
                           "gpu_tlimit_margin_c": GPU_TLIMIT_MARGIN_C,
                           "cpu_temp_c": CPU_TEMP_C,
                           "mem_available_gib": MEM_AVAILABLE_GIB,
                           "gpu_power_w": GPU_POWER_W,
                           "gpu_utilization_gate": None}}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "watchdog_controls.json").write_text(json.dumps(body, indent=2) + "\n")
    if not body["all_pass"]:
        raise AssertionError("watchdog classifier controls failed")
    return body


if __name__ == "__main__":
    print(json.dumps(run_controls(), indent=2))
