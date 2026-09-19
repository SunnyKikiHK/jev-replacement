from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.scan_candidates import scan


class ScanCandidatesTests(unittest.TestCase):
    def test_finds_classifier_implementation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "triage.py").write_text(
                "def classify_ticket(text):\n"
                "    return 'billing' if 'invoice' in text else 'other'\n",
                encoding="utf-8",
            )

            candidates = scan(root, max_file_bytes=100_000)

        categories = {candidate.category for candidate in candidates}
        self.assertIn("semantic-decision", categories)
        self.assertIn("heuristic", categories)


if __name__ == "__main__":
    unittest.main()

