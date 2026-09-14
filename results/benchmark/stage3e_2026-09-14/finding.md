# Stage 3e — findings and stop

**14 September 2026 UTC. No Stage 4 or W2 run was opened.**

| Item | Result | Disposition |
|---|---|---|
| CPU thermal specification | On **model node 11**, seven `acpitz` zones expose zero readable `trip_point_*` files. An initial node-10 reading was superseded by the required node-11 repeat. NVIDIA publishes GPU T.Limit semantics and Spark ambient/TDP information, **not** this host's CPU trip. The 85°C abort came from an 84.4°C observation, not hardware. | **(c) trip unreadable**. No new CPU threshold; **no pilot recell**. The interrupted pilot remains UNDEMONSTRATED. |
| ESM-2 convention | Source masks the site, uses the whole supplied `target_seq`, and pins ESM-2 8M revision `c731040f...`. Twenty frozen same-assay candidates versus released ESM-2 650M give rank ρ **0.5578947368**. Deliberately unmasked A1R control differs. | **Matches masked-marginal scheme.** Track A resumed from its intact **1,507-call** checkpoint, not zero; no labels opened for this audit. 8M versus 650M remains a method difference. |
| W2 ruling | Option A accepted. OpenMM endpoint renamed `openmm_snapshot_potential_delta` and restricted to a structural diagnostic; no minimization, mutation modeling or ddG claim. PyRosetta blocked; Rosetta-style physics claim removed. | **W2 secondary and deferred until W1 result.** Small/absent Arm 3–Arm 2 gap preregistered. New endpoint name is **not recertified** and is not admitted as a scorer. |

The one-cell pilot retry was **not attempted** because disposition (a) did not clear. The 1,200-output-token harness cap therefore was **not applied or tested**; no `pilot_recell.md` is generated. The full 240-cell pilot and Stage 4 remain closed. No cohort or task spec was changed. The historical Stage 3 floors and Stage 2 certification are preserved; the new W2 endpoint requires separate MCP execution certification if ever mounted in a future scored run.

**Recommendation to panel/hardware owner:** obtain a published GB10 CPU-junction limit or expose the firmware/ACPI passive, active or critical trip point; only then specify a margin and decide whether the single interrupted pilot cell can be rerun. Track A can continue its label-blind CPU recomputation under its existing conservative operational stop, but that 83°C stop is **not** called a hardware-derived trip.
