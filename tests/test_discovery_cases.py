from __future__ import annotations

import json
import unittest
from pathlib import Path


CASES_PATH = Path(__file__).resolve().parents[1] / "evals" / "discovery-cases.jsonl"


class DiscoveryCasesTests(unittest.TestCase):
    def test_cases_cover_positive_and_negative_discovery(self) -> None:
        cases = [
            json.loads(line)
            for line in CASES_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertGreaterEqual(len(cases), 8)
        ids = [case["id"] for case in cases]
        self.assertEqual(len(ids), len(set(ids)))

        expected_values = {case["expected"] for case in cases}
        self.assertEqual(expected_values, {"invoke", "not_invoke"})

        for case in cases:
            self.assertTrue(case["request"])
            self.assertTrue(case["rationale"])
            self.assertIn(case["expected"], {"invoke", "not_invoke"})


if __name__ == "__main__":
    unittest.main()

