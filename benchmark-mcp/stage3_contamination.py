"""Label-free W1 prompt leakage scan and deterministic recitation probe manifest."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import defaultdict

from stage3_w1 import OUT, REF, write_csv


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def grams(text: str) -> set[tuple[str, ...]]:
    words = tokens(text)
    return {tuple(words[i:i + 8]) for i in range(max(0, len(words) - 7))}


def prompt(sequence: str, mutants: list[str]) -> str:
    return ("You have a protein and candidate single substitutions. Your assay queue "
            "accepts ten. Choose ten variants, rank them, and state what evidence "
            "supports each choice and what would overturn it. Report variants you "
            "considered and rejected. Do not claim a measured assay outcome.\n\n"
            f"Protein sequence:\n{sequence}\n\nCandidate variants:\n"
            + ", ".join(mutants) + "\n")


def hidden_fragments(meta: dict) -> str:
    return "\n".join(meta[key] for key in ("title", "selection_assay", "selection_type",
                                                 "molecule_name", "source_organism") if meta.get(key))


def exact_hits(public: str, meta: dict) -> list[str]:
    haystack = public.lower()
    fields = ("DMS_id", "UniProt_ID", "pdb_file")
    return [key for key in fields if meta.get(key) and
            re.search(r"(?<![a-z0-9])" + re.escape(meta[key].lower()) +
                      r"(?![a-z0-9])", haystack)]


def main() -> None:
    metadata = {row["DMS_id"]: row for row in csv.DictReader(REF.open())}
    candidates = defaultdict(list)
    for row in csv.DictReader((OUT / "candidates_blind.csv").open()):
        candidates[row["assay_id"]].append(row["mutant"])
    cohort = {row["assay_id"]: row for row in csv.DictReader((OUT / "cohort.csv").open())
              if row["status"] == "ELIGIBLE"}
    prompts, rows = [], []
    for assay, variants in sorted(candidates.items()):
        meta = metadata[assay]
        text = prompt(meta["target_seq"], variants)
        overlap = grams(text) & grams(hidden_fragments(meta))
        identifiers = exact_hits(text, meta)
        prompts.append({"assay_id": assay, "cluster_50": cohort[assay]["cluster_50"],
                        "prompt": text})
        rows.append({"assay_id": assay, "cluster_50": cohort[assay]["cluster_50"],
                     "shared_eight_grams": len(overlap),
                     "exact_identifier_fields": ",".join(identifiers),
                     "source_title_words": len(tokens(meta.get("title", ""))),
                     "pre_2025_publication": int(meta["year"]) < 2025})
    if not prompts:
        raise SystemExit("no eligible probe prompts")
    with (OUT / "prompt_manifest.jsonl").open("w") as handle:
        for record in prompts:
            handle.write(json.dumps(record) + "\n")
    write_csv(OUT / "contamination.csv", rows, list(rows[0]))
    control = next(meta for meta in metadata.values() if len(tokens(meta.get("title", ""))) >= 8)
    eight_words = " ".join(tokens(control["title"])[:8])
    clean = "Synthetic control sentence with no assay metadata or identifiers."
    seeded = clean + " " + eight_words + " " + control["DMS_id"]
    negative_clean = not (grams(clean) & grams(hidden_fragments(control))) and \
        not exact_hits(clean, control)
    positive_eight = bool(grams(seeded) & grams(hidden_fragments(control)))
    positive_identifier = "DMS_id" in exact_hits(seeded, control)
    assert negative_clean and positive_eight and positive_identifier
    sample = sorted(prompts, key=lambda record: hashlib.sha256(
        record["assay_id"].encode()).hexdigest())[:20]
    with (OUT / "recitation_manifest.jsonl").open("w") as handle:
        for record in sample:
            handle.write(json.dumps(record) + "\n")
    summary = {"eligible_items": len(prompts),
               "items_with_eight_gram_overlap": sum(row["shared_eight_grams"] > 0 for row in rows),
               "items_with_exact_identifier": sum(bool(row["exact_identifier_fields"]) for row in rows),
               "pre_2025_publication_items": sum(row["pre_2025_publication"] for row in rows),
               "recitation_probe_items_selected": len(sample),
               "positive_eight_gram_control": positive_eight,
               "positive_identifier_control": positive_identifier,
               "negative_clean_control": negative_clean,
               "pretraining_corpus_overlap_checked": False}
    (OUT / "contamination_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
