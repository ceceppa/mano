import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_SCRIPT = REPO_ROOT / "src" / "scripts" / "state.js"
BACKLOG_SCRIPT = REPO_ROOT / "src" / "scripts" / "backlog.js"
STORIES_SCRIPT = REPO_ROOT / "src" / "scripts" / "stories.js"
OWNER_SCRIPT = REPO_ROOT / "src" / "scripts" / "owner.js"
MODE_SCRIPT = REPO_ROOT / "src" / "scripts" / "mode.js"

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

IN_PHASE_FEATURE_BLOCK = """### Current phase callable API
- **Type:** feature
- **Context:**
  Define exact method names and argument shapes.
- **Status:** in-phase-3"""

IN_PHASE_TEST_BLOCK = """### Current phase contract coverage
- **Type:** test
- **Context:**
  Verify every public method mapping.
- **Status:** in-phase-3"""

SPEC_INPUT_BACKLOG = f"""# Backlog

## Core Product Principles

- PRINCIPLE_SPEC_SENTINEL must never enter spec input.

## Items

{IN_PHASE_FEATURE_BLOCK}

{IN_PHASE_TEST_BLOCK}

{OPEN_SPEC_BLOCK}

### Other phase work
- **Type:** feature
- **Context:**
  OTHER_PHASE_SENTINEL
- **Status:** in-phase-2

### Deferred ordinary feature
- **Type:** feature
- **Context:**
  DEFERRED_FEATURE_SENTINEL
- **Status:** backlog

{OPEN_RULE_BLOCK}

### Resolved phase spec gap
- **Type:** spec-gap
- **Context:**
  RESOLVED_SPEC_INPUT_SENTINEL
- **Status:** resolved
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

    def run_state_as(self, owner, *args):
        env = os.environ.copy()
        env["MANO_OWNER"] = owner
        return subprocess.run(
            ["node", str(STATE_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            env=env,
        )

    def run_backlog(self, *args):
        return subprocess.run(
            ["node", str(BACKLOG_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
        )

    def run_backlog_as(self, owner, *args):
        env = os.environ.copy()
        env["MANO_OWNER"] = owner
        return subprocess.run(
            ["node", str(BACKLOG_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            env=env,
        )

    def run_stories_as(self, owner, *args):
        env = os.environ.copy()
        env["MANO_OWNER"] = owner
        return subprocess.run(
            ["node", str(STORIES_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            env=env,
        )

    def run_mode(self, *args, env_mode=None):
        env = os.environ.copy()
        env.pop("MANO_MODE", None)
        if env_mode is not None:
            env["MANO_MODE"] = env_mode
        return subprocess.run(
            ["node", str(MODE_SCRIPT), *args],
            cwd=self.root,
            text=True,
            capture_output=True,
            env=env,
        )

    def run_state_with_mode(self, env_mode, *args):
        env = os.environ.copy()
        env["MANO_MODE"] = env_mode
        return subprocess.run(
            ["node", str(STATE_SCRIPT), *args, str(self.root)],
            cwd=self.root,
            text=True,
            capture_output=True,
            env=env,
        )

    def run_owner(self, *args):
        return subprocess.run(
            ["node", str(OWNER_SCRIPT), *args],
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

    def test_spec_projection_exposes_only_current_phase_and_open_spec_gaps(self):
        phase = self.output / "phase-3"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 3\n")
        self.backlog.write_text(SPEC_INPUT_BACKLOG)

        result = self.run_state("--spec")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--- SPEC INPUT", result.stdout)
        self.assertIn("STATUS: READY", result.stdout)
        self.assertIn("PHASE: 3", result.stdout)
        self.assertIn("BRIEF: _mano_output/phase-3/phase-brief.md", result.stdout)
        self.assertIn("BRIEF_STATUS: present", result.stdout)
        self.assertIn("IN_PHASE_STATUS: in-phase-3", result.stdout)
        self.assertIn("IN_PHASE_COUNT: 2", result.stdout)
        self.assertIn("SPEC_GAP_STATUS: backlog", result.stdout)
        self.assertIn("SPEC_GAP_COUNT: 1", result.stdout)
        self.assertIn("--- BEGIN IN-PHASE ITEM 1/2 ---", result.stdout)
        self.assertIn("--- END IN-PHASE ITEM 2/2 ---", result.stdout)
        self.assertIn("--- BEGIN SPEC-GAP ITEM 1/1 ---", result.stdout)
        self.assertIn("--- END SPEC-GAP ITEM 1/1 ---", result.stdout)
        self.assertIn("END_IN_PHASE_COUNT: 2", result.stdout)
        self.assertIn("END_SPEC_GAP_COUNT: 1", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith("--- END SPEC INPUT ---"))
        self.assertIn(IN_PHASE_FEATURE_BLOCK, result.stdout)
        self.assertIn(IN_PHASE_TEST_BLOCK, result.stdout)
        self.assertIn(OPEN_SPEC_BLOCK, result.stdout)
        for sentinel in (
            "PRINCIPLE_SPEC_SENTINEL",
            "OTHER_PHASE_SENTINEL",
            "DEFERRED_FEATURE_SENTINEL",
            "Open rule",
            "RESOLVED_SPEC_INPUT_SENTINEL",
        ):
            self.assertNotIn(sentinel, result.stdout)

    def test_spec_projection_json_and_active_phase_missing_backlog_blocks(self):
        phase = self.output / "phase-3"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 3\n")
        self.backlog.write_text(SPEC_INPUT_BACKLOG)

        result = self.run_state("--spec", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "READY")
        self.assertEqual(data["phase"], 3)
        self.assertEqual(data["briefPath"], "_mano_output/phase-3/phase-brief.md")
        self.assertTrue(data["briefExists"])
        self.assertEqual(data["briefStatus"], "present")
        self.assertEqual(data["inPhaseStatus"], "in-phase-3")
        self.assertEqual(data["inPhaseCount"], 2)
        self.assertEqual(data["inPhaseItems"], [
            IN_PHASE_FEATURE_BLOCK,
            IN_PHASE_TEST_BLOCK,
        ])
        self.assertEqual(data["specGapStatus"], "backlog")
        self.assertEqual(data["specGapCount"], 1)
        self.assertEqual(data["specGapItems"], [OPEN_SPEC_BLOCK])

        self.backlog.unlink()
        missing = self.run_state("--spec")
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn("active phase 3", missing.stderr)
        self.assertIn("backlog.md is missing", missing.stderr)
        self.assertNotIn("STATUS: READY", missing.stdout)

    def test_spec_projection_without_phase_accepts_missing_backlog(self):
        result = self.run_state("--spec")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("STATUS: READY", result.stdout)
        self.assertIn("PHASE: none", result.stdout)
        self.assertIn("IN_PHASE_COUNT: 0", result.stdout)
        self.assertIn("SPEC_GAP_COUNT: 0", result.stdout)
        self.assertTrue(result.stdout.rstrip().endswith("--- END SPEC INPUT ---"))

    def test_spec_projection_active_phase_requires_canonical_items_section(self):
        phase = self.output / "phase-3"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 3\n")

        invalid_backlogs = (
            "",
            "# Backlog\n\n## Core Product Principles\n\nNo items section.\n",
        )
        for backlog_text in invalid_backlogs:
            with self.subTest(backlog_text=backlog_text):
                self.backlog.write_text(backlog_text)
                result = self.run_state("--spec")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("active phase 3", result.stderr)
                self.assertIn("no canonical ## Items section", result.stderr)
                self.assertNotIn("STATUS: READY", result.stdout)

    def test_spec_projection_reports_missing_phase_or_brief_without_blocking(self):
        self.backlog.write_text(SPEC_INPUT_BACKLOG)

        no_phase = self.run_state("--spec")
        self.assertEqual(no_phase.returncode, 0, no_phase.stderr)
        self.assertIn("STATUS: READY", no_phase.stdout)
        self.assertIn("PHASE: none", no_phase.stdout)
        self.assertIn("BRIEF: missing", no_phase.stdout)
        self.assertIn("BRIEF_STATUS: missing", no_phase.stdout)
        self.assertIn("IN_PHASE_STATUS: unavailable", no_phase.stdout)
        self.assertIn("IN_PHASE_COUNT: 0", no_phase.stdout)
        self.assertIn("SPEC_GAP_COUNT: 1", no_phase.stdout)

        phase = self.output / "phase-3"
        phase.mkdir()
        missing_brief = self.run_state("--spec")
        self.assertEqual(missing_brief.returncode, 0, missing_brief.stderr)
        self.assertIn("STATUS: READY", missing_brief.stdout)
        self.assertIn("PHASE: 3", missing_brief.stdout)
        self.assertIn("BRIEF: _mano_output/phase-3/phase-brief.md", missing_brief.stdout)
        self.assertIn("BRIEF_STATUS: missing", missing_brief.stdout)
        self.assertIn("IN_PHASE_COUNT: 2", missing_brief.stdout)

    def test_spec_projection_reports_read_errors_instead_of_empty_input(self):
        phase = self.output / "phase-3"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 3\n")
        self.backlog.mkdir()

        result = self.run_state("--spec")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot project spec input", result.stderr)
        self.assertNotIn("IN_PHASE_COUNT: 0", result.stdout)
        self.assertNotIn("SPEC_GAP_COUNT: 0", result.stdout)

    def test_spec_projection_rejects_malformed_backlog_items(self):
        phase = self.output / "phase-3"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 3\n")
        self.backlog.write_text("""# Backlog

