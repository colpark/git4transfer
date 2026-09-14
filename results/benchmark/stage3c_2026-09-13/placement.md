# Stage 3c GPU placement and tool-call thermal observation

**Disposition: one-tool reachability PASS; sustained envelope INTERRUPTED at
the predeclared GPU T.Limit margin gate.** Qwen2.5 7B Instruct Q4_K_M ran on
node 11 with 99 GPU layers, 32K configured context, batch 128, and two CPU
threads. Codex and the MCP echo server ran on node 10. The short and
W1-length probes each made exactly one genuine MCP call and cited a resolving
receipt. Their raw model replies used native structured `tool_calls`, which
the repaired bridge mapped correctly.

| Phase | Agent calls passing / attempted | Peak sampled GPU util | GPU temp, peak | CPU zone, peak | Minimum T.Limit margin | Max power | Min available memory |
|---|---:|---:|---:|---:|---:|---:|---:|
| 136-char short prompt | 1 / 1 | 93% | 53°C | 60.3°C | 37°C | 56.58 W | 88.760 GiB |
| 1,792-char W1-length echo context | 1 / 1 | 93% | 54°C | 62.3°C | 40°C | 54.15 W | 88.760 GiB |
| Sustained W1-length echo loop, ~403.7 s | **104 / 105**; last run interrupted | 95% | **69°C** | **82.4°C** | **20°C — gate fired** | 60.83 W | 88.703 GiB |

The per-phase windows are reconstructed from trace end times and recorded
run durations, with approximately two-second sensor samples; the raw samples
are in `watchdog_samples.jsonl`. The 104 completed loop attempts all passed
receipt and value audits. Attempt 105 obtained an MCP result but the watchdog
terminated the agent before it could finish/cite that receipt; it is
**UNDEMONSTRATED**, not a failed model call. The 10-minute checkpoint was not
reached, so the requested 10-minute sustained placement and 30-minute
tool-call envelope are **not certified**. The observed last-five-minute GPU
temperature median was 65°C, but it is not a 10- or 30-minute steady-state
temperature.

The frozen watchdog reported GPU utilization but did not gate on it. It
stopped at T.Limit headroom **≤20°C**, its declared margin to the device's
maximum operating limit. The other gates did not fire: GPU absolute
temperature remained below 76°C, CPU zones below 85°C, available memory
above 20 GiB, and GPU power below 100 W. High GPU utilization coincided with
lower CPU-zone temperatures than Stage 3's tool-free, mostly-CPU run, which
peaked at 84.4°C; this is a workload comparison, not an isolated causal
estimate.

After the stop, node 11 was checked at 0% GPU use, 56°C GPU, about 59.1°C
for each monitored ACPI zone, and no Stage 3c llama-server process. The
pre-existing Ollama service was not altered. No remount or model scoring ran
after the first thermal gate.
