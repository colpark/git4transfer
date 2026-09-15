# Stable-context gate reflection

## (a) Named failure prevented

**Threat:** The agent receives behaviour-affecting instructions, a different tool list or grant, or different sandbox/approval controls on different cells, so the nominal B4 arm is not one arm and its results are not comparable.

The raw hash is only a proxy for this threat. The stop condition should be: **stop when the normalized received contexts differ in any behaviour-affecting instruction, ordered developer message, tool/grant content, CLI identity, sandbox type, or approval policy.**

## (b) Did a fourth developer hash constitute the failure?

No fourth developer-message hash exists in the three cells. `developer_message_sha256` is an ordered array of three simultaneously received developer messages, not three alternative permitted variants. Every cell exactly matched all three values in order. The only mismatch used by the active validator was the base-instructions SHA-256. Its complete diff was one heading-capitalization character and did not instantiate the named threat.

## (c) Why three rather than one?

The record shows three distinct developer-message layers: (1) skills and permission instructions, (2) `/root` team-agent instructions, and (3) the multi-agent delegation restriction. `stage4step3_run.py` collects every received developer message and hashes the resulting ordered list. No record states a rationale for the number three, and no record describes the hashes as alternatives. Therefore the reason for “three permitted variants” is **not recorded because that configuration did not exist**.

## (d) Normalized context

Yes, the gate should compare the instruction-bearing quantity after an exact, reviewable normalization. For this recovery the normalization is deliberately narrow:

1. Split base instructions into lines without otherwise changing bytes.
2. Canonicalize an exact whole line equal to `# Destructive actions` or `# Destructive Actions` to `# Destructive Actions`.
3. Leave every other base-instruction byte unchanged.
4. Leave every developer-message byte and its ordered position unchanged.
5. Compare `cli_version`, `sandbox_type`, and `approval_policy` by exact equality.
6. Hash the canonical object formed from the normalized base hash, ordered raw developer hashes, and those three exact runtime controls.

No general case-folding, whitespace deletion, path stripping, or regular-expression removal is allowed: those operations could hide a changed tool path or instruction. Session/thread IDs and timestamps were never part of this gate object; `turn_context.cwd` was also not included. If a future stable instruction field embeds a run-varying value, it must first be structurally named and shown by a must-fire control not to carry instruction content before being added to normalization.

## (e) Control status

The original gate shipped with **no context mutation control** in `test_stage4step2e.py`; its tests cover answer contracts, trace pairing, bound inputs, checkpoints, and tool surfaces. Therefore the original context gate was **not checked**, not passed. The later live rejection is an incident, not a prospective control.

The repaired gate ships with one positive cosmetic control and five must-fire controls. All 6 passed: a changed instruction sentence, developer message, CLI version, sandbox type, and approval policy each fire the repaired gate. See `gate_controls.json`.
