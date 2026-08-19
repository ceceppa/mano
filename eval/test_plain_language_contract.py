from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class PlainLanguageContractTests(unittest.TestCase):
    def test_workflow_applies_one_contract_to_every_skill(self) -> None:
        workflow = _read("src/workflow.md")

        self.assertIn("### Plain-language contract", workflow)
        self.assertIn("Every Mano skill applies this contract", workflow)
        self.assertIn("overrides stylistic wording in examples", workflow)
        self.assertIn("a teammate with no prior context", workflow)
        self.assertIn("Length is not the target. Understanding is.", workflow)
        self.assertIn("Use active voice.", workflow)
        self.assertIn("Do not use marketing words as requirements", workflow)
        self.assertIn("Do not use a metaphor as a requirement", workflow)
        self.assertIn("Use bullets when one requirement contains multiple", workflow)
        self.assertIn("put the trigger on the parent line", workflow)
        self.assertIn("Never compress several observable results", workflow)
        self.assertNotIn("15 words or fewer", workflow)
        self.assertNotIn("Grade 8", workflow)

    def test_contract_keeps_precision_in_the_owning_artifact(self) -> None:
        workflow = _read("src/workflow.md")

        self.assertIn("Put concrete detail in its canonical home", workflow)
        self.assertIn("Do not invent technical detail merely to sound precise", workflow)
        self.assertIn("states, transitions, inputs, outputs, defaults, or endpoints", workflow)
        self.assertIn("reference that definition instead of copying it", workflow)
        self.assertIn("Never fill the gap with confident-sounding prose", workflow)

    def test_contract_requires_honest_parameters_and_testable_behavior(self) -> None:
        workflow = _read("src/workflow.md")

        for vague_word in ("configurable", "tunable", "fast", "scalable"):
            self.assertIn(vague_word, workflow)
        self.assertIn("Never invent a default", workflow)
        self.assertIn("What starts this behavior?", workflow)
        self.assertIn("What should the user or caller observe?", workflow)
        self.assertIn("Do not add empty Trigger or Out of Scope fields", workflow)

    def test_contract_preserves_product_feelings_as_human_questions(self) -> None:
        workflow = _read("src/workflow.md")

        self.assertIn('“Fun,” “calm,” and “rewarding”', workflow)
        self.assertIn("Name who will judge that feeling", workflow)
        self.assertIn("Never treat the adjective alone as acceptance evidence", workflow)

    def test_contract_makes_user_questions_clear_without_making_them_ceremonial(self) -> None:
        workflow = _read("src/workflow.md")

        self.assertIn("Ask clear questions", workflow)
        self.assertIn("Ask only when the answer changes the current work", workflow)
        self.assertIn("Put one decision in each numbered item", workflow)
        self.assertIn("do not force one question per message", workflow)
        self.assertIn("Offer options only when the real choices are known", workflow)
        self.assertIn("Accept a natural-language reply", workflow)
        self.assertIn("Do not turn every question into a requirements form", workflow)

    def test_fixed_question_templates_follow_the_shared_contract(self) -> None:
        import_skill = _read("src/skills/import.md")
        start = _read("src/skills/start.md")
        review = _read("src/skills/review.md")

        self.assertIn("I need these product decisions", import_skill)
        self.assertIn("I need these decisions before I draft Phase [N]", start)
        self.assertIn("Did I put each outcome in the right section?", review)
        self.assertNotIn("Does this look right?", review)

    def test_stories_unpack_compound_acceptance_criteria(self) -> None:
        stories = _read("src/skills/stories.md")

        self.assertIn("**Unpack compound acceptance criteria.**", stories)
        self.assertIn("Put the trigger on the checkbox line", stories)
        self.assertIn("Treat every nested result as required acceptance evidence", stories)

    def test_stories_never_infer_missing_values_or_proxies_for_feelings(self) -> None:
        stories = _read("src/skills/stories.md")

        self.assertIn("Do not infer a value", stories)
        self.assertIn("turn the gap into a story-level `❓ Decide:`", stories)
        self.assertIn("Never invent a proxy AC for a feeling", stories)
        self.assertNotIn("infer the most consistent value, build the story with it", stories)

    def test_bootstrap_points_all_agents_to_the_contract(self) -> None:
        agents = _read("src/bootstrap/AGENTS.md")

        self.assertIn("Plain-language contract", agents)
        self.assertIn("Assume a teammate has no prior context", agents)

    def test_start_separates_promises_from_learning(self) -> None:
        start = _read("src/skills/start.md")
        template = _read("src/templates/phase-brief.md")

        self.assertIn("Exit Criteria lists what must work", start)
        self.assertIn("Never use the plan as a substitute", start)
        self.assertIn("Never join independent questions", start)
        self.assertIn("Every Question needs at least one Try bullet", start)
        self.assertIn("Every Try bullet must support a Question", start)
        self.assertIn("### Questions", template)
        self.assertIn("### Try", template)

    def test_review_drops_the_old_ceremonial_prompt(self) -> None:
        review = _read("src/skills/review.md")

        self.assertNotIn("Planned validation:", review)
        self.assertNotIn("Based on that evidence, what do you decide about:", review)
        self.assertIn("Check what the phase promised:", review)
        self.assertIn("Questions to consider:", review)
        self.assertIn("Try this:", review)
        self.assertIn("Reply naturally", review)


if __name__ == "__main__":
    unittest.main()
