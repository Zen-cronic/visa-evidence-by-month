"""The check counts claimed in the README and in references/testing.md must equal the real number of tests."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def count(start_dir: str, pattern: str) -> int:
    suite = unittest.defaultTestLoader.discover(str(ROOT / start_dir), pattern=pattern, top_level_dir=str(ROOT / start_dir))
    return suite.countTestCases()


class ReadmeCountsAreTrue(unittest.TestCase):
    def test_counts_match(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        rules = int(re.search(r"(\d+) rule checks", text).group(1))
        runs = int(re.search(r"(\d+) simulated runs", text).group(1))
        self.assertEqual(rules, count("tools/rulecheck", "test_rules.py"))
        self.assertEqual(runs, count("tools/simrun", "test_simulate.py"))

    def test_testing_md_counts_match(self):
        text = (ROOT / "relationship-evidence-pack/references/testing.md").read_text(encoding="utf-8")
        rules = int(re.search(r"\((\d+) rule cases\)", text).group(1))
        runs = int(re.search(r"\((\d+) control-flow scenarios\)", text).group(1))
        self.assertEqual(rules, count("tools/rulecheck", "test_rules.py"))
        self.assertEqual(runs, count("tools/simrun", "test_simulate.py"))


if __name__ == "__main__":
    unittest.main()
