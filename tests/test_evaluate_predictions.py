from __future__ import annotations

import unittest

from scripts.evaluate_predictions import (
    bootstrap_delta_intervals,
    metrics,
    per_label_deltas,
)


class EvaluatePredictionsTests(unittest.TestCase):
    def test_metrics_and_confidence_coverage(self) -> None:
        gold = {
            "1": {"id": "1", "label": "a"},
            "2": {"id": "2", "label": "b"},
            "3": {"id": "3", "label": "b"},
        }
        baseline = {
            "1": {"id": "1", "predicted": "a", "latency_ms": 10},
            "2": {"id": "2", "predicted": "a", "latency_ms": 20},
            "3": {"id": "3", "predicted": "b", "latency_ms": 30},
        }
        candidate = {
            "1": {
                "id": "1",
                "predicted": "a",
                "confidence": 0.9,
                "latency_ms": 5,
                "cost_usd": 0.001,
            },
            "2": {
                "id": "2",
                "predicted": "b",
                "confidence": 0.7,
                "latency_ms": 6,
                "cost_usd": 0.001,
            },
            "3": {
                "id": "3",
                "predicted": "b",
                "confidence": 0.95,
                "latency_ms": 7,
                "cost_usd": 0.001,
            },
        }

        baseline_metrics = metrics(
            gold,
            baseline,
            label_field="label",
            prediction_field="predicted",
        )
        candidate_metrics = metrics(
            gold,
            candidate,
            label_field="label",
            prediction_field="predicted",
        )

        self.assertEqual(baseline_metrics["accuracy"], 0.6667)
        self.assertEqual(candidate_metrics["accuracy"], 1.0)
        self.assertEqual(candidate_metrics["confidence"]["0.8"]["accepted"], 2)
        self.assertEqual(candidate_metrics["confidence"]["0.8"]["coverage"], 0.6667)
        self.assertEqual(candidate_metrics["confidence"]["0.8"]["accuracy"], 1.0)

        deltas = per_label_deltas(baseline_metrics, candidate_metrics)
        self.assertGreater(deltas["b"]["f1"], 0)

        intervals = bootstrap_delta_intervals(
            gold,
            baseline,
            candidate,
            label_field="label",
            prediction_field="predicted",
            samples=100,
            seed=7,
        )
        self.assertEqual(intervals["completed_pairs"], 3)
        self.assertLessEqual(
            intervals["accuracy_delta"]["lower"],
            intervals["accuracy_delta"]["upper"],
        )
        self.assertLessEqual(
            intervals["macro_f1_delta"]["lower"],
            intervals["macro_f1_delta"]["upper"],
        )


if __name__ == "__main__":
    unittest.main()
