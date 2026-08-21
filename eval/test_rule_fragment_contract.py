"""Wave 6 §6.1 — the one structural cut, and the rule that keeps it a cut.

`core.md` was ~25 KB and every skill that loaded `core` paid for all of it,
including the auto-chain rules, which are dead weight on every manual run —
and `manual` is the default and the common path. Those rules now live in
`src/rules/auto.md`, loaded only when the state projection reports
`MODE: auto`.

Measured with `npm run stacks` (chars; ~tok is chars/4):

    command    manual before   manual after     delta
    stories          112,000        107,391    -4,609  (-4.1%)
    start            109,687        105,057    -4,630  (-4.2%)
    review            88,044         83,432    -4,612  (-5.2%)
    spec              86,579         81,970    -4,609  (-5.3%)
    import            64,872         60,263    -4,609  (-7.1%)
    rules             64,686         60,077    -4,609  (-7.1%)
    ui                57,818         53,209    -4,609  (-8.0%)
    ux                49,119         44,510    -4,609  (-9.4%)

`mano review` keeps the saving in **both** modes: it is always human-run and
outside the chain, so it never declares the fragment at all. The auto path pays
~1.5 KB more than before — the fragment's own preamble and the cross-file
pointers that used to be same-file references — and pays it only there.

The failure mode this guards is quiet re-merging: a fragment named in a plain
`requires:` is back on the common path and the split is undone with nothing
visibly broken. `check-refs` fails on that; these tests fail on the prose
drifting away from it.

D8a is the whole justification: a fragment must remove resident context from a
common real path. Do not add fragments to improve a size table.
"""

from __future__ import annotations

import json
import re
import subprocess
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SKILLS = REPO_ROOT / "src" / "skills"


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _front_matter_list(text: str, key: str) -> list[str] | None:
    m = re.search(rf"^{key}:\s*\[(.*?)\]\s*$", text[:600], re.M)
    if not m:
        return None
    return [s.strip() for s in m.group(1).split(",") if s.strip()]


class AutoFragmentTests(unittest.TestCase):
    def test_the_auto_rules_left_core_and_kept_their_content(self) -> None:
        core = _read("src/rules/core.md")
        auto = _read("src/rules/auto.md")

        # The rules themselves are in the fragment...
        for rule in (
            "## The pause rule",
            "## Continuing is an action, not an announcement",
            "## What the chain prints",
            "- Remaining:",
            "Every pause is named.",
            "If you have written words describing what you are about to run",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, auto)
        # ...and not still in core.
        for rule in ("## The pause rule", "Every pause is named."):
            with self.subTest(rule=rule):
                self.assertNotIn(rule, core)

    def test_core_states_the_conditional_load(self) -> None:
        core = _read("src/rules/core.md")
        self.assertIn("`_mano/rules/auto.md`", core)
        self.assertIn("**Read that file when, and only when, the state projection reports `MODE: auto`.**", core)
        self.assertIn("In `manual` it is never opened", core)

    def test_the_fragment_says_when_it_is_loaded(self) -> None:
        auto = _read("src/rules/auto.md")
        self.assertIn("**Loaded only when the state projection reports `MODE: auto`.**", auto)

    def test_review_never_loads_it_even_in_auto(self) -> None:
        """Review is human-run and outside the chain — the one skill that keeps
        the saving in auto mode too."""
        review = _read("src/skills/review.md")
        self.assertIsNone(_front_matter_list(review, "requires-in-auto"))
        self.assertIn("always human-run and outside the auto chain", review)

    def test_every_chain_capable_skill_declares_it_conditionally(self) -> None:
        for name in ("start", "spec", "ux", "ui", "rules", "stories", "import"):
            text = (SKILLS / f"{name}.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertEqual(_front_matter_list(text, "requires-in-auto"), ["auto"])
                self.assertNotIn("auto", _front_matter_list(text, "requires") or [])

    def test_no_skill_loads_the_fragment_unconditionally(self) -> None:
        """The split is undone the moment `auto` appears in a plain requires."""
        for path in sorted(SKILLS.glob("*.md")):
            with self.subTest(skill=path.stem):
                self.assertNotIn("auto", _front_matter_list(path.read_text(encoding="utf-8"), "requires") or [])

    def test_the_implementation_skills_keep_their_own_copy(self) -> None:
        """`build` and `dev` never load `core` or `auto`; the closing block they
        need is stated in full in `implement.md`, and the two must stay in step."""
        implement = _read("src/rules/implement.md")
        self.assertIn("## Closing an armed auto chain", implement)
        self.assertIn("The planning skills' copy lives in `_mano/rules/auto.md`", implement)
        for name in ("build", "dev"):
            text = (SKILLS / f"{name}.md").read_text(encoding="utf-8")
            with self.subTest(skill=name):
                self.assertEqual(_front_matter_list(text, "requires"), ["implement"])
                self.assertIsNone(_front_matter_list(text, "requires-in-auto"))


class StackMeasurementTests(unittest.TestCase):
    """The measurement is a command, not a claim in a commit message."""

    def _stacks(self) -> dict:
        out = subprocess.run(
            ["node", str(REPO_ROOT / "eval" / "stacks.js"), "--json"],
            capture_output=True, text=True, check=True,
        )
        return json.loads(out.stdout)

    def test_stacks_reports_both_modes(self) -> None:
        rows = {r["command"]: r for r in self._stacks()["rows"]}
        for name in ("start", "spec", "stories", "ui", "ux", "rules", "import"):
            with self.subTest(command=name):
                self.assertGreater(rows[name]["auto"], rows[name]["manual"])
        # Review and the two implementation skills cost the same in both modes.
        for name in ("review", "build", "dev"):
            with self.subTest(command=name):
                self.assertEqual(rows[name]["auto"], rows[name]["manual"])

    def test_the_manual_saving_is_the_whole_fragment(self) -> None:
        data = self._stacks()
        fragment = data["rules"]["auto"]
        rows = {r["command"]: r for r in data["rows"]}
        for name in ("start", "spec", "stories"):
            with self.subTest(command=name):
                self.assertEqual(rows[name]["auto"] - rows[name]["manual"], fragment)

    def test_check_refs_rejects_an_unconditional_auto_requirement(self) -> None:
        """The guard that keeps the split from being quietly undone."""
        skill = SKILLS / "spec.md"
        original = skill.read_text(encoding="utf-8")
        broken = original.replace("requires: [core, artifact]", "requires: [core, artifact, auto]")
        self.assertNotEqual(broken, original)
        try:
            skill.write_text(broken, encoding="utf-8")
            result = subprocess.run(
                ["node", str(REPO_ROOT / "eval" / "check-refs.js")],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("must not sit in the unconditional requires list", result.stderr)
        finally:
            skill.write_text(original, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
