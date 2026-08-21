"""Wave 5 §5.1 — the recorded finding, and the checks that keep it removed.

**The finding.** `mano review`'s opening rule is one sentence — *one numbered
list and one closing question* — and the file then hands the model seven
separate things to add to that same response, at the exact point of
composition. Every shape §5.1 names as a competitor was present, and all of
them were inside or immediately under STEP 1:

1. **A second question in the "one ask".** The closer read *"How did it go?
   Reply naturally — a clear all-good verdict closes the phase; or say 'close
   it' to close without validation."* — two closers and a mechanics aside in
   the line that is supposed to be the single ask.
2. **A recording-mechanics paragraph the model narrates back.** *"Mano records
   each check as `passed` / `failed` / `not tested`, each assumption as
   `confirmed` / `invalidated` / `inconclusive`; 'close it' records every
   unchecked promise as `not tested`…"* — four status vocabularies stated one
   line under the output template, ending in *"Do not print these mechanics"*.
   A model that has just read them prints them.
3. **A display-tag grammar.** `*(assumption)*` and `*(decide)*`, plus a
   paragraph on when to omit each tag and how to convert a legacy
   `Decision this informs` plan into them.
4. **Three more paragraphs appending to the "entire response"** — the
   one-list-one-ask gloss, the legacy-brief rule, and a build-path paragraph
   adding `needs-human` reasons — each after the block that declared the
   response complete.
5. **An example that models a longer response.** STEP 2's presentation template
   was the file's richest concrete example of a review message: nine blocks,
   roughly thirty lines, ending in **four alternative closers**
   (*"Did I put each outcome in the right section? / Tell me what to move or
   remove. / You may add where or how you checked it. / Say 'close it' to
   record the review as shown."*). It is read before STEP 1 is composed.
6. **A checklist that implies enumeration.** The follow-up opening listed
   *resolved / still broken / still rough / new* as a bulleted menu and asked
   three times in one message.

The constraint was one sentence; the additions were seven paragraphs. A
shorter file that kept them would produce the same long output, which is why
§5.1 requires finding this before rewriting prose (plan6 D8).

These tests pin the removal so it cannot drift back in.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class CompetingShapesRemovedTests(unittest.TestCase):
    """§5.1: every shape that competed with *one response, one ask*."""

    COMPETING = (
        # the two-closer ask
        "How did it go? Reply naturally",
        'or say "close it" to close without validation',
        # the recording-mechanics paragraph
        "Mano records each check as",
        "leaves unchecked assumptions `inconclusive`",
        # the display-tag grammar
        "*(assumption)*",
        "*(decide)*",
        # the four alternative closers
        "Did I put each outcome in the right section",
        "Tell me what to move or remove",
        "You may add where or how you checked it",
        'Say "close it" to record the review as shown',
        # the follow-up enumeration checklist
        "List anything:",
        "Or say \"close it\" to append a follow-up with no new validation",
    )

    def test_no_competing_shape_survives(self) -> None:
        review = _read("src/skills/review.md")
        for shape in self.COMPETING:
            with self.subTest(shape=shape):
                self.assertNotIn(shape, review)

    def test_each_step_ends_in_exactly_one_ask(self) -> None:
        review = _read("src/skills/review.md")
        asks = {
            'What broke, what you\'d change, or "close it".': 1,
            'Anything in the wrong bucket? Otherwise "close it".': 2,
            'What\'s fixed, what\'s still broken, or "close it".': 1,
        }
        for ask, expected in asks.items():
            with self.subTest(ask=ask):
                self.assertEqual(review.count(ask), expected)

    def test_no_fenced_review_message_offers_a_closer_menu(self) -> None:
        """A closer menu inside an example is what the model copies."""
        review = _read("src/skills/review.md")
        for block in re.findall(r"```[a-z]*\n(.*?)```", review, re.S):
            if "[mano review]:" not in block:
                continue
            trailing = [l for l in block.strip().split("\n") if l.strip()]
            closers = [l for l in trailing if l.strip().endswith("?") or '"close it"' in l]
            with self.subTest(block=trailing[0][:60]):
                self.assertLessEqual(
                    len(closers),
                    1,
                    f"example offers {len(closers)} closers: {closers}",
                )


class OpeningShapeTests(unittest.TestCase):
    """§5.3: the opening, exactly."""

    def test_the_opening_is_the_planned_shape(self) -> None:
        review = _read("src/skills/review.md")
        for line in (
            "[mano review]: [PHASE_ID] — [phase goal, one line].",
            "Promised:",
            "1. E1a — [Exit Criterion leaf]",
            "   Try: [the brief's matching Try guidance, when one exists]",
            "Open bet A1: [the assumption, one compact line].",
            "Open question Q1: [the Validation Plan question, one line per question].",
            'What broke, what you\'d change, or "close it".',
        ):
            with self.subTest(line=line):
                self.assertIn(line, review)

    def test_every_exit_leaf_stays_separately_visible(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("**Every Exit Criterion leaf gets its own line.**", review)
        self.assertIn(
            "the exact defect addressable Exit Criteria were built to remove",
            review,
        )

    def test_shorter_is_not_weaker(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn(
            "**Every unresolved Validation Question gets its own `Open question` line.**",
            review,
        )
        self.assertIn("a question the human was asked does not disappear", review)

    def test_the_opening_forbids_tags_and_mechanics(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn(
            "No tags. No status vocabulary. No explanation of how any of it gets recorded.",
            review,
        )

    def test_silence_closes_nothing(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("**silence is not approval and closes nothing**", review)


class StableAddressTests(unittest.TestCase):
    """§5.2: `Q…` / `A…` addresses, written for new briefs, derived for old."""

    def test_the_brief_template_carries_the_addresses(self) -> None:
        template = _read("src/templates/phase-brief.md")
        self.assertIn("- **Q1.**", template)
        self.assertIn("| ID | Assumption | Risk if wrong |", template)
        self.assertIn("| A1 |", template)

    def test_start_writes_them_and_never_renumbers(self) -> None:
        start = _read("src/skills/start.md")
        self.assertIn("Lead each bullet with its stable address", start)
        self.assertIn(
            "Address each question `Q1`, `Q2`, … in document order and each "
            "Assumption Log row `A1`, `A2`, … in the table's first column.",
            start,
        )
        self.assertIn("never add addresses to a brief that already exists", start)

    def test_review_derives_them_for_an_existing_brief(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn(
            "**Use the brief's own addresses — `E1a`, `Q1`, `A1` — never display numbering you invented.**",
            review,
        )
        self.assertIn("is *not* rewritten to add them: derive the same IDs by document order", review)

    def test_the_review_record_keeps_them(self) -> None:
        template = _read("src/templates/phase-review.md")
        self.assertIn("| [E1a] |", template)
        self.assertIn("| [Q1] |", template)
        self.assertIn("| [A1] |", template)


class ClosingSemanticsTests(unittest.TestCase):
    """§5.4 / D10: `close it` is an attestation, and the record says so."""

    def test_close_it_is_full_human_sign_off(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("**Closing semantics — `close it` is full human sign-off.**", review)
        self.assertIn(
            "recording it as *untested* would be the framework second-guessing the person it exists to serve",
            review,
        )

    def test_an_unruled_assumption_is_accepted_not_inconclusive(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("One they did not rule on records `accepted`", review)
        self.assertIn("not for one they never mentioned", review)

    def test_an_unanswered_question_is_recorded_as_such(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("An unanswered question records `unanswered at close`", review)
        self.assertIn(
            '*"Ship it" does not answer a question the human was asked*',
            review,
        )

    def test_there_is_no_second_closing_keyword(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("There is no second closing keyword.", review)

    def test_close_it_does_not_erase_a_negative_finding(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn(
            "**`close it` arriving with a negative finding closes the phase; it does not erase the finding.**",
            review,
        )
        self.assertIn("routed to rework, or dismissed in their own words", review)

    def test_the_public_docs_agree(self) -> None:
        readme = _read("README.md")
        workflow = _read("src/workflow.md")
        self.assertIn("that is your sign-off", readme)
        self.assertIn("unanswered at close", readme)
        self.assertIn("unanswered at close", workflow)


class ValidateNowTests(unittest.TestCase):
    """§5.5 / D6: one definition, three consumers, two appearances."""

    def test_the_contract_is_defined_once_in_the_shared_rule(self) -> None:
        implement = _read("src/rules/implement.md")
        self.assertIn("## `Validate now:` — the one expansion of the terminal line", implement)
        self.assertIn("**Source every line from the brief's `## Validation Plan` → `### Try`.**", implement)
        self.assertIn("**Once per run, not per row and not per story.**", implement)
        self.assertIn("sole** sanctioned expansion", implement)

    def test_neither_implementation_skill_restates_it(self) -> None:
        pointer = "`_mano/rules/implement.md`"
        for skill in ("src/skills/build.md", "src/skills/dev.md"):
            text = _read(skill)
            with self.subTest(skill=skill):
                self.assertIn("Validate now:", text)
                self.assertIn(pointer, text)
                # The block itself is defined once; the skills point at it.
                self.assertNotIn("### Try`.**", text)

    def test_review_repeats_it_beside_the_promise(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn(
            "**The `Try` lines repeat what the implementation handoff already printed under `Validate now:`.**",
            review,
        )
        self.assertIn("chat delivery is not durable state", review)


class CompactTriageTests(unittest.TestCase):
    """§5.6: the echo carries judgments; the record carries everything."""

    def test_the_echo_is_findings_and_one_ask(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("echo **only the findings about to be recorded** and ask once", review)
        self.assertIn("**Echo the judgments, not the record.**", review)
        self.assertIn("are **recorded in STEP 3, not echoed here**", review)

    def test_the_follow_up_uses_the_same_rule(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("**The standard STEP 2's echo rule applies unchanged:**", review)
        self.assertIn("Same rule as the standard opening: one response, one ask", review)

    def test_the_record_is_still_complete(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn(
            "**The record is the complete one, even though the echo was short:**",
            review,
        )
        for address in ("`E…` address", "`Q…` address", "`A…` address"):
            with self.subTest(address=address):
                self.assertIn(address, review)


if __name__ == "__main__":
    unittest.main()
