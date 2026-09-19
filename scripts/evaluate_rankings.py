#!/usr/bin/env python3
"""Compare reranking or retrieval predictions with Recall@K, MRR, and NDCG."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def keyed(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result = {}
    for row in rows:
        key = str(row["id"])
        if key in result:
            raise ValueError(f"Duplicate id: {key}")
        result[key] = row
    return result


def relevance_map(row: dict[str, Any]) -> dict[str, float]:
    relevance = row.get("relevance")
    if isinstance(relevance, dict):
        return {str(key): float(value) for key, value in relevance.items()}
    if isinstance(relevance, list):
        return {str(key): 1.0 for key in relevance}
    raise ValueError("Gold row must contain a relevance list or mapping.")


def dcg(gains: list[float]) -> float:
    return sum(
        (2**gain - 1) / math.log2(index + 2)
        for index, gain in enumerate(gains)
    )


def evaluate_one(
    gold: dict[str, Any],
    prediction: dict[str, Any],
    ks: list[int],
) -> dict[str, Any]:
    relevance = relevance_map(gold)
    ranked = [str(item) for item in prediction.get("ranked", [])]
    relevant_ids = {key for key, value in relevance.items() if value > 0}
    if not relevant_ids:
        raise ValueError(f"Gold row {gold['id']} has no relevant items.")

    metrics: dict[str, Any] = {}
    for k in ks:
        top_k = ranked[:k]
        hits = sum(item in relevant_ids for item in top_k)
        metrics[f"recall@{k}"] = hits / len(relevant_ids)
        metrics[f"precision@{k}"] = hits / k if k else 0.0

        reciprocal_rank = 0.0
        for index, item in enumerate(top_k, start=1):
            if item in relevant_ids:
                reciprocal_rank = 1.0 / index
                break
        metrics[f"mrr@{k}"] = reciprocal_rank

        gains = [relevance.get(item, 0.0) for item in top_k]
        ideal_gains = sorted(relevance.values(), reverse=True)[:k]
        ideal = dcg(ideal_gains)
        metrics[f"ndcg@{k}"] = dcg(gains) / ideal if ideal else 0.0

    metrics["severe_evidence_miss"] = not any(
        item in relevant_ids for item in ranked[: max(ks)]
    )
    if isinstance(prediction.get("latency_ms"), (int, float)):
        metrics["latency_ms"] = float(prediction["latency_ms"])
    if isinstance(prediction.get("cost_usd"), (int, float)):
        metrics["cost_usd"] = float(prediction["cost_usd"])
    return metrics


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, round((len(ordered) - 1) * fraction))
    return round(ordered[index], 4)


def summarize(rows: list[dict[str, Any]], ks: list[int]) -> dict[str, Any]:
    metric_names = [
        f"{name}@{k}"
        for k in ks
        for name in ("recall", "precision", "mrr", "ndcg")
    ]
    summary: dict[str, Any] = {
        "queries": len(rows),
        "metrics": {},
    }
    for name in metric_names:
        values = [float(row[name]) for row in rows]
        summary["metrics"][name] = round(sum(values) / len(values), 4)

    summary["severe_evidence_misses"] = sum(
        bool(row["severe_evidence_miss"]) for row in rows
    )
    latencies = [
        float(row["latency_ms"]) for row in rows if "latency_ms" in row
    ]
    costs = [float(row["cost_usd"]) for row in rows if "cost_usd" in row]
    summary["latency_ms"] = {
        "p50": percentile(latencies, 0.5),
        "p95": percentile(latencies, 0.95),
        "p99": percentile(latencies, 0.99),
    }
    summary["cost_usd"] = {
        "total": round(sum(costs), 8),
        "mean": round(sum(costs) / len(costs), 8) if costs else 0.0,
    }
    return summary


def ratio(candidate: float, baseline: float) -> float | None:
    if not baseline:
        return None
    return round(candidate / baseline, 4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--k", default="1,5,8,10")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    ks = sorted({int(value.strip()) for value in args.k.split(",") if value.strip()})
    if not ks or any(k <= 0 for k in ks):
        raise SystemExit("--k must contain positive integers.")

    gold = keyed(read_jsonl(args.gold))
    baseline = keyed(read_jsonl(args.baseline))
    candidate = keyed(read_jsonl(args.candidate))
    missing = sorted((set(gold) | set(baseline) | set(candidate)) - set(gold))
    if missing:
        raise SystemExit(f"Prediction IDs missing from gold: {', '.join(missing)}")

    baseline_rows = [
        evaluate_one(gold[key], baseline[key], ks)
        for key in gold
        if key in baseline
    ]
    candidate_rows = [
        evaluate_one(gold[key], candidate[key], ks)
        for key in gold
        if key in candidate
    ]
    if len(baseline_rows) != len(gold) or len(candidate_rows) != len(gold):
        raise SystemExit("Baseline and candidate must contain every gold ID.")

    baseline_summary = summarize(baseline_rows, ks)
    candidate_summary = summarize(candidate_rows, ks)
    comparison: dict[str, Any] = {}
    for name in baseline_summary["metrics"]:
        comparison[f"{name}_delta"] = round(
            candidate_summary["metrics"][name] - baseline_summary["metrics"][name],
            4,
        )
    comparison["p95_latency_ratio"] = ratio(
        candidate_summary["latency_ms"]["p95"],
        baseline_summary["latency_ms"]["p95"],
    )
    comparison["mean_cost_ratio"] = ratio(
        candidate_summary["cost_usd"]["mean"],
        baseline_summary["cost_usd"]["mean"],
    )

    payload = {
        "ks": ks,
        "baseline": baseline_summary,
        "candidate": candidate_summary,
        "comparison": comparison,
    }
    rendered = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

