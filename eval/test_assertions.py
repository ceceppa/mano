from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import assertions


PASSING_STORY = """### STORY-1: Public report formatter

#### What and why
Plugin authors can format reports through a stable public class.

#### Done when
- [ ] Formatting a report as plain text and Markdown returns the selected representation.
- [ ] The Markdown API reference page for `ReportFormatter` exists with an overview, one minimal example, and its public methods.
- [ ] The exported `ReportFormatter` class has a source documentation comment that gives its one-line purpose.

#### Not this story
- HTML and PDF output.

#### Implementation Reference
- **Rules:** `_mano_output/project-rules.md §Documentation` — both documentation channels are required
- **Files:** `src/api/ReportFormatter.ts`; `docs/api/report-formatter.md`
- **Build:** public `ReportFormatter` class; source documentation comment directly above its declaration
"""


POINTER_ONLY_STORY = """### STORY-1: Public report formatter

#### What and why
Plugin authors can format reports through a stable public class.

#### Done when
- [ ] Formatting a report as plain text and Markdown returns the selected representation.

#### Not this story
- The `ReportFormatter` documentation page.

#### Implementation Reference
- **Rules:** `_mano_output/project-rules.md §Documentation`
- **Files:** `src/api/ReportFormatter.ts`; `docs/api/report-formatter.md`
- **Build:** public `ReportFormatter` class with a source documentation comment
"""


class ProjectRuleCoverageAssertionTests(unittest.TestCase):
    def _run(self, story: str):
        with tempfile.TemporaryDirectory(prefix="mano-assertion-test-") as raw:
            output = Path(raw) / "_mano_output"
            stories = output / "phase-1" / "stories"
            stories.mkdir(parents=True)
            (stories / "story-1-public-report-formatter.md").write_text(
                story,
                encoding="utf-8",
            )
            ctx = assertions.Ctx(output, phase=1)
            return assertions.public_class_documentation_rule_covered(ctx)

    def test_accepts_concrete_documentation_acceptance_criteria(self):
        self.assertEqual(self._run(PASSING_STORY), [])

    def test_rejects_rule_pointer_without_required_deliverables_in_done_when(self):
        failures = self._run(POINTER_ONLY_STORY)
        self.assertEqual(len(failures), 1)
        self.assertIn("Markdown page Done-when criterion", failures[0].detail)
        self.assertIn("source documentation Done-when criterion", failures[0].detail)

    def test_rejects_missing_markdown_page_content_requirement(self):
        missing_example = PASSING_STORY.replace("one minimal example, and ", "")
        failures = self._run(missing_example)
        self.assertEqual(len(failures), 1)
        self.assertIn("Markdown page minimal-example requirement", failures[0].detail)

    def test_rejects_missing_source_comment_placement_requirement(self):
        missing_placement = PASSING_STORY.replace(
            "; source documentation comment directly above its declaration", ""
        )
        failures = self._run(missing_placement)
        self.assertEqual(len(failures), 1)
        self.assertIn(
            "source documentation direct-placement requirement",
            failures[0].detail,
        )

    def test_rejects_source_documentation_deferred_in_scope_boundary(self):
        source_deferred = PASSING_STORY.replace(
            "- HTML and PDF output.",
            "- Source documentation comments.\n"
            "- HTML and PDF output.",
        )
        failures = self._run(source_deferred)
        self.assertEqual(len(failures), 1)
        self.assertIn("source documentation is not deferred", failures[0].detail)


if __name__ == "__main__":
    unittest.main()
