"""Deterministic checks on wave 4's prompt contracts.

Wave 4 makes three things canonical: which implementation action a given state
routes to, how many rows one build pass may cover, and what an invocation-time
argument to `mano build` means. All three failed the same way before: prose in
one file agreed with the rule while an operational block beside it did not, so
the drift was invisible to a reader who only looked at the narrative. These
tests read the operational blocks.
"""

from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

import assertions

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class ImplementationEntryTests(unittest.TestCase):
    """4.1: one rule, applied at every operational site — not only in prose."""

    def test_workflow_states_the_rule_once_and_in_order(self) -> None:
        workflow = _read("src/workflow.md")
        self.assertIn("### Implementation entry", workflow)
        self.assertIn("**Choose implementation by validated state, then mode, in this order.**", workflow)
        section = workflow.split("### Implementation entry", 1)[1]
        # The six clauses, in the order they are evaluated.
        clauses = (
            "Either ledger invalid, or both ledger paths present",
            "A pending rework event, any open Scope row, or an unresolved deviation",
            "An incomplete stories ledger",
            "A complete stories ledger",
            "A progress ledger with every Scope leaf `done`",
            "Only with **no ledger**",
        )
        positions = [section.find(clause) for clause in clauses]
        self.assertNotIn(-1, positions, "a clause of the entry rule is missing")
        self.assertEqual(positions, sorted(positions), "the entry rule's clauses are out of order")

    def test_only_the_no_ledger_case_consults_the_mode(self) -> None:
        workflow = _read("src/workflow.md")
        section = workflow.split("### Implementation entry", 1)[1]
        self.assertIn("Rule 6 is the only one where mode has a say", section)
        self.assertIn("**auto** terminates at `mano build`", section)
        self.assertIn("**manual** offers `mano stories` first and `mano build` second", section)

    def test_the_auto_no_ledger_path_keeps_every_guardrail(self) -> None:
        workflow = _read("src/workflow.md")
        section = workflow.split("### Implementation entry", 1)[1]
        self.assertIn("only** after an explicit human approval of the phase scope", section)
        self.assertIn("never bypasses an open question, a missing-artifact decision, or a hard gate", section)
        self.assertIn("a pre-existing stories ledger keeps the stories path", section)
        self.assertIn("stops before `mano review` and never scopes another phase", section)

    def test_import_start_approve_in_auto_reaches_build_with_no_stories(self) -> None:
        # The case earlier plans omitted: the whole path from a document to a
        # built phase must never produce a story file.
        workflow = _read("src/workflow.md")
        self.assertIn(
            "`mano import` → `mano start` → scope approval, in auto, therefore ends in `mano build` "
            "and **writes no story files**",
            workflow,
        )

    def test_the_state_map_and_continue_fallback_apply_the_rule(self) -> None:
        workflow = _read("src/workflow.md")
        # State map: the no-ledger row is mode-aware, not stories-by-default.
        self.assertIn("the projected phase has **neither ledger** → planning stage", workflow)
        self.assertIn("This is rule 6 of **Implementation entry**", workflow)
        # Continue has one fallback per path, not one story-shaped fallback.
        self.assertIn("Build-mode fallback output, on the **stories** path", workflow)
        self.assertIn("Build-mode fallback output, on the **build** path", workflow)
        self.assertIn("Use `mano build` to resume at the row state reports next.", workflow)

    def test_the_command_menu_marks_the_entry_the_state_implies(self) -> None:
        workflow = _read("src/workflow.md")
        self.assertIn("Mark the suggested next action by **Implementation entry**", workflow)
        self.assertIn("in `manual` leave `stories` and `build` both visible and mark neither", workflow)

    def test_the_planning_decision_tree_no_longer_hardcodes_stories(self) -> None:
        artifact = _read("src/rules/artifact.md")
        tree = artifact.split("Use this decision tree", 1)[1]
        self.assertNotIn("suggest `mano stories`", tree)
        self.assertIn("suggest implementation", tree)
        self.assertIn("go straight to implementation", tree)
        self.assertIn("in `auto`, the approved chain terminates at `mano build`", artifact)

    def test_every_planning_skill_offers_both_paths(self) -> None:
        for skill in ("spec", "rules", "ux", "ui"):
            text = _read(f"src/skills/{skill}.md")
            with self.subTest(skill=skill):
                self.assertIn("- `mano build` — if the phase is", text)
                self.assertIn("- `mano stories` — if the phase is", text)
                self.assertIn(
                    "**Show both implementation paths in `manual`, and only `mano build` in `auto`.**",
                    text,
                )

    def test_start_recommends_by_mode_rather_than_defaulting_to_stories(self) -> None:
        start = _read("src/skills/start.md")
        self.assertNotIn(
            "Default recommendation is `mano stories` when the phase is self-contained",
            start,
        )
        self.assertIn("the recommendation is **implementation**, and the phase has no ledger yet", start)
        self.assertIn("In `auto`, the chain you just armed terminates at `mano build`", start)

    def test_state_js_action_strings_are_mode_aware_only_where_no_ledger_exists(self) -> None:
        state = _read("src/scripts/state.js")
        self.assertIn(
            'action = s.runMode === "auto"',
            state,
            "the no-ledger verdict still reads the same in both modes",
        )
        self.assertIn("the armed chain's terminal action is mano build", state)
        self.assertIn("run mano stories (then mano dev) for story files, or mano build", state)
        # The projection mano build itself reads.
        self.assertIn("in auto the implementation entry is mano build", state)

    def test_bootstrap_names_the_entry_rule(self) -> None:
        agents = _read("src/bootstrap/AGENTS.md")
        self.assertIn("### Which implementation entry", agents)
        self.assertIn("Decide by **validated state, then mode**", agents)
        self.assertIn("`_mano/workflow.md` → **Implementation entry**", agents)


