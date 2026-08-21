from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


class FluentChainContractTests(unittest.TestCase):
    def test_spec_requires_return_type_chain_closure(self) -> None:
        text = _read("src/skills/spec.md")
        self.assertIn("chain-closure matrix", text)
        self.assertIn("Exact returned type", text)
        self.assertIn("Terminals still callable", text)
        self.assertIn("Declaring `play()` on one leaf type does not cover", text)
        self.assertIn("inspect the declared return type at every named chain boundary", text)

    def test_tech_spec_template_has_chain_closure_surface(self) -> None:
        text = _read("src/templates/tech-spec.md")
        self.assertIn("Expression before call", text)
        self.assertIn("Context retained", text)
        self.assertIn("Terminals still callable", text)

    def test_stories_preserve_exact_terminal_paths(self) -> None:
        text = _read("src/skills/stories.md")
        self.assertIn("trace every in-scope chain transition", text)
        self.assertIn("Verify every `Implementation Reference` citation against its target", text)
        self.assertIn("Before accepting a `Not this story` boundary", text)
        self.assertIn("**0f.1 Exit-path coverage.**", text)
        self.assertIn("alternative entry point", text)
        self.assertIn("composition and its terminal action in the same path", text)

    def test_start_expands_broad_scope_into_exit_criteria(self) -> None:
        text = _read("src/skills/start.md")
        self.assertIn("breadth words such as", text)
        self.assertIn("Do not let one representative happy path silently narrow", text)

    def test_dev_checks_phase_contract_before_final_story(self) -> None:
        dev = _read("src/skills/dev.md")
        self.assertIn("**Final-story phase-contract gate.**", dev)
        # The gate runs before the shared pre-reads, which now start at the
        # pointer into _mano/rules/implement.md.
        self.assertLess(
            dev.index("**Final-story phase-contract gate.**"),
            dev.index("6.2–10. **The gap gates, pre-reads, and verification are in"),
        )
        self.assertIn("same user/caller route and breadth", dev)
        self.assertIn("In YOLO mode", dev)
        self.assertIn("this gate still applies before the final snapshotted story", dev)

    def test_review_cannot_close_unowned_phase_contract(self) -> None:
        text = _read("src/skills/review.md")
        self.assertIn("**Phase-contract safety net — stories path only.**", text)
        self.assertIn("before asking for feedback or closing the phase", text)
        self.assertIn("exact cited canonical spec section", text)
        self.assertIn("closes the chain through each named returned type", text)
        self.assertIn("do not let `close it` waive this gate", text)

    def test_the_story_safety_nets_are_scoped_to_the_stories_path(self) -> None:
        # B6: review branched on PROGRESS_STATUS and then still asked for "the
        # story's Implementation Reference" and routed gaps through mano stories
        # / mano dev — which on a build-path phase creates the second ledger the
        # projection refuses.
        text = _read("src/skills/review.md")
        self.assertIn("**Artifact-polarity safety net — stories path only.**", text)
        self.assertIn(
            "Review never asks for an `Implementation Reference`, never opens a story file, "
            "and never routes to `mano stories` or `mano dev`",
            text,
        )
        self.assertIn(
            "**Review's only sanctioned `progress.js` surfaces are `request-rework`, "
            "`resolve-rework`, and `sign-off`.**",
            text,
        )


if __name__ == "__main__":
    unittest.main()
