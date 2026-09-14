"""Pre-registered, CPU-only classical W1/W2 computations."""

from __future__ import annotations

import math
import os
import re
import subprocess
import tempfile
from collections import Counter
from pathlib import Path

from Bio.Align import PairwiseAligner, substitution_matrices
from Bio import SeqIO

from common import ROOT, reference_path, require_sequence

AA = "ACDEFGHIKLMNPQRSTVWY"
BLOSUM62 = substitution_matrices.load("BLOSUM62")
MMSEQS = ROOT / "biology-stack/mmseqs-gpu/bin/mmseqs"
BLASTP = ROOT / "biology-stack/ncbi-blast/usr/bin/blastp"
BLAST_LIB = ROOT / "biology-stack/ncbi-blast/usr/lib/ncbi-blast+"
BLAST_LIB_ARCH = ROOT / "biology-stack/ncbi-blast/usr/lib/aarch64-linux-gnu"


def _msa(query: str, msa: list[str], position: int) -> tuple[str, list[str]]:
    query = require_sequence(query)
    if not msa or msa[0] != query or any(len(row) != len(query) for row in msa):
        raise ValueError("MSA must have equal-length rows and exact query first")
    if not 1 <= position <= len(query):
        raise ValueError("position outside query")
    if any(set(row) - set(AA + "-") for row in msa):
        raise ValueError("MSA contains a noncanonical residue")
    if sum(1 for row in msa if row.count("-") <= .2 * len(query)) < 2:
        raise ValueError("MSA has fewer than two rows at >=80% coverage")
    column = [row[position - 1] for row in msa if row[position - 1] != "-"]
    if len(column) < 2:
        raise ValueError("MSA column depth below two")
    return query, column


def pssm_score(query: str, msa: list[str], position: int, mutant: str) -> dict:
    query, column = _msa(query, msa, position)
    mutant = require_sequence(mutant)
    if len(mutant) != 1:
        raise ValueError("mutant must be one amino acid")
    counts = Counter(column)
    depth = len(column)
    def score(aa: str) -> float:
        return math.log2(20 * (counts[aa] + 1) / (depth + 20))
    wt = query[position - 1]
    return {"position": position, "wt": wt, "mutant": mutant,
            "wt_bits": score(wt), "mutant_bits": score(mutant),
            "delta_bits": score(mutant) - score(wt), "depth": depth,
            "pseudocount_per_aa": 1, "background": 0.05}


def conservation(query: str, msa: list[str], position: int) -> dict:
    _, column = _msa(query, msa, position)
    depth = len(column)
    entropy = -sum((n/depth)*math.log2(n/depth) for n in Counter(column).values())
    return {"position": position, "conservation": 1 - entropy/math.log2(20),
            "entropy_bits": entropy, "depth": depth,
            "gap_fraction": 1 - depth/len(msa)}


def blosum_score(wt: str, mutant: str) -> dict:
    wt = require_sequence(wt)
    mutant = require_sequence(mutant)
    if len(wt) != 1 or len(mutant) != 1:
        raise ValueError("WT and mutant must each be one amino acid")
    return {"matrix": "BLOSUM62", "wt": wt, "mutant": mutant,
            "score": int(BLOSUM62[wt, mutant]),
            "zero_effect": wt == mutant}


def motif_scan(sequence: str, pattern: str) -> dict:
    sequence = require_sequence(sequence)
    if not pattern or len(pattern) > 128:
        raise ValueError("motif pattern must have 1–128 characters")
    compiled = re.compile(f"(?=({pattern}))")
    hits = [{"start": match.start() + 1, "end": match.start() + len(match.group(1)),
             "match": match.group(1)} for match in compiled.finditer(sequence)]
    return {"pattern": pattern, "hits": hits, "coordinate_system": "one_based_closed"}


def hbond_geometry(donor: list[float], hydrogen: list[float], acceptor: list[float]) -> dict:
    if any(len(v) != 3 or any(not math.isfinite(float(x)) for x in v)
           for v in (donor, hydrogen, acceptor)):
        raise ValueError("three finite XYZ coordinates are required")
    def dist(a: list[float], b: list[float]) -> float:
        return math.sqrt(sum((a[i]-b[i])**2 for i in range(3)))
    da, ha, dh = dist(donor, acceptor), dist(hydrogen, acceptor), dist(donor, hydrogen)
    if min(ha, dh) == 0:
        raise ValueError("coincident atoms make the angle undefined")
    cosine = sum((donor[i]-hydrogen[i])*(acceptor[i]-hydrogen[i])
                 for i in range(3))/(dh*ha)
    angle = math.degrees(math.acos(max(-1, min(1, cosine))))
    return {"donor_acceptor_A": da, "hydrogen_acceptor_A": ha,
            "dha_angle_deg": angle,
            "is_hbond": da <= 3.5 and ha <= 2.5 and angle >= 120}


def seq_identity(sequence_a: str, sequence_b: str) -> dict:
    a, b = require_sequence(sequence_a), require_sequence(sequence_b)
    aligner = PairwiseAligner(mode="global")
    aligner.substitution_matrix = BLOSUM62
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -0.5
    alignment = aligner.align(a, b)[0]
    aligned_a, aligned_b = str(alignment[0]), str(alignment[1])
    matches = sum(x == y and x != "-" for x, y in zip(aligned_a, aligned_b))
    return {"identity": matches / len(aligned_a), "matches": matches,
            "alignment_columns": len(aligned_a), "aligned_a": aligned_a,
            "aligned_b": aligned_b, "definition": "global_matches_over_all_columns"}


