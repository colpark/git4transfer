"""Source-blind, no-tool W1 recitation diagnostic on the Stage 2b subject model."""

from __future__ import annotations

import csv
import hashlib
import json
import re
import threading
import time
import urllib.request

from run_stage2b_envelope import remote, sample
from run_stage2b_llama_envelope import server_pid
from stage3_w1 import OUT, REF, write_csv

MODEL_URL = "http://127.0.0.1:18080/v1/chat/completions"


def exact(output: str, value: str) -> bool:
    if not value:
        return False
    return bool(re.search(r"(?<![A-Za-z0-9])" + re.escape(value) +
                          r"(?![A-Za-z0-9])", output, flags=re.IGNORECASE))


def monitor(stop: threading.Event, state: dict, pid: int) -> None:
    while not stop.is_set():
        try:
            row = sample()
            row["time_unix"] = time.time()
            state["samples"].append(row)
            if row["gpu_util_pct"] > 90:
                state["abort"] = "GPU utilization exceeded 90%"
            elif row["gpu_c"] >= 80:
                state["abort"] = "GPU reached 80 C"
            elif max(row["cpu_zone0_c"], row["cpu_zone4_c"]) >= 85:
                state["abort"] = "CPU thermal zone reached 85 C"
            if state["abort"]:
                remote(f"kill -TERM {pid}")
                stop.set()
                return
        except Exception as error:
            state["abort"] = f"thermal monitor failed: {error}"
            remote(f"kill -TERM {pid}")
            stop.set()
            return
        stop.wait(5)


def main() -> None:
    pid = server_pid()
    metadata = {row["DMS_id"]: row for row in csv.DictReader(REF.open())}
    manifest = [json.loads(line) for line in (OUT / "recitation_manifest.jsonl").read_text().splitlines()]
    assert len(manifest) == 20
    assert all(record["assay_id"] not in record["prompt"] for record in manifest)
    assert exact("Source A0A123_TEST_2020", "A0A123_TEST_2020")
    assert not exact("Source A0A123_TEST_2021", "A0A123_TEST_2020")
    stop = threading.Event()
    state = {"abort": None, "samples": []}
    watcher = threading.Thread(target=monitor, args=(stop, state, pid), daemon=True)
    watcher.start()
    rows = []
    with (OUT / "recitation_trace.jsonl").open("w") as trace:
        for record in manifest:
            if state["abort"]:
                break
            assay = record["assay_id"]
            meta = metadata[assay]
            body = {"model": "qwen2.5-7b-instruct-q4_k_m", "messages": [
                {"role": "system", "content": "Answer the user's protein-prioritisation task. Do not invent measurements."},
                {"role": "user", "content": record["prompt"]}],
                "temperature": 0, "seed": 19, "max_tokens": 512, "stream": False}
            request = urllib.request.Request(MODEL_URL, json.dumps(body).encode(),
                                             {"Content-Type": "application/json"})
            started = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=300) as response:
                    output = json.load(response)
                content = output["choices"][0]["message"]["content"] or ""
                status = "COMPLETED"
                error = ""
            except Exception as failure:
                output, content = None, "", ""
                status = "UNDEMONSTRATED" if state["abort"] else "FAILED"
                error = str(failure)
            entry = {"assay_id": assay, "cluster_50": record["cluster_50"],
                     "status": status, "runtime_s": round(time.monotonic() - started, 3),
                     "prompt_sha256": hashlib.sha256(record["prompt"].encode()).hexdigest(),
                     "output": content, "error": error,
                     "usage": output.get("usage") if output else None}
            trace.write(json.dumps(entry) + "\n")
            trace.flush()
            named = [field for field in ("DMS_id", "UniProt_ID", "pdb_file")
                     if exact(content, meta.get(field, ""))]
            rows.append({"assay_id": assay, "cluster_50": record["cluster_50"],
                         "status": status, "runtime_s": entry["runtime_s"],
                         "exact_source_fields_named": ",".join(named),
                         "burn": bool(named) if status == "COMPLETED" else "UNDEMONSTRATED"})
            print(json.dumps({"assay": assay, "status": status, "burn": rows[-1]["burn"],
                              "runtime_s": entry["runtime_s"]}), flush=True)
            if status != "COMPLETED":
                break
    stop.set()
    watcher.join(timeout=10)
    fields = ["assay_id", "cluster_50", "status", "runtime_s",
              "exact_source_fields_named", "burn"]
    write_csv(OUT / "recitation.csv", rows, fields)
    completed = [row for row in rows if row["status"] == "COMPLETED"]
    report = {"selected_items": len(manifest), "attempted_items": len(rows),
              "completed_items": len(completed),
              "burn_count": sum(row["burn"] is True for row in completed),
              "burn_rate_among_completed": sum(row["burn"] is True for row in completed) /
              len(completed) if completed else None,
              "interrupted_or_failed_items": len(rows) - len(completed),
              "not_attempted_items": len(manifest) - len(rows),
              "source_absence_control": True,
              "exact_match_positive_and_wrong_id_controls": True,
              "abort_reason": state["abort"],
              "thermal_samples": len(state["samples"]),
              "max_gpu_util_pct": max((row["gpu_util_pct"] for row in state["samples"]), default=None),
              "max_gpu_c": max((row["gpu_c"] for row in state["samples"]), default=None),
              "max_cpu_c": max((max(row["cpu_zone0_c"], row["cpu_zone4_c"])
                                 for row in state["samples"]), default=None)}
    (OUT / "recitation_summary.json").write_text(json.dumps(report, indent=2) + "\n")
    thermal_fields = ["gpu_util_pct", "gpu_c", "gpu_power_w", "cpu_zone0_c",
                      "cpu_zone4_c", "mem_available_gib", "time_unix"]
    write_csv(OUT / "recitation_thermal.csv", state["samples"], thermal_fields)
    print(json.dumps(report, indent=2))
    if state["abort"] or len(completed) != len(manifest):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
