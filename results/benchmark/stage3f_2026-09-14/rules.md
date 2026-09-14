# Stage 3f standing rules — panel amendment, 14 September 2026 UTC

The [Stage 3e rules](../stage3e_2026-09-14/rules.md) remain historical context. The 85 °C CPU safety abort is withdrawn; the earlier “must have a hardware-specified temperature threshold” language does **not** block a measurement-validity gate when firmware already protects hardware.

1. **A gate must protect against a named failure, and must not duplicate protection the hardware already provides.** For the single pilot cell, the named failure is unrepresentative timing under throttling; an unloaded, three-repeat model tokens/s baseline and a sustained 70% threshold protect measurement validity. Temperature, power, memory and utilization are reported, never abort thresholds.
2. **A tool must measure the quantity the task scores on.** A substitute is justified against the measurement, not against the tool it replaces.
3. **A served checkpoint is part of the tool's identity.** Record model size, immutable revision or content hash, device and precision. Change cache and receipt identity when a model changes. An 8M smoke model cannot silently stand in for a 650M scored tool.
4. **Not checked is not pass.** Every gate ships with an input/control that fails and one that passes. Interrupted work is `UNDEMONSTRATED`, never a zero-success result.
5. **Do not widen a definition to make it pass.** Count scarce independent units and report the decision metric, not ranking alone. Unknowns stay unknown; do not score the Stage 3f pilot cell or open labels.
