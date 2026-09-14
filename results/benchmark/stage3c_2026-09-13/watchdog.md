# Stage 3c watchdog pre-registration

Frozen **13 September 2026, 23:57 UTC**, before any Stage 3c model run.
Node 11 (`spark-0b70`, NVIDIA GB10) was idle at GPU 43°C, T.Limit headroom
53°C, GPU utilization 0%, GPU power draw about 10.3 W, ACPI thermal zones 0
and 4 at 45.1°C, and 95 GiB available shared memory. Agent/MCP remain on
node 10; only the exact Stage 3c model process may be terminated by this
watchdog. Samples are to be saved with timestamps at roughly two-second
intervals. A failed sensor read aborts the owned run; it is not a pass.

| Quantity | Gate | Source and rationale |
|---|---|---|
| GPU utilization | **Report only; no gate.** | The 90% abort is withdrawn by the panel. Busy GPU is evidence of placement, not overheating. Record peak and steady-state distribution. |
| GPU temperature | Abort at **≥76°C**, or at **T.Limit headroom ≤20°C**, whichever occurs first. | `nvidia-smi -q -d TEMPERATURE` on this device reported current 43°C and T.Limit margin 53°C, implying max operating temperature about 96°C. T.Limit is a *relative margin*, not an absolute 53°C limit, per [NVIDIA's nvidia-smi documentation](https://docs.nvidia.com/deploy/nvidia-smi/). The gate holds at least a declared 20°C margin to the inferred max operating limit. The absolute 76°C check is a redundant fail-safe if the reported margin changes. Device shutdown and slowdown T.Limit specifications are −5°C and −2°C relative to max operating, not 5°C/2°C absolute temperatures. |
| CPU thermal zones | Abort if either `/sys/class/thermal/thermal_zone0` or `thermal_zone4` reads **≥85°C**. | The existing Stage 2b/3 threshold and panel instruction. Both report `acpitz` on this host; treat them as the project's CPU-adjacent thermal proxy, not a validated per-core die sensor. Stage 3 tool-free generation reached 84.4°C, motivating the unchanged limit. |
| Available shared memory | Abort if `/proc/meminfo` `MemAvailable` is **<20 GiB**. | Predeclared operational floor carried from the Stage 3b runner, leaving space for the OS and pre-existing services in the 119 GiB reported system memory. This is a conservative project floor, not a device hardware trip point. |
| GPU power draw | Abort if `nvidia-smi` `power.draw` is **≥100 W**; unreadable is a sensor failure. | This device reports draw but `power.limit` is `N/A`. The 100 W threshold is a conservative *project* cap, not a published GPU power limit: it leaves 40 W below the GB10 SoC's 140 W TDP listed in the [NVIDIA DGX Spark hardware guide](https://docs.nvidia.com/dgx/dgx-spark/hardware.html). GPU-reported draw and whole-SoC TDP are not identical quantities; retain that caveat. NVIDIA states the one-second board-power reading has about ±5 W accuracy in its [nvidia-smi field documentation](https://docs.nvidia.com/deploy/nvidia-smi/). |

**Must-fail controls before live inference:** a synthetic sample at each
temperature, memory and power threshold must trip the classifier; a synthetic
100% GPU-utilization sample with otherwise safe sensors must *not* trip it;
missing/unparseable sensor input must trip it. Save results to
`watchdog_controls.json`. The earlier four utilization stops are evidence that
the old guard measured the wrong quantity, not failed model calls.

The intended model operating point starts with Qwen2.5 7B Q4_K_M and 32K
configured context on node 11. GPU-bound inference should reduce sustained
CPU work here, but that is a hypothesis to be tested against the measured
temperatures, not an exemption from either gate. An interrupted probe is
UNDEMONSTRATED, never zero-percent model capability.

For a sustained loop, the predeclared cooling duty cycle is: after a completed
tool call, wait 5 seconds if the latest CPU-zone reading is at least 82°C,
or 15 seconds if at least 83.5°C; otherwise proceed immediately. The hard
85°C abort is unchanged. Report active-call time divided by elapsed time,
including these waits. The same loop uses a label-blind W1-length context
only to impose prompt load; it does not rank or score variants.
