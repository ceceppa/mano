"""Deterministic checks on the build path's prompt contracts.

Wave 3 exists because four files disagreed about whether `mano build` and its
ledger were legitimate at all, and because build's own routing looped. Those are
contradictions between documents, so they can be checked by reading the
documents — no model spend required. Each test names the defect it pins.
"""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class AmbientContractTests(unittest.TestCase):
    """B9: four files disagreed about whether `mano build` exists."""

    def test_core_no_longer_forbids_the_ledger_it_ships(self) -> None:
        core = _read("src/rules/core.md")
        self.assertNotIn("There is no mutable progress ledger", core)
        self.assertIn("A phase's ledger is `stories/README.md` or `PHASE_DIR/progress.md`", core)
        # "No invented files" must forbid inventing state, not keeping it.
        self.assertNotIn("Do not create tracking files, progress files,", core)
        self.assertIn("What is forbidden is *inventing* state, not keeping it.", core)

    def test_core_exempts_both_implementation_actions(self) -> None:
        core = _read("src/rules/core.md")
        self.assertIn(
            "`mano dev` and `mano build` are the two implementation entry points and are exempt",
            core,
        )

    def test_core_no_longer_claims_every_skill_requires_it(self) -> None:
        core = _read("src/rules/core.md")
        self.assertNotIn("Shared execution rules for every Mano skill", core)
        self.assertIn("Not every skill requires it", core)
        self.assertIn("implementation's shared contract is `_mano/rules/implement.md`", core)

    def test_cursorrules_dispatches_build_with_its_literal_argument(self) -> None:
        rules = _read("src/bootstrap/cursorrules")
        self.assertIn("`mano build` maps to `_mano/skills/build.md`", rules)
        self.assertIn("`mano dev` maps to `_mano/skills/dev.md`", rules)
        # A dropped argument would silently turn a correction into a plain build.
        self.assertIn("**Preserve a literal trailing modifier or argument.**", rules)
        self.assertIn("invokes `mano-build` with that exact text intact", rules)
        self.assertIn("never paraphrase an argument", rules)
        self.assertIn(
            "`mano dev` and `mano build` are the two Mano actions allowed to write application code",
            rules,
        )

    def test_agents_md_no_longer_contradicts_its_own_build_section(self) -> None:
        agents = _read("src/bootstrap/AGENTS.md")
        self.assertNotIn("it produces planning artifacts, not code", agents)
        self.assertNotIn("Mano does not use a dedicated phase-state file", agents)
        self.assertIn("There is no third state file to invent", agents)

    def test_claude_md_already_names_both_paths(self) -> None:
        claude = _read("src/bootstrap/CLAUDE.md")
        self.assertIn('"Implementing a story" (`mano dev`) or "Building a phase" (`mano build`)', claude)
        self.assertIn("_mano/rules/implement.md", claude)


class SelfContainmentTests(unittest.TestCase):
    """A skill may not be told to open a file it forbids itself from opening."""

    def test_the_auto_closing_block_lives_where_implementation_loads_it(self) -> None:
        implement = _read("src/rules/implement.md")
        self.assertIn("## Closing an armed auto chain", implement)
        self.assertIn("[mano auto]: phase-[N]", implement)
        for skill in ("src/skills/build.md", "src/skills/dev.md"):
            text = _read(skill)
            self.assertIn(
                "`[mano auto]` closing block from `_mano/rules/implement.md`",
                text,
                f"{skill} still sources the closing block from a file it does not load",
            )
            self.assertNotIn("closing block from `_mano/workflow.md`", text)

    def test_source_edits_have_a_surgical_rule_of_their_own(self) -> None:
        # core.md's equivalent covers artifacts only, and neither implementation
        # skill loads core.md — so nothing enforced this for source.
        implement = _read("src/rules/implement.md")
        self.assertIn("## Writing source: surgical edits only", implement)
        self.assertIn("smallest regions the change actually owns", implement)
        self.assertIn("stays byte-identical", implement)


