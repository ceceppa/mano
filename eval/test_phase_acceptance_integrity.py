from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class PhaseAcceptanceIntegrityTests(unittest.TestCase):
    def test_spec_retires_stale_decisions_that_invert_phase_promises(self) -> None:
        spec = _read("src/skills/spec.md")

        self.assertIn("Phase-promise consistency — hard gate", spec)
        self.assertIn("every `Exit Criteria` action/result, including nested bullets", spec)
        self.assertIn("recoverable while another spec paragraph says it remains locked", spec)
        self.assertIn("replace the stale decision in place", spec)
        self.assertIn("no enabling decision or has an opposing decision", spec)

    def test_stories_block_when_supporting_artifacts_invert_a_phase_promise(self) -> None:
        stories = _read("src/skills/stories.md")

        self.assertIn("0c.3 Phase-promise polarity — hard gate", stories)
        self.assertIn("supporting artifact contradicts phase promise", stories)
        self.assertIn("`recoverable` vs `stays locked`", stories)
        self.assertIn("write no new story files", stories)
        self.assertIn("An AC appearing in a story is coverage, not readiness", stories)

    def test_dev_cannot_mark_done_when_evidence_asserts_the_inverse(self) -> None:
        agents = _read("src/bootstrap/AGENTS.md")
        dev = _read("src/skills/dev.md")

        gate = agents.index("10.1 **Acceptance-evidence gate")
        status_write = agents.index("11. After implementing, mark the story `done`")
        self.assertLess(gate, status_write)
        self.assertIn("A passing suite is not enough", agents)
        self.assertIn("states the opposite outcome", agents)
        self.assertIn("leave the row pending", agents)
        self.assertIn("do not rewrite the AC's meaning, invert the test", agents)
        self.assertIn("Green tests cannot prove the opposite AC", dev)
        self.assertIn("never invert the AC to match stale code", dev)

    def test_review_refuses_to_close_opposing_story_and_spec_outcomes(self) -> None:
        review = _read("src/skills/review.md")

        self.assertIn("Artifact-polarity safety net", review)
        self.assertIn("recoverable versus locked", review)
        self.assertIn("If a cited section contains both outcomes", review)
        self.assertIn("stop before asking for feedback or closing the phase", review)
        self.assertIn("Do not inspect source/tests, accept `close it`", review)

    def test_incident_rule_is_present_on_all_three_prevention_layers(self) -> None:
        surfaces = (
            "src/skills/spec.md",
            "src/skills/stories.md",
            "src/bootstrap/AGENTS.md",
            "src/skills/dev.md",
            "src/skills/review.md",
        )
        for relative in surfaces:
            with self.subTest(relative=relative):
                self.assertIn("id=phase-acceptance-integrity;", _read(relative))


if __name__ == "__main__":
    unittest.main()
