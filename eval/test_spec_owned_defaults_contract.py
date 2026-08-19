from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class SpecOwnedDefaultsContractTests(unittest.TestCase):
    def test_spec_sweeps_exit_states_for_implicit_quantities(self) -> None:
        text = _read("src/skills/spec.md")
        self.assertIn("**Exit-state sweep — mandatory, not a prose skim.**", text)
        self.assertIn("including nested action/result bullets", text)
        self.assertIn("“small area”", text)
        self.assertIn("`initial_radius`", text)
        self.assertIn("Do not let a later story choose either value", text)
        self.assertIn("Never conceal the missing decision with a story-owned default", text)

    def test_template_exposes_initial_values_as_data_model_decisions(self) -> None:
        text = _read("src/templates/tech-spec.md")
        self.assertIn("starting or first-use state", text)
        self.assertIn("initial_radius", text)
        self.assertIn("Never leave that value to a story", text)

    def test_stories_hard_stop_on_unowned_technical_defaults(self) -> None:
        text = _read("src/skills/stories.md")
        self.assertIn("**0c.0 Spec-owned defaults and initial state — hard gate.**", text)
        self.assertIn("⚠️ Story readiness gap: spec-owned default missing", text)
        self.assertIn("Do not offer a story-owned default", text)
        self.assertIn("they never choose it", text)

    def test_dev_defers_missing_defaults_to_spec(self) -> None:
        dev = _read("src/skills/dev.md")
        self.assertIn("6.2 **Spec-owned default gap.**", dev)
        self.assertIn("“story-owned default,”", dev)
        self.assertIn("Stop and route to `mano spec` when it is missing", dev)


if __name__ == "__main__":
    unittest.main()
