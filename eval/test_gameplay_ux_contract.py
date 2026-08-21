from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class GameplayUxContractTests(unittest.TestCase):
    def test_workflow_treats_gameplay_interaction_as_ux(self) -> None:
        text = _read("src/rules/artifact.md")
        self.assertIn("**player-facing game loops**", text)
        self.assertIn("available-versus-locked states", text)
        self.assertIn("does not make an interaction flow self-evident", text)
        self.assertIn("a hardcoded default cannot stand in", text)

    def test_start_audits_missing_ux_for_player_facing_phases(self) -> None:
        text = _read("src/skills/start.md")
        self.assertIn("For a user-facing or player-facing game phase", text)
        self.assertIn("Keep `mano ux` visible", text)
        self.assertIn("The human may still explicitly choose `skip ux`", text)
        self.assertIn("Run the user/player-flow check above", text)

    def test_spec_and_rules_keep_missing_gameplay_ux_visible(self) -> None:
        for relative in ("src/skills/spec.md", "src/skills/rules.md"):
            with self.subTest(relative=relative):
                text = _read(relative)
                self.assertIn("For player-facing games", text)
                self.assertIn("progression or unlock actions", text)
                self.assertIn("a minimal or in-world presentation is still a flow", text)

    def test_stories_stop_when_gameplay_flow_is_unowned(self) -> None:
        text = _read("src/skills/stories.md")
        self.assertIn("**Player-flow check.**", text)
        self.assertIn("**0c.1 Player choice interaction — hard gate.**", text)
        self.assertIn("⚠️ Story readiness gap: player choice interaction missing", text)
        self.assertIn("Do not propose a hotkey, picker, cycling scheme", text)
        self.assertIn("Minimal” presentation does not let stories invent", text)

    def test_ux_and_dev_capture_in_world_selection(self) -> None:
        ux = _read("src/skills/ux.md")
        template = _read("src/templates/ux-flow.md")
        dev = _read("src/skills/dev.md") + _read("src/rules/implement.md")

        self.assertIn("an in-world/HUD interaction is a flow", ux)
        self.assertIn("Do not leave a hardcoded active item", ux)
        self.assertIn("## Player / In-World Interaction", template)
        self.assertIn("6.3 **Player-choice UX gap.**", dev)
        self.assertIn("do not invent a hotkey, picker, cycling scheme", dev)


if __name__ == "__main__":
    unittest.main()
