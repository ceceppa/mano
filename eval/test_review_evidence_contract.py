from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class ReviewEvidenceContractTests(unittest.TestCase):
    def test_phase_brief_plans_evidence_before_assumptions(self) -> None:
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
        self.assertIn("closed without evidence", start)
        self.assertIn("Do not block the new phase", start)

    def test_review_distinguishes_evidence_from_closure(self) -> None:
        review = _read("src/skills/review.md")

        for status in ("`gathered`", "`partial`", "`none`"):
            self.assertIn(status, review)
        self.assertIn("Evidence says how strongly this review is grounded", review)
        self.assertIn("`none` means the phase closed without validation", review)
        self.assertIn("mark every unspecified assumption `inconclusive`", review)
        self.assertIn('A vague phrase such as "all good"', review)
        self.assertIn('Or say "close it" to close without evidence.', review)

    def test_fast_close_matches_the_review_template(self) -> None:
        review = _read("src/skills/review.md")
        template = _read("src/templates/phase-review.md")

        self.assertNotIn("What we'd do differently", review)
        self.assertNotIn("### What worked", template)
        self.assertNotIn("### What didn't", template)
        self.assertGreaterEqual(template.count("**Level:** gathered / partial / none"), 2)
        self.assertGreaterEqual(template.count("**Tried:**"), 2)
        self.assertGreaterEqual(template.count("**Result:**"), 2)
        self.assertIn("### Decision", template)
        self.assertIn("### Phase checks", template)
        self.assertIn("### Backlog changes", template)
        self.assertIn("**No release recap.**", review)
        self.assertIn("Record the decision as `Not assessed`", review)

    def test_review_keeps_learning_questions_human_owned(self) -> None:
        review = _read("src/skills/review.md")

        self.assertIn("Questions to consider:", review)
        self.assertIn("Choose what to keep, change, reject, or test again.", review)
        self.assertIn("Never infer a choice from completion or test success", review)

    def test_review_never_hides_phase_promises_behind_the_validation_plan(self) -> None:
        review = _read("src/skills/review.md")
        template = _read("src/templates/phase-review.md")

        self.assertIn("every Exit Criterion", review)
        self.assertIn("Never omit an Exit Criterion", review)
        self.assertIn("passed`, `failed`, or `not tested", review)
        self.assertIn("Mano will mark every unchecked promise as `not tested`.", review)
        self.assertIn("Always include every Phase check", review)
        self.assertIn("If a legacy plan uses `Decision this informs`", review)
        self.assertIn("Other planned checks", review)
        self.assertIn("| Phase promise | Result | What happened |", template)

    def test_public_docs_keep_feedback_optional_but_evidence_honest(self) -> None:
        readme = _read("README.md")
        workflow = _read("src/workflow.md")

        self.assertIn("Feedback is optional; an honest record of its absence is not.", readme)
        self.assertIn("closure never masquerades as validation", workflow)


if __name__ == "__main__":
    unittest.main()
