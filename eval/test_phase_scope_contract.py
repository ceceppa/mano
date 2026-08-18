from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class PhaseScopeContractTests(unittest.TestCase):
    def test_dev_stops_instead_of_hiding_a_scope_expansion(self) -> None:
        dev = _read("src/skills/dev.md") + _read("src/rules/implement.md")

        self.assertIn("6.4 **Phase-scope conflict.**", dev)
        self.assertIn("Do not treat “do it anyway” as permission to leave the brief stale", dev)
        self.assertIn("amend the phase brief to include it", dev)
        self.assertIn("This gate applies in default, YOLO, and auto mode", dev)

    def test_clear_user_direction_is_limited_to_current_phase_scope(self) -> None:
        dev = _read("src/skills/dev.md")

        self.assertIn("Clear user-directed behaviour change within the phase", dev)
        self.assertIn("Scope-expanding change:** apply step 6.4", dev)


if __name__ == "__main__":
    unittest.main()
