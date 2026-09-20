from __future__ import annotations

import unittest
from pathlib import Path

from scripts.update_repository_metadata import build_requests, load_metadata


ROOT = Path(__file__).resolve().parents[1]


class RepositoryMetadataTests(unittest.TestCase):
    def test_metadata_builds_description_and_topic_requests(self) -> None:
        metadata = load_metadata(ROOT / ".github" / "repository-metadata.json")
        requests = build_requests("SunnyKikiHK/jev-replacement", metadata)

        self.assertEqual(len(requests), 2)
        self.assertEqual(requests[0]["method"], "PATCH")
        self.assertIn("description", requests[0]["payload"])
        self.assertEqual(requests[1]["method"], "PUT")
        self.assertIn("jev", requests[1]["payload"]["names"])


if __name__ == "__main__":
    unittest.main()

