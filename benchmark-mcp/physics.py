"""W1/W2 structure physics: DSSP and disclosed OpenMM deviation."""

from __future__ import annotations

import os
import subprocess

from common import ROOT, reference_path

DSSP_ROOT = ROOT / "benchmark-mcp/vendor/dssp"
MKDSSP = DSSP_ROOT / "usr/bin/mkdssp"
DSSP_LIB = DSSP_ROOT / "usr/lib/aarch64-linux-gnu"


def dssp(pdb_path: str) -> dict:
    pdb = reference_path(pdb_path)
    if not MKDSSP.exists():
        raise RuntimeError("mkdssp is not installed")
    environment = os.environ.copy()
    environment["LD_LIBRARY_PATH"] = f"{DSSP_LIB}:{environment.get('LD_LIBRARY_PATH', '')}"
    command = [str(MKDSSP), "--output-format", "dssp", str(pdb)]
    process = subprocess.run(command, capture_output=True, text=True,
                             env=environment, timeout=90)
    if process.returncode:
        raise RuntimeError(f"mkdssp exited {process.returncode}: {process.stderr[-300:]}")
    lines = process.stdout.splitlines()
    marker = next((i for i, line in enumerate(lines) if line.startswith("  #  RESIDUE")), None)
    if marker is None:
        raise ValueError("mkdssp did not emit a residue table")
    residues = []
    for line in lines[marker+1:]:
        if len(line) < 17 or not line[5:10].strip().isdigit() or line[13] == "!":
            continue
        residues.append({"position": int(line[5:10]), "chain": line[11].strip(),
                         "aa": line[13], "secondary_structure": line[16].strip() or "-"})
    if not residues:
        raise ValueError("mkdssp emitted no residue assignments")
    return {"residue_count": len(residues), "residues": residues, "backend": "mkdssp_4.2.2"}


def pyrosetta_ddg(wt_pdb: str, mutant_pdb: str) -> dict:
    reference_path(wt_pdb)
    reference_path(mutant_pdb)
    raise RuntimeError("PyRosetta institutional license and runnable current-host aarch64 build not verified; use openmm_delta_energy, which is not ddG")


def openmm_delta_energy(wt_pdb: str, mutant_pdb: str) -> dict:
    """Potential-energy delta for two fully prepared structures, not folding ddG."""
    import openmm as mm
    from openmm import unit
    from openmm.app import ForceField, NoCutoff, PDBFile

    paths = [reference_path(wt_pdb), reference_path(mutant_pdb)]
    energies = []
    atom_counts = []
    for path in paths:
        pdb = PDBFile(str(path))
        has_water = any(residue.name in {"HOH", "WAT"} for residue in pdb.topology.residues())
        files = ["amber14-all.xml", "amber14/tip3p.xml"] if has_water else ["amber14-all.xml", "implicit/gbn2.xml"]
        forcefield = ForceField(*files)
        system = forcefield.createSystem(pdb.topology, nonbondedMethod=NoCutoff)
        integrator = mm.VerletIntegrator(0.001*unit.picoseconds)
        context = mm.Context(system, integrator, mm.Platform.getPlatformByName("CPU"))
        context.setPositions(pdb.positions)
        energy = context.getState(getEnergy=True).getPotentialEnergy().value_in_unit(unit.kilojoules_per_mole)
        energies.append(energy)
        atom_counts.append(system.getNumParticles())
        del context, integrator
    if atom_counts[0] != atom_counts[1]:
        raise ValueError("atom counts differ; raw potential energies are not directly comparable")
    return {"wt_kj_per_mol": energies[0], "mutant_kj_per_mol": energies[1],
            "delta_kj_per_mol": energies[1] - energies[0],
            "atom_count": atom_counts[0], "method": "OpenMM_8.6.1_CPU_unminimized_potential_energy",
            "is_folding_ddg": False,
            "deviation": "not PyRosetta ddG; requires fully prepared matched-topology WT and mutant PDBs"}

