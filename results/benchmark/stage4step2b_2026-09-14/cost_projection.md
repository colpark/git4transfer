# B4 wall-clock and quota projection (pipeline smoke, not performance)

The three B4 cells used Codex `gpt-5.6-sol` at high reasoning effort, one sample each. ARGR is the accepted Step 1 matched-control trace; AACC1 and ENVZ are the two new Step-2b attempts. Codex reports cached input as a subset of input, not an additional token total. No direct dollar charge or reliable per-cell dollar price is exposed on this authenticated ChatGPT-plan path.

| Sealed item | Wall seconds | Input tokens, including cache hits | Cached input tokens | Cache-write input tokens | Output tokens | Reasoning output tokens |
|---|---:|---:|---:|---:|---:|---:|
| ARGR | 413.588 | 753,312 | 685,696 | 0 | 15,943 | 7,437 |
| AACC1 | 929.156 | 1,006,510 | 921,728 | 0 | 8,947 | 3,017 |
| ENVZ | 1,154.817 | 1,693,148 | 1,589,504 | 0 | 19,521 | 5,611 |

Observed median wall clock: **929.156 s**; range: **413.588–1,154.817 s**. At one serial cell per scorable item, 145 items project to **37.4 wall-clock hours** (about 1.56 continuous days) at the median. Applying the observed minimum and maximum gives a descriptive **16.7–46.5-hour** range, not a confidence interval. The median-token analogue is about 146 million input tokens and 2.31 million output tokens for 145 cells; cache behavior and per-item difficulty can change both. AACC1 overlapped the separate-node Qwen smoke and the opening of ENVZ; ENVZ overlapped AACC1 briefly. These timings are measured end-to-end but not isolated single-cell throughput.

The authenticated Codex account's read-only rate-limit endpoint reported the `codex` seven-day window **49% used** at 2026-09-14 21:09 UTC, resetting 2026-09-19 15:30:29 UTC, with no extra credits. The meter moved from 48% to 49% during this smoke, but whole-percent rounding and unrelated usage prevent extrapolating calendar quota consumption per item. The full 145-cell run is therefore **not guaranteed to fit the remaining window**; quota-induced waiting time is unknown. The Claude Max weekly cap applies to the B1 fallback smoke, not to the chosen Codex B4 cohort harness. The account readout is preserved in `account_limits.json`.
