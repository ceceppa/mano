"""Deterministic pins for the dev implementation contract.

The contract lives in two files: src/skills/dev.md owns the story path, and
src/rules/implement.md owns the half mano build shares. DEV is their
concatenation — a pin cares that the contract says it, not which half.

These are text pins, not behaviour evals: the load-bearing sentences that must
survive verbatim wherever the contract lives. If one fails, the contract was
reworded or dropped during an edit — inspect before shipping.
"""

from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEV = (
    (REPO_ROOT / "src" / "skills" / "dev.md").read_text(encoding="utf-8")
    + (REPO_ROOT / "src" / "rules" / "implement.md").read_text(encoding="utf-8")
)
AGENTS = (REPO_ROOT / "src" / "bootstrap" / "AGENTS.md").read_text(encoding="utf-8")


class DevContractPins(unittest.TestCase):
    def test_step11_concurrent_edit_guard_survives_verbatim(self) -> None:
        # The OWNER/PHASE_ID re-check before the status write is the
        # concurrent-edit guard; it must never be optimised away.
        self.assertIn(
            "rerun `state.js --next` immediately before this command and stop "
            "unless `OWNER` and `PHASE_ID` still match",
            DEV,
        )
        self.assertIn(
            "After the writer succeeds, rerun `state.js --next`. Confirm that "
            "`OWNER` and `PHASE_ID` are unchanged",
            DEV,
        )

    def test_step12_single_line_with_fresh_session_suffix(self) -> None:
        self.assertIn(
            "`Story [N] done — status updated in stories/README.md. "
            "Start a fresh session for the next story.`",
            DEV,
        )

    def test_repair_mode_budget_present(self) -> None:
        self.assertIn("## Repair Mode", DEV)
        self.assertIn("the FIRST error only", DEV)
        self.assertIn("Attempt limit: 3 on the same error", DEV)
        # The two checks that are never optimised away inside Repair Mode.
        self.assertIn("acceptance-evidence gate (10.1), run in full regardless", DEV)

    def test_verification_runs_through_verify_script(self) -> None:
        self.assertIn("node _mano/scripts/verify.js -- <command>", DEV)

    def test_agents_stub_keeps_the_two_ambient_rules(self) -> None:
        # AGENTS.md keeps only the stub; its two inline rules are deliberate
        # redundancy from a recorded incident and must not shrink to a pointer.
        self.assertIn("Its full contract is `_mano/skills/dev.md`, plus the shared", AGENTS)
        self.assertIn("`_mano/skills/build.md`, plus the", AGENTS)
        self.assertIn(
            "The index `Status` column is the only done-signal", AGENTS
        )
        self.assertIn("`Not this story` is a hard boundary", AGENTS)
        # The moved sections must not still live in AGENTS.md.
        self.assertNotIn("## Execution modes", AGENTS)
        self.assertNotIn("Implementation Output Discipline", AGENTS)
        self.assertNotIn("## Changes", AGENTS)

    def test_completed_stories_immutable_rule_routes_to_stories(self) -> None:
        self.assertIn("### Completed stories are immutable", AGENTS)
        self.assertIn('mano stories "[what changed]"', AGENTS)
        # The old self-implement procedure (add-row + hand-written story file)
        # must be gone: corrections route through mano stories → mano dev.
        self.assertNotIn("stories.js add-row", AGENTS)

    def test_dev_never_edits_story_files(self) -> None:
        self.assertIn("**`mano dev` never edits a story file.**", DEV)


if __name__ == "__main__":
    unittest.main()
