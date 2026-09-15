"""Produce the label-free Stage 4 Step 3b stable-context diagnosis.

This script reads only the frozen context calibrations, the three named B4
traces, and the Codex rollout files referenced by those traces.  It does not
read labels, validate answers, score submissions, or invoke a model.
"""

from __future__ import annotations

import difflib
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "results/benchmark/stage4step3_2026-09-14"
DEST = ROOT / "results/benchmark/stage4step3b_2026-09-15"
ITEMS = ("cmp_004", "cmp_008", "cmp_009")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def rollout_for_trace(trace: Path) -> tuple[Path, list[dict]]:
    events = [json.loads(line) for line in trace.read_text().splitlines() if line.strip()]
    thread_ids = {event.get("thread_id") for event in events if event.get("type") == "thread.started"}
    if len(thread_ids) != 1:
        raise RuntimeError(f"{trace}: expected exactly one thread id")
    thread_id = next(iter(thread_ids))
    matches = list((Path.home() / ".codex/sessions").rglob(f"*{thread_id}.jsonl"))
    if len(matches) != 1:
        raise RuntimeError(f"{trace}: expected exactly one rollout for {thread_id}")
    path = matches[0]
    return path, [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def context(trace: Path) -> dict:
    rollout_path, rollout = rollout_for_trace(trace)
    session = next(event["payload"] for event in rollout if event.get("type") == "session_meta")
    turn = next(event["payload"] for event in rollout if event.get("type") == "turn_context")
    developers: list[str] = []
    for event in rollout:
        payload = event.get("payload") or {}
        if (event.get("type") == "response_item" and payload.get("type") == "message"
                and payload.get("role") == "developer"):
            developers.append("".join(
                part.get("text", "") for part in payload.get("content", [])
                if isinstance(part, dict)
            ))
    base = (session.get("base_instructions") or {}).get("text", "")
    return {
        "rollout_path": str(rollout_path),
        "base": base,
        "base_sha256": sha_text(base),
        "developers": developers,
        "developer_sha256": [sha_text(text) for text in developers],
        "cli_version": session.get("cli_version"),
        "sandbox_type": (turn.get("sandbox_policy") or {}).get("type"),
        "approval_policy": turn.get("approval_policy"),
    }


def fenced(text: str) -> str:
    fence = "````"
    return f"{fence}text\n{text}{'' if text.endswith(chr(10)) else chr(10)}{fence}\n"


def main() -> None:
    pinned_doc = json.loads((SOURCE / "context_calibration.json").read_text())
    pinned = pinned_doc["stable_context"]
    calibration = context(SOURCE / "runs/b4_context_calibration/trace.jsonl")
    active_doc = json.loads((SOURCE / "release_requirements.json").read_text())
    active = active_doc["expected_stable_context"]
    resume = context(SOURCE / "runs/b4_context_calibration_2026-09-15/trace.jsonl")
    cells = {
        item: context(SOURCE / f"runs/b4/{item}/trace.jsonl")
        for item in ITEMS
    }

    if calibration["base_sha256"] != pinned["base_instructions_sha256"]:
        raise RuntimeError("original calibration rollout does not reproduce context_calibration.json")
    if calibration["developer_sha256"] != pinned["developer_message_sha256"]:
        raise RuntimeError("original developer messages do not reproduce context_calibration.json")
    if resume["base_sha256"] != active["base_instructions_sha256"]:
        raise RuntimeError("resume calibration rollout does not reproduce active base pin")

    expected_controls = {
        "cli_version": pinned["cli_version"],
        "sandbox_type": pinned["sandbox_type"],
        "approval_policy": pinned["approval_policy"],
    }
    for item, cell in cells.items():
        if cell["base"] != calibration["base"]:
            raise RuntimeError(f"{item}: base differs from context_calibration.json text")
        if cell["developers"] != calibration["developers"]:
            raise RuntimeError(f"{item}: developer messages differ from context_calibration.json texts")
        if any(cell[key] != value for key, value in expected_controls.items()):
            raise RuntimeError(f"{item}: runtime controls differ from context_calibration.json")

    diff = "".join(difflib.unified_diff(
        resume["base"].splitlines(keepends=True),
        calibration["base"].splitlines(keepends=True),
        fromfile="active-gate/context_calibration_2026-09-15.base_instructions",
        tofile="received/context_calibration.base_instructions",
    ))
    expected_diff = (
        "--- active-gate/context_calibration_2026-09-15.base_instructions\n"
        "+++ received/context_calibration.base_instructions\n"
        "@@ -111,7 +111,7 @@\n"
        " \n"
        " If completion requires new authority, external coordination, or a meaningful expansion beyond the user’s implied intent and task scope (e.g. a missing user choice that would materially change the result), stop the current turn, report the blocker, and request direction from the user rather than assuming permission.\n"
        " \n"
        "-# Destructive Actions\n"
        "+# Destructive actions\n"
        " \n"
        " Be cautious with commands or API calls that can delete, overwrite, or otherwise make data difficult to recover.\n"
        " \n"
    )
    if diff != expected_diff:
        raise RuntimeError(f"unexpected base-instructions diff:\n{diff}")

    lines = [
        "# Stage 4 Step 3b: stable-context gate diagnosis",
        "",
        "## Scope and evidence boundary",
        "",
        "This diagnosis was completed before validation, scoring, or any label access. It reads only "
        "`context_calibration.json`, the later resume calibration and active release requirement needed "
        "to explain the recorded rejection, the three named public traces, and the rollout records "
        "identified by those traces. No model was called.",
        "",
        "The premise that `developer_message_sha256` lists three permitted alternatives is not what the "
        "record or validator implements. It is an ordered fingerprint of **three separate developer "
        "messages** received in one run. The validator requires exact equality of the whole three-hash "
        "array. All three cells reproduce all three hashes in the same order.",
        "",
        "## Per-cell findings",
        "",
        "| cell | base SHA-256 | matches `context_calibration.json` | developer hashes matching ordered pins | cli | sandbox | approval |",
        "|---|---|---:|---|---|---|---|",
    ]
    for item, cell in cells.items():
        hashes = "<br>".join(f"{idx + 1}. `{value}`" for idx, value in enumerate(cell["developer_sha256"]))
        lines.append(
            f"| {item} | `{cell['base_sha256']}` | yes | {hashes} | "
            f"`{cell['cli_version']}` | `{cell['sandbox_type']}` | `{cell['approval_policy']}` |"
        )
    lines.extend([
        "",
        f"Pinned base SHA-256: `{pinned['base_instructions_sha256']}`.",
        "",
        "Pinned ordered developer-message SHA-256 values:",
        "",
    ])
    lines.extend(f"{idx + 1}. `{value}`" for idx, value in enumerate(pinned["developer_message_sha256"]))
    lines.extend([
        "",
        "There is therefore no non-matching base or developer text relative to "
        "`context_calibration.json`, and no diff is applicable against that calibration.",
        "",
        "## Why the recorded gate nevertheless fired",
        "",
        "Before these cells were validated, `release_requirements.json.expected_stable_context` had been "
        "replaced from the original calibration with `context_calibration_2026-09-15.json`. The active "
        f"base pin was `{active['base_instructions_sha256']}`, while every rejected cell received "
        f"`{pinned['base_instructions_sha256']}`. The developer-message array and all three runtime "
        "controls remained identical. This substituted base pin—not any developer message—caused the "
        "raw-object inequality in the validator.",
        "",
        "Literal diff of the only non-matching received text against the active permitted text:",
        "",
        "```diff",
        diff.rstrip("\n"),
        "```",
        "",
        "## Classification",
        "",
        "**COSMETIC**",
        "",
        "The complete literal delta changes only the capitalization of the word `Actions` in a Markdown "
        "heading. It changes no instruction sentence, tool list, grant, runtime control, or "
        "behaviour-affecting text. The trace carries the complete texts and therefore provides enough "
        "evidence to classify the delta without inference.",
        "",
        "## Verbatim received texts",
        "",
        "The following texts are byte-identical in `cmp_004`, `cmp_008`, and `cmp_009`; their per-cell "
        "hashes above were computed independently. They are printed once to avoid disguising equality "
        "with three redundant copies.",
        "",
        "### Base instructions received by each cell",
        "",
        fenced(calibration["base"]).rstrip("\n"),
    ])
    for idx, text in enumerate(calibration["developers"], start=1):
        lines.extend([
            "",
            f"### Developer message {idx} received by each cell",
            "",
            fenced(text).rstrip("\n"),
        ])
    lines.append("")

    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "gate_diagnosis.md").write_text("\n".join(lines))
    print(DEST / "gate_diagnosis.md")


if __name__ == "__main__":
    main()
