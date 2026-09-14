"""Pinned ProteinGym-sized ESM-2 masked-marginal worker (E1 Torch environment)."""

from __future__ import annotations

import json
import sys

import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

MODEL = "facebook/esm2_t33_650M_UR50D"
REVISION = "08e4846e537177426273712802403f7ba8261b6c"
AA = set("ACDEFGHIKLMNPQRSTVWY")


def score(sequence: str, position: int, mutant: str) -> dict:
    torch.set_num_threads(2)
    sequence = sequence.upper()
    mutant = mutant.upper()
    if not sequence or len(sequence) > 1022 or set(sequence) - AA:
        raise ValueError("sequence must be 1–1022 canonical residues")
    if not 1 <= position <= len(sequence) or len(mutant) != 1 or mutant not in AA:
        raise ValueError("position or mutant is invalid")
    tokenizer = AutoTokenizer.from_pretrained(MODEL, revision=REVISION)
    model = AutoModelForMaskedLM.from_pretrained(MODEL, revision=REVISION).eval()
    tokens = tokenizer(sequence, return_tensors="pt")
    input_ids = tokens["input_ids"].clone()
    input_ids[0, position] = tokenizer.mask_token_id
    with torch.inference_mode():
        logits = model(input_ids=input_ids, attention_mask=tokens["attention_mask"]).logits[0, position]
        log_probs = torch.log_softmax(logits.float(), dim=-1)
    wt = sequence[position-1]
    wt_id = tokenizer.convert_tokens_to_ids(wt)
    mut_id = tokenizer.convert_tokens_to_ids(mutant)
    wt_logp, mutant_logp = float(log_probs[wt_id]), float(log_probs[mut_id])
    return {"wt": wt, "mutant": mutant, "position": position,
            "wt_log_probability": wt_logp, "mutant_log_probability": mutant_logp,
            "delta_log_probability": mutant_logp-wt_logp,
            "method": "ESM2_single_position_masked_marginal_natural_log",
            "model": MODEL, "revision": REVISION, "device": "cpu", "precision": "float32"}


if __name__ == "__main__":
    arguments = json.load(sys.stdin)
    print(json.dumps(score(**arguments), allow_nan=False))
