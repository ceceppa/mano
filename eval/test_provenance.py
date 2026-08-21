from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import provenance


REPO_ROOT = Path(__file__).resolve().parent.parent


def _install(project: Path, *extra_args: str) -> None:
    subprocess.run(
        ["node", str(REPO_ROOT / "bin" / "mano-plan.js"), "install", "--yes", *extra_args],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


class ProvenanceTests(unittest.TestCase):
    def test_repository_markers_are_valid_and_mapped(self) -> None:
        rules = provenance.discover_rules(REPO_ROOT)

        self.assertIn("post-hook-findings-triage", rules)
        self.assertIn("post-stories-hook-findings-triage", rules)
        self.assertIn("project-rule-story-coverage", rules)
        self.assertIn("dev-yolo-batch", rules)
        self.assertIn("ui-phase-preview-ownership", rules)
        self.assertIn("public-interface-contract-readiness", rules)
        self.assertEqual(
            len(rules["post-hook-findings-triage"].occurrences),
            5,
        )
        self.assertEqual(
            rules["post-hook-findings-triage"].evals,
            (
                "hook-triage-no-approval",
                "hook-triage-selected-only",
                "hook-triage-start-no-approval",
                "hook-triage-rules-no-approval",
            ),
        )
        self.assertEqual(
            len(rules["project-rule-story-coverage"].occurrences),
            5,
        )
        self.assertEqual(
            rules["project-rule-story-coverage"].evals,
            ("stories-project-rule-coverage",),
        )
        # `mano build` carries the same obligation on its own path, under its
        # own id and its own case: the unit of work is a Scope leaf, not a
        # story, so a green stories case proves nothing about it (plan6-6 §6.2).
        self.assertEqual(
            len(rules["build-project-rule-coverage"].occurrences),
            2,
        )
        self.assertEqual(
            rules["build-project-rule-coverage"].evals,
            ("build-project-rule-coverage",),
        )
        self.assertEqual(
            len(rules["dev-yolo-batch"].occurrences),
            6,
        )
        self.assertEqual(
            rules["dev-yolo-batch"].evals,
            ("dev-yolo-batch", "dev-yolo-blocker", "dev-default-single"),
        )
        self.assertEqual(
            len(rules["ui-phase-preview-ownership"].occurrences),
            16,
        )
        self.assertEqual(
            rules["ui-phase-preview-ownership"].evals,
            ("ui-phase-preview", "ui-no-phase-preview"),
        )
        self.assertEqual(
            len(rules["public-interface-contract-readiness"].occurrences),
            23,
        )
        self.assertEqual(
            rules["public-interface-contract-readiness"].evals,
            ("spec-public-interface-completeness", "stories-public-interface-gap"),
        )

    def test_no_rule_ships_with_an_unrecorded_pending_eval(self) -> None:
        """The ship guard. `eval=pending` is allowed, but only as a recorded,
        temporary exception with a reason and an owner — never as a silent
        field in a marker nobody reads."""
        provenance.check_pending(REPO_ROOT)

    def test_the_pending_allowlist_is_empty_for_a_release(self) -> None:
        allowlist = json.loads(
            (REPO_ROOT / "eval" / "pending-evals.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            allowlist["rules"],
            {},
            "a release ships with no rule waiting on its eval; pay the debt or "
            "record the exception deliberately and change this test with it",
        )

    def test_the_guard_rejects_an_unrecorded_pending_rule(self) -> None:
        rules = provenance.discover_rules(REPO_ROOT)
        victim = sorted(rules)[0]
        rules[victim].evals = ("pending",)
        with self.assertRaises(provenance.ProvenanceError) as caught:
            provenance.check_pending(REPO_ROOT, rules)
        self.assertIn("no recorded exception", str(caught.exception))

    def test_the_guard_rejects_a_stale_exception(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "eval").mkdir()
            (root / "eval" / "pending-evals.json").write_text(
                json.dumps({"rules": {"long-since-fixed": {"reason": "x", "owner": "y"}}}),
                encoding="utf-8",
            )
            with self.assertRaises(provenance.ProvenanceError) as caught:
                provenance.check_pending(root, {})
            self.assertIn("no longer pending", str(caught.exception))

    def test_a_rule_in_a_conditional_fragment_needs_a_case_in_that_mode(self) -> None:
        """`rules/auto.md` loads only under `MODE: auto`. A rule living there
        whose cases all run in `manual` cannot be probed: stripping it changes
        nothing those cases can see."""
        provenance.check_conditional_coverage(REPO_ROOT)

    def test_the_conditional_guard_catches_a_manual_only_case(self) -> None:
        rules = provenance.discover_rules(REPO_ROOT)
        victim = sorted(rules)[0]
        rule = rules[victim]
        rule.occurrences[0] = provenance.Occurrence(
            REPO_ROOT / "src" / "rules" / "auto.md", 1, 0, 0
        )
        rule.evals = ("review-positive-summary",)  # a manual-mode case
        with self.assertRaises(provenance.ProvenanceError) as caught:
            provenance.check_conditional_coverage(REPO_ROOT, rules)
        self.assertIn("the probe would never load it", str(caught.exception))

    def test_conditional_fragments_come_from_the_skills_themselves(self) -> None:
        self.assertEqual(provenance.conditional_fragments(REPO_ROOT), {"auto": "auto"})

    def test_default_install_contains_no_rule_markers(self) -> None:
        """P0.1 guard: installed files are marker-free (the rule bodies stay)."""
        with tempfile.TemporaryDirectory(prefix="mano-strip-test-") as raw:
            project = Path(raw)
            _install(project)

            offending = []
            for relative in ("AGENTS.md", "CLAUDE.md"):
                path = project / relative
                if path.is_file() and "mano-rule:" in path.read_text(encoding="utf-8"):
                    offending.append(relative)
            for path in (project / "_mano").rglob("*.md"):
                if "mano-rule:" in path.read_text(encoding="utf-8"):
                    offending.append(str(path.relative_to(project)))
            self.assertEqual(offending, [])

            # The rule bodies themselves must survive the marker strip.
            workflow = (project / "_mano" / "workflow.md").read_text(encoding="utf-8")
            self.assertIn("`mano dev yolo` and `mano-dev yolo`", workflow)
            hooks_rules = (project / "_mano" / "rules" / "hooks.md").read_text(encoding="utf-8")
            self.assertIn("## Post-Hook Findings Triage", hooks_rules)

    def test_retirement_probe_strips_every_installed_occurrence(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-provenance-test-") as raw:
            project = Path(raw)
            # Probes install with markers kept so whole rules can be removed.
            _install(project, "--keep-rule-markers")

            removed = provenance.strip_rules(project, {"post-hook-findings-triage"})
            self.assertEqual(removed, {"post-hook-findings-triage": 5})

            stripped_sections = {
                "AGENTS.md": "hook has printed findings",
                "_mano/rules/hooks.md": "## Post-Hook Findings Triage",
                "_mano/skills/start.md": "## Addressing post-start hook findings",
                "_mano/skills/spec.md": "## Addressing post-spec hook findings",
                "_mano/skills/rules.md": "## Addressing post-rules hook findings",
            }
            for relative, heading in stripped_sections.items():
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=post-hook-findings-triage;", text)
                self.assertNotIn(heading, text)

            stories = (project / "_mano" / "skills" / "stories.md").read_text(
                encoding="utf-8"
            )
            self.assertIn("id=post-stories-hook-findings-triage;", stories)

            removed_yolo = provenance.strip_rules(project, {"dev-yolo-batch"})
            # --yes installs CLAUDE.md, workflow.md, and dev.md occurrences; the
            # optional .cursorrules surface is intentionally not installed, and
            # AGENTS.md no longer carries the dev contract.
            self.assertEqual(removed_yolo, {"dev-yolo-batch": 5})
            for relative in (
                "AGENTS.md",
                "CLAUDE.md",
                "_mano/workflow.md",
                "_mano/skills/dev.md",
            ):
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=dev-yolo-batch;", text)

            removed_ui = provenance.strip_rules(
                project, {"ui-phase-preview-ownership"}
            )
            self.assertEqual(
                removed_ui,
                {"ui-phase-preview-ownership": 16},
            )
            for relative in (
                "_mano/workflow.md",
                "_mano/skills/start.md",
                "_mano/skills/ui.md",
                "_mano/templates/design-brief.md",
                "_mano/hooks/post-ui.example.md",
            ):
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=ui-phase-preview-ownership;", text)

            removed_interface = provenance.strip_rules(
                project, {"public-interface-contract-readiness"}
            )
            self.assertEqual(
                removed_interface,
                {"public-interface-contract-readiness": 23},
            )
            for relative in (
                "AGENTS.md",
                "_mano/rules/backlog.md",
                "_mano/skills/start.md",
                "_mano/skills/spec.md",
                "_mano/skills/stories.md",
                "_mano/skills/dev.md",
                "_mano/skills/review.md",
                "_mano/templates/tech-spec.md",
            ):
                text = (project / relative).read_text(encoding="utf-8")
                self.assertNotIn("id=public-interface-contract-readiness;", text)

            # review.md keeps an untagged Identity-level mention of the
            # safety net, so it stays out of this joined phrase check.
            stripped_prompt = "\n".join(
                (project / relative).read_text(encoding="utf-8")
                for relative in (
                    "AGENTS.md",
                    "_mano/workflow.md",
                    "_mano/rules/backlog.md",
                    "_mano/skills/start.md",
                    "_mano/skills/spec.md",
                    "_mano/skills/stories.md",
                    "_mano/skills/dev.md",
                    "_mano/templates/tech-spec.md",
                )
            )
            for incident_phrase in (
                "node _mano/scripts/state.js --spec",
                "Public interface completeness check",
                "Public-interface readiness",
                "A section title or broad capability list is not a usable contract",
                "Exact operation / event",
                "Final-story phase-contract gate",
                "Phase-contract safety net",
            ):
                self.assertNotIn(incident_phrase, stripped_prompt)

            # After a probe's strips, marker normalisation returns the install
            # to the production (marker-free) shape.
            provenance.strip_markers(project)
            for path in (project / "_mano").rglob("*.md"):
                self.assertNotIn("mano-rule:", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
