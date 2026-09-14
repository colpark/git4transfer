# Prompt-only instruction ruling

14 September 2026. B1 and B2 are each split into an `a` condition with the exact sentence “Do not use foundation models.” and a `b` condition without it. The only difference in the user prompt is that sentence. This is an instruction variable, not a tool-access restriction or a claim about what the pretrained weights contain. No foundation-model server, MCP server, native tool, shell, or network-fetch tool is to be supplied to either condition. A prompt-only answer is one model turn and plain JSON, not a record-server call.

Carry this disclosure **verbatim** wherever B1 or B2 appears:

> "No foundation model was reachable in this condition. The instruction not to use foundation models could not be enforced and was not verified. It is reported as an instruction-compliance variable, not a capability control."

The sentence cannot remove knowledge already internalized by a model, and this stage does not claim to verify whether that knowledge influenced its ranking. Compare `a` against `b` only when both use the same model, same item, same serving point, and identical parser. Do not interpret a different item as an instruction effect.
