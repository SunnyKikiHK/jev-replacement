"""Evaluate the baseline and replacement classifiers on the same dataset."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Callable

from config import CATEGORIES, DATASET_PATH, EXAMPLE_DIR, REPO_ROOT
from llm_classifier import ClassificationResult, classify_llm

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.evaluate_predictions import (  # noqa: E402
    bootstrap_delta_intervals,
    per_label_deltas,
)


def load_dataset(path: Path = DATASET_PATH) -> list[dict[str, str]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def calculate_metrics(
    results: list[ClassificationResult], labels: list[str]
) -> dict[str, Any]:
    total = len(results)
    correct = sum(result.predicted == result.expected for result in results)
    failed = sum(result.error is not None for result in results)
    missing = sum(result.predicted is None and result.error is None for result in results)

    per_label: dict[str, dict[str, float | int]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for label in labels:
        true_positive = sum(
            result.expected == label and result.predicted == label for result in results
        )
        false_positive = sum(
            result.expected != label and result.predicted == label for result in results
        )
        false_negative = sum(
            result.expected == label and result.predicted != label for result in results
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1": round(f1, 4),
            "support": sum(result.expected == label for result in results),
        }
        precisions.append(precision)
        recalls.append(recall)
        f1s.append(f1)

    latencies = sorted(result.latency_ms for result in results)
    costs = [result.cost_usd or 0.0 for result in results]
    confidences = [
        result.confidence
        for result in results
        if result.confidence is not None and result.predicted is not None
    ]
    accepted = [
        result
        for result in results
        if result.confidence is not None
        and result.confidence >= 0.8
        and result.predicted is not None
    ]

    return {
        "total": total,
        "correct": correct,
        "accuracy": round(correct / total, 4) if total else 0.0,
        "macro_precision": round(sum(precisions) / len(precisions), 4)
        if precisions
        else 0.0,
        "macro_recall": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
        "macro_f1": round(sum(f1s) / len(f1s), 4) if f1s else 0.0,
        "provider_errors": failed,
        "missing_predictions": missing,
        "latency_ms": {
            "mean": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
            "p50": latencies[len(latencies) // 2] if latencies else 0.0,
            "p95": latencies[min(len(latencies) - 1, int(len(latencies) * 0.95))]
            if latencies
            else 0.0,
        },
        "cost_usd": {
            "total": round(sum(costs), 8),
            "mean_per_request": round(sum(costs) / len(costs), 8) if costs else 0.0,
        },
        "confidence": {
            "mean": round(sum(confidences) / len(confidences), 4) if confidences else None,
            "accepted_at_0_8": len(accepted),
            "coverage_at_0_8": round(len(accepted) / total, 4) if total else 0.0,
            "accuracy_at_0_8": round(
                sum(result.predicted == result.expected for result in accepted)
                / len(accepted),
                4,
            )
            if accepted
            else None,
        },
        "per_label": per_label,
        "prediction_counts": dict(
            Counter(result.predicted or "<none>" for result in results)
        ),
    }


def run_classifier(
    rows: list[dict[str, str]],
    classifier: Callable[[dict[str, str]], ClassificationResult],
) -> list[ClassificationResult]:
    results = []
    for index, row in enumerate(rows, start=1):
        result = classifier(row)
        status = result.predicted or f"ERROR: {result.error}"
        print(
            f"[{index:02d}/{len(rows):02d}] {row['id']}: "
            f"expected={row['label']} predicted={status} "
            f"latency={result.latency_ms:.1f}ms"
        )
        results.append(result)
    return results


def evaluate_mode(
    mode: str,
    rows: list[dict[str, str]],
    classifier: Callable[[dict[str, str]], ClassificationResult],
    output_path: Path,
) -> dict[str, Any]:
    results = run_classifier(rows, classifier)
    metrics = calculate_metrics(results, list(CATEGORIES))
    payload = {
        "mode": mode,
        "dataset_size": len(rows),
        "metrics": metrics,
        "results": [result.to_dict() for result in results],
    }
    output_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(metrics, indent=2, ensure_ascii=True))
    return payload


def compare_payloads(
    baseline: dict[str, Any], candidate: dict[str, Any]
) -> dict[str, Any]:
    baseline_metrics = baseline["metrics"]
    candidate_metrics = candidate["metrics"]
    gold = {
        result["id"]: {"id": result["id"], "label": result["expected"]}
        for result in baseline["results"]
    }
    baseline_predictions = {
        result["id"]: {
            "id": result["id"],
            "predicted": result["predicted"],
            "error": result["error"],
        }
        for result in baseline["results"]
    }
    candidate_predictions = {
        result["id"]: {
            "id": result["id"],
            "predicted": result["predicted"],
            "error": result["error"],
        }
        for result in candidate["results"]
    }

    return {
        "accuracy_delta": round(
            candidate_metrics["accuracy"] - baseline_metrics["accuracy"], 4
        ),
        "macro_f1_delta": round(
            candidate_metrics["macro_f1"] - baseline_metrics["macro_f1"], 4
        ),
        "latency_p50_ratio": round(
            candidate_metrics["latency_ms"]["p50"]
            / baseline_metrics["latency_ms"]["p50"],
            4,
        )
        if baseline_metrics["latency_ms"]["p50"]
        else None,
        "cost_ratio": round(
            candidate_metrics["cost_usd"]["mean_per_request"]
            / baseline_metrics["cost_usd"]["mean_per_request"],
            4,
        )
        if baseline_metrics["cost_usd"]["mean_per_request"]
        else None,
        "per_label_delta": per_label_deltas(baseline_metrics, candidate_metrics),
        "bootstrap": bootstrap_delta_intervals(
            gold,
            baseline_predictions,
            candidate_predictions,
            label_field="label",
            prediction_field="predicted",
            samples=1000,
            seed=42,
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["llm", "jev", "compare"],
        default="llm",
        help="Classifier implementation to evaluate.",
    )
    parser.add_argument("--dataset", type=Path, default=DATASET_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    rows = load_dataset(args.dataset)

    if args.mode in {"llm", "compare"}:
        evaluate_mode("llm", rows, classify_llm, EXAMPLE_DIR / "evaluation-llm.json")

    if args.mode == "jev":
        try:
            from jev_classifier import classify_jev
        except ImportError as exc:
            raise SystemExit(
                "Jev replacement is not installed yet. Complete the replacement "
                "milestone before running --mode jev."
            ) from exc
        evaluate_mode("jev", rows, classify_jev, EXAMPLE_DIR / "evaluation-jev.json")

    if args.mode == "compare":
        try:
            from jev_classifier import classify_jev
        except ImportError as exc:
            raise SystemExit(
                "Jev replacement is not installed yet. Complete the replacement "
                "milestone before running --mode compare."
            ) from exc
        evaluate_mode("jev", rows, classify_jev, EXAMPLE_DIR / "evaluation-jev.json")
        baseline = json.loads(
            (EXAMPLE_DIR / "evaluation-llm.json").read_text(encoding="utf-8")
        )
        candidate = json.loads(
            (EXAMPLE_DIR / "evaluation-jev.json").read_text(encoding="utf-8")
        )
        comparison = compare_payloads(baseline, candidate)
        (EXAMPLE_DIR / "comparison.json").write_text(
            json.dumps(comparison, indent=2) + "\n", encoding="utf-8"
        )
        print("COMPARISON")
        print(json.dumps(comparison, indent=2))


if __name__ == "__main__":
    main()
