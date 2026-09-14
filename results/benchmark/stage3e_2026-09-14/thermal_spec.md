# Item 1 — CPU thermal-trip read, 14 September 2026 UTC

**Host-scope correction:** the first reading at 02:47 UTC was inadvertently taken on agent/MCP node 10 (`spark-112b`, 192.168.100.10). It cannot establish the pilot-model host's trip points. The exact commands were repeated at 02:56 UTC over SSH on **model node 11** (`spark-0b70`, confirmed 192.168.100.11). The following are the **verbatim stdout/stderr from node 11**, in glob order; node 10 happened to return the same three outputs, but is not the basis for the disposition:

```text
$ cat /sys/class/thermal/thermal_zone*/type
acpitz
acpitz
acpitz
acpitz
acpitz
acpitz
acpitz

$ cat /sys/class/thermal/thermal_zone*/trip_point_*_type
cat: '/sys/class/thermal/thermal_zone*/trip_point_*_type': No such file or directory

$ cat /sys/class/thermal/thermal_zone*/trip_point_*_temp
cat: '/sys/class/thermal/thermal_zone*/trip_point_*_temp': No such file or directory
```

Both node-11 trip-point commands exited 1. A separate node-11 directory listing found **zero `trip_point_*` entries in each of the seven zones**. This is absence of a readable hardware trip, not evidence that no thermal protection exists.

NVIDIA's [Grace power and thermals guide](https://docs.nvidia.com/dccpu/grace-perf-tuning-guide/power-thermals.html) says shutdown follows a critical-temperature limit and shows the same sysfs trip-point read, but supplies **no readable GB10 CPU trip value for this machine**. The [DGX Spark hardware guide](https://docs.nvidia.com/dgx/dgx-spark/hardware.html) publishes 5–30°C *ambient* operating range and 140 W GB10 SoC TDP, not an 85°C CPU-junction trip. NVIDIA's [`nvidia-smi` field definitions](https://docs.nvidia.com/deploy/nvidia-smi/) call T.Limit a **GPU** margin to GPU maximum operating temperature; it cannot be used as a CPU-zone trip. On **node 11**, `nvidia-smi` showed GPU current 42°C and T.Limit 54°C, from which ~96°C GPU maximum is **inferred**, not a published GB10 CPU threshold.

**Disposition (c): trip points unreadable.** The old 85°C CPU abort was rounded up from the observed 84.4°C Stage 3 run, not sourced from hardware. The Stage 4 pilot was interrupted at 85.2°C by that arbitrary line; the interruption remains **UNDEMONSTRATED**, not a model failure. No replacement CPU gate is proposed from a guess. Do **not** run the single pilot cell or any further pilot workload until a published device specification, firmware/ACPI trip, or equivalent hardware-authoritative limit is made readable and reviewed. Keep the existing conservative stop in place for other diagnostic work; it is not relabeled as a hardware trip.