## Items

### Missing status
- **Type:** feature
- **Context:**
  Its status cannot be inferred safely.
""")

        result = self.run_state("--spec")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot project spec input", result.stderr)
        self.assertIn("malformed backlog item", result.stderr)
        self.assertNotIn("STATUS: READY", result.stdout)
        self.assertNotIn("IN_PHASE_COUNT:", result.stdout)
        self.assertNotIn("SPEC_GAP_COUNT:", result.stdout)

    def test_spec_projection_help_and_conflicting_modes(self):
        help_result = self.run_state("--help")
        self.assertEqual(help_result.returncode, 0, help_result.stderr)
        self.assertIn("--spec", help_result.stdout)

        for args in (
            ("--spec", "--scope"),
            ("--spec", "--next"),
            ("--spec", "--ui"),
            ("--spec", "--gaps", "spec-gap"),
            ("--spec", "--verbose"),
        ):
            with self.subTest(args=args):
                conflict = self.run_state(*args)
                self.assertNotEqual(conflict.returncode, 0)

    def test_ui_projection_reports_exact_phase_local_paths(self):
        phase = self.output / "phase-2"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 2\n")
        (phase / "design-preview.html").write_text("phase 2 preview\n")
        (self.output / "design-brief.md").write_text("# Design brief\n")
        (self.output / "design-preview.html").write_text("legacy root preview\n")

        result = self.run_state("--ui")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--- UI INPUT", result.stdout)
        self.assertIn("STATUS: READY", result.stdout)
        self.assertIn("PHASE: 2", result.stdout)
        self.assertIn("BRIEF: _mano_output/phase-2/phase-brief.md", result.stdout)
        self.assertIn("PREVIEW: _mano_output/phase-2/design-preview.html", result.stdout)
        self.assertIn("PREVIEW_STATUS: present", result.stdout)
        self.assertIn("DESIGN_BRIEF_STATUS: present", result.stdout)
        self.assertIn("LEGACY_ROOT_PREVIEW: present", result.stdout)
        self.assertIn("leave untouched", result.stdout)
        self.assertNotIn("legacy root preview", result.stdout)

    def test_ui_projection_blocks_without_an_approved_phase_brief(self):
        no_phase = self.run_state("--ui")
        self.assertEqual(no_phase.returncode, 0, no_phase.stderr)
        self.assertIn("STATUS: BLOCKED", no_phase.stdout)
        self.assertIn("PHASE: none", no_phase.stdout)
        self.assertIn("ROUTE: mano start", no_phase.stdout)

        phase = self.output / "phase-3"
        phase.mkdir()
        unfinished = self.run_state("--ui")
        self.assertEqual(unfinished.returncode, 0, unfinished.stderr)
        self.assertIn("STATUS: BLOCKED", unfinished.stdout)
        self.assertIn("PHASE: 3", unfinished.stdout)
        self.assertIn("BRIEF: _mano_output/phase-3/phase-brief.md", unfinished.stdout)
        self.assertIn("finish the draft", unfinished.stdout)

    def test_ui_projection_json_and_conflicting_modes(self):
        phase = self.output / "phase-1"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Phase 1\n")

        result = self.run_state("--ui", "--json")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["status"], "READY")
        self.assertEqual(data["phase"], 1)
        self.assertEqual(data["previewPath"], "_mano_output/phase-1/design-preview.html")
        self.assertFalse(data["previewExists"])

        for args in (
            ("--ui", "--scope"),
            ("--ui", "--next"),
            ("--ui", "--gaps", "spec-gap"),
            ("--ui", "--verbose"),
        ):
            with self.subTest(args=args):
                conflict = self.run_state(*args)
                self.assertNotEqual(conflict.returncode, 0)

    def test_ui_projection_blocks_a_closed_phase_but_allows_reopened_work(self):
        phase = self.output / "phase-4"
        stories = phase / "stories"
        stories.mkdir(parents=True)
        (phase / "phase-brief.md").write_text("# Phase 4\n")
        (stories / "README.md").write_text(
            "| # | Story | File | Status |\n"
            "|---|-------|------|--------|\n"
            "| 1 | Demo | story-1-demo.md | done |\n"
        )
        (self.output / "reviews.md").write_text("## Phase 4 Review\n\nShipped.\n")

        closed = self.run_state("--ui")
        self.assertEqual(closed.returncode, 0, closed.stderr)
        self.assertIn("STATUS: BLOCKED", closed.stdout)
        self.assertIn("already reviewed", closed.stdout)
        self.assertIn("mano start", closed.stdout)

        (stories / "README.md").write_text(
            "| # | Story | File | Status |\n"
            "|---|-------|------|--------|\n"
            "| 1 | Demo | story-1-demo.md | pending |\n"
        )
        reopened = self.run_state("--ui")
        self.assertEqual(reopened.returncode, 0, reopened.stderr)
        self.assertIn("STATUS: READY", reopened.stdout)
        self.assertIn("PHASE: 4", reopened.stdout)

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

    def test_reject_retires_only_the_named_open_items(self):
        self.backlog.write_text(MIXED_BACKLOG)
        expected = MIXED_BACKLOG.replace(
            FEATURE_BLOCK,
            FEATURE_BLOCK.replace("- **Status:** backlog", "- **Status:** rejected"),
        )

        result = self.run_backlog("reject", "--title", "Ordinary feature")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("1 item(s) marked rejected", result.stdout)
        self.assertEqual(self.backlog.read_text(), expected)

        # Rejecting is idempotent and never re-writes an already-rejected item.
        second = self.run_backlog("reject", "--title", "ordinary FEATURE")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("already 'rejected'", second.stdout)
        self.assertEqual(self.backlog.read_text(), expected)

    def test_reject_leaves_non_open_and_unidentifiable_targets_untouched(self):
        duplicate = MIXED_BACKLOG.replace(
            FEATURE_BLOCK, f"{FEATURE_BLOCK}\n\n{FEATURE_BLOCK}"
        )
        cases = (
            # (backlog text, title, expected marker in stdout)
            (MIXED_BACKLOG, "In phase spec", "only open 'backlog' items"),
            (MIXED_BACKLOG, "Resolved spec", "only open 'backlog' items"),
            (MIXED_BACKLOG, "Missing title", "no matching item"),
            # A heading under Core Product Principles is not a backlog item.
            (MIXED_BACKLOG, "Principle-shaped sentinel", "no matching item"),
            (duplicate, "Ordinary feature", "ambiguous"),
        )
        for text, title, marker in cases:
            with self.subTest(title=title):
                self.backlog.write_text(text)
                before = self.backlog.read_bytes()
                result = self.run_backlog("reject", "--title", title)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(marker, result.stdout)
                self.assertEqual(self.backlog.read_bytes(), before)

        self.backlog.write_text(MIXED_BACKLOG)
        before = self.backlog.read_bytes()
        for args in (("reject",), ("reject", "--title")):
            with self.subTest(args=args):
                result = self.run_backlog_here(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.backlog.read_bytes(), before)

    def test_rejected_items_are_never_scopeable_or_assignable(self):
        self.backlog.write_text(MIXED_BACKLOG)
        self.run_backlog("reject", "--title", "Ordinary feature")
        after_reject = self.backlog.read_bytes()

        scope = self.run_state("--scope")
        self.assertEqual(scope.returncode, 0, scope.stderr)
        self.assertNotIn("Ordinary feature", scope.stdout)

        # assign must not pull a rejected item back into a phase.
        assigned = self.run_backlog("assign", "--phase", "4", "--title", "Ordinary feature")
        self.assertEqual(assigned.returncode, 0, assigned.stderr)
        self.assertIn("already 'rejected'", assigned.stdout)
        self.assertEqual(self.backlog.read_bytes(), after_reject)

        # review's phase close sweep must not convert a rejection into "resolved".
        resolved = self.run_backlog("resolve", "--phase", "4")
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertIn("- **Status:** rejected", self.backlog.read_text())

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

    def test_legacy_routing_remains_default_when_owned_phases_exist(self):
        (self.output / "alice-phase-9").mkdir()
        (self.output / "bob-phase-12").mkdir()

        owned_only = self.run_state("--current")
        self.assertEqual(owned_only.returncode, 0, owned_only.stderr)
        self.assertIn("OWNER_MODE: legacy", owned_only.stdout)
        self.assertIn("STATUS: NO_PHASE", owned_only.stdout)
        self.assertIn("PHASE_ID: none", owned_only.stdout)

        (self.output / "phase-2").mkdir()

        current = self.run_state("--current")

        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertIn("OWNER: none (legacy phase-N mode)", current.stdout)
        self.assertIn("OWNER_MODE: legacy", current.stdout)
        self.assertIn("PHASE: 2", current.stdout)
        self.assertIn("PHASE_ID: phase-2", current.stdout)
        self.assertIn("PHASE_DIR: _mano_output/phase-2", current.stdout)
        self.assertNotIn("alice-phase-9", current.stdout)
        self.assertNotIn("bob-phase-12", current.stdout)

    def test_owner_routing_selects_only_that_owners_phase_sequence(self):
        (self.output / "phase-15").mkdir()
        (self.output / "alice-phase-1").mkdir()
        (self.output / "alice-phase-3").mkdir()
        (self.output / "bob-phase-20").mkdir()

        current = self.run_state_as("alice", "--current")
        self.assertEqual(current.returncode, 0, current.stderr)
        self.assertIn("OWNER: alice", current.stdout)
        self.assertIn("OWNER_MODE: owned", current.stdout)
        self.assertIn("PHASE: 3", current.stdout)
        self.assertIn("PHASE_ID: alice-phase-3", current.stdout)
        self.assertIn("PHASE_DIR: _mano_output/alice-phase-3", current.stdout)
        self.assertNotIn("bob-phase-20", current.stdout)

        self.backlog.write_text(f"# Backlog\n\n## Items\n\n{FEATURE_BLOCK}\n")
        scoped = self.run_state_as("alice", "--scope")
        self.assertEqual(scoped.returncode, 0, scoped.stderr)
        self.assertIn("NEXT: resume-draft", scoped.stdout)
        self.assertIn("PHASE_ID: alice-phase-3", scoped.stdout)
        self.assertIn("PHASE_DIR: _mano_output/alice-phase-3", scoped.stdout)
        self.assertIn("IN_PHASE_STATUS: in-alice-phase-3", scoped.stdout)

        (self.output / "reviews.md").write_text(
            "## Phase 15 Review — 2026-08-04\n\nLEGACY_REVIEW_SENTINEL\n\n"
            "## Phase 20 Review — Owner: bob — 2026-08-04\n\n"
            "BOB_REVIEW_SENTINEL\n"
        )
        first_for_new_owner = self.run_state_as("charlie", "--scope")
        self.assertEqual(
            first_for_new_owner.returncode, 0, first_for_new_owner.stderr
        )
        self.assertIn("NEXT: scope-backlog", first_for_new_owner.stdout)
        self.assertIn("PHASE: 1", first_for_new_owner.stdout)
        self.assertIn("PHASE_ID: charlie-phase-1", first_for_new_owner.stdout)
        self.assertIn(
            "PHASE_DIR: _mano_output/charlie-phase-1",
            first_for_new_owner.stdout,
        )
        self.assertIn(
            "IN_PHASE_STATUS: in-charlie-phase-1",
            first_for_new_owner.stdout,
        )
        self.assertNotIn("LEGACY_REVIEW_SENTINEL", first_for_new_owner.stdout)
        self.assertNotIn("BOB_REVIEW_SENTINEL", first_for_new_owner.stdout)

    def test_owned_spec_projection_reads_only_exact_owner_phase_items(self):
        phase = self.output / "alice-phase-3"
        phase.mkdir()
        (phase / "phase-brief.md").write_text("# Alice phase 3\n")
        alice_item = IN_PHASE_FEATURE_BLOCK.replace(
            "in-phase-3", "in-alice-phase-3"
        )
        bob_item = IN_PHASE_TEST_BLOCK.replace(
            "in-phase-3", "in-bob-phase-3"
        )
        self.backlog.write_text(
            f"# Backlog\n\n## Items\n\n{alice_item}\n\n{bob_item}\n\n"
            f"{IN_PHASE_TEST_BLOCK}\n\n{OPEN_SPEC_BLOCK}\n"
        )

        result = self.run_state_as("alice", "--spec")

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OWNER: alice", result.stdout)
        self.assertIn("PHASE_ID: alice-phase-3", result.stdout)
        self.assertIn("BRIEF: _mano_output/alice-phase-3/phase-brief.md", result.stdout)
        self.assertIn("IN_PHASE_STATUS: in-alice-phase-3", result.stdout)
        self.assertIn("IN_PHASE_COUNT: 1", result.stdout)
        self.assertIn(alice_item, result.stdout)
        self.assertIn(OPEN_SPEC_BLOCK, result.stdout)
        self.assertNotIn("in-bob-phase-3", result.stdout)
        self.assertNotIn(IN_PHASE_TEST_BLOCK, result.stdout)

    def test_owned_backlog_assign_and_resolve_are_isolated(self):
        item_a = FEATURE_BLOCK
        item_b = FEATURE_BLOCK.replace("Ordinary feature", "Second feature")
        self.backlog.write_text(
            f"# Backlog\n\n## Items\n\n{item_a}\n\n{item_b}\n"
        )

        alice = self.run_backlog_as(
            "alice", "assign", "--phase", "1", "--title", "Ordinary feature"
        )
        self.assertEqual(alice.returncode, 0, alice.stderr)
        bob = self.run_backlog_as(
            "bob", "assign", "--phase", "1", "--title", "Second feature"
        )
        self.assertEqual(bob.returncode, 0, bob.stderr)
        assigned = self.backlog.read_text()
        self.assertIn("- **Status:** in-alice-phase-1", assigned)
        self.assertIn("- **Status:** in-bob-phase-1", assigned)

        resolved = self.run_backlog_as("alice", "resolve", "--phase", "1")
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        after = self.backlog.read_text()
        self.assertEqual(after.count("- **Status:** resolved"), 1)
        self.assertNotIn("- **Status:** in-alice-phase-1", after)
        self.assertIn("- **Status:** in-bob-phase-1", after)

    def test_owned_stories_writer_uses_exact_owner_directory(self):
        result = self.run_stories_as(
            "alice", "add-row", "--phase", "2", "--story", "1",
            "--title", "Owned story", "--file", "story-1-owned.md",
            "--project", "Demo",
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        index = self.output / "alice-phase-2" / "stories" / "README.md"
        self.assertTrue(index.exists())
        self.assertIn("Phase 2 — Owner: alice", index.read_text())
        self.assertIn("| 1 | Owned story | story-1-owned.md | pending |", index.read_text())
        self.assertFalse((self.output / "phase-2").exists())

    def test_owned_review_closes_only_with_matching_owner_heading(self):
        phase = self.output / "alice-phase-1"
        stories = phase / "stories"
        stories.mkdir(parents=True)
        (phase / "phase-brief.md").write_text("# Alice phase 1\n")
        (stories / "README.md").write_text(
            "| # | Story | File | Status |\n"
            "|---|-------|------|--------|\n"
            "| 1 | Demo | story-1-demo.md | done |\n"
        )
        self.backlog.write_text("# Backlog\n\n## Items\n")
        (self.output / "reviews.md").write_text(
            "## Phase 1 Review — Owner: bob — 2026-08-04\n\nShipped.\n"
        )

        wrong_owner = self.run_state_as("alice", "--json")
        self.assertEqual(wrong_owner.returncode, 0, wrong_owner.stderr)
        self.assertFalse(json.loads(wrong_owner.stdout)["closed"])

        (self.output / "reviews.md").write_text(
            "## Phase 1 Review — Owner: alice — 2026-08-04\n\nShipped.\n"
        )
        matching = self.run_state_as("alice", "--json")
        self.assertEqual(matching.returncode, 0, matching.stderr)
        data = json.loads(matching.stdout)
        self.assertTrue(data["reviewEntry"])
        self.assertTrue(data["closed"])

    def test_run_mode_defaults_to_manual_and_is_an_explicit_local_opt_in(self):
        initialized = subprocess.run(
            ["git", "init"], cwd=self.root, text=True, capture_output=True
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)

        # A project that never opted in is manual, and says so as a default.
        shown = self.run_mode("show", str(self.root))
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("manual (default)", shown.stdout)
        self.assertIn("MODE: manual", self.run_state().stdout)

        # `mano mode auto` is the natural spelling — no `set` required.
        enabled = self.run_mode("auto", str(self.root))
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        self.assertIn("auto", enabled.stdout)
        self.assertIn("Never runs mano review", enabled.stdout)
        self.assertIn("auto (git config --local mano.mode)", self.run_mode("show", str(self.root)).stdout)

        cleared = self.run_mode("clear", str(self.root))
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertIn("manual is active", cleared.stdout)
        self.assertIn("manual (default)", self.run_mode("show", str(self.root)).stdout)

        for bad in ("turbo", "yolo", "AUTO-ish"):
            with self.subTest(bad=bad):
                invalid = self.run_mode("set", bad, str(self.root))
                self.assertNotEqual(invalid.returncode, 0)
                self.assertIn("invalid Mano mode", invalid.stderr)
        # Still manual after every rejected value — a failed set never opts in.
        self.assertIn("manual (default)", self.run_mode("show", str(self.root)).stdout)

    def test_run_mode_reaches_every_projection_a_skill_reads(self):
        (self.output / "phase-1").mkdir()
        (self.output / "phase-1" / "phase-brief.md").write_text("# Phase Brief\n")
        self.backlog.write_text(MIXED_BACKLOG)

        # Skills decide whether to chain from the projection they already run,
        # so every projection must carry the mode — not just the default one.
        for args in (
            [], ["--current"], ["--next"], ["--ui"], ["--spec"],
            ["--gaps", "rule-gap"],
        ):
            with self.subTest(args=args or ["(default)"]):
                self.assertIn("MODE: auto", self.run_state_with_mode("auto", *args).stdout)
                self.assertIn("MODE: manual", self.run_state_with_mode("manual", *args).stdout)

        for args in (
            ["--json"], ["--current", "--json"], ["--ui", "--json"],
            ["--spec", "--json"], ["--gaps", "rule-gap", "--json"],
        ):
            with self.subTest(json_args=args):
                auto = self.run_state_with_mode("auto", *args)
                manual = self.run_state_with_mode("manual", *args)
                self.assertEqual(auto.returncode, 0, auto.stderr)
                self.assertEqual(manual.returncode, 0, manual.stderr)
                self.assertEqual(json.loads(auto.stdout)["runMode"], "auto")
                self.assertEqual(json.loads(manual.stdout)["runMode"], "manual")

    def test_owner_command_is_explicit_local_opt_in_and_can_be_cleared(self):
        initialized = subprocess.run(
            ["git", "init"], cwd=self.root, text=True, capture_output=True
        )
        self.assertEqual(initialized.returncode, 0, initialized.stderr)
        (self.output / "alice-phase-1").mkdir()
        (self.output / "bob-phase-2").mkdir()
        (self.output / "phase-4").mkdir()

        set_owner = self.run_owner("set", "alice", str(self.root))
        self.assertEqual(set_owner.returncode, 0, set_owner.stderr)
        self.assertIn("owner set to alice", set_owner.stdout)
        shown = self.run_owner("show", str(self.root))
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertIn("alice (git config --local mano.owner)", shown.stdout)
        current = self.run_state("--current")
        self.assertIn("PHASE_ID: alice-phase-1", current.stdout)
        overridden = self.run_state_as("bob", "--current")
        self.assertEqual(overridden.returncode, 0, overridden.stderr)
        self.assertIn("OWNER: bob", overridden.stdout)
        self.assertIn("PHASE_ID: bob-phase-2", overridden.stdout)

        invalid = self.run_owner("set", "alice@example.com", str(self.root))
        self.assertNotEqual(invalid.returncode, 0)
        self.assertIn("invalid Mano owner", invalid.stderr)

        cleared = self.run_owner("clear", str(self.root))
        self.assertEqual(cleared.returncode, 0, cleared.stderr)
        self.assertIn("legacy phase routing is active", cleared.stdout)
        legacy = self.run_state("--current")
        self.assertIn("OWNER_MODE: legacy", legacy.stdout)
        self.assertIn("PHASE_ID: phase-4", legacy.stdout)


class GapSkillContractTests(unittest.TestCase):
    def test_spec_and_rules_use_only_narrow_projections_and_targeted_writer(self):
        spec = (REPO_ROOT / "src" / "skills" / "spec.md").read_text()
        rules = (REPO_ROOT / "src" / "skills" / "rules.md").read_text()

        self.assertIn("node _mano/scripts/state.js --spec", spec)
        self.assertIn("--- END SPEC INPUT ---", spec)
        self.assertIn("matching BEGIN/END item envelopes", spec)
        self.assertIn("output was truncated, elided, or omitted", spec)
        self.assertIn("regardless of which sentinels survived", spec)
        self.assertIn(
            "node _mano/scripts/backlog.js resolve-gap --type spec-gap", spec
        )
        self.assertIn("Do not open `_mano_output/backlog.md`", spec)

        self.assertIn("node _mano/scripts/state.js --gaps rule-gap", rules)
        self.assertIn(
            "node _mano/scripts/backlog.js resolve-gap --type rule-gap", rules
        )
        self.assertIn("Do not open `_mano_output/backlog.md`", rules)


class AutoModeContractTests(unittest.TestCase):
    def test_suggest_hook_mode_is_consistent_across_prompt_surfaces(self):
        prompt_files = [
            REPO_ROOT / "README.md",
            REPO_ROOT / "src" / "workflow.md",
            REPO_ROOT / "src" / "bootstrap" / "AGENTS.md",
        ]
        prompt_files.extend((REPO_ROOT / "src" / "skills").glob("*.md"))
        prompt_files.extend((REPO_ROOT / "src" / "hooks").glob("*.md"))

        for prompt_file in prompt_files:
            text = prompt_file.read_text()
            with self.subTest(file=prompt_file.relative_to(REPO_ROOT)):
                self.assertNotIn(
                    "Do not run a `suggest` hook automatically.", text
                )
                self.assertNotIn(
                    "When this hook is active, do not run it automatically.", text
                )
                self.assertNotIn(
                    "Do not run the hook without explicit user confirmation.", text
                )

        workflow = (REPO_ROOT / "src" / "workflow.md").read_text()
        agents = (REPO_ROOT / "src" / "bootstrap" / "AGENTS.md").read_text()
        hooks_readme = (REPO_ROOT / "src" / "hooks" / "README.md").read_text()
        for text in (workflow, agents, hooks_readme):
            self.assertIn("manual mode", text)
            self.assertIn("armed auto chain", text)

    def test_auto_pause_preserves_chain_and_yolo_can_close_it(self):
        workflow = (REPO_ROOT / "src" / "workflow.md").read_text()
        agents = (REPO_ROOT / "src" / "bootstrap" / "AGENTS.md").read_text()

        self.assertIn("- Remaining:", workflow)
        self.assertIn("approved run plan", workflow)
        self.assertIn("refresh the state projection", workflow)
        self.assertIn("Auto-chain exception", agents)
        self.assertIn("required `[mano auto]` closing block", agents)

    def test_mid_phase_backlog_assignment_is_the_only_stories_exception(self):
        stories = (REPO_ROOT / "src" / "skills" / "stories.md").read_text()

        self.assertIn("sole exception is the exact `backlog.js assign`", stories)
        self.assertIn("Do not hand-edit `_mano_output/backlog.md`", stories)
        self.assertIn("exact user-named item", stories)


if __name__ == "__main__":
    unittest.main()
