from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


class ConsistencyContractTests(unittest.TestCase):
    def test_superseded_phase_and_state_wording_does_not_return(self) -> None:
        start = read("src/skills/start.md")
        workflow = read("src/workflow.md")
        core = read("src/rules/core.md")

        for stale in (
            "one testable layer",
            "one-testable-layer",
            "State detection — relying on context",
            "determine where the user is by reading the contents of `_mano_output/`",
            "One screen at a time",
        ):
            self.assertNotIn(stale, start + workflow + core)

        self.assertIn("one independently verifiable outcome", start)
        self.assertIn("State detection — deterministic projections", core)

    def test_start_propagates_track_to_every_deferred_add_path(self) -> None:
        start = read("src/skills/start.md")

        self.assertIn(
            'backlog.js add --title "..." --type [type] --context "..." [--track "[TRACK]"]',
            start,
        )
        self.assertIn(
            'backlog.js add --title "..." --type feature --context "what it is\\nwhy it matters" [--track "[TRACK]"]',
            start,
        )
        self.assertIn("include that exact value on every deferred item", start)

    def test_exact_component_contract_has_one_owner(self) -> None:
        spec = read("src/skills/spec.md")
        rules = read("src/skills/rules.md")
        template = read("src/templates/project-rules.md")

        self.assertIn("particular shared component's consumer-visible prop/event contract remains a spec decision", spec)
        self.assertIn("exact consumer-visible props, events, variants, defaults, and state transitions belong in `tech-spec.md`", rules)
        self.assertIn("Do not define a particular component's exact props, events, variants, defaults, or state transitions here", template)
        self.assertNotIn("exact API props/states", rules)

    def test_every_suggest_hook_has_an_application_boundary(self) -> None:
        hooks_rules = read("src/rules/hooks.md")
        agents = read("src/bootstrap/AGENTS.md")
        post_stories = read("src/hooks/post-stories.example.md")

        self.assertIn("when any active `suggest` or `check` hook has run", hooks_rules)
        for name in ("post-import", "post-start", "post-spec", "post-rules", "post-ux", "post-ui", "post-review", "post-stories"):
            self.assertIn(f"**{name}:**", hooks_rules)
        self.assertIn("When any just-run `suggest` or `check` hook has printed findings", agents)
        self.assertIn("Done stories still require lettered corrective work", post_stories)
        self.assertNotIn("they will run `mano stories`", post_stories)

    def test_bootstrap_status_routing_uses_the_state_projection(self) -> None:
        cursor = read("src/bootstrap/cursorrules")

        self.assertIn("run the required `_mano/scripts/state.js` projection", cursor)
        self.assertIn("Never infer the active phase from chat context or directory listings", cursor)

    def test_done_message_cannot_hide_an_unmet_acceptance_criterion(self) -> None:
        dev = read("src/skills/dev.md") + read("src/rules/implement.md")
        stories_script = read("src/scripts/stories.js")

        self.assertNotIn("an AC you could not meet", dev)
        self.assertIn("An unmet or unverified AC is never an allowed suffix", dev)
        self.assertIn("An unmet or unverified AC leaves the row pending under step 10.1", dev)
        self.assertIn("no statuses changed", stories_script)

    def test_shipped_hook_examples_ship_no_active_checks(self) -> None:
        """A check hook is the user's own review. The shipped examples must
        carry their items commented out, so activating one applies nothing
        until a human chooses the checks."""
        hooks = sorted((ROOT / "src" / "hooks").glob("post-*.example.md"))
        self.assertEqual(len(hooks), 8)
        for path in hooks:
            with self.subTest(hook=path.name):
                text = path.read_text(encoding="utf-8")
                body = text.split("## Checklist", 1)[-1] if "## Checklist" in text else text.split("## Focus", 1)[-1]
                active = [
                    line for line in body.split("\n")
                    if line.startswith("- ") and "-->" not in line
                ]
                # Every item must sit inside the <!-- ... --> example block.
                commented = body.index("<!--") < body.index("- ") < body.index("-->")
                self.assertTrue(commented, f"{path.name} ships uncommented checklist items")
                self.assertTrue(active, f"{path.name} has no example items left to uncomment")

    def test_run_section_belongs_to_suggest_hooks_only(self) -> None:
        """`## Run` names the external skill a suggest hook points at. A check
        hook never runs a command, so a `## Run` there would be inert and
        misleading."""
        for path in sorted((ROOT / "src" / "hooks").glob("post-*.example.md")):
            with self.subTest(hook=path.name):
                text = path.read_text(encoding="utf-8")
                mode = text.split("## Mode", 1)[1].strip().split("\n", 1)[0].strip()
                self.assertIn(mode, {"check", "suggest", "command"})
                self.assertEqual(
                    "## Run" in text,
                    mode == "suggest",
                    f"{path.name} is mode {mode} but {'has' if '## Run' in text else 'lacks'} a ## Run section",
                )

    def test_phase_scoped_hooks_can_see_the_phase_brief(self) -> None:
        """A hook that checks a phase-scoped artifact needs the brief that
        artifact was written for — otherwise it cannot tell what is missing."""
        for name in ("post-start", "post-spec", "post-rules", "post-ux", "post-ui", "post-stories", "post-review"):
            with self.subTest(hook=name):
                text = (ROOT / "src" / "hooks" / f"{name}.example.md").read_text(encoding="utf-8")
                inputs = text.split("## Inputs", 1)[1].split("\n## ", 1)[0]
                self.assertIn("`BRIEF`", inputs, f"{name} cannot see the phase brief")

    def test_hook_inputs_have_a_stated_contract(self) -> None:
        """Every shipped hook declares ## Inputs; the rules file must say what
        Mano does with them, per mode."""
        hooks_rules = read("src/rules/hooks.md")
        self.assertIn("## `## Inputs` — what the hook is allowed to look at", hooks_rules)
        self.assertIn("Allow the review skill to read:", hooks_rules)
        self.assertIn("A `check` hook may not out-read its own skill", hooks_rules)
        self.assertIn("Never invent checklist items", hooks_rules)

    def test_readme_uses_artifact_ownership_not_a_global_rank(self) -> None:
        readme = read("README.md")

        self.assertIn("## Artifact Ownership and Conflicts", readme)
        self.assertNotIn("## Artifact Trust Hierarchy", readme)
        self.assertNotIn("Mano should not:\n- run hooks automatically", readme)
        self.assertNotIn("Use `mano start` to talk to `mano start`", readme)


if __name__ == "__main__":
    unittest.main()