class TwoLevelScopeTests(unittest.TestCase):
    """4.2: grouping needs a ceiling the human drew, not one the model chose."""

    def test_the_template_scope_is_two_level(self) -> None:
        template = _read("src/templates/phase-brief.md")
        scope = template.split("## Phase Scope", 1)[1].split("## Not This Phase", 1)[0]
        self.assertIn("1. **[Category]**", scope)
        self.assertIn("   a. **[Short title]** —", scope)
        self.assertIn("   b. **[Short title]** —", scope)

    def test_a_category_is_an_outcome_area_not_a_promised_module(self) -> None:
        # A model reading `**Task management**` will otherwise create TaskManager.
        for path in ("src/templates/phase-brief.md", "src/skills/start.md"):
            text = _read(path)
            with self.subTest(path=path):
                self.assertIn(
                    "coherent outcome area likely to be implemented together — not a promised module, "
                    "class, or file",
                    text,
                )
                self.assertIn("TaskManager", text)

    def test_flat_briefs_stay_valid_and_are_never_migrated(self) -> None:
        start = _read("src/skills/start.md")
        self.assertIn("A **flat** numbered list is still valid and builds row by row", start)
        self.assertIn("never rewrite one into categories", start)
        template = _read("src/templates/phase-brief.md")
        self.assertIn("leave an existing flat brief alone rather than converting it", template)

    def test_the_label_joins_category_and_leaf_and_the_contract_stays_recoverable(self) -> None:
        start = _read("src/skills/start.md")
        self.assertIn("`mano build` addresses category 1 leaf b as `S1b`", start)
        self.assertIn("join into the ledger's label (`Task management — Persistence`)", start)
        build = _read("src/skills/build.md")
        self.assertIn("The projection's `ROW_CONTRACT` carries the row's exact text", build)


