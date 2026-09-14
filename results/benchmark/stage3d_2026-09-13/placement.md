# Stage 3d full-grant placement and thermal envelope

Status: **PASS**. Stop reason: none. Elapsed 1810.67 s; 430/430 agent echo runs passed.

Measured active-agent duty cycle: 0.952 (sum of agent-run wall times / envelope elapsed, including thermal waits). This is not model-only GPU duty cycle.

| Metric | Peak/worst sampled | Last-five-minute median | Gate |
|---|---:|---:|---:|
| GPU temperature | 71.0°C | 66.0°C | <76°C |
| GPU T.Limit margin | 20.0°C | 31.0°C | >10°C |
| CPU zone maximum | 83.9°C | 73.5°C | <85°C |
| GPU power draw | 58.73 W | 35.65 W | <100 W |
| Available shared memory | 88.264 GiB | 88.303 GiB | ≥20 GiB |
| GPU utilization (reported only) | 95% | 90% | none |

Raw timestamped samples are in `watchdog_samples.jsonl`. The latest five minutes describe this observed workload only; no temperature is extrapolated beyond it. Within the same window, 71 samples had GPU utilization ≥50%; their median GPU temperature was 67.0°C, CPU-zone maximum 76.9°C, and GPU power 50.65 W.
