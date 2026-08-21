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
        implement = _read("src/rules/implement.md")
        dev = _read("src/skills/dev.md")

        # The gate is in the shared contract; dev's status write cites it as
        # the thing that must have passed first.
        self.assertIn("10.1 **Acceptance-evidence gate", implement)
        self.assertIn("the acceptance-evidence gate (10.1) has passed", dev)
        dev = dev + implement
        self.assertIn("A passing suite is not enough", dev)
        self.assertIn("states the opposite outcome", dev)
        self.assertIn("leave the row pending", dev)
        self.assertIn("do not rewrite the AC's meaning, invert the test", dev)

    def test_review_refuses_to_close_opposing_story_and_spec_outcomes(self) -> None:
        review = _read("src/skills/review.md")

        self.assertIn("Artifact-polarity safety net", review)
        self.assertIn("recoverable versus locked", review)
        self.assertIn("If a cited section contains both outcomes", review)
        self.assertIn("stop before asking for feedback or closing the phase", review)
        self.assertIn("Do not inspect source/tests, accept `close it`", review)

    def test_build_refuses_a_brief_its_artifacts_contradict(self) -> None:
        build = _read("src/skills/build.md")

        self.assertIn("0c.3 Phase-promise polarity — hard gate", build)
        self.assertIn("supporting artifact contradicts phase promise", build)
        self.assertIn("`recoverable` vs `stays locked`", build)
        self.assertIn("**write no ledger**", build)

    def test_every_prevention_layer_carries_its_own_provenance(self) -> None:
        """One incident, five surfaces — and each surface's marker names a case
        that actually loads it. A build gate pointing at a stories case is a
        marker that cannot be probed: the case never reads the file the probe
        strips (plan6-6 §6.2).
        """
        surfaces = {
            "src/skills/spec.md": ("spec-promise-consistency", "spec-acceptance-polarity"),
            "src/skills/stories.md": ("phase-acceptance-integrity", "stories-acceptance-polarity"),
            "src/skills/review.md": ("phase-acceptance-integrity", "stories-acceptance-polarity"),
            "src/rules/implement.md": ("acceptance-evidence-polarity", "dev-acceptance-polarity"),
            "src/skills/build.md": ("build-promise-polarity", "build-acceptance-polarity"),
        }
        for relative, (rule_id, case) in surfaces.items():
            with self.subTest(relative=relative):
                text = _read(relative)
                self.assertIn(f"id={rule_id};", text)
                self.assertIn(f"eval={case}", text)
                self.assertIn("incident=exit-criterion-tested-in-reverse", text)
                self.assertTrue((REPO_ROOT / "eval" / "cases" / f"{case}.json").is_file())


if __name__ == "__main__":
    unittest.main()
