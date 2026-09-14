# Stage 4 pilot pre-envelope gate control

On 13 September 2026 EST, before the Stage 3d 30-minute envelope
file existed, `benchmark-mcp/.venv/bin/python benchmark-mcp/pilot_prepare.py`
exited with the explicit message `Stage 3d full-grant envelope is not on disk;
pilot selection forbidden`. No `selection.json` was written. This is the
must-fail control for the pilot-opening gate. The pilot remains closed until
the same command observes the completed Stage 3d controls, eight PASS
remounts, and a 30-minute envelope with `thirty_minute_envelope_pass: true`.
