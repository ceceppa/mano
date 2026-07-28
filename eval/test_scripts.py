import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_SCRIPT = REPO_ROOT / "src" / "scripts" / "state.js"
BACKLOG_SCRIPT = REPO_ROOT / "src" / "scripts" / "backlog.js"

OPEN_SPEC_BLOCK = """### Open spec
- **Type:** spec-gap
- **Source:** Phase 2 review
- **Context:**
  Define the persistence boundary.
  - **Status:** resolved
  Keep unrelated product context out.
- **Status:** backlog"""

OPEN_RULE_BLOCK = """### Open rule
- **Type:** rule-gap
- **Context:**
  Define the naming convention.
- **Status:** backlog"""

FEATURE_BLOCK = """### Ordinary feature
- **Type:** feature
- **Context:**
  This is phase work, not gap context.
- **Status:** backlog"""

FIELD_SHAPED_FEATURE_BLOCK = """### Feature with metadata-shaped context
- **Type:** feature
- **Context:**
  - **Type:** spec-gap
  CONTEXT_TYPE_SENTINEL
- **Status:** backlog"""

MIXED_BACKLOG = f"""# Backlog

## Core Product Principles

### Principle-shaped sentinel
- **Type:** spec-gap
- **Context:** MUST_NOT_LEAK_FROM_PRINCIPLES
- **Status:** backlog

## Items

{OPEN_SPEC_BLOCK}

{OPEN_RULE_BLOCK}

{FEATURE_BLOCK}

### Resolved spec
- **Type:** spec-gap
- **Context:**
  RESOLVED_SPEC_SENTINEL
- **Status:** resolved

### In phase spec
- **Type:** spec-gap
- **Context:**
  IN_PHASE_SPEC_SENTINEL
- **Status:** in-phase-3

### Resolved spec with metadata-shaped context
- **Type:** spec-gap
- **Context:**
  - **Status:** backlog
  CONTEXT_STATUS_SENTINEL
- **Status:** resolved

{FIELD_SHAPED_FEATURE_BLOCK}
"""


