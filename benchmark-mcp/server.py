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
        """Retrieve protein homologs from an explicit FASTA using MMseqs2."""
        args = locals()
        return emit("classical", "mmseqs_search", args,
                    lambda: classical.mmseqs_search(**args))

    @mcp.tool(name="blast_search")
    def blast_search(sequence: str, reference_fasta: str, max_hits: int = 5) -> dict:
        """Retrieve protein homologs from an explicit FASTA using BLASTP."""
        args = locals()
        return emit("classical", "blast_search", args,
                    lambda: classical.blast_search(**args))

    @mcp.tool(name="pssm_score")
    def pssm_score(query: str, msa: list[str], position: int, mutant: str) -> dict:
        """Score a substitution in a supplied MSA with pre-registered pseudocounts."""
        args = locals()
        return emit("classical", "pssm_score", args,
                    lambda: classical.pssm_score(**args))

    @mcp.tool(name="conservation")
    def conservation(query: str, msa: list[str], position: int) -> dict:
        """Return normalized Shannon conservation for one MSA column."""
        args = locals()
        return emit("classical", "conservation", args,
                    lambda: classical.conservation(**args))

    @mcp.tool(name="motif_scan")
    def motif_scan(sequence: str, pattern: str) -> dict:
        """Find overlapping sequence-regex motifs with one-based coordinates."""
        args = locals()
        return emit("classical", "motif_scan", args,
                    lambda: classical.motif_scan(**args))

    @mcp.tool(name="blosum_score")
    def blosum_score(wt: str, mutant: str) -> dict:
        """Return the canonical raw BLOSUM62 substitution score."""
        args = locals()
        return emit("classical", "blosum_score", args,
                    lambda: classical.blosum_score(**args))

    @mcp.tool(name="hbond_geometry")
    def hbond_geometry(donor: list[float], hydrogen: list[float], acceptor: list[float]) -> dict:
        """Classify an explicit donor-hydrogen-acceptor triplet by distance and angle."""
        args = locals()
        return emit("classical", "hbond_geometry", args,
                    lambda: classical.hbond_geometry(**args))

    if presentation == "guided":
        @mcp.tool(name="screen_variant_classical")
        def screen_variant_classical(query: str, msa: list[str], position: int,
                                     mutant: str) -> dict:
            """Guided workflow: PSSM, conservation, and BLOSUM for one variant."""
            args = locals()
            def compute() -> dict:
                p = classical.pssm_score(query, msa, position, mutant)
                return {"pssm": p, "conservation": classical.conservation(query, msa, position),
                        "blosum": classical.blosum_score(p["wt"], mutant)}
            return emit("classical", "screen_variant_classical", args, compute)

    return mcp


def make_analysis(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-analysis", version="0.1.0")

    @mcp.tool(name="seq_identity")
    def seq_identity(sequence_a: str, sequence_b: str) -> dict:
        """Global BLOSUM62-aligned identity including terminal gap columns."""
        args = locals()
        return emit("analysis", "seq_identity", args,
                    lambda: analysis.seq_identity(**args))

    @mcp.tool(name="tmalign")
    def tmalign(pdb_a: str, pdb_b: str) -> dict:
        """Compare two explicit PDBs with the TM-align structure algorithm."""
        args = locals()
        return emit("analysis", "tmalign", args,
                    lambda: analysis.tmalign(**args))

    return mcp


def make_record(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-record", version="0.1.0")

    @mcp.tool(name="submit_answer")
    def submit_answer(item_id: str, answer: dict) -> dict:
        """Accept one JSON answer per synthetic smoke item, without scoring it."""
        args = locals()
        return emit("record", "submit_answer", args,
                    lambda: record.submit_answer(**args))

    @mcp.tool(name="log_note")
    def log_note(item_id: str, note: str) -> dict:
        """Append an auditable note for a synthetic smoke item."""
        args = locals()
        return emit("record", "log_note", args,
                    lambda: record.log_note(**args))

    return mcp


def make_physics(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-physics", version="0.1.0")

    @mcp.tool(name="dssp")
    def dssp(pdb_path: str) -> dict:
        """Assign per-residue secondary structure with mkdssp 4.2.2."""
        args = locals()
        return emit("physics", "dssp", args, lambda: physics.dssp(**args))

    @mcp.tool(name="pyrosetta_ddg")
    def pyrosetta_ddg(wt_pdb: str, mutant_pdb: str) -> dict:
        """Blocked PyRosetta ddG; no physics ddG substitute is authorized."""
        args = locals()
        return emit("physics", "pyrosetta_ddg", args,
                    lambda: physics.pyrosetta_ddg(**args))

    @mcp.tool(name="openmm_snapshot_potential_delta")
    def openmm_snapshot_potential_delta(wt_pdb: str, mutant_pdb: str) -> dict:
        """Diagnostic: two unminimized PDB potential-energy snapshots; NOT ddG or a stability ranker."""
        args = locals()
        return emit("physics", "openmm_snapshot_potential_delta", args,
                    lambda: physics.openmm_snapshot_potential_delta(**args))

    return mcp


def make_lit(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-lit-ncbi-substitute", version="0.1.0")

    @mcp.tool(name="pubmed_search")
    def pubmed_search(term: str, max_hits: int = 3) -> dict:
        """Search live PubMed via NCBI E-utilities; scireason MCP is unavailable."""
        args = locals()
        return emit("lit", "pubmed_search", args,
                    lambda: lit.pubmed_search(**args))

    return mcp


def make_predictive(presentation: str) -> MCPServer:
    mcp = MCPServer("rescue-predictive", version="0.1.0")

    @mcp.tool(name="esm2_likelihood")
    def esm2_likelihood(sequence: str, position: int, mutant: str) -> dict:
        """Pinned ESM-2 650M masked-marginal substitution log-likelihood."""
        args = locals()
        receipt_args = {**args, "model": predictive.ESM2_MODEL,
                        "revision": predictive.ESM2_REVISION}
        return emit("predictive", "esm2_likelihood", receipt_args,
                    lambda: predictive.esm2_likelihood(**args))

    @mcp.tool(name="esmfold")
    def esmfold(sequence: str, seed: int = 0) -> dict:
        """Pinned ESMFold v1 structure prediction; returns CA count and PDB artifact."""
        args = locals()
        return emit("predictive", "esmfold", args,
                    lambda: predictive.esmfold(**args))

    if presentation == "guided":
        @mcp.tool(name="screen_variant_fm")
        def screen_variant_fm(sequence: str, position: int, mutant: str,
                              pdb_path: str, chain: str = "A") -> dict:
            """Guided FM workflow: ESM-2 650M mutation score and ESM-IF1 backbone score."""
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
        """Pinned ESM-IF1 backbone-conditioned sequence log-likelihood."""
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
