#!/usr/bin/env python3
"""Compare baseline and candidate prediction files against the same gold set."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def keyed(rows: list[dict[str, Any]], key_field: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = str(row[key_field])
        if key in result:
            raise ValueError(f"Duplicate {key_field}: {key}")
        result[key] = row
    return result


def metrics(
    gold: dict[str, dict[str, Any]],
    predictions: dict[str, dict[str, Any]],
    *,
    label_field: str,
    prediction_field: str,
) -> dict[str, Any]:
    labels = sorted({str(row[label_field]) for row in gold.values()})
    paired = []
    for key, gold_row in gold.items():
        prediction = predictions.get(key)
        paired.append((gold_row, prediction))

    total = len(paired)
    completed = [(g, p) for g, p in paired if p is not None and p.get("error") is None]
    correct = sum(
        str(p.get(prediction_field)) == str(g[label_field])
        for g, p in completed
        if p.get(prediction_field) is not None
    )
    missing = total - len(completed)
    errors = sum(p is not None and p.get("error") is not None for _, p in paired)

    per_label: dict[str, dict[str, float | int]] = {}
    for label in labels:
        tp = sum(
            str(g[label_field]) == label and str(p.get(prediction_field)) == label
            for g, p in completed
        )
        fp = sum(
            str(g[label_field]) != label and str(p.get(prediction_field)) == label
            for g, p in completed
        )
        fn = sum(
            str(g[label_field]) == label and str(p.get(prediction_field)) != label
            for g, p in completed
        )
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(str(g[label_field]) == label for g in gold.values()),
        }

    latencies = sorted(
        float(p["latency_ms"])
        for _, p in completed
        if isinstance(p.get("latency_ms"), (int, float))
    )
    costs = [
        float(p.get("cost_usd") or 0.0)
        for _, p in completed
    ]
    confidences = [
        (str(g[label_field]), float(p["confidence"]), str(p[prediction_field]))
        for g, p in completed
        if isinstance(p.get("confidence"), (int, float))
    ]

    def pctl(values: list[float], fraction: float) -> float:
        if not values:
            return 0.0
        index = min(len(values) - 1, round((len(values) - 1) * fraction))
        return round(values[index], 4)

    thresholds = [0.5, 0.7, 0.8, 0.9, 0.95]
    confidence_metrics = {}
    for threshold in thresholds:
        accepted = [pair for pair in confidences if pair[1] >= threshold]
        confidence_metrics[str(threshold)] = {
            "coverage": round(len(accepted) / total, 4) if total else 0.0,
            "accuracy": round(
                sum(expected == predicted for expected, _, predicted in accepted)
                / len(accepted),
                4,
            )
            if accepted
            else None,
            "accepted": len(accepted),
        }

    return {
        "total": total,
        "completed": len(completed),
        "errors": errors,
        "missing": missing,
        "correct": correct,
        "accuracy": round(correct / len(completed), 4) if completed else 0.0,
        "macro_f1": round(
            sum(float(value["f1"]) for value in per_label.values()) / len(per_label),
            4,
        )
        if per_label
        else 0.0,
        "latency_ms": {
            "p50": pctl(latencies, 0.5),
            "p95": pctl(latencies, 0.95),
        },
        "cost_usd": {
            "total": round(sum(costs), 8),
            "mean": round(sum(costs) / len(costs), 8) if costs else 0.0,
        },
        "confidence": confidence_metrics,
        "per_label": per_label,
        "prediction_counts": dict(
            Counter(
                str(p.get(prediction_field) or "<none>")
                for _, p in completed
            )
        ),
    }


def ratio(candidate: float, baseline: float) -> float | None:
    if not baseline:
        return None
    return round(candidate / baseline, 4)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gold", type=Path, required=True)
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--key-field", default="id")
    parser.add_argument("--label-field", default="label")
    parser.add_argument("--prediction-field", default="predicted")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    gold = keyed(read_jsonl(args.gold), args.key_field)
    baseline = keyed(read_jsonl(args.baseline), args.key_field)
    candidate = keyed(read_jsonl(args.candidate), args.key_field)

    baseline_metrics = metrics(
        gold,
        baseline,
        label_field=args.label_field,
        prediction_field=args.prediction_field,
    )
    candidate_metrics = metrics(
        gold,
        candidate,
        label_field=args.label_field,
        prediction_field=args.prediction_field,
    )

    payload = {
        "baseline": baseline_metrics,
        "candidate": candidate_metrics,
        "comparison": {
            "accuracy_delta": round(
                candidate_metrics["accuracy"] - baseline_metrics["accuracy"], 4
            ),
            "macro_f1_delta": round(
                candidate_metrics["macro_f1"] - baseline_metrics["macro_f1"], 4
            ),
            "latency_p50_ratio": ratio(
                candidate_metrics["latency_ms"]["p50"],
                baseline_metrics["latency_ms"]["p50"],
            ),
            "latency_p95_ratio": ratio(
                candidate_metrics["latency_ms"]["p95"],
                baseline_metrics["latency_ms"]["p95"],
            ),
            "mean_cost_ratio": ratio(
                candidate_metrics["cost_usd"]["mean"],
                baseline_metrics["cost_usd"]["mean"],
            ),
        },
    }

    rendered = json.dumps(payload, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()

