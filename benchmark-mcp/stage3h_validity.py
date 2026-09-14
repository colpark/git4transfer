"""Per-response and cross-response active-generation throughput gates."""

from __future__ import annotations

WINDOW_S = 60.0
FRACTION = 0.70


def response_breach(tokens: int, seconds: float, baseline_tps: float) -> bool | None:
    if seconds < WINDOW_S:
        return None
    return tokens / seconds < FRACTION * baseline_tps


def session_windows(responses: list[dict], baseline_tps: float) -> list[dict]:
    """Check every 60-s window at response boundaries on active-time axis.

    llama.cpp exposes completion tokens and generation duration per completed
    response, not individual token timestamps. Each response is therefore a
    piecewise-constant-rate segment; no prompt prefill/tool wall time counts.
    """
    windows = []
    elapsed = 0.0
    segments = []
    for response in responses:
        seconds = float(response["generation_s"])
        tokens = int(response["generation_tokens"])
        if seconds <= 0:
            continue
        segments.append((elapsed, elapsed + seconds, tokens / seconds))
        elapsed += seconds
        if elapsed < WINDOW_S:
            continue
        left = elapsed - WINDOW_S
        total = sum(max(0.0, min(end, elapsed) - max(start, left)) * rate
                    for start, end, rate in segments)
        tps = total / WINDOW_S
        windows.append({"response": response.get("response"), "active_end_s": elapsed,
                        "active_start_s": left, "estimated_tps": tps,
                        "breach": tps < FRACTION * baseline_tps})
    return windows


def controls() -> dict:
    baseline = 100.0
    fast = {"response": "fast", "generation_s": 35.0, "generation_tokens": 3500}
    slow = {"response": "slow", "generation_s": 35.0, "generation_tokens": 1050}
    good = {"response": "good", "generation_s": 35.0, "generation_tokens": 3500}
    return {
        "per_response_synthetic_throttle_aborts": response_breach(4100, 60, baseline) is True,
        "per_response_healthy_passes": response_breach(4300, 60, baseline) is False,
        "per_response_short_is_unassessed": response_breach(100, 59, baseline) is None,
        "session_synthetic_throttle_aborts": session_windows([fast, slow], baseline)[-1]["breach"] is True,
        "session_healthy_passes": session_windows([fast, good], baseline)[-1]["breach"] is False,
        "session_short_is_unassessed": session_windows([fast], baseline) == [],
    }
