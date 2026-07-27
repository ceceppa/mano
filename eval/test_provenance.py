from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

import provenance


REPO_ROOT = Path(__file__).resolve().parent.parent


class ProvenanceTests(unittest.TestCase):
    def test_repository_markers_are_valid_and_mapped(self) -> None:
        rules = provenance.discover_rules(REPO_ROOT)

        self.assertIn("post-hook-findings-triage", rules)
        self.assertIn("post-stories-hook-findings-triage", rules)
        self.assertEqual(
            len(rules["post-hook-findings-triage"].occurrences),
            5,
        )
        self.assertEqual(
            rules["post-hook-findings-triage"].evals,
            (
                "hook-triage-no-approval",
                "hook-triage-selected-only",
                "hook-triage-start-no-approval",
                "hook-triage-rules-no-approval",
            ),
        )

    def test_retirement_probe_strips_every_installed_occurrence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-provenance-test-") as raw:
            project = Path(raw)
            subprocess.run(
                ["node", str(REPO_ROOT / "bin" / "mano-plan.js"), "install", "--yes"],
                cwd=project,
                check=True,
                capture_output=True,
                text=True,
            )

            removed = provenance.strip_rules(project, {"post-hook-findings-triage"})
            self.assertEqual(removed, {"post-hook-findings-triage": 5})

            stripped_sections = {
                "AGENTS.md": "When a just-run `post-start`, `post-spec`, or `post-rules`",
                "_mano/workflow.md": "## Post-Hook Findings Triage",
                "_mano/skills/start.md": "## Addressing post-start hook findings",
                "_mano/skills/spec.md": "## Addressing post-spec hook findings",
                "_mano/skills/rules.md": "## Addressing post-rules hook findings",
            }
            for relative, heading in stripped_sections.items():
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=post-hook-findings-triage;", text)
                self.assertNotIn(heading, text)

            stories = (project / "_mano" / "skills" / "stories.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("id=post-stories-hook-findings-triage;", stories)


if __name__ == "__main__":
    unittest.main()
