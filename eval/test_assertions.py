from __future__ import annotations

import contextlib
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


HOMED_BACKLOG = """# Backlog

## Items

### Record an expense
- **Type:** feature
- **Source:** product-brief.md
- **Context:**
  Amount, category, optional note; stamped with the current date.
- **Status:** backlog

### Stated: minimum runtime
- **Type:** spec-gap
- **Source:** product-brief.md
- **Context:**
  Stated directive (verbatim): "**Runtime:** Node.js (v20 or newer)."
  No feature item owns this; the tech spec does.
- **Status:** backlog

### Stated: project directory structure
- **Type:** rule-gap
- **Source:** product-brief.md
- **Context:**
  Stated directive, from "Project directory structure": src/store.js, src/cli.js, test/store.test.js.
  No feature item owns this; project rules do.
- **Status:** backlog
"""


class B1DirectiveHomingAssertionTests(unittest.TestCase):
    def _ctx(self, stack, backlog: str) -> assertions.Ctx:
        raw = stack.enter_context(
            tempfile.TemporaryDirectory(prefix="mano-homing-test-")
        )
        output = Path(raw) / "_mano_output"
        output.mkdir(parents=True)
        (output / "backlog.md").write_text(backlog, encoding="utf-8")
        return assertions.Ctx(output, phase=None)

    def _run(self, fn, backlog: str):
        with contextlib.ExitStack() as stack:
            return fn(self._ctx(stack, backlog))

    def test_accepts_both_directives_homed_as_gap_items(self):
        self.assertEqual(
            self._run(
                assertions.unhomed_runtime_directive_homed_as_spec_gap,
                HOMED_BACKLOG,
            ),
            [],
        )
        self.assertEqual(
            self._run(
                assertions.unhomed_structure_directive_homed_as_rule_gap,
                HOMED_BACKLOG,
            ),
            [],
        )

    def test_rejects_a_backlog_with_no_gap_items(self):
        dropped = HOMED_BACKLOG.split("### Stated: minimum runtime")[0]
        runtime = self._run(
            assertions.unhomed_runtime_directive_homed_as_spec_gap, dropped
        )
        structure = self._run(
            assertions.unhomed_structure_directive_homed_as_rule_gap, dropped
        )
        self.assertEqual(len(runtime), 1)
        self.assertIn("no spec-gap item written", runtime[0].detail)
        self.assertEqual(len(structure), 1)
        self.assertIn("no rule-gap item written", structure[0].detail)

    def test_rejects_a_gap_item_that_dropped_the_stated_values(self):
        summarised = HOMED_BACKLOG.replace(
            "  Stated directive, from \"Project directory structure\": "
            "src/store.js, src/cli.js, test/store.test.js.",
            "  The document states a project directory structure.",
        )
        failures = self._run(
            assertions.unhomed_structure_directive_homed_as_rule_gap, summarised
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("none carries the stated file layout", failures[0].detail)

    def test_rejects_a_spec_gap_item_that_is_about_something_else(self):
        # A spec-gap item exists, but the runtime directive still went nowhere —
        # the count is not the contract, carrying the stated value is.
        other = HOMED_BACKLOG.replace(
            '  Stated directive (verbatim): "**Runtime:** Node.js (v20 or newer)."\n'
            "  No feature item owns this; the tech spec does.",
            "  How expenses are stored on disk is not stated.",
        )
        failures = self._run(
            assertions.unhomed_runtime_directive_homed_as_spec_gap, other
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("none carries the stated runtime constraint", failures[0].detail)

    def test_rejects_the_runtime_directive_homed_under_the_wrong_type(self):
        # Routed to mano rules instead of mano spec: no spec-gap item survives,
        # so the tech spec never sees the constraint.
        misrouted = HOMED_BACKLOG.replace(
            "### Stated: minimum runtime\n- **Type:** spec-gap",
            "### Stated: minimum runtime\n- **Type:** rule-gap",
        )
        failures = self._run(
            assertions.unhomed_runtime_directive_homed_as_spec_gap, misrouted
        )
        self.assertEqual(len(failures), 1)
        self.assertIn("no spec-gap item written", failures[0].detail)


if __name__ == "__main__":
    unittest.main()
