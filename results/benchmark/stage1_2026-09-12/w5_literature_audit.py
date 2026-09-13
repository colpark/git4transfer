#!/usr/bin/env python3
"""Count distinct measured lanthanide-pair contrasts without row inflation."""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

OUT = Path(__file__).resolve().parent

# Kd,app in pM; second number is the published SD or parenthetic error.
# Within-study, same-protein and same-pH values only are compared.
STUDIES = {
    "CaMLBT_pH6": {
        "source": "https://doi.org/10.1002/ejic.202500468",
        "table": "Table 1 fluorescence, pH 6",
        "year": 2026,
        "values": {"La": (437,259),"Ce": (100,45),"Pr": (21.9,9.3),"Nd": (8.5,1.0),
                   "Sm": (6.3,1.2),"Eu": (4.5,1.2),"Gd": (7.2,2.6),"Tb": (1.6,.7),
                   "Dy": (2.9,.4),"Er": (10,8),"Tm": (2.4,.8),"Yb": (3.7,.5),
                   "Lu": (1.1,.4)},
    },
    "Mex_LanM_pH7p2": {
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13128445/",
        "table": "Supplementary Table 2, pH 7.2; omit La two-phase weighted average",
        "year": 2018,
        "values": {"Nd": (5.3,.6),"Sm": (6.6,2.8),"Gd": (10,.4),
                   "Tb": (21,.2),"Ho": (25,.4)},
    },
    "Hans_R100K_pH5": {
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13128445/",
        "table": "Supplementary Table 2, pH 5",
        "year": 2023,
        "values": {"La": (120,10),"Nd": (99,7),"Dy": (2700,400)},
    },
    "o36_pH5": {
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13128445/",
        "table": "Supplementary Table 2, pH 5",
        "year": 2026,
        "values": {"La": (389,91),"Nd": (44.7,4.1),"Sm": (39.5,7.7),"Dy": (249,52)},
    },
    "o127_pH5": {
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13128445/",
        "table": "Supplementary Table 2, pH 5",
        "year": 2026,
        "values": {"La": (662,72),"Nd": (187,25),"Sm": (280,31),"Dy": (1020,70)},
    },
    "o412_pH5": {
        "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC13128445/",
        "table": "Supplementary Table 2, pH 5; omit single-titration Gd",
        "year": 2026,
        "values": {"La": (11,1.4),"Pr": (6.8,.5),"Tb": (23,1),"Dy": (42,1.4)},
    },
    "Al_LanM_pH5": {
        "source": "https://doi.org/10.1021/jacs.6c08525.s001",
        "table": "Supplementary Table S1, 2-uM Al-LanM, pH 5",
        "year": 2026,
        "values": {"La": (14,1),"Pr": (8.7,4),"Sm": (27,3),"Gd": (80,3),
                   "Tb": (138,8),"Dy": (291,14),"Ho": (958,189)},
    },
    "Hans_LanM_pH5": {
        "source": "https://doi.org/10.1021/jacs.6c08525.s001",
        "table": "Supplementary Table S2 CD, pH 5",
        "year": 2026,
        "values": {"La": (68,7),"Nd": (91,6),"Sm": (240,40),"Gd": (404,21),
                   "Tb": (612,36),"Dy": (2600,700),"Ho": (3500,210)},
    },
    "Al_LanM_pH7": {
        "source": "https://doi.org/10.1021/jacs.6c08525.s001",
        "table": "Supplementary Table S3 WT Al-LanM, pH 7",
        "year": 2026,
        "values": {"La": (.75,.07),"Pr": (.60,.10),"Nd": (.80,.06),"Sm": (2,.2),
                   "Gd": (6.5,.5),"Tb": (7.7,.4),"Dy": (15,1),"Ho": (35,3)},
    },
}


def main() -> None:
    robust: dict[tuple[str, str], list[str]] = defaultdict(list)
    measured: set[tuple[str, str]] = set()
    for name, study in STUDIES.items():
        values = study["values"]
        for a, b in combinations(sorted(values), 2):
            measured.add((a,b))
            x, sx = values[a]
            y, sy = values[b]
            # Conservative *screen*, not a formal 95% confidence test:
            # published mean +/- two reported SDs must not overlap.
            if x + 2*sx < y - 2*sy or y + 2*sy < x - 2*sx:
                stronger = a if x < y else b
                robust[(a,b)].append(f"{name}:{stronger}")
    assert ("Ce", "Lu") in robust, "wide-separation positive control failed"
    assert ("Nd", "Sm") in measured, "measurement inventory failed"
    assert ("Eu", "Sm") not in robust, "near-equal negative control failed"
    structural = list(csv.DictReader((OUT / "w5_structural_pairs.csv").open(newline="")))
    fields = ["evidence_type", "independent_unit_key", "element_a", "element_b",
              "selectivity_ground_truth", "protein_or_sequence", "supporting_studies",
              "relative_affinity", "ree_pdb", "ca_pdb", "source", "limitation"]
    rows = [{
        "evidence_type": "pdb_exact_sequence_ca_ree",
        "independent_unit_key": "CA/"+r["element_b"],
        "element_a": "CA", "element_b": r["element_b"],
        "selectivity_ground_truth": "false",
        "protein_or_sequence": r["protein_sequence_sha256"],
        "supporting_studies": "", "relative_affinity": "",
        "ree_pdb": r["ree_pdb"], "ca_pdb": r["ca_pdb"],
        "source": r["source"], "limitation": r["limitation"],
    } for r in structural]
    rows += [{
        "evidence_type": "measured_Kdapp_2SD_nonoverlap",
        "independent_unit_key": a+"/"+b,
        "element_a": a, "element_b": b,
        "selectivity_ground_truth": "true",
        "protein_or_sequence": ";".join(x.split(":")[0] for x in supports),
        "supporting_studies": ";".join(supports),
        "relative_affinity": "lower Kd element after colon in each supporting_studies token",
        "ree_pdb": "", "ca_pdb": "",
        "source": ";".join(sorted({STUDIES[x.split(":")[0]]["source"] for x in supports})),
        "limitation": "shared ion measurements and related proteins make pair contrasts correlated",
    } for (a,b), supports in sorted(robust.items())]
    with (OUT / "w5_pairs.csv").open("w", newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=fields)
        writer.writeheader();writer.writerows(rows)
    summary = {
        "measurement_rule": "nonoverlap of mean +/- 2 published SD within same protein, pH and assay",
        "measured_unique_lanthanide_pairs": len(measured),
        "distinguishable_unique_lanthanide_pairs": len(robust),
        "structural_entry_pairs": len(structural),
        "structural_ca_ree_element_pairs": len({r["independent_unit_key"] for r in rows if r["evidence_type"].startswith("pdb")}),
        "structural_selectivity_ground_truth_pairs": 0,
        "full_length_protein_conditions": len(STUDIES),
        "controls": {"Ce/Lu_separated": "PASS", "Eu/Sm_near_equal_excluded": "PASS",
                     "duplicate_pair_across_proteins_collapsed": "PASS"},
    }
    (OUT / "w5_literature_summary.json").write_text(json.dumps(summary,indent=2)+"\n")
    print(json.dumps(summary,indent=2))


if __name__ == "__main__":
    main()
