"""Stage 2 W1/W2 MCP servers. Classical is deliberately registered first."""

from __future__ import annotations

import argparse
import asyncio

from mcp.server.mcpserver import MCPServer

from common import emit
import classical
import analysis
import record
import physics
import lit
import predictive
import generative


def make_classical(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-classical", version="0.1.0")

    @mcp.tool(name="mmseqs_search")
    def mmseqs_search(sequence: str, reference_fasta: str, max_hits: int = 5) -> dict:
        """RETRIEVE: MMseqs2 homolog IDs and alignment statistics, not sequences. Use blast_msa for query-anchored rows before pssm_score or conservation; compare learned esm2_likelihood separately."""
        args = locals()
        return emit("classical", "mmseqs_search", args,
                    lambda: classical.mmseqs_search(**args))

    @mcp.tool(name="blast_search")
    def blast_search(sequence: str, reference_fasta: str, max_hits: int = 5) -> dict:
        """RETRIEVE: BLASTP homolog IDs and alignment statistics, not MSA rows. Use blast_msa to retrieve and align sequences for pssm_score or conservation; avoid repeating identical calls."""
        args = locals()
        return emit("classical", "blast_search", args,
                    lambda: classical.blast_search(**args))

    @mcp.tool(name="blast_msa")
    def blast_msa(sequence: str, reference_fasta: str, max_hits: int = 10) -> dict:
        """RETRIEVE→ANALYSE: BLASTP hits plus distinct query-anchored homolog rows, query first. Pass result.msa and result.query to pssm_score or conservation; no fitness label is used."""
        args = locals()
        return emit("classical", "blast_msa", args,
                    lambda: classical.blast_msa(**args))

    @mcp.tool(name="pssm_score")
    def pssm_score(query: str, msa: list[str], position: int, mutant: str) -> dict:
        """SCORE, classical evolutionary evidence: substitution log-odds from aligned homologs. Supply full query, one-letter mutant and blast_msa rows; compare orthogonal learned esm2_likelihood, not measured fitness."""
        args = locals()
        return emit("classical", "pssm_score", args,
                    lambda: classical.pssm_score(**args))

    @mcp.tool(name="conservation")
    def conservation(query: str, msa: list[str], position: int) -> dict:
        """ANALYSE, classical site evidence: normalized Shannon conservation of a homolog MSA column. Use blast_msa rows; one sequence fails. Not mutation-specific; pair with pssm_score and learned esm2_likelihood."""
        args = locals()
        return emit("classical", "conservation", args,
                    lambda: classical.conservation(**args))

    @mcp.tool(name="motif_scan")
    def motif_scan(sequence: str, pattern: str) -> dict:
        """ANALYSE: one-based overlapping sequence-regex motif hits. A motif is contextual evidence, not a measured variant effect; compare pssm_score and learned esm2_likelihood."""
        args = locals()
        return emit("classical", "motif_scan", args,
                    lambda: classical.motif_scan(**args))

    @mcp.tool(name="blosum_score")
    def blosum_score(wt: str, mutant: str) -> dict:
        """SCORE, classical generic substitution evidence: raw BLOSUM62 for one-letter wild type and mutant. Protein-independent; pair with MSA-based pssm_score and learned esm2_likelihood."""
        args = locals()
        return emit("classical", "blosum_score", args,
                    lambda: classical.blosum_score(**args))

    @mcp.tool(name="hbond_geometry")
    def hbond_geometry(donor: list[float], hydrogen: list[float], acceptor: list[float]) -> dict:
        """ANALYSE, geometric evidence: distance/angle hydrogen-bond check on supplied coordinates. Not energy, ddG or variant fitness; compare dssp and learned sequence scores separately."""
        args = locals()
        return emit("classical", "hbond_geometry", args,
                    lambda: classical.hbond_geometry(**args))

    if presentation == "guided":
        @mcp.tool(name="screen_variant_classical")
        def screen_variant_classical(sequence: str, reference_fasta: str, position: int,
                                     mutant: str, max_hits: int = 10) -> dict:
            """GUIDED RETRIEVE→SCORE: BLASTP, construct homolog MSA, then PSSM, conservation and BLOSUM for one position/one-letter mutant. Classical channel; compare screen_variant_fm for complementary learned evidence."""
            args = locals()
            def compute() -> dict:
                aligned = classical.blast_msa(sequence, reference_fasta, max_hits)
                p = classical.pssm_score(sequence, aligned["msa"], position, mutant)
                return {"retrieval": {"depth": aligned["depth"], "hit_ids_used": aligned["hit_ids_used"]},
                        "pssm": p, "conservation": classical.conservation(sequence, aligned["msa"], position),
                        "blosum": classical.blosum_score(p["wt"], mutant)}
            return emit("classical", "screen_variant_classical", args, compute)

    return mcp


def make_analysis(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-analysis", version="0.1.0")

    @mcp.tool(name="seq_identity")
    def seq_identity(sequence_a: str, sequence_b: str) -> dict:
        """ANALYSE: global BLOSUM62-aligned sequence identity including terminal gaps. Detect redundancy; not fitness or independent validation. For mutation evidence compare pssm_score and esm2_likelihood."""
        args = locals()
        return emit("analysis", "seq_identity", args,
                    lambda: analysis.seq_identity(**args))

    @mcp.tool(name="tmalign")
    def tmalign(pdb_a: str, pdb_b: str) -> dict:
        """ANALYSE: TM-align two explicit PDB backbones for structural similarity. Not measured stability; complement learned esmfold structure and sequence plausibility with geometric comparison."""
        args = locals()
        return emit("analysis", "tmalign", args,
                    lambda: analysis.tmalign(**args))

    return mcp


def make_record(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-record", version="0.1.0")

    @mcp.tool(name="submit_answer")
    def submit_answer(item_id: str, answer: dict) -> dict:
        """SUBMIT: record the one final ranked answer after evaluating and filtering candidates. Receipts must resolve; this records an unscored answer, not a measured assay result."""
        args = locals()
        return emit("record", "submit_answer", args,
                    lambda: record.submit_answer(**args))

    @mcp.tool(name="log_note")
    def log_note(item_id: str, note: str) -> dict:
        """RECORD: append an auditable working note or rejection rationale; not final submission. Use submit_answer exactly once when evaluation is finished."""
        args = locals()
        return emit("record", "log_note", args,
                    lambda: record.log_note(**args))

    return mcp


def make_physics(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-physics", version="0.1.0")

    @mcp.tool(name="dssp")
    def dssp(pdb_path: str) -> dict:
        """ANALYSE, geometric structural evidence: mkdssp 4.2.2 secondary structure and solvent exposure from a valid PDB. Not stability or fitness; compare learned esmfold and esm2_likelihood separately."""
        args = locals()
        return emit("physics", "dssp", args, lambda: physics.dssp(**args))

    @mcp.tool(name="pyrosetta_ddg")
    def pyrosetta_ddg(wt_pdb: str, mutant_pdb: str) -> dict:
        """SCORE, physics channel BLOCKED: PyRosetta ddG unavailable on this host. Do not treat openmm_snapshot_potential_delta as ddG or use it to rank W1 fitness."""
        args = locals()
        return emit("physics", "pyrosetta_ddg", args,
                    lambda: physics.pyrosetta_ddg(**args))

    @mcp.tool(name="openmm_snapshot_potential_delta")
    def openmm_snapshot_potential_delta(wt_pdb: str, mutant_pdb: str) -> dict:
        """ANALYSE, physics diagnostic: potential-energy difference of two supplied unminimized PDB snapshots. Neither ddG nor stability/fitness ranker; complementary to learned esm2_likelihood, never interchangeable."""
        args = locals()
        return emit("physics", "openmm_snapshot_potential_delta", args,
                    lambda: physics.openmm_snapshot_potential_delta(**args))

    return mcp


def make_lit(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-lit-ncbi-substitute", version="0.1.0")

    @mcp.tool(name="pubmed_search")
    def pubmed_search(term: str, max_hits: int = 3) -> dict:
        """RETRIEVE, literature evidence: live PubMed titles/records via NCBI E-utilities. Prior publications provide context, not this assay's label; compare sequence and structural tools independently."""
        args = locals()
        return emit("lit", "pubmed_search", args,
                    lambda: lit.pubmed_search(**args))

    return mcp


def make_predictive(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-predictive", version="0.1.0")

    @mcp.tool(name="esm2_likelihood")
    def esm2_likelihood(sequence: str, position: int, mutant: str) -> dict:
        """SCORE, learned sequence channel: pinned ESM-2 650M masked-marginal one-letter substitution log-odds. Not measured fitness or ddG; compare complementary classical pssm_score/BLOSUM and ESM-IF1."""
        args = locals()
        receipt_args = {**args, "model": predictive.ESM2_MODEL,
                        "revision": predictive.ESM2_REVISION}
        return emit("predictive", "esm2_likelihood", receipt_args,
                    lambda: predictive.esm2_likelihood(**args))

    @mcp.tool(name="esmfold")
    def esmfold(sequence: str, seed: int = 0) -> dict:
        """PREDICT, learned structure channel: pinned ESMFold v1 PDB artifact, CA count and confidence. pLDDT is local structural confidence, not fitness/stability; compare geometry with dssp or tmalign."""
        args = locals()
        return emit("predictive", "esmfold", args,
                    lambda: predictive.esmfold(**args))

    if presentation == "guided":
        @mcp.tool(name="screen_variant_fm")
        def screen_variant_fm(sequence: str, position: int, mutant: str,
                              pdb_path: str, chain: str = "A") -> dict:
            """GUIDED LEARNED SCORES: ESM-2 650M masked-marginal mutation score plus ESM-IF1 backbone-conditioned plausibility. Compare screen_variant_classical's BLAST/PSSM/BLOSUM channel before ranking."""
            args = locals()
            identity = {**args, "esm2_model": predictive.ESM2_MODEL,
                        "esm2_revision": predictive.ESM2_REVISION,
                        "esm_if_checkpoint_sha256":
                        "be4ba36edec22a9bfaa4946ff6b2815f1f19d8a3d7e0eada8b796d5a0eae9fd4"}
            def compute() -> dict:
                e2 = predictive.esm2_likelihood(sequence, position, mutant)
                changed = sequence[:position-1] + mutant + sequence[position:]
                inverse = generative.esm_if(pdb_path=pdb_path, chain=chain, sequence=changed)
                return {"esm2_likelihood": e2, "esm_if": inverse,
                        "note": "Model plausibility scores, not measured fitness or stability."}
            return emit("predictive", "screen_variant_fm", identity, compute)

    return mcp


def make_generative(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-generative", version="0.1.0")

    @mcp.tool(name="esm_if")
    def esm_if(pdb_path: str, chain: str, sequence: str) -> dict:
        """SCORE, learned structure-conditioned channel: pinned ESM-IF1 sequence log-likelihood on a supplied backbone. Not ddG or measured fitness; compare esm2_likelihood and classical PSSM independently."""
        args = locals()
        return emit("generative", "esm_if", args,
                    lambda: generative.esm_if(**args))

    return mcp


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", choices=["classical", "analysis", "record", "physics", "lit", "predictive", "generative"], required=True)
    parser.add_argument("--presentation", choices=["unguided", "guided"], default="unguided")
    args = parser.parse_args()
    builders = {"classical": make_classical, "analysis": make_analysis,
                "record": make_record, "physics": make_physics, "lit": make_lit,
                "predictive": make_predictive, "generative": make_generative}
    asyncio.run(builders[args.server](args.presentation).run_stdio_async())


if __name__ == "__main__":
    main()
