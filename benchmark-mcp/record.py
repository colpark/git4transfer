"""Stage 2 record tools; do not score or adjudicate submitted answers."""

from __future__ import annotations

import json
import re
import uuid

from common import OUT


def _item_id(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,120}", value):
        raise ValueError("item_id must be 1–120 safe characters")
    return value


def submit_answer(item_id: str, answer: dict) -> dict:
    item_id = _item_id(item_id)
    if not answer or not isinstance(answer, dict):
        raise ValueError("answer must be a nonempty JSON object")
    path = OUT / "submissions" / f"{item_id}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ValueError("item_id has already been submitted")
    path.write_text(json.dumps({"item_id": item_id, "answer": answer}, sort_keys=True,
                               indent=2, allow_nan=False) + "\n")
    return {"accepted": True, "item_id": item_id, "submission_path": str(path)}


def log_note(item_id: str, note: str) -> dict:
    item_id = _item_id(item_id)
    if not note.strip() or len(note) > 2000:
        raise ValueError("note must be nonempty and at most 2000 characters")
    path = OUT / "notes" / f"{item_id}_{uuid.uuid4().hex}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"item_id": item_id, "note": note}, sort_keys=True) + "\n")
    return {"logged": True, "item_id": item_id, "note_path": str(path)}