def _write_query(temp: Path, sequence: str) -> Path:
    path = temp / "query.fasta"
    path.write_text(f">query\n{require_sequence(sequence)}\n")
    return path


def mmseqs_search(sequence: str, reference_fasta: str, max_hits: int = 5) -> dict:
    target = reference_path(reference_fasta)
    if not MMSEQS.exists() or not 1 <= max_hits <= 100:
        raise ValueError("MMseqs executable missing or invalid max_hits")
    with tempfile.TemporaryDirectory(prefix="stage2_mmseqs_") as temp_s:
        temp = Path(temp_s)
        query = _write_query(temp, sequence)
        out = temp / "hits.tsv"
        command = [str(MMSEQS), "easy-search", str(query), str(target), str(out),
                   str(temp / "tmp"), "--threads", "1", "--format-output",
                   "query,target,pident,alnlen,evalue,bits,qcov,tcov", "--max-seqs", str(max_hits)]
        process = subprocess.run(command, text=True, capture_output=True, timeout=90)
        if process.returncode:
            raise RuntimeError(f"mmseqs exit {process.returncode}: {process.stderr[-300:]}")
        hits = []
        for line in out.read_text().splitlines()[:max_hits]:
            q, sid, pid, length, evalue, bits, qcov, tcov = line.split("\t")
            hits.append({"target": sid, "pident_pct": float(pid), "alignment_length": int(length),
                         "evalue": float(evalue), "bitscore": float(bits),
                         "query_coverage": float(qcov), "target_coverage": float(tcov)})
    return {"hits": hits, "reference_fasta": str(target)}


def blast_search(sequence: str, reference_fasta: str, max_hits: int = 5) -> dict:
    target = reference_path(reference_fasta)
    seq = require_sequence(sequence)
    if not BLASTP.exists() or not 1 <= max_hits <= 100:
        raise ValueError("BLASTP executable missing or invalid max_hits")
    with tempfile.TemporaryDirectory(prefix="stage2_blast_") as temp_s:
        query = _write_query(Path(temp_s), seq)
        command = [str(BLASTP), "-query", str(query), "-subject", str(target),
                   "-task", "blastp-short" if len(seq) < 30 else "blastp",
                   "-outfmt", "6 sseqid pident length evalue bitscore qcovs", "-max_target_seqs", str(max_hits)]
        environment = os.environ.copy()
        environment["LD_LIBRARY_PATH"] = ":".join(
            [str(BLAST_LIB), str(BLAST_LIB_ARCH), environment.get("LD_LIBRARY_PATH", "")])
        environment["BLASTDATADIR"] = str(ROOT / "biology-stack/ncbi-blast/usr/share/ncbi/data")
        process = subprocess.run(command, text=True, capture_output=True, timeout=90,
                                 env=environment)
        if process.returncode:
            raise RuntimeError(f"blastp exit {process.returncode}: {process.stderr[-300:]}")
        hits = []
        for line in process.stdout.splitlines()[:max_hits]:
            sid, pid, length, evalue, bits, qcov = line.split("\t")
            hits.append({"target": sid, "pident_pct": float(pid), "alignment_length": int(length),
                         "evalue": float(evalue), "bitscore": float(bits),
                         "query_coverage_pct": float(qcov)})
    return {"hits": hits, "reference_fasta": str(target)}


def blast_msa(sequence: str, reference_fasta: str, max_hits: int = 10) -> dict:
    """Retrieve BLAST hits and anchor their full sequences to the exact query."""
    query = require_sequence(sequence)
    search = blast_search(query, reference_fasta, max_hits)
    wanted = {hit["target"] for hit in search["hits"]}
    target = reference_path(reference_fasta)
    sequences = {record.id: require_sequence(str(record.seq)) for record in SeqIO.parse(target, "fasta")
                 if record.id in wanted}
    aligner = PairwiseAligner(mode="global")
    aligner.substitution_matrix = BLOSUM62
    aligner.open_gap_score = -10
    aligner.extend_gap_score = -0.5
    rows = [query]
    used = []
    for hit in search["hits"]:
        sid = hit["target"]
        subject = sequences.get(sid)
        if subject is None or subject == query:
            continue
        alignment = aligner.align(query, subject)[0]
        anchored = "".join(b for a, b in zip(str(alignment[0]), str(alignment[1])) if a != "-")
        if len(anchored) != len(query):
            raise RuntimeError("query-anchored alignment lost a query column")
        if anchored.count("-") <= .2 * len(query) and anchored not in rows:
            rows.append(anchored)
            used.append(sid)
    if len(rows) < 2:
        raise ValueError("BLAST produced fewer than two distinct >=80%-coverage MSA rows")
    return {"query": query, "msa": rows, "depth": len(rows), "hit_ids_used": used,
            "search_hits": search["hits"],
            "construction": "global_pairwise_query_anchored_drop_subject_insertions",
            "reference_fasta": str(target)}
