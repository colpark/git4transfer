"""Post-specified comprehensive analysis for the ten-item comparison.

The frozen evaluator's per-item Spearman and precision@10 values are asserted
byte-derived inputs, not replaced.  All additional metrics are exploratory.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
import zipfile
from collections import defaultdict
from pathlib import Path

from pilot_score import full_ranking
from stage3_evaluate import label_map, precision_at_10, spearman
from stage3_w1 import RAW, percentiles
from stage4step2e_contract import ranking_scores


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results/benchmark/stage4step3_2026-09-14"
ARMS = ("floor_c", "floor_m", "b1", "b2", "b4")
LABELS = {"floor_c": "Floor C", "floor_m": "Floor M (B3)",
          "b1": "B1", "b2": "B2", "b4": "B4"}
METRICS = ("spearman", "kendall_tau_b", "pearson", "precision_at_5",
           "precision_at_10", "precision_at_20", "ndcg_at_10",
           "average_precision_top_10", "roc_auc_top_10",
           "reciprocal_rank_true_best", "top_1_hit", "top_5_overlap",
           "normalized_top_10_regret", "mean_true_percentile_top_10")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def items() -> list[dict]:
    return [json.loads(line) for line in
            (OUT / "blind_item_manifest_internal.jsonl").read_text().splitlines()]


def ordered(scores: dict[str, float]) -> list[str]:
    return [key for key, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def pearson(a: dict[str, float], b: dict[str, float]) -> float | None:
    keys = sorted(a)
    if keys != sorted(b):
        raise ValueError("unequal candidate sets")
    ma = statistics.mean(a[k] for k in keys)
    mb = statistics.mean(b[k] for k in keys)
    numerator = sum((a[k] - ma) * (b[k] - mb) for k in keys)
    da = sum((a[k] - ma) ** 2 for k in keys)
    db = sum((b[k] - mb) ** 2 for k in keys)
    return numerator / math.sqrt(da * db) if da and db else None


def kendall_tau_b(a: dict[str, float], b: dict[str, float]) -> float | None:
    keys = sorted(a)
    if keys != sorted(b):
        raise ValueError("unequal candidate sets")
    concordant = discordant = ties_a = ties_b = 0
    for i, left in enumerate(keys):
        for right in keys[i + 1:]:
            da = (a[left] > a[right]) - (a[left] < a[right])
            db = (b[left] > b[right]) - (b[left] < b[right])
            if da == 0 and db == 0:
                continue
            if da == 0:
                ties_a += 1
            elif db == 0:
                ties_b += 1
            elif da == db:
                concordant += 1
            else:
                discordant += 1
    denom = math.sqrt((concordant + discordant + ties_a) *
                      (concordant + discordant + ties_b))
    return (concordant - discordant) / denom if denom else None


def precision_at_k(predicted: dict[str, float], truth: dict[str, float], k: int) -> float:
    return len(set(ordered(predicted)[:k]) & set(ordered(truth)[:k])) / k


def ndcg_at_k(predicted: dict[str, float], truth: dict[str, float], k: int) -> float:
    relevance = percentiles(truth)
    def dcg(order: list[str]) -> float:
        return sum((2 ** relevance[key] - 1) / math.log2(rank + 2)
                   for rank, key in enumerate(order[:k]))
    ideal = dcg(ordered(truth))
    return dcg(ordered(predicted)) / ideal if ideal else 0.0


def average_precision_top_k(predicted: dict[str, float], truth: dict[str, float], k: int) -> float:
    positives = set(ordered(truth)[:k])
    hits = 0
    total = 0.0
    for rank, key in enumerate(ordered(predicted), 1):
        if key in positives:
            hits += 1
            total += hits / rank
    return total / len(positives)


def roc_auc_top_k(predicted: dict[str, float], truth: dict[str, float], k: int) -> float:
    positives = set(ordered(truth)[:k])
    negatives = set(truth) - positives
    wins = 0.0
    for positive in positives:
        for negative in negatives:
            if predicted[positive] > predicted[negative]:
                wins += 1
            elif predicted[positive] == predicted[negative]:
                wins += 0.5
    return wins / (len(positives) * len(negatives))


def item_metrics(predicted: dict[str, float], truth: dict[str, float]) -> dict[str, float]:
    pred_order = ordered(predicted)
    true_order = ordered(truth)
    true_best = true_order[0]
    top_10 = pred_order[:10]
    spread = max(truth.values()) - min(truth.values())
    regret = (max(truth.values()) - max(truth[k] for k in top_10)) / spread if spread else 0.0
    true_pct = percentiles(truth)
    values = {
        "spearman": spearman(predicted, truth),
        "kendall_tau_b": kendall_tau_b(predicted, truth),
        "pearson": pearson(predicted, truth),
        "precision_at_5": precision_at_k(predicted, truth, 5),
        "precision_at_10": precision_at_10(predicted, truth),
        "precision_at_20": precision_at_k(predicted, truth, 20),
        "ndcg_at_10": ndcg_at_k(predicted, truth, 10),
        "average_precision_top_10": average_precision_top_k(predicted, truth, 10),
        "roc_auc_top_10": roc_auc_top_k(predicted, truth, 10),
        "reciprocal_rank_true_best": 1 / (pred_order.index(true_best) + 1),
        "top_1_hit": float(pred_order[0] == true_best),
        "top_5_overlap": precision_at_k(predicted, truth, 5),
        "normalized_top_10_regret": regret,
        "mean_true_percentile_top_10": statistics.mean(true_pct[k] for k in top_10),
    }
    if any(value is None or not math.isfinite(value) for value in values.values()):
        raise ValueError("undefined exploratory metric")
    return values  # type: ignore[return-value]


def bootstrap_mean(values: list[float], seed: int, replicates: int = 10000) -> dict:
    if not values:
        return {"n": 0, "mean": None, "median": None, "ci95": None}
    rng = random.Random(seed)
    means = []
    for _ in range(replicates):
        means.append(statistics.mean(values[rng.randrange(len(values))] for _ in values))
    means.sort()
    return {"n": len(values), "mean": statistics.mean(values),
            "median": statistics.median(values),
            "ci95": [means[249], means[9749]]}


def sign_test_two_sided(wins: int, losses: int) -> float | None:
    n = wins + losses
    if n == 0:
        return None
    tail = sum(math.comb(n, k) for k in range(0, min(wins, losses) + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def load_rankings() -> tuple[dict, dict]:
    blind = json.loads((OUT / "blind_bundle_manifest.json").read_text())
    for record in blind["predictions"].values():
        path = ROOT / record["path"]
        if sha(path) != record["sha256"]:
            raise SystemExit("blind prediction hash mismatch")
    status: dict[tuple[str, str], dict] = {}
    rankings: dict[tuple[str, str], dict[str, float]] = {}
    for arm in ("floor_c", "floor_m"):
        grouped: dict[str, dict[str, float]] = defaultdict(dict)
        for line in (OUT / f"blind_{arm}.jsonl").read_text().splitlines():
            row = json.loads(line)
            grouped[row["neutral_item_id"]][row["mutant"]] = float(row["score"])
        for neutral, scores in grouped.items():
            status[arm, neutral] = {"status": "SCORABLE", "coverage_failure_reason": ""}
            rankings[arm, neutral] = scores
    for arm in ("b1", "b2", "b4"):
        for line in (OUT / f"blind_{arm}.jsonl").read_text().splitlines():
            row = json.loads(line)
            neutral = row["neutral_item_id"]
            status[arm, neutral] = {"status": row["status"],
                                    "coverage_failure_reason": row["coverage_failure_reason"]}
            if row["status"] == "SCORABLE":
                contract = json.loads((OUT / "contracts" / f"{neutral}.json").read_text())
                candidates = set(contract["candidates"])
                rankings[arm, neutral] = (ranking_scores(row["answer"]) if arm == "b4"
                                           else full_ranking(row["answer"], candidates))
    return status, rankings


def format_metric(value: float | None) -> str:
    return "—" if value is None else f"{value:.3f}"


def main() -> None:
    rows_target = OUT / "comprehensive_metric_rows.csv"
    summary_target = OUT / "comprehensive_summary.json"
    report_target = OUT / "comprehensive_report.md"
    if any(path.exists() for path in (rows_target, summary_target, report_target)):
        raise SystemExit("comprehensive evaluation already exists")

    primary_path = OUT / "comparison_rows.csv"
    integrity = json.loads((OUT / "evaluation_integrity.json").read_text())
    if sha(primary_path) != integrity["rows_sha256"]:
        raise SystemExit("frozen primary rows hash mismatch")
    primary = {(r["arm"], r["neutral_item_id"]): r
               for r in csv.DictReader(primary_path.open())}
    status, rankings = load_rankings()
    item_rows = items()
    detailed = []
    truths = {}
    with zipfile.ZipFile(RAW) as archive:
        for item in item_rows:
            neutral = item["neutral_item_id"]
            contract = json.loads((ROOT / item["contract_path"]).read_text())
            candidates = set(contract["candidates"])
            truth = label_map(archive, item["internal_assay_id"], candidates)
            if set(truth) != candidates:
                raise SystemExit(f"incomplete labels for {neutral}")
            truths[neutral] = truth
            for arm in ARMS:
                state = status[arm, neutral]
                row = {"neutral_item_id": neutral, "assay_id": item["internal_assay_id"],
                       "published_quartile": item["published_quartile"], "arm": arm,
                       "n_candidates": len(candidates), "status": state["status"],
                       "coverage_failure_reason": state["coverage_failure_reason"]}
                if state["status"] == "SCORABLE":
                    metrics = item_metrics(rankings[arm, neutral], truth)
                    frozen = primary[arm, neutral]
                    if (abs(metrics["spearman"] - float(frozen["spearman"])) > 1e-12
                            or abs(metrics["precision_at_10"] -
                                   float(frozen["precision_at_10"])) > 1e-12):
                        raise SystemExit(f"primary metric mismatch for {arm}/{neutral}")
                    row.update(metrics)
                else:
                    row.update({metric: "" for metric in METRICS})
                detailed.append(row)

    fields = ["neutral_item_id", "assay_id", "published_quartile", "arm",
              "n_candidates", "status", "coverage_failure_reason", *METRICS]
    with rows_target.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(detailed)

    aggregate = {}
    for arm_index, arm in enumerate(ARMS):
        valid = [row for row in detailed if row["arm"] == arm and row["status"] == "SCORABLE"]
        aggregate[arm] = {
            "coverage": {"scorable": len(valid), "attempted": 10, "rate": len(valid) / 10},
            "metrics": {metric: bootstrap_mean([float(row[metric]) for row in valid],
                                                seed=19000 + arm_index * 100 + i)
                        for i, metric in enumerate(METRICS)},
        }

    comparisons = {}
    pairs = (("floor_m", "floor_c"), ("b4", "floor_m"), ("b4", "floor_c"),
             ("b1", "floor_m"), ("b1", "floor_c"), ("b4", "b1"))
    lookup = {(row["arm"], row["neutral_item_id"]): row for row in detailed}
    for pair_index, (left, right) in enumerate(pairs):
        common = [item["neutral_item_id"] for item in item_rows
                  if lookup[left, item["neutral_item_id"]]["status"] == "SCORABLE"
                  and lookup[right, item["neutral_item_id"]]["status"] == "SCORABLE"]
        metrics = {}
        for metric_index, metric in enumerate(METRICS):
            diffs = [float(lookup[left, n][metric]) - float(lookup[right, n][metric])
                     for n in common]
            wins = sum(value > 1e-12 for value in diffs)
            losses = sum(value < -1e-12 for value in diffs)
            ties = len(diffs) - wins - losses
            metrics[metric] = {**bootstrap_mean(diffs,
                seed=29000 + pair_index * 100 + metric_index),
                "wins_ties_losses": [wins, ties, losses],
                "two_sided_exact_sign_p": sign_test_two_sided(wins, losses)}
        comparisons[f"{left}_minus_{right}"] = {"paired_items": common,
                                                  "n": len(common), "metrics": metrics}

    failures = {arm: [
        {"neutral_item_id": item["neutral_item_id"],
         "reason": status[arm, item["neutral_item_id"]]["coverage_failure_reason"]}
        for item in item_rows if status[arm, item["neutral_item_id"]]["status"] != "SCORABLE"
    ] for arm in ARMS}
    summary = {
        "analysis_class": "exploratory_postspecified_except_frozen_primary_metrics",
        "primary_metrics": ["spearman", "precision_at_10"],
        "exploratory_metrics": [m for m in METRICS if m not in {"spearman", "precision_at_10"}],
        "bootstrap": {"replicates": 10000, "interval": "percentile 95%",
                      "resampling_unit": "assay/item", "conditional_on_scorable_items": True},
        "aggregate": aggregate,
        "paired_comparisons": comparisons,
        "coverage_failures": failures,
        "provenance": {
            "blind_bundle_sha256": sha(OUT / "blind_bundle_manifest.json"),
            "primary_rows_sha256": sha(primary_path),
            "evaluation_integrity_sha256": sha(OUT / "evaluation_integrity.json"),
            "execution_amendment_sha256": sha(OUT / "evaluation_execution_amendment.json"),
            "label_archive_sha256": sha(RAW),
            "other_135_labels_opened_by_this_analysis": False,
            "comprehensive_rows_sha256": sha(rows_target),
        },
    }
    summary_target.write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n")

    lines = [
        "# Comprehensive ten-item comparison", "",
        "## Executive result", "",
        "The preregistered primary metrics are Spearman correlation and precision at 10. "
        "All other metrics below were specified after model completion and are exploratory.", "",
        "| Arm | Coverage | Mean Spearman (95% bootstrap CI) | Mean P@10 (95% bootstrap CI) | Kendall tau-b | NDCG@10 | AP(top-10) | AUC(top-10) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for arm in ARMS:
        data = aggregate[arm]
        def ci(metric: str) -> str:
            x = data["metrics"][metric]
            return ("—" if x["mean"] is None else
                    f"{x['mean']:.3f} [{x['ci95'][0]:.3f}, {x['ci95'][1]:.3f}]")
        lines.append(f"| {LABELS[arm]} | {data['coverage']['scorable']}/10 | {ci('spearman')} | "
                     f"{ci('precision_at_10')} | {format_metric(data['metrics']['kendall_tau_b']['mean'])} | "
                     f"{format_metric(data['metrics']['ndcg_at_10']['mean'])} | "
                     f"{format_metric(data['metrics']['average_precision_top_10']['mean'])} | "
                     f"{format_metric(data['metrics']['roc_auc_top_10']['mean'])} |")

    lines += ["", "## Additional exploratory summaries", "",
              "| Arm | Pearson | P@5 | P@20 | MRR(true best) | Top-1 hit | Top-5 overlap | Norm. top-10 regret ↓ | Mean true percentile of predicted top-10 |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for arm in ARMS:
        m = aggregate[arm]["metrics"]
        lines.append("| " + LABELS[arm] + " | " + " | ".join(format_metric(m[key]["mean"])
            for key in ("pearson", "precision_at_5", "precision_at_20",
                        "reciprocal_rank_true_best", "top_1_hit", "top_5_overlap",
                        "normalized_top_10_regret", "mean_true_percentile_top_10")) + " |")

    lines += ["", "## Paired Spearman comparisons", "",
              "Positive values favor the first-named arm. Intervals resample paired items; sign-test p-values are exploratory and unadjusted.", "",
              "| Contrast | Paired n | Mean difference (95% bootstrap CI) | Win/tie/loss | Exact sign p |",
              "|---|---:|---:|---:|---:|"]
    for name, comparison in comparisons.items():
        x = comparison["metrics"]["spearman"]
        ci_text = "—" if x["mean"] is None else f"{x['mean']:.3f} [{x['ci95'][0]:.3f}, {x['ci95'][1]:.3f}]"
        wtl = "/".join(str(v) for v in x["wins_ties_losses"])
        p = format_metric(x["two_sided_exact_sign_p"])
        lines.append(f"| {name.replace('_minus_', ' − ')} | {comparison['n']} | {ci_text} | {wtl} | {p} |")

    lines += ["", "## Coverage failures", ""]
    for arm in ("b1", "b2", "b4"):
        lines.append(f"### {LABELS[arm]}")
        lines.append("")
        if failures[arm]:
            lines.extend(f"- {row['neutral_item_id']}: {row['reason']}" for row in failures[arm])
        else:
            lines.append("None.")
        lines.append("")

    lines += [
        "## Interpretation and limitations", "",
        "- Floor M has the strongest fully covered preregistered result. B4's conditional mean is similar, but its 6/10 coverage prevents claiming equivalence or superiority.",
        "- B4 and B1 conditional means describe different, non-random item subsets. Cross-arm conditional means are therefore vulnerable to coverage-selection bias; paired contrasts are more defensible but often have very small n.",
        "- B2 has zero schema-valid outputs and cannot be scored. This is a coverage result, not evidence of zero biological accuracy.",
        "- The ten assays were selected by a frozen stratified rule and do not estimate the other 135 assays. Model family and tool access differ together, so this is not a causal tool-access experiment.",
        "- Bootstrap intervals are descriptive with at most ten assay-level units. Exploratory metrics and sign tests were not preregistered, and no multiplicity correction was applied.",
        "- The prospective human content audit was replaced by a disclosed automated audit at the user's instruction; this is a protocol deviation.",
        "- B4 uses a moving model alias and generic sequence/backbone proxy evidence, which may be misaligned with each assay endpoint.",
        "",
        "## Integrity", "",
        f"Blind bundle SHA-256: `{summary['provenance']['blind_bundle_sha256']}`  ",
        f"Frozen primary rows SHA-256: `{summary['provenance']['primary_rows_sha256']}`  ",
        f"Comprehensive rows SHA-256: `{summary['provenance']['comprehensive_rows_sha256']}`  ",
        "Only the authorized ten labels were read; the other 135 remained unopened by this analysis.", "",
    ]
    report_target.write_text("\n".join(lines))
    print(json.dumps({"report": str(report_target), "coverage": {
        arm: aggregate[arm]["coverage"]["scorable"] for arm in ARMS},
        "mean_spearman": {arm: aggregate[arm]["metrics"]["spearman"]["mean"] for arm in ARMS}},
        sort_keys=True))


if __name__ == "__main__":
    main()