class GroupingTests(unittest.TestCase):
    """4.3: one pass may cover several rows; no gate ever covers several."""

    def test_build_owns_the_candidate_and_pass_mechanics(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("## Grouping rows into one pass", build)
        section = build.split("## Grouping rows into one pass", 1)[1].split("\n## ", 1)[0]
        for condition in (
            "Start at the first actionable non-`done` normal brief leaf",
            "Take only contiguous normal brief leaves with the same numeric category",
            "Never include a `+N` correction or a dotted split row",
            "Stop before a leaf whose real implementation surface differs",
            "Stop before any per-row gate failure",
            "The whole candidate can be implemented *and verified* within this turn",
        ):
            self.assertIn(condition, section)

    def test_the_category_is_a_ceiling_and_there_is_no_numeric_cap(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn(
            "**There is no numeric cap and no cross-category group. The category is a ceiling, "
            "never a mandate.**",
            build,
        )
        self.assertIn(
            "A category of eight leaves does not become one pass because it is one category",
            build,
        )
        self.assertIn("Taking fewer rows is always available and never needs a justification", build)

    def test_a_flat_brief_is_never_grouped_by_inference(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("A **flat** brief has no categories, so every row is its own pass", build)
        self.assertIn("the ceiling has to have come from the human", build)

    def test_the_pass_order_keeps_gates_and_evidence_per_row(self) -> None:
        build = _read("src/skills/build.md")
        section = build.split("**Execution order for a pass:**", 1)[1].split("\n## ", 1)[0]
        self.assertIn("**per row**, before any code", section)
        self.assertIn("One status batch to `doing`", section)
        self.assertIn("apply gate **10.1 separately to every row and every `E` leaf**", section)
        self.assertIn("A partial pass closes what it proved and nothing else", section)
        self.assertIn("One state and identity post-check for the pass", section)

    def test_grouping_needs_no_confirmation_and_never_holds_a_deviation(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("It composes no scope text, invents no row, and needs no human confirmation", build)
        self.assertIn(
            "A split, a reopen, or a correction remains a **deviation stop**, and none of the three "
            "ever appears inside a group",
            build,
        )

    def test_the_shared_contract_states_the_per_unit_rule_too(self) -> None:
        # The load-bearing sentence must not live only in the plan.
        implement = _read("src/rules/implement.md")
        self.assertIn("**One pass may cover several units. The gates never do.**", implement)
        self.assertIn("gates **6.2**, **6.3**, and **6.4** run **per unit**", implement)
        self.assertIn("acceptance-evidence gate **10.1** is applied **per unit and per acceptance criterion**", implement)
        self.assertIn("Verification may be shared across a pass — one suite run can serve several units.", implement)
        self.assertIn("**Evidence may not.**", implement)


class InvocationArgumentTests(unittest.TestCase):
    """4.4: the argument is a correction channel, never a scope channel."""

    def test_the_argument_needs_a_valid_ledger(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**An argument is a correction, never new scope.**", build)
        self.assertIn(
            '`mano build "[what changed]"` is accepted **only when a valid ledger exists**',
            build,
        )
        # The old blanket refusal is gone, so it cannot be applied by habit.
        self.assertNotIn("**No free-text argument.**", build)

    def test_durable_state_wins_over_a_new_argument(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**A pending `R…` rework event wins over the argument.**", build)
        self.assertIn("**refuses without mutation**", build)
        self.assertIn("no row, no code, no queue, no ledger change of any kind", build)
        self.assertIn(
            "An approval or a rejection of a pending event is a response *inside that event's "
            "deviation flow*",
            build,
        )

    def test_the_argument_enters_the_abc_classifier_unchanged(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("the argument enters the A/B/C classifier", build)
        self.assertIn("**no row is appended**", build)
        self.assertIn("offer the explicit backlog-defer choice", build)
        self.assertIn("allocate a `+N` row from the *exact* text", build)
        # One classifier, two channels.
        self.assertIn(
            "typed into a running build, or as the invocation argument",
            build,
        )

    def test_a_no_ledger_argument_creates_nothing(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn(
            "**With no ledger, the argument is rejected without running pre-flight and without `init`.**",
            build,
        )
        self.assertIn("Write no ledger, no source, and no backlog item.", build)
        self.assertIn("it is not consumed, spent, or reused by this refusal", build)

    def test_the_signature_reaches_help_text_and_the_forbidden_block(self) -> None:
        workflow = _read("src/workflow.md")
        self.assertIn('mano build ["<fix>"]', workflow)
        self.assertIn(
            '`mano build "[what changed]"` passes a mid-phase correction at invocation, and is accepted '
            "only when a valid ledger exists",
            workflow,
        )
        build = _read("src/skills/build.md")
        self.assertIn(
            "- Do not accept an invocation argument as new scope, create a ledger to hold one, or "
            "accept one at all while a rework event is pending.",
            build,
        )
        self.assertIn(
            "- Do not group a correction row, a split row, or leaves from two brief categories into one pass.",
            build,
        )
        readme = _read("README.md")
        self.assertIn('| `mano build ["what changed"]` |', readme)

    def test_the_skill_description_advertises_the_argument(self) -> None:
        build = _read("src/skills/build.md")
        front = build.split("---", 2)[1]
        self.assertIn('`mano build "[what changed]"`', front)


class EvalCoverageTests(unittest.TestCase):
    """Every wave 4 behaviour the plan names has a case that can fail."""

    # (case name, the wave 4 behaviour it is the evidence for)
    REQUIRED_CASES = (
        ("build-auto-direct", "import → start → approve in auto reaches build, no story files"),
        ("build-single-pass", "a two-level brief groups, and every leaf keeps its own evidence"),
        ("build-group-boundary", "a group stops at a category/gate boundary and resumes correctly"),
        ("build-resume", "a flat brief stays row by row"),
        ("build-defect-reopen", "invocation A reopens before code and adds no row"),
        ("build-arg-distinct-outcome", "invocation B adds no row and no code, in manual"),
        ("build-scope-refusal-auto", "invocation B adds no row and no code, in auto"),
        ("build-nuance-row", "invocation C keeps the exact text and stops before code"),
        ("build-nuance-spec-gap", "invocation C with a missing spec-owned default writes no code"),
        ("build-arg-rework-precedence", "a pending R… event outranks an invocation argument"),
        ("build-arg-no-ledger", "a no-ledger argument writes no ledger and re-routes to start"),
    )

    def test_each_required_case_exists_and_names_registered_assertions(self) -> None:
        cases = REPO_ROOT / "eval" / "cases"
        for name, behaviour in self.REQUIRED_CASES:
            path = cases / f"{name}.json"
            with self.subTest(case=name):
                self.assertTrue(path.exists(), f"{name}.json is missing — it is the evidence for: {behaviour}")
                case = json.loads(path.read_text(encoding="utf-8"))
                self.assertTrue(case["assertions"], f"{name} asserts nothing")
                for assertion in case["assertions"]:
                    self.assertIn(assertion, assertions.REGISTRY, f"{name} names an unregistered assertion")

    def test_the_invocation_cases_pass_the_argument_as_a_quoted_argument(self) -> None:
        # The em-dash form exercised the classifier but not the channel wave 4
        # adds; the quoted form is what a user actually types.
        cases = REPO_ROOT / "eval" / "cases"
        for name in (
            "build-defect-reopen",
            "build-arg-distinct-outcome",
            "build-scope-refusal-auto",
            "build-nuance-row",
            "build-nuance-spec-gap",
            "build-arg-rework-precedence",
            "build-arg-no-ledger",
        ):
            case = json.loads((cases / f"{name}.json").read_text(encoding="utf-8"))
            with self.subTest(case=name):
                self.assertRegex(case["prompt"], r'^mano[- ]build "', f"{name} does not use the quoted argument")

    def test_the_grouping_fixture_has_a_two_level_scope(self) -> None:
        brief = _read("eval/fixtures/build-single-pass/phase-brief.md")
        scope = brief.split("## Phase Scope", 1)[1].split("## Not This Phase", 1)[0]
        categories = re.findall(r"^\d+\. \*\*", scope, re.M)
        leaves = re.findall(r"^   [a-z]\. \*\*", scope, re.M)
        self.assertGreaterEqual(len(categories), 2, "one category cannot test a category boundary")
        self.assertGreaterEqual(len(leaves), 4, "too few leaves to form a group and then stop")


if __name__ == "__main__":
    unittest.main()
