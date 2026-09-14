# Served foundation-model checkpoint inventory

14 September 2026 UTC, inspected from worker code and local checkpoint files.

| Tool | Served checkpoint | Pinned identity | Local precision/device | Smoke placeholder? |
|---|---|---|---|---|
| `esm2_likelihood` | ESM-2 t33, **650M** | Hugging Face revision `08e4846e537177426273712802403f7ba8261b6c` | CPU float32 | **No**; upgraded from the Stage 2 t6 8M smoke model. |
| `esm_if` | ESM-IF1 `esm_if1_gvp4_t16_142M_UR50`, **142M** as named by upstream | Local `.pt` SHA-256 `be4ba36edec22a9bfaa4946ff6b2815f1f19d8a3d7e0eada8b796d5a0eae9fd4` (1.6 GiB file); no upstream git revision exposed by `fair-esm` loader | CPU; Torch default float32 | No smaller test checkpoint found; this is the named ESM-IF1 release. Upstream revision remains unknown, content hash is the reproducible identity. |
| `esmfold` | `facebook/esmfold_v1`, configured `esm2_3B` language-model backbone (36 layers, width 2560) | Hugging Face revision `75a3841ee059df2bf4d56688166c8fb459ddd97a` (7.9 GiB checkpoint file) | Worker selects device at runtime; default Torch model precision | No; ESMFold v1 production checkpoint, not an 8M substitute. |

The ESM-IF1 model is not yet content-hash-checked inside each worker call. The hash above identifies the **currently served local file**, not an asserted upstream git revision. The 650M ESM-2 cache/receipt identity is enforced in code; changes to any other served checkpoint must likewise invalidate its tool cache before a scored run.
