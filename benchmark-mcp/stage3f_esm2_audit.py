"""Label-blind checkpoint comparison on 20 frozen ProteinGym candidates."""

from __future__ import annotations

import csv
import json
import sys
import zipfile
from pathlib import Path

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

from esm2_worker import MODEL, REVISION
from stage3_evaluate import spearman

ROOT = Path(__file__).resolve().parents[1]
STAGE3 = ROOT / "results/benchmark/stage3_2026-09-13"
OUT = ROOT / "results/benchmark/stage3f_2026-09-14"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    candidates = list(csv.DictReader((STAGE3 / "candidates_blind.csv").open()))[:20]
    metadata = {r["DMS_id"]: r for r in csv.DictReader((STAGE3 / "input/DMS_substitutions.csv").open())}
    assay = candidates[0]["assay_id"]
    if any(r["assay_id"] != assay for r in candidates):
        raise RuntimeError("the frozen first 20 span more than one assay")
    wanted = {r["mutant"] for r in candidates}
    released = {}
    with zipfile.ZipFile(STAGE3 / "input/zero_shot_substitutions_scores.zip") as archive:
        with archive.open(assay + ".csv") as stream:
            reader = csv.DictReader(line.decode() for line in stream)
            for row in reader:
                if row["mutant"] in wanted:
                    released[row["mutant"]] = float(row["ESM2_650M"])
    if set(released) != wanted:
        raise RuntimeError("released scores missing")
    torch.set_num_threads(2)
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForMaskedLM.from_pretrained(MODEL, revision=REVISION).eval()
    sequence = metadata[assay]["target_seq"]
    tokens = tokenizer(sequence, return_tensors="pt")
    if len(sequence) > 1022:
        raise RuntimeError("unanticipated truncation")
    wt_ids = {aa: tokenizer.convert_tokens_to_ids(aa) for aa in set(sequence)}
    mut_ids = {aa: tokenizer.convert_tokens_to_ids(aa) for aa in {r["alt"] for r in candidates}}
    by_position = {}
    rows = []
    with torch.inference_mode():
        for row in candidates:
            position = int(row["position"])
            if sequence[position-1] != row["wt"]:
                raise RuntimeError("sequence/variant mismatch")
            if position not in by_position:
                masked = tokens["input_ids"].clone()
                masked[0, position] = tokenizer.mask_token_id
                logits = model(input_ids=masked, attention_mask=tokens["attention_mask"]).logits[0, position]
                by_position[position] = torch.log_softmax(logits.float(), dim=-1)
            lp = by_position[position]
            ours = float(lp[mut_ids[row["alt"]]] - lp[wt_ids[row["wt"]]])
            rows.append({"assay_id": assay, "mutant": row["mutant"], "esm2_650m_ours": ours,
                         "esm2_650m_released": released[row["mutant"]]})
    with (OUT / "esm2_20_candidate_audit.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    rho = spearman({r["mutant"]: r["esm2_650m_ours"] for r in rows},
                   {r["mutant"]: r["esm2_650m_released"] for r in rows})
    print(json.dumps({"assay": assay, "count": len(rows), "sequence_length": len(sequence),
                      "model": MODEL, "revision": REVISION, "spearman_rho": rho,
                      "audit_csv": str(OUT / "esm2_20_candidate_audit.csv")}), flush=True)


if __name__ == "__main__":
    main()