@unittest.skipUnless(shutil.which("node"), "Node.js is required for Mano script tests")
class ManoScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.output = self.root / "_mano_output"
        self.output.mkdir()
        self.backlog = self.output / "backlog.md"

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_state(self, *args):
        return subprocess.run(
            ["node", str(STATE_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
        )

    def run_backlog(self, *args):
        return subprocess.run(
            ["node", str(BACKLOG_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
        )

    def run_backlog_here(self, *args):
        return subprocess.run(
            ["node", str(BACKLOG_SCRIPT), *args],
            cwd=self.root,
            text=True,
            capture_output=True,
        )

    def test_gap_projection_exposes_only_open_exact_type(self):
        self.backlog.write_text(MIXED_BACKLOG)

        spec = self.run_state("--gaps", "spec-gap")
        self.assertEqual(spec.returncode, 0, spec.stderr)
        self.assertIn("TYPE: spec-gap", spec.stdout)
        self.assertIn("COUNT: 1", spec.stdout)
        self.assertIn(OPEN_SPEC_BLOCK, spec.stdout)
        for sentinel in (
            "Open rule",
            "Ordinary feature",
            "RESOLVED_SPEC_SENTINEL",
            "IN_PHASE_SPEC_SENTINEL",
            "MUST_NOT_LEAK_FROM_PRINCIPLES",
            "CONTEXT_STATUS_SENTINEL",
            "CONTEXT_TYPE_SENTINEL",
        ):
            self.assertNotIn(sentinel, spec.stdout)

        rule = self.run_state("--gaps", "rule-gap")
        self.assertEqual(rule.returncode, 0, rule.stderr)
        self.assertIn("TYPE: rule-gap", rule.stdout)
        self.assertIn("COUNT: 1", rule.stdout)
        self.assertIn(OPEN_RULE_BLOCK, rule.stdout)
        self.assertNotIn("Open spec", rule.stdout)

    def test_gap_projection_json_and_missing_backlog_are_safe(self):
        self.backlog.write_text(MIXED_BACKLOG)
        result = self.run_state("--gaps", "spec-gap", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["type"], "spec-gap")
        self.assertEqual(data["status"], "backlog")
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["items"], [OPEN_SPEC_BLOCK])

        self.backlog.unlink()
        missing = self.run_state("--gaps", "rule-gap")
        self.assertEqual(missing.returncode, 0, missing.stderr)
        self.assertIn("COUNT: 0", missing.stdout)
        self.assertIn("(none)", missing.stdout)

    def test_gap_projection_reports_read_errors_instead_of_zero_gaps(self):
        self.backlog.mkdir()

        result = self.run_state("--gaps", "spec-gap")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read _mano_output/backlog.md", result.stderr)
        self.assertNotIn("COUNT: 0", result.stdout)

    def test_gap_projection_rejects_invalid_or_conflicting_modes(self):
        self.backlog.write_text(MIXED_BACKLOG)
        for args in (
            ("--gaps",),
            ("--gaps", "feature"),
            ("--gaps", "spec-gap", "--scope"),
            ("--gaps", "rule-gap", "--next"),
        ):
            with self.subTest(args=args):
                result = self.run_state(*args)
                self.assertNotEqual(result.returncode, 0)

    def test_start_scope_excludes_gaps_and_gap_only_state_stops(self):
        self.backlog.write_text(MIXED_BACKLOG)
        scoped = self.run_state("--scope")
        self.assertEqual(scoped.returncode, 0, scoped.stderr)
        self.assertIn("DECISION: PROCEED", scoped.stdout)
        self.assertIn(FEATURE_BLOCK, scoped.stdout)
        self.assertNotIn("Open spec", scoped.stdout)
        self.assertNotIn("Open rule", scoped.stdout)

        gap_only = MIXED_BACKLOG.replace(f"\n\n{FEATURE_BLOCK}", "")
        gap_only = gap_only.replace(f"\n\n{FIELD_SHAPED_FEATURE_BLOCK}", "")
        self.backlog.write_text(gap_only)
        stopped = self.run_state("--scope")
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        self.assertIn("DECISION: STOP", stopped.stdout)
        self.assertIn("No phase-scopeable backlog items", stopped.stdout)
        self.assertIn("spec-gap → mano spec", stopped.stdout)
        self.assertIn("rule-gap → mano rules", stopped.stdout)
        self.assertNotIn("SCOPE INPUT", stopped.stdout)

    def test_resolve_gap_changes_only_the_exact_target(self):
        self.backlog.write_text(MIXED_BACKLOG)
        before = self.backlog.read_text()
        expected = before.replace(
            OPEN_SPEC_BLOCK,
            OPEN_SPEC_BLOCK.replace("- **Status:** backlog", "- **Status:** resolved"),
        )

        result = self.run_backlog(
            "resolve-gap", "--type", "spec-gap", "--title", "Open spec"
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 item marked resolved", result.stdout)
        self.assertEqual(self.backlog.read_text(), expected)

        second = self.run_backlog(
            "resolve-gap", "--type", "spec-gap", "--title", "open SPEC"
        )
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("already resolved", second.stdout)
        self.assertEqual(self.backlog.read_text(), expected)

    def test_resolve_gap_refuses_unsafe_targets_without_writing(self):
        attempts = (
            ("resolve-gap", "--type", "rule-gap", "--title", "Open spec"),
            ("resolve-gap", "--type", "spec-gap", "--title", "Open"),
            ("resolve-gap", "--type", "spec-gap", "--title", "Missing title"),
            ("resolve-gap", "--type", "spec-gap", "--title", "In phase spec"),
            ("resolve-gap", "--type", "feature", "--title", "Ordinary feature"),
            ("resolve-gap", "--type", "spec-gap"),
        )
        for args in attempts:
            with self.subTest(args=args):
                self.backlog.write_text(MIXED_BACKLOG)
                before = self.backlog.read_bytes()
                result = self.run_backlog(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.backlog.read_bytes(), before)

        self.backlog.write_text(MIXED_BACKLOG)
        before = self.backlog.read_bytes()
        dangling = self.run_backlog_here(
            "resolve-gap", "--type", "spec-gap", "--title"
        )
        self.assertNotEqual(dangling.returncode, 0)
        self.assertIn("non-empty value", dangling.stderr)
        self.assertEqual(self.backlog.read_bytes(), before)

    def test_resolve_gap_rejects_ambiguous_or_malformed_items(self):
        duplicate = MIXED_BACKLOG.replace(
            OPEN_SPEC_BLOCK, f"{OPEN_SPEC_BLOCK}\n\n{OPEN_SPEC_BLOCK}"
        )
        malformed = MIXED_BACKLOG.replace(
            "- **Type:** spec-gap\n- **Source:** Phase 2 review",
            "- **Source:** Phase 2 review",
            1,
        )
        for text, expected_error in (
            (duplicate, "ambiguous"),
            (malformed, "malformed item"),
        ):
            with self.subTest(expected_error=expected_error):
                self.backlog.write_text(text)
                before = self.backlog.read_bytes()
                result = self.run_backlog(
                    "resolve-gap", "--type", "spec-gap", "--title", "Open spec"
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_error, result.stderr)
                self.assertEqual(self.backlog.read_bytes(), before)

    def test_assign_refuses_gap_items_even_when_named_directly(self):
        self.backlog.write_text(MIXED_BACKLOG)
        before = self.backlog.read_text()

        spec = self.run_backlog(
            "assign", "--phase", "4", "--title", "Open spec"
        )
        self.assertEqual(spec.returncode, 0, spec.stderr)
        self.assertIn("route to mano spec", spec.stdout)
        self.assertEqual(self.backlog.read_text(), before)

        rule = self.run_backlog(
            "assign", "--phase", "4", "--title", "Open rule"
        )
        self.assertEqual(rule.returncode, 0, rule.stderr)
        self.assertIn("route to mano rules", rule.stdout)
        self.assertEqual(self.backlog.read_text(), before)

        ordinary = self.run_backlog(
            "assign", "--phase", "4", "--title",
            "Feature with metadata-shaped context",
        )
        self.assertEqual(ordinary.returncode, 0, ordinary.stderr)
        self.assertIn("1 assigned", ordinary.stdout)
        self.assertIn(
            FIELD_SHAPED_FEATURE_BLOCK.replace(
                "- **Status:** backlog", "- **Status:** in-phase-4"
            ),
            self.backlog.read_text(),
        )

        before_dangling = self.backlog.read_bytes()
        dangling = self.run_backlog_here("assign", "--phase", "4", "--title")
        self.assertNotEqual(dangling.returncode, 0)
        self.assertIn("non-empty value", dangling.stderr)
        self.assertEqual(self.backlog.read_bytes(), before_dangling)

    def test_human_edited_field_label_case_is_consistent_across_commands(self):
        lowercase = """# Backlog

## Items

### Lowercase labels
- **type:** spec-gap
- **Context:**
  Human-edited metadata casing remains safe.
- **status:** backlog
"""
        self.backlog.write_text(lowercase)

        projected = self.run_state("--gaps", "spec-gap")
        self.assertEqual(projected.returncode, 0, projected.stderr)
        self.assertIn("COUNT: 1", projected.stdout)
        self.assertIn("Lowercase labels", projected.stdout)

        assigned = self.run_backlog(
            "assign", "--phase", "4", "--title", "Lowercase labels"
        )
        self.assertEqual(assigned.returncode, 0, assigned.stderr)
        self.assertIn("route to mano spec", assigned.stdout)
        self.assertEqual(self.backlog.read_text(), lowercase)

        resolved = self.run_backlog(
            "resolve-gap", "--type", "spec-gap", "--title", "Lowercase labels"
        )
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertIn("1 item marked resolved", resolved.stdout)
        self.assertIn("- **status:** resolved", self.backlog.read_text())


class GapSkillContractTests(unittest.TestCase):
    def test_spec_and_rules_use_only_the_gap_projection_and_targeted_writer(self):
        spec = (REPO_ROOT / "src" / "skills" / "spec.md").read_text()
        rules = (REPO_ROOT / "src" / "skills" / "rules.md").read_text()

        self.assertIn("node _mano/scripts/state.js --gaps spec-gap", spec)
        self.assertIn(
            "node _mano/scripts/backlog.js resolve-gap --type spec-gap", spec
        )
        self.assertIn("Do not open `_mano_output/backlog.md`", spec)

        self.assertIn("node _mano/scripts/state.js --gaps rule-gap", rules)
        self.assertIn(
            "node _mano/scripts/backlog.js resolve-gap --type rule-gap", rules
        )
        self.assertIn("Do not open `_mano_output/backlog.md`", rules)


if __name__ == "__main__":
    unittest.main()
