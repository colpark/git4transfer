"""Resume-safe, label-blind Floor M recomputation through certified MCP tools.

`score` reads only the frozen candidate list, sequence metadata, AF2 PDBs, and
the already-blind released-score prediction file. `evaluate` refuses to run
until the complete blind MCP file exists and its SHA-256 seal matches.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import statistics
import time
import zipfile
from collections import defaultdict
from contextlib import AsyncExitStack
from pathlib import Path

from mcp import Client
from mcp.client.stdio import StdioServerParameters

from stage3_w1 import percentiles, allowed_score_fields
from stage3_evaluate import label_map, precision_at_10, spearman

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "results/benchmark/stage3_2026-09-13"
STRUCTURES = ROOT / "results/benchmark/stage3b_2026-09-13/ProteinGym_AF2_structures"
OUT = ROOT / "results/benchmark/stage3f_2026-09-14"
PROGRESS = OUT / "floor_m_650m_progress.jsonl"
BLIND = OUT / "floor_m_mcp.csv"
SEAL = OUT / "floor_m_mcp.sha256"
FINAL_COUNT = 14668
EXPECTED_ITEMS = 148


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def frozen_inputs() -> tuple[list[dict], dict, dict]:
    candidates = list(csv.DictReader((OLD / "candidates_blind.csv").open()))
    if len(candidates) != FINAL_COUNT or len({r["assay_id"] for r in candidates}) != EXPECTED_ITEMS:
        raise RuntimeError("frozen candidate dimensions changed")
    if len({(r["assay_id"], r["mutant"]) for r in candidates}) != len(candidates):
        raise RuntimeError("duplicate candidate")
    metadata = {r["DMS_id"]: r for r in csv.DictReader((OLD / "input/DMS_substitutions.csv").open())}
    released = {(r["assay_id"], r["mutant"]): r for r in
                csv.DictReader((OLD / "floor_predictions_blind.csv").open())}
    if set(released) != {(r["assay_id"], r["mutant"]) for r in candidates}:
        raise RuntimeError("released and frozen candidate sets differ")
    return candidates, metadata, released


def sensor_sample() -> dict:
    zones = {}
    for n in (0, 1, 2, 3, 4, 5, 6):
        base = Path(f"/sys/class/thermal/thermal_zone{n}")
        if (base / "type").is_file() and (base / "type").read_text().strip() == "acpitz":
            zones[str(n)] = int((base / "temp").read_text()) / 1000
    available_kib = next(int(line.split()[1]) for line in Path("/proc/meminfo").read_text().splitlines()
                         if line.startswith("MemAvailable:"))
    return {"utc_unix_s": time.time(), "cpu_zones_c": zones,
            "max_cpu_c": max(zones.values()) if zones else None,
            "mem_available_gib": available_kib / 1024**2}


def load_progress() -> dict[tuple[str, str, str], dict]:
    done = {}
    if not PROGRESS.is_file():
        return done
    for line_number, line in enumerate(PROGRESS.open(), 1):
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"corrupt checkpoint line {line_number}") from exc
        key = (row["assay_id"], row["mutant"], row["tool"])
        if key in done and done[key]["value"] != row["value"]:
            raise RuntimeError(f"conflicting checkpoint {key}")
        done[key] = row
    return done


def unpack(response, tool: str, arguments: dict) -> tuple[float, dict]:
    body = response.structured_content or json.loads(response.content[0].text)
    if body.get("error") or body.get("result") is None:
        raise RuntimeError(f"{tool} returned error: {body.get('error')}")
    receipt = body.get("receipt", {})
    artifact = Path(receipt.get("artifact_path", "/__missing__"))
    if receipt.get("tool") != tool or not artifact.is_file():
        raise RuntimeError(f"{tool} missing resolving receipt")
    saved = json.loads(artifact.read_text())
    expected_args = ({**arguments, "model": "facebook/esm2_t33_650M_UR50D",
                      "revision": "08e4846e537177426273712802403f7ba8261b6c"}
                     if tool == "esm2_likelihood" else arguments)
    if saved.get("receipt", {}).get("call_id") != receipt.get("call_id") or saved.get("args") != expected_args:
        raise RuntimeError(f"{tool} receipt/argument mismatch")
    key = "delta_log_probability" if tool == "esm2_likelihood" else "mean_log_likelihood"
    value = float(body["result"][key])
    if not math.isfinite(value):
        raise RuntimeError(f"{tool} nonfinite score")
    return value, receipt


async def score() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    if BLIND.exists() or SEAL.exists():
        raise RuntimeError("sealed blind prediction exists; never overwrite it")
    candidates, metadata, released = frozen_inputs()
    done = load_progress()
    print(json.dumps({"expected_candidates": len(candidates), "completed_tool_calls": len(done),
                      "expected_tool_calls": 2 * len(candidates), "node": os.uname().nodename}), flush=True)
    params = lambda server: StdioServerParameters(
        command=str(ROOT / "benchmark-mcp/.venv/bin/python"),
        args=[str(ROOT / "benchmark-mcp/server.py"), "--server", server, "--presentation", "unguided"],
        cwd=ROOT)
    started = time.monotonic()
    max_cpu, min_memory = 0.0, float("inf")
    async with AsyncExitStack() as stack:
        clients = {server: await stack.enter_async_context(Client(params(server), raise_exceptions=True,
                          read_timeout_seconds=650)) for server in ("predictive", "generative")}
        with PROGRESS.open("a") as output, (OUT / "floor_m_node10_sensors.jsonl").open("a") as sensors:
            for i, row in enumerate(candidates, 1):
                assay, mutant = row["assay_id"], row["mutant"]
                meta = metadata[assay]
                sequence = meta["target_seq"]
                position = int(row["position"])
                if sequence[position - 1] != row["wt"] or mutant != row["wt"] + str(position) + row["alt"]:
                    raise RuntimeError(f"candidate/reference mismatch {assay} {mutant}")
                mutated = sequence[:position - 1] + row["alt"] + sequence[position:]
                pdb = STRUCTURES / meta["pdb_file"]
                if not pdb.is_file():
                    raise RuntimeError(f"missing frozen PDB: {pdb}")
                calls = (("esm2_likelihood", "predictive", {"sequence": sequence,
                          "position": position, "mutant": row["alt"]}),
                         ("esm_if", "generative", {"pdb_path": str(pdb),
                          "chain": "A", "sequence": mutated}))
                for tool, server, arguments in calls:
                    key = (assay, mutant, tool)
                    if key in done:
                        continue
                    sample = sensor_sample()
                    if sample["max_cpu_c"] is not None:
                        max_cpu = max(max_cpu, sample["max_cpu_c"])
                    min_memory = min(min_memory, sample["mem_available_gib"])
                    result = await clients[server].call_tool(tool, arguments)
                    value, receipt = unpack(result, tool, arguments)
                    sample["after_tool"] = tool
                    sample["assay_id"] = assay
                    sample["mutant"] = mutant
                    sensors.write(json.dumps(sample, sort_keys=True) + "\n")
                    sensors.flush()
                    checkpoint = {"assay_id": assay, "mutant": mutant, "tool": tool,
                                  "value": value, "receipt": receipt}
                    output.write(json.dumps(checkpoint, sort_keys=True) + "\n")
                    output.flush()
                    os.fsync(output.fileno())
                    done[key] = checkpoint
                if i % 100 == 0:
                    print(json.dumps({"candidates_seen": i, "tool_calls_done": len(done),
                                      "elapsed_s": round(time.monotonic() - started, 1),
                                      "max_cpu_c": max_cpu, "min_mem_gib": min_memory}), flush=True)
    if len(done) != 2 * FINAL_COUNT:
        raise RuntimeError(f"incomplete MCP calls {len(done)}/{2 * FINAL_COUNT}")
    grouped = defaultdict(list)
    for row in candidates:
        grouped[row["assay_id"]].append(row)
    predictions = []
    for assay, variants in sorted(grouped.items()):
        selected = {r["mutant"] for r in variants}
        c_old = {r["mutant"]: float(released[(assay, r["mutant"])]["floor_c_score"])
                 for r in variants}
        c_rank = percentiles(c_old)
        esm2 = {m: done[(assay, m, "esm2_likelihood")]["value"] for m in selected}
        esm_if = {m: done[(assay, m, "esm_if")]["value"] for m in selected}
        esm2_rank, esm_if_rank = percentiles(esm2), percentiles(esm_if)
        for row in variants:
            m = row["mutant"]
            predictions.append({"cluster_50": row["cluster_50"], "assay_id": assay,
                                "mutant": m, "floor_c_score": c_old[m],
                                "esm2_mcp": esm2[m], "esm_if_mcp": esm_if[m],
                                "floor_m_mcp_score": (c_rank[m] + esm2_rank[m] + esm_if_rank[m]) / 3,
                                "floor_m_released_score": released[(assay, m)]["floor_m_score"],
                                "esm2_call_id": done[(assay, m, "esm2_likelihood")]["receipt"]["call_id"],
                                "esm_if_call_id": done[(assay, m, "esm_if")]["receipt"]["call_id"]})
    tmp = OUT / "floor_m_mcp.csv.tmp"
    write_csv(tmp, predictions)
    if len(predictions) != FINAL_COUNT:
        raise RuntimeError("blind prediction count changed")
    tmp.replace(BLIND)
    digest = sha256(BLIND)
    SEAL.write_text(digest + "  floor_m_mcp.csv\n")
    print(json.dumps({"blind_rows": len(predictions), "sha256": digest,
                      "elapsed_s": round(time.monotonic() - started, 1)}), flush=True)


def evaluate() -> None:
    if not BLIND.is_file() or not SEAL.is_file() or sha256(BLIND) != SEAL.read_text().split()[0]:
        raise RuntimeError("complete hashed blind prediction file required before labels")
    rows = list(csv.DictReader(BLIND.open()))
    if len(rows) != FINAL_COUNT:
        raise RuntimeError("blind prediction file incomplete")
    by_assay = defaultdict(list)
    for row in rows:
        by_assay[row["assay_id"]].append(row)
    # Published score archive contains labels in other columns. This reader
    # indexes only the frozen model-score allowlist, never DMS_score.
    released = {}
    with zipfile.ZipFile(OLD / "input/zero_shot_substitutions_scores.zip") as archive:
        for assay, variants in by_assay.items():
            with archive.open(assay + ".csv") as handle:
                table = csv.reader(line.decode("utf-8") for line in handle)
                header = next(table)
                indices = {name: header.index(name) for name in ("mutant", "ESM2_650M", "ESM-IF1")}
                selected = {r["mutant"] for r in variants}
                for fields in table:
                    m = fields[indices["mutant"]]
                    if m in selected:
                        released[(assay, m)] = allowed_score_fields(fields, indices)
    compare = []
    with zipfile.ZipFile(OLD / "input/DMS_ProteinGym_substitutions.zip") as labels_archive:
        for assay, variants in sorted(by_assay.items()):
            selected = {r["mutant"] for r in variants}
            labels = label_map(labels_archive, assay, selected)
            if set(labels) != selected:
                raise RuntimeError(f"label coverage mismatch {assay}")
            def values(column):
                return {r["mutant"]: float(r[column]) for r in variants}
            c, new, old = values("floor_c_score"), values("floor_m_mcp_score"), values("floor_m_released_score")
            e2_new = values("esm2_mcp")
            if_new = values("esm_if_mcp")
            e2_old = {m: released[(assay, m)]["esm2"] for m in selected}
            if_old = {m: released[(assay, m)]["esm_if1"] for m in selected}
            def paired_correlation(a, b):
                keys = [m for m in selected if a[m] is not None and b[m] is not None]
                return spearman({m: a[m] for m in keys}, {m: b[m] for m in keys}) if len(keys) >= 3 else None
            compare.append({"assay_id": assay, "cluster_50": variants[0]["cluster_50"],
                            "n_candidates": len(selected), "chance_p_at_10": 10 / len(selected),
                            "floor_c_rho": spearman(c, labels), "floor_c_p_at_10": precision_at_10(c, labels),
                            "released_m_rho": spearman(old, labels), "released_m_p_at_10": precision_at_10(old, labels),
                            "mcp_m_rho": spearman(new, labels), "mcp_m_p_at_10": precision_at_10(new, labels),
                            "mcp_vs_released_ensemble_rho": spearman(new, old),
                            "mcp_vs_released_esm2_rho": paired_correlation(e2_new, e2_old),
                            "mcp_vs_released_esm_if_rho": paired_correlation(if_new, if_old),
                            "released_esm_if_coverage": sum(if_old[m] is not None for m in selected)})
    write_csv(OUT / "floor_m_item_compare.csv", compare)
    def mean(name):
        vals = [float(r[name]) for r in compare if r[name] is not None]
        return statistics.mean(vals) if vals else None
    report = ["# Floor M: released scores versus certified MCP scores", "",
              f"Blind prediction SHA-256: `{sha256(BLIND)}`. The complete {len(rows):,}-candidate prediction file was written and sealed before this label evaluator ran.", "",
              "The frozen equal-rank rule averages percentile ranks of Floor C, ESM2, and ESM-IF; the released-score run is unchanged. Local MCP tools use ESM2 8M rather than released ESM2 650M, and score ESM-IF as whole mutant-sequence likelihood rather than ProteinGym's released variant field. These are implementation differences, not agency effects.", "",
              "| Metric (mean over 148 assays) | Floor C | Released Floor M | MCP Floor M |",
              "|---|---:|---:|---:|",
              f"| Spearman | {mean('floor_c_rho'):.4f} | {mean('released_m_rho'):.4f} | {mean('mcp_m_rho'):.4f} |",
              f"| Precision@10 | {mean('floor_c_p_at_10'):.4f} | {mean('released_m_p_at_10'):.4f} | {mean('mcp_m_p_at_10'):.4f} |",
              f"| Per-item chance P@10 | {mean('chance_p_at_10'):.4f} | {mean('chance_p_at_10'):.4f} | {mean('chance_p_at_10'):.4f} |", "",
              f"Mean per-item rank correlation, MCP versus released: ensemble {mean('mcp_vs_released_ensemble_rho'):.4f}, ESM2 {mean('mcp_vs_released_esm2_rho'):.4f}, ESM-IF {mean('mcp_vs_released_esm_if_rho'):.4f}. Per-item values are in `floor_m_item_compare.csv`.", "",
              "147/148 AF2 PDB sequences match the metadata target sequence exactly; P53_HUMAN differs at residue 72 (P in PDB, R in metadata), and remains included with this discrepancy disclosed."]
    (OUT / "floor_m_compare.md").write_text("\n".join(report) + "\n")
    print(json.dumps({"items": len(compare), "mcp_mean_p_at_10": mean("mcp_m_p_at_10"),
                      "mcp_mean_rho": mean("mcp_m_rho")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("score", "evaluate"))
    args = parser.parse_args()
    asyncio.run(score()) if args.phase == "score" else evaluate()