class PreFlightOrderTests(unittest.TestCase):
    """B7: the order decides whether a gap costs nothing or costs a rewrite."""

    def test_preflight_runs_whole_and_before_any_ledger(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**before any ledger and before any code**", build)
        self.assertIn("**stop, with no ledger written.**", build)

    def test_build_reads_every_present_artifact_not_the_relevant_ones(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**every artifact the projection's `ARTIFACTS` line reports as `present`**", build)
        self.assertIn("Read all of them, not the ones that look relevant.", build)

    def test_project_rule_mapping_moved_ahead_of_the_ledger(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**0g. Project-rule coverage.** Before the ledger exists", build)
        self.assertNotIn("**0g. Project-rule coverage.** After the ledger exists", build)
        # Style and naming are not product promises.
        self.assertIn("do not invent a product promise for them", build)

    def test_an_unmapped_phase_goal_outcome_is_a_hard_outcome(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**0f. Prove the chain: `Phase Goal` outcome → Scope leaves → Exit leaves.**", build)
        self.assertIn("Every Phase Goal outcome has both.", build)
        self.assertIn("**stops the run with no ledger written**", build)

    def test_the_gates_run_per_row_before_any_status_or_code(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**Run the gates first, before touching any status or any code.**", build)
        self.assertIn("a false record of what happened", build)

    def test_the_story_note_gap_option_is_gone(self) -> None:
        # Stories are forbidden on this path, so "note it in the story" named a
        # file that cannot exist.
        build = _read("src/skills/build.md")
        self.assertNotIn("Continue with an explicit temporary note in the story", build)
        self.assertIn("There is no story file on this path to hold a temporary note", build)


class CorrectionRoutingTests(unittest.TestCase):
    """B5/D3/D12: the documented route used to loop."""

    def test_build_has_five_cases_and_none_of_them_loops(self) -> None:
        build = _read("src/skills/build.md")
        for case in (
            "**(A) A defect in work already marked done",
            "**(B) A distinct outcome the phase does not contain",
            "**(C) A nuance inside the phase goal that no row covers",
            "**(D) Nothing is built yet and the brief itself is wrong.**",
            "**(E) An addressed brief section changed after `init`.**",
        ):
            self.assertIn(case, build)
        self.assertIn(
            "do not route to `mano start` to amend a brief that a ledger has already frozen",
            build,
        )

    def test_a_defect_reopens_existing_rows_before_any_code(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("Reopen the affected rows **before writing any code**", build)
        self.assertIn("never attach correction-only `affects:` metadata to a normal row", build)
        self.assertIn("records a sequence that did not happen", build)

    def test_a_correction_never_derives_both_contracts_from_one_sentence(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("--exit E2c", build)
        self.assertIn("**it is required**", build)
        self.assertIn("show the user the complete proposed criterion wording and get explicit approval", build)
        self.assertIn("the model marking its own homework", build)

    def test_a_distinct_outcome_previews_the_whole_backlog_item(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("### Deferring a distinct outcome", build)
        self.assertIn('**"Defer it" is not approval of model-invented metadata.**', build)
        for field in ("Title:", "Type:", "Context:", "Source:", "Track:"):
            self.assertIn(field, build)
        self.assertIn("**Never assign it to the current phase or any phase.**", build)
        self.assertIn("Do not proceed on silence", build)

    def test_a_frozen_brief_offers_no_migration(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("Implicit migration is not supported", build)
        self.assertIn("Do not offer to reconcile, re-fingerprint, or migrate.", build)


class AmendCurrentTests(unittest.TestCase):
    """The one route by which an approved brief changes."""

    def test_start_gates_an_amendment_on_the_dedicated_projection(self) -> None:
        start = _read("src/skills/start.md")
        self.assertIn('## Amending the current phase\'s brief — `mano start "[what changed]"`', start)
        self.assertIn("node _mano/scripts/state.js --scope --amend-current", start)
        self.assertIn("`DECISION: REFUSE` → relay its `REASON:` line and stop. Write nothing.", start)
        self.assertIn("never route the user to a command that will route them back here", start)

    def test_the_amendment_writes_nothing_before_approval(self) -> None:
        start = _read("src/skills/start.md")
        self.assertIn("**Show the whole proposed scope and stop.** Nothing is written.", start)
        self.assertIn("the approval of a *changed contract*", start)
        self.assertIn("confirm it still reports `AMEND_CURRENT` with the same `OWNER` and `PHASE_ID`", start)
        self.assertIn("it is invalidated, not reused", start)

    def test_stories_does_not_bounce_an_amendment_back_to_start(self) -> None:
        stories = _read("src/skills/stories.md")
        self.assertIn("**Do not route to `mano start` from here**", stories)


class ReworkTests(unittest.TestCase):
    """D4: a confirmed finding must survive a compaction."""

    def test_review_persists_one_event_per_finding(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("progress.js request-rework", review)
        self.assertIn("**One event per finding, each with its own exact text.**", review)
        self.assertIn("an aggregate event cannot be classified at all", review)

    def test_review_may_relay_a_dismissal_but_never_infer_one(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("resolve-rework", review)
        self.assertIn("**Relay a dismissal, never conclude one**", review)
        build = _read("src/skills/build.md")
        self.assertIn("**Dismissal is the human's word, never an inference.**", build)

    def test_a_pending_finding_routes_to_build_even_when_the_ledger_is_complete(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("## Review findings (rework)", build)
        self.assertIn("**even when every row was already `done` and every criterion `met`**", build)
        self.assertIn("classify it into A, B, or C above — per event, never in aggregate", build)

    def test_sign_off_records_who_proved_each_criterion(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("progress.js sign-off", review)
        self.assertIn("Typing `close it` **is** a human attestation", review)
        self.assertIn("Do not run `sign-off` when the review produced findings", review)


class ReviewLedgerSpecificTests(unittest.TestCase):
    """B6: review branched on the ledger and then asked for a story anyway."""

    def test_activation_requires_exactly_one_valid_ledger(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("**Neither present** → refuse", review)
        self.assertIn("**`PROGRESS_STATUS: invalid`**, or both ledgers present → refuse", review)
        self.assertIn("**`STORIES_STATUS: present`** → the stories path", review)
        self.assertIn("**`PROGRESS_STATUS: present`** → the build path", review)

    def test_a_needs_human_leaf_passes_the_gate_and_reaches_the_human(self) -> None:
        review = _read("src/skills/review.md")
        self.assertIn("A `needs-human` leaf is **not** an open row.", review)
        self.assertIn("**On the build path, show every `needs-human` leaf with its reason.**", review)


class TerminalSweepTests(unittest.TestCase):
    """B8: a criterion marked met early can be regressed by later work."""

    def test_the_sweep_runs_before_the_terminal_line(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("## Terminal evidence sweep", build)
        self.assertIn("**That is not sufficient to report the phase built.**", build)
        self.assertIn("**Reopen any leaf that later work invalidated**", build)
        self.assertIn("only after the **Terminal evidence sweep** passes", build)

    def test_the_sweep_refuses_a_correction_it_cannot_prove(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn('*"Fixed but unprovable" cannot close a phase.*', build)

    def test_needs_human_is_a_handoff_and_never_stops_to_author_try_text(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**terminal handoff, not an escape hatch**", build)
        self.assertIn("not for a missing test, unavailable tooling, a failed check, or an artifact gap", build)
        self.assertIn("Do **not** stop mid-run to ask the human to author `Try` text", build)


class CommandSurfaceTests(unittest.TestCase):
    """Wave 2 changed every mutating call; the prompts must match the scripts."""

    SCRIPT_CALL = re.compile(r"progress\.js (init|set-status|split|add-row|request-rework|resolve-rework|sign-off)\b")

    def _calls(self, text: str) -> list[tuple[str, str]]:
        """(command, the rest of that fenced invocation) for each example."""
        calls = []
        for block in re.findall(r"```[a-z]*\n(.*?)```", text, re.S):
            joined = block.replace("\\\n", " ")
            for line in joined.split("\n"):
                match = self.SCRIPT_CALL.search(line)
                if match:
                    calls.append((match.group(1), line))
        return calls

    def test_every_documented_mutation_carries_the_identity_guard(self) -> None:
        for skill in ("src/skills/build.md", "src/skills/review.md"):
            for command, line in self._calls(_read(skill)):
                with self.subTest(skill=skill, command=command):
                    self.assertIn(
                        "--expect-phase-id",
                        line,
                        f"{skill}: `{command}` example omits the identity guard",
                    )

    def test_no_documented_call_passes_text_inline(self) -> None:
        # Quotes, backticks, $(), and newlines do not survive a shell round-trip.
        for skill in ("src/skills/build.md", "src/skills/review.md"):
            text = _read(skill)
            for command, line in self._calls(text):
                with self.subTest(skill=skill, command=command):
                    self.assertNotRegex(line, r'--(text|part) [^-]', f"{skill}: inline text in `{command}`")

    def test_build_documents_the_grammar_the_script_enforces(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("**`+` is a human correction**", build)
        self.assertIn("**`.` is a split you authored**", build)
        self.assertIn("a correction of a correction cannot be written at all", build)
        self.assertIn("`pending | met | needs-human`", build)

    def test_build_branches_on_all_three_ledger_states(self) -> None:
        build = _read("src/skills/build.md")
        self.assertIn("Branch on `PROGRESS_STATUS`, and on nothing else", build)
        for state in ("**`invalid`**", "**`missing`**", "**`present`**"):
            self.assertIn(state, build)


if __name__ == "__main__":
    unittest.main()
