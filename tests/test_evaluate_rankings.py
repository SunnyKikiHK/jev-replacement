from __future__ import annotations

import unittest

from scripts.evaluate_rankings import evaluate_one, summarize


class EvaluateRankingsTests(unittest.TestCase):
    def test_recall_mrr_and_ndcg(self) -> None:
        gold = {"id": "q1", "relevance": {"d1": 3, "d2": 1, "d3": 0}}
        baseline = {"id": "q1", "ranked": ["d3", "d1", "d2"], "latency_ms": 20}
        candidate = {"id": "q1", "ranked": ["d1", "d3", "d2"], "latency_ms": 10}

        baseline_metrics = evaluate_one(gold, baseline, [1, 2])
        candidate_metrics = evaluate_one(gold, candidate, [1, 2])

        self.assertEqual(baseline_metrics["recall@1"], 0.0)
        self.assertEqual(baseline_metrics["mrr@2"], 0.5)
        self.assertEqual(candidate_metrics["recall@1"], 0.5)
        self.assertEqual(candidate_metrics["mrr@1"], 1.0)
        self.assertGreater(candidate_metrics["ndcg@2"], baseline_metrics["ndcg@2"])

        summary = summarize([candidate_metrics], [1, 2])
        self.assertEqual(summary["queries"], 1)
        self.assertEqual(summary["latency_ms"]["p95"], 10.0)


if __name__ == "__main__":
    unittest.main()

