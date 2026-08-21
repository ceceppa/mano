from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class ReviewValidationContractTests(unittest.TestCase):
    def test_phase_brief_plans_validation_before_assumptions(self) -> None:
        template = _read("src/templates/phase-brief.md")
        exit_at = template.index("## Exit Criteria")
        validation_at = template.index("## Validation Plan")
        assumptions_at = template.index("## Assumption Log")

        self.assertLess(exit_at, validation_at)
        self.assertLess(validation_at, assumptions_at)
        self.assertIn("### Questions", template)
        self.assertIn("### Try", template)

    def test_start_owns_the_lightweight_validation_plan(self) -> None:
        start = _read("src/skills/start.md")

        self.assertIn("**Validation-plan checkpoint.**", start)
        self.assertIn("The human owns every decision", start)
        self.assertIn("Exit Criteria lists what must work", start)
        self.assertIn("closed without validation", start)
        self.assertIn("Do not block the new phase", start)

    def test_review_records_results_without_grading_optional_context(self) -> None:
        review = _read("src/skills/review.md")

        self.assertIn("**Validation rule:**", review)
        self.assertIn("A clear summary result is enough", review)
        self.assertIn("Omit this field when the human does not supply it", review)
        self.assertIn("Never grade validation", review)
        self.assertIn("`Validation` as `Result: Not tested`", review)
        self.assertIn("**Whole-review verdict rule.**", review)
        self.assertIn("`all went as planned`", review)
        self.assertIn('What broke, what you\'d change, or "close it".', review)

    def test_positive_summary_close_preserves_the_human_verdict(self) -> None:
        review = _read("src/skills/review.md")

        self.assertIn("Record the user's verdict in `Result`.", review)
        self.assertIn("Mark every Phase check `passed`.", review)
        self.assertIn("Mark every presented assumption `confirmed`.", review)
        self.assertIn("A positive summary verdict never uses this path.", review)
        self.assertIn("`all went as planned, close it`", review)
        self.assertIn("reuse that result as the Decision's `Why`", review)

    def test_fast_close_matches_the_review_template(self) -> None:
        review = _read("src/skills/review.md")
        template = _read("src/templates/phase-review.md")

        self.assertNotIn("What we'd do differently", review)
        self.assertNotIn("### What worked", template)
        self.assertNotIn("### What didn't", template)
        self.assertGreaterEqual(template.count("**Result:**"), 2)
        self.assertGreaterEqual(template.count("**Checked with:**"), 2)
        self.assertNotIn("**Level:**", template)
        self.assertNotIn("**Tried:**", template)
        self.assertNotIn("`Not recorded`", template)
        self.assertIn("### Decision", template)
        self.assertIn("### Phase checks", template)
        self.assertIn("### Questions", template)
        self.assertIn("### Backlog changes", template)
        self.assertIn("**No release recap.**", review)
        self.assertIn("Record the decision as `Not assessed`", review)

    def test_review_confirmation_echoes_judgments_and_records_everything(self) -> None:
        review = _read("src/skills/review.md")

        # The echo is short; the record is complete. Both halves are pinned so a
        # future trim cannot take the second one with the first.
        self.assertIn("**Echo the judgments, not the record.**", review)
        self.assertIn("**The record is the complete one, even though the echo was short:**", review)
        self.assertIn("every assumption at its `A…` address", review)
        self.assertIn('Anything in the wrong bucket? Otherwise "close it".', review)

    def test_review_keeps_learning_questions_human_owned(self) -> None:
        review = _read("src/skills/review.md")

        self.assertIn("**Every unresolved Validation Question gets its own `Open question` line.**", review)
        self.assertIn("unanswered at close", review)
        self.assertIn("Do not infer a Decision choice", review)
        self.assertIn("Never infer a choice from completion or test success", review)

    def test_review_never_hides_phase_promises_behind_the_validation_plan(self) -> None:
        review = _read("src/skills/review.md")
        template = _read("src/templates/phase-review.md")

        self.assertIn("every Exit Criterion", review)
        self.assertIn("Never omit an Exit Criterion", review)
        self.assertIn("`passed`, `failed`, `not tested`, or `signed off`", review)
        self.assertIn("add every Exit Criterion leaf to `Phase checks` at its `E…` address", review)
        self.assertIn("A legacy plan that uses `Decision this informs`", review)
        self.assertIn("| # | Phase promise | Result | What happened |", template)

    def test_public_docs_keep_feedback_optional_but_validation_honest(self) -> None:
        readme = _read("README.md")
        workflow = _read("src/workflow.md")

        self.assertIn("Feedback is optional; an honest record of its absence is not.", readme)
        self.assertIn("closure never masquerades as validation", workflow)


if __name__ == "__main__":
    unittest.main()
