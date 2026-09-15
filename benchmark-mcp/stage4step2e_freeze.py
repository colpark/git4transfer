"""Create or verify the prospective B4 v3 remediation freeze."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from stage4step2e_prepare import tool_surface

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step2e_2026-09-14"
FREEZE = OUT / "freeze_hashes.json"
IF_WEIGHT = Path.home() / ".cache/torch/hub/checkpoints/esm_if1_gvp4_t16_142M_UR50.pt"
ESM2 = (Path.home() / ".cache/huggingface/hub/models--facebook--esm2_t33_650M_UR50D/"
        "snapshots/08e4846e537177426273712802403f7ba8261b6c")


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def packages(python: Path) -> str:
    code = ("import importlib.metadata as m; "
            "print('\\n'.join(sorted((d.metadata.get('Name') or d.name)+'=='+d.version "
            "for d in m.distributions())))")
    result = subprocess.run([str(python), "-c", code], capture_output=True, text=True, check=True)
    return "\n".join(sorted(x.strip() for x in result.stdout.splitlines() if x.strip())) + "\n"


def workspace_targets() -> dict[str, Path]:
    paths = {name: OUT / filename for name, filename in {
        "remediation": "remediation.md", "fixture_contract": "fixture_contract.json",
        "fixture_prompt": "fixture_prompt.txt", "provenance": "provenance.json",
        "endpoint_registry": "endpoint_registry_145_internal.jsonl",
        "model_visible_endpoint_registry": "endpoint_registry_145_model_visible.jsonl",
        "endpoint_readiness": "endpoint_readiness.json", "release_requirements": "release_requirements.json",
        "model_identity": "model_identity.json", "tool_surface": "tool_surface_manifest.json",
        "fixture_fasta": "fixture_inputs/item_fixture.fasta", "fixture_pdb": "fixture_inputs/item_fixture.pdb",
        "benchmark_packages": "runtime/benchmark_pip_freeze.txt",
        "fm_packages": "runtime/fm_pip_freeze.txt"}.items()}
    for name in ("contract", "prepare", "record_server", "server", "run", "validate",
                 "content_gate", "release_gate", "freeze"):
        paths[f"step2e_{name}_code"] = ROOT / f"benchmark-mcp/stage4step2e_{name}.py"
    paths["step2e_tests"] = ROOT / "benchmark-mcp/test_stage4step2e.py"
    for name in ("common", "classical", "predictive", "generative", "physics",
                 "esm2_worker", "esm_if_worker"):
        paths[f"mcp_{name}_code"] = ROOT / f"benchmark-mcp/{name}.py"
    return paths


def external_targets() -> dict[str, Path]:
    logical = {"codex_cli": Path(shutil.which("codex") or "/__missing__").resolve(),
        "benchmark_python": (ROOT / "benchmark-mcp/.venv/bin/python").resolve(),
        "fm_python": (ROOT / "E1/.venv/bin/python").resolve(), "esm_if_checkpoint": IF_WEIGHT,
        "mkdssp": ROOT / "benchmark-mcp/vendor/dssp/usr/bin/mkdssp",
        "libcifpp": ROOT / "benchmark-mcp/vendor/dssp/usr/lib/aarch64-linux-gnu/libcifpp.so.5.0.7.1",
        "blastp": ROOT / "biology-stack/ncbi-blast/usr/bin/blastp"}
    for name in ("config.json", "model.safetensors", "pytorch_model.bin", "special_tokens_map.json",
                 "tokenizer_config.json", "vocab.txt"):
        logical[f"esm2_{name}"] = (ESM2 / name).resolve()
    return logical


def runtime_dependencies(external: dict[str, Path]) -> dict[str, Path]:
    found = {}
    for parent in ("benchmark_python", "fm_python", "mkdssp", "blastp"):
        proc = subprocess.run(["ldd", str(external[parent])], capture_output=True, text=True)
        for line in proc.stdout.splitlines():
            for token in line.replace("=>", " ").split():
                path = Path(token)
                if token.startswith("/") and path.is_file():
                    found[f"ldd_{parent}_{path.name}"] = path.resolve()
    return found


def create() -> None:
    if FREEZE.exists() or (OUT / "runs").exists():
        raise SystemExit("freeze already exists or a run directory makes it too late")
    runtime = OUT / "runtime"; runtime.mkdir(parents=True, exist_ok=True)
    (runtime / "benchmark_pip_freeze.txt").write_text(packages(ROOT / "benchmark-mcp/.venv/bin/python"))
    (runtime / "fm_pip_freeze.txt").write_text(packages(ROOT / "E1/.venv/bin/python"))
    workspace, external = workspace_targets(), external_targets()
    external.update(runtime_dependencies(external))
    missing = [str(p) for p in (*workspace.values(), *external.values()) if not p.is_file()]
    if missing:
        raise SystemExit("freeze targets missing: " + ", ".join(missing))
    body = {"frozen_at_utc": datetime.now(timezone.utc).isoformat(),
        "cohort_authorized": False, "batch_one_open": False, "b1_ruling": "OUTSTANDING",
        "model_calls": 0, "labels_opened": False,
        "step2d_artifacts_modified": False,
        "workspace_sha256": {k: {"path": str(p.relative_to(ROOT)), "digest": sha(p)} for k, p in workspace.items()},
        "external_sha256": {k: {"path": str(p), "digest": sha(p)} for k, p in external.items()}}
    FREEZE.write_text(json.dumps(body, sort_keys=True, indent=2) + "\n")
    print(json.dumps({"created": True, "workspace_targets": len(workspace),
                      "external_targets": len(external), "freeze_sha256": sha(FREEZE)}, sort_keys=True))


def verify() -> None:
    body = json.loads(FREEZE.read_text())
    failures = []
    for section in ("workspace_sha256", "external_sha256"):
        for name, row in body[section].items():
            path = ROOT / row["path"] if section == "workspace_sha256" else Path(row["path"])
            if not path.is_file() or sha(path) != row["digest"]:
                failures.append(name)
    if failures:
        raise SystemExit("freeze verification failed: " + ", ".join(failures))
    current_surface = json.dumps(tool_surface(), sort_keys=True, indent=2) + "\n"
    if (OUT / "tool_surface_manifest.json").read_text() != current_surface:
        raise SystemExit("generated item-bound MCP surface changed")
    for name, py in (("benchmark_packages", ROOT / "benchmark-mcp/.venv/bin/python"),
                     ("fm_packages", ROOT / "E1/.venv/bin/python")):
        path = ROOT / body["workspace_sha256"][name]["path"]
        if path.read_text() != packages(py):
            raise SystemExit(f"installed packages changed: {name}")
    if body.get("cohort_authorized") is not False or body.get("batch_one_open") is not False:
        raise SystemExit("freeze unexpectedly authorizes cohort work")
    print(json.dumps({"verified": True, "workspace_targets": len(body["workspace_sha256"]),
                      "external_targets": len(body["external_sha256"]),
                      "freeze_sha256": sha(FREEZE)}, sort_keys=True))


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in {"create", "verify"}:
        raise SystemExit("usage: stage4step2e_freeze.py {create|verify}")
    create() if sys.argv[1] == "create" else verify()
