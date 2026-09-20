from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.validate_skill import validate


class ValidateSkillTests(unittest.TestCase):
    def test_valid_minimal_skill(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sample-skill"
            (root / "agents").mkdir(parents=True)
            (root / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Sample"\n',
                encoding="ascii",
            )
            (root / "SKILL.md").write_text(
                "---\n"
                "name: sample-skill\n"
                "license: MIT\n"
                "metadata:\n"
                '  version: "0.1.0"\n'
                'description: "Use this skill for a bounded sample task."\n'
                "---\n\n"
                "# Sample\n",
                encoding="ascii",
            )

            self.assertEqual(validate(root), [])

    def test_invalid_name_and_broken_link(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir) / "sample-skill"
            (root / "agents").mkdir(parents=True)
            (root / "agents" / "openai.yaml").write_text(
                'interface:\n  display_name: "Sample"\n',
                encoding="ascii",
            )
            (root / "SKILL.md").write_text(
                "---\n"
                "name: WrongName\n"
                "license: MIT\n"
                "metadata:\n"
                '  version: "0.1.0"\n'
                'description: "Use this skill for a bounded sample task."\n'
                "---\n\n"
                "# Sample\n\n"
                "[Missing](references/missing.md)\n",
                encoding="ascii",
            )

            failures = validate(root)
            self.assertTrue(any("lowercase" in failure for failure in failures))
            self.assertTrue(any("Broken local link" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
