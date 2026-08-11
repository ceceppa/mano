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
        self.assertIn("project-rule-story-coverage", rules)
        self.assertIn("dev-yolo-batch", rules)
        self.assertIn("ui-phase-preview-ownership", rules)
        self.assertIn("public-interface-contract-readiness", rules)
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
        self.assertEqual(
            len(rules["project-rule-story-coverage"].occurrences),
            5,
        )
        self.assertEqual(
            rules["project-rule-story-coverage"].evals,
            ("stories-project-rule-coverage",),
        )
        self.assertEqual(
            len(rules["dev-yolo-batch"].occurrences),
            7,
        )
        self.assertEqual(
            rules["dev-yolo-batch"].evals,
            ("dev-yolo-batch", "dev-yolo-blocker", "dev-default-single"),
        )
        self.assertEqual(
            len(rules["ui-phase-preview-ownership"].occurrences),
            16,
        )
        self.assertEqual(
            rules["ui-phase-preview-ownership"].evals,
            ("ui-phase-preview", "ui-no-phase-preview"),
        )
        self.assertEqual(
            len(rules["public-interface-contract-readiness"].occurrences),
            24,
        )
        self.assertEqual(
            rules["public-interface-contract-readiness"].evals,
            ("spec-public-interface-completeness", "stories-public-interface-gap"),
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

            removed_yolo = provenance.strip_rules(project, {"dev-yolo-batch"})
            # --yes installs AGENTS.md, CLAUDE.md, workflow.md, and dev.md; the
            # optional .cursorrules surface is intentionally not installed.
            self.assertEqual(removed_yolo, {"dev-yolo-batch": 6})
            for relative in (
                "AGENTS.md",
                "CLAUDE.md",
                "_mano/workflow.md",
                "_mano/skills/dev.md",
            ):
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=dev-yolo-batch;", text)

            removed_ui = provenance.strip_rules(
                project, {"ui-phase-preview-ownership"}
            )
            self.assertEqual(
                removed_ui,
                {"ui-phase-preview-ownership": 16},
            )
            for relative in (
                "_mano/workflow.md",
                "_mano/skills/start.md",
                "_mano/skills/ui.md",
                "_mano/templates/design-brief.md",
                "_mano/hooks/post-ui.example.md",
            ):
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=ui-phase-preview-ownership;", text)

            removed_interface = provenance.strip_rules(
                project, {"public-interface-contract-readiness"}
            )
            self.assertEqual(
                removed_interface,
                {"public-interface-contract-readiness": 24},
            )
            for relative in (
                "AGENTS.md",
                "_mano/skills/start.md",
                "_mano/skills/spec.md",
                "_mano/skills/stories.md",
                "_mano/skills/dev.md",
                "_mano/skills/review.md",
                "_mano/templates/tech-spec.md",
            ):
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=public-interface-contract-readiness;", text)

            stripped_prompt = "\n".join(
                (project / relative).read_text(encoding="utf-8")
                for relative in (
                    "AGENTS.md",
                    "_mano/workflow.md",
                    "_mano/skills/start.md",
                    "_mano/skills/spec.md",
                    "_mano/skills/stories.md",
                    "_mano/templates/tech-spec.md",
                )
            )
            for incident_phrase in (
                "node _mano/scripts/state.js --spec",
                "Public interface completeness check",
                "Public-interface readiness",
                "A section title or broad capability list is not a usable contract",
                "Exact operation / event",
                "Final-story phase-contract gate",
                "Phase-contract safety net",
            ):
                self.assertNotIn(incident_phrase, stripped_prompt)


if __name__ == "__main__":
    unittest.main()
