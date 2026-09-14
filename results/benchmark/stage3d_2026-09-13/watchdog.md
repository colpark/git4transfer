# Stage 3d watchdog amendment — frozen before inference

Frozen 13 September 2026, 19:50 EST (14 September 00:50 UTC), before the
Stage 3d model run. The panel lowers the GPU T.Limit margin gate from 20°C to
10°C. All other Stage 3c gates and the sensor-failure stop are unchanged.
Node 11 is the Qwen model host; node 10 runs the agent and MCP servers.
Audit note: at 00:53 UTC the local EST clock label was corrected from
"20:50" to "19:50"; the UTC freeze time, thresholds, and classifier were
unchanged. The pre-inference synthetic control file records those thresholds.

| Quantity | Gate | Source |
|---|---|---|
| GPU utilization | Report, never abort | Panel ruling: utilization is a placement/duty-cycle statistic. |
| GPU temperature | Abort at **≥76°C** | Panel ruling; `nvidia-smi` sensor. |
| GPU T.Limit margin | Abort at **≤10°C** | Panel amendment; device `nvidia-smi` reports relative margin to maximum operating temperature, not an absolute temperature. Prior stop at margin 20°C occurred at GPU 69°C. [NVIDIA field definitions](https://docs.nvidia.com/deploy/nvidia-smi/). |
| CPU thermal zone 0 or 4 | Abort at **≥85°C** | Panel unchanged; `/sys/class/thermal/thermal_zone{0,4}/temp`. |
| Available memory | Abort at **<20 GiB** | Panel unchanged; `/proc/meminfo` `MemAvailable`. |
| GPU power draw | Abort at **≥100 W** | Panel unchanged; `nvidia-smi` `power.draw`. This is a project cap, not a vendor GPU power limit. |
| Missing or unreadable required sensor | Abort | Not checked is not pass. |

The GPU absolute and margin gates are both retained as specified even though
the absolute gate is likely to fire first at the observed inferred maximum
of about 96°C. The CPU cooling waits remain: after a completed call, 5 s if
the latest CPU zone is ≥82°C, or 15 s if ≥83.5°C. The 85°C hard stop remains.
The controls must show each gate fires at its boundary, a 10.1°C margin does
not fire by itself, and 100% utilization with otherwise safe sensors passes.
Save the control result before starting the model; no threshold is changed
during the run.
