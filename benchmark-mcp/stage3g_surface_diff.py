"""Mechanically preserve every MCP tool-description change for Stage 3g."""

import ast
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage3g_2026-09-14"
NEW = ROOT / "benchmark-mcp/server.py"
OLD = subprocess.check_output(["git", "-C", str(ROOT / "git4transfer"),
                               "show", "1a3cbd03e14ab2f8bd669e0efc636ecaaf42c4eb:benchmark-mcp/server.py"],
                              text=True)


def descriptions(code: str) -> dict[str, str]:
    result = {}
    for node in ast.walk(ast.parse(code)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not (isinstance(deco.func, ast.Attribute) and deco.func.attr == "tool"):
                continue
            name = next((kw.value.value for kw in deco.keywords
                         if kw.arg == "name" and isinstance(kw.value, ast.Constant)), None)
            if name:
                result[name] = ast.get_docstring(node) or ""
    return result


before = descriptions(OLD)
after = descriptions(NEW.read_text())
rows = [{"tool": name, "before": before.get(name), "after": after.get(name),
         "status": "ADDED" if name not in before else "CHANGED" if before[name] != after[name] else "UNCHANGED"}
        for name in sorted(set(before) | set(after))]
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "surface_description_diff.json").write_text(json.dumps(rows, indent=2) + "\n")
lines = ["# Item 1 — every W1 tool-description change, exact before/after",
         "", "Compared against the Stage 3g pre-rebuild server at commit `1a3cbd03`; schemas and implementation are described separately below.",
         "The descriptions below are our own code, not quotations from BioDesignBench. The released benchmark's provider uses short mechanism/output descriptions, category workflow guidance and cross-tool pointers; our adaptation makes the evidence channels explicit.", ""]
for row in rows:
    if row["status"] == "UNCHANGED":
        continue
    lines += [f"## `{row['tool']}` — {row['status']}", "",
              f"Before: {row['before'] or '(not exposed)' }", "",
              f"After: {row['after'] or '(removed)' }", ""]
lines += ["## Non-description surface changes", "",
          "`blast_msa` is a new unguided retrieval→alignment tool. It returns the exact query first and distinct BLAST-hit sequences globally aligned to query columns; it fails if no row passes the preregistered 80% coverage requirement. Guided `screen_variant_classical` now takes sequence, reference FASTA, position, one-letter mutant and max_hits, and chains BLAST→MSA→PSSM/conservation/BLOSUM. Guided `screen_variant_fm` remains its learned-channel counterpart, unchanged in computation. Neither scoring formula nor any assay label changed. A direct positive, malformed-mutant negative, and one-sequence conservation negative are in `surface_controls.json`.",
          "", "## Arm 3F paragraph — proposed, not applied to frozen prompts", "",
          "The request asks both to rewrite this paragraph and not to change prompts. The immutable pilot prompt and its manifest remain untouched; the following is a W1 adaptation for panel approval, **not** the text used in any run:", "",
          "> Consider the supplied variants as the candidate pool; do not invent new variants. Evaluate each shortlisted candidate across multiple complementary evidence categories, including learned and classical channels when granted, and record values for candidates you reject. Rank the supplied pool, then submit only the ten best-supported variants with auditable evidence and validation receipts. Do not submit unevaluated picks.",
          "", "The public design-task intervention instead requires at least five generated designs, four categories per design, a composite ranking and only three final sequences; copying those counts into a fixed 100-variant W1 task would change the task. If the panel adopts this proposed prompt, all eight pilot items must be discarded under the existing tuning-set rule. Separately, the executable tool-surface change already makes those eight pilot items non-comparable with future runs; discard them for the full-run analysis.", ""]
(OUT / "our_surface_diff.md").write_text("\n".join(lines))
print(json.dumps({"changed": sum(r["status"] == "CHANGED" for r in rows),
                  "added": sum(r["status"] == "ADDED" for r in rows),
                  "unchanged": sum(r["status"] == "UNCHANGED" for r in rows)}))
