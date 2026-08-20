"""Trap matrix for the two-phase extension assertions.

The eval case itself costs real model spend, so these tests build the project
state a *correct* Phase 2 would leave behind, prove all eight assertions pass on
it, then reintroduce one defect at a time and prove the matching assertion is
the one that fires. An assertion that cannot fail is not coverage.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

import assertions as A
import run

GROUP_ENTRIES = '''"use strict";

const ORDER = ["open", "blocked", "done"];

/** Group entries under their status, in the fixed digest order. */
function groupEntries(entries) {
  return ORDER
    .map((status) => ({ status, entries: entries.filter((e) => e.status === status) }))
    .filter((group) => group.entries.length > 0);
}

module.exports = { groupEntries };
'''

RENDER_DIGEST = '''"use strict";

const { formatEntry } = require("./format-entry.js");
const { groupEntries } = require("./group-entries.js");

const HEADINGS = { open: "## Open", blocked: "## Blocked", done: "## Done" };

/** Render the whole digest, one heading per non-empty status group. */
function renderDigest(entries) {
  return groupEntries(entries)
    .map((group) => [
      HEADINGS[group.status],
      ...group.entries.map((entry) => `- ${formatEntry(entry)}`),
    ].join("\\n"))
    .join("\\n\\n");
}

module.exports = { renderDigest };
'''

EXTENDED_INDEX = '''"use strict";

// sentinel: phase-1-public-surface-must-survive

const { formatEntry } = require("./format-entry.js");
const { groupEntries } = require("./group-entries.js");
const { renderDigest } = require("./render-digest.js");

module.exports = { formatEntry, groupEntries, renderDigest };
'''

PHASE_2_LEDGER = """# Progress — Signal Digest — Phase 2

## Scope
| # | What | Status |
|---|------|--------|
| S1 | Status grouping | done |
| S2 | Digest rendering | done |
| S3 | Public surface | done |

## Exit Criteria
| # | Criterion | Status |
|---|-----------|--------|
| E1a | Status grouping — `groupEntries` returns groups ordered open, blocked, done, and omits a status that has no entries | met |
| E1b | Status grouping — `groupEntries` returns an empty array for an empty entry list | met |
| E2a | Digest rendering — `renderDigest` writes each group's heading line and then one `- ` line per entry, using the Phase 1 entry format unchanged | met |
| E3a | Public surface — Requiring `src/digest/index.js` exposes `formatEntry`, `groupEntries`, and `renderDigest` | met |
"""

ALL_ASSERTIONS = [
    "two_phase_one_behaviour_survives",
    "two_phase_extension_behaviour_works",
    "two_phase_source_untouched_regions_preserved",
    "two_phase_artifacts_extended_not_reemitted",
    "two_phase_no_duplicated_or_reordered_sections",
    "two_phase_identity_and_ledger_held",
    "two_phase_did_not_read_other_phase_brief",
    "two_phase_each_step_wrote_only_its_own_artifact",
]


class Phase2Run:
    """A synthetic run of the five-step chain over the real fixture."""

    def __init__(self, project: Path):
        self.project = project
        self.out = project / "_mano_output"
        run.seed_fixture(project, "two-phase-extension", "seed", 2)
        self.baseline = run.snapshot_output(project)
        self.steps: list[A.Step] = []

    def append_output(self, relative: str, text: str) -> None:
        path = self.out / relative
        path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")

    def write_output(self, relative: str, text: str) -> None:
        path = self.out / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def write_source(self, relative: str, text: str) -> None:
        path = self.project / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def step(self, prompt: str) -> None:
        self.steps.append(A.Step(
            index=len(self.steps) + 1,
            prompt=prompt,
            session="fresh",
            returncode=0,
            passed=True,
            final_response=f"[{prompt}]: done.",
            output_snapshot=run.snapshot_output(self.project),
            source_files=run.snapshot_sources(self.project),
            phase=2,
        ))

    def ctx(self) -> A.Ctx:
        fixture_dir = run.FIXTURES_DIR / "two-phase-extension"
        snapshot = {
            p.relative_to(fixture_dir).as_posix(): p.read_text(encoding="utf-8")
            for p in fixture_dir.rglob("*")
            if p.is_file()
        }
        return A.Ctx(
            self.out,
            2,
            snapshot,
            self.steps[-1].final_response if self.steps else "",
            steps=self.steps,
            baseline=self.baseline,
        )


def good_run(project: Path) -> Phase2Run:
    """What a correct Phase 2 leaves behind, step by step."""
    r = Phase2Run(project)

    r.append_output("tech-spec.md", """
## Grouping and Rendering

- `groupEntries(entries) -> Array<{ status, entries }>` in `src/digest/group-entries.js` returns groups in the order `open`, `blocked`, `done`, omits a status with no entries, and preserves the caller's order inside a group.
- `renderDigest(entries) -> string` in `src/digest/render-digest.js` writes each group's heading line, then one `- ` line per entry, delegating every entry line to `formatEntry`.
""")
    r.step("mano spec")

    r.append_output("project-rules.md", """
## Rendered Headings

**What:** A heading a renderer emits is Title Case after the `## ` marker, matching the status name it stands for.

**Why:** Two renderers would otherwise disagree the first time there is a second one.
""")
    r.write_output(
        "backlog.md",
        (r.out / "backlog.md").read_text(encoding="utf-8").replace(
            "  Nothing states how a heading emitted by a renderer is capitalised, so two renderers could disagree the first time there is a second one. Decide the project-wide convention.\n- **Status:** backlog",
            "  Nothing states how a heading emitted by a renderer is capitalised, so two renderers could disagree the first time there is a second one. Decide the project-wide convention.\n- **Status:** resolved",
        ),
    )
    r.step("mano rules")

    r.append_output("ux-flow.md", """
## Phase 2 — Scan by status

1. The reviewer opens the digest view.
2. Entries appear under a heading for their status, in the order open, then blocked, then done.
3. A status with nothing in it is not shown at all.
""")
    r.step("mano ux")

    r.append_output("design-brief.md", """
### Phase 2 — Grouped Digest

- **Purpose:** Scan the digest by status.
- **Sections (top to bottom):** Header; one status group per non-empty status.
- **Shared components used:** EntryLine; StatusHeading.
- **Layout / hierarchy notes:** One column; the heading carries the grouping, the entry line is unchanged.
""")
    r.write_output("phase-2/design-preview.html", "<!doctype html><title>Digest</title>\n")
    r.step("mano ui")

    r.write_source("src/digest/group-entries.js", GROUP_ENTRIES)
    r.write_source("src/digest/render-digest.js", RENDER_DIGEST)
    r.write_source("src/digest/index.js", EXTENDED_INDEX)
    r.write_output("phase-2/progress.md", PHASE_2_LEDGER)
    r.step("mano build")
    return r


def failures_for(ctx: A.Ctx, name: str) -> list[A.Failure]:
    return A.REGISTRY[name](ctx)


class TwoPhaseAssertionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="mano-two-phase-"))
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.run = good_run(self.tmp)

    def assert_caught_by(self, name: str) -> None:
        """The named assertion must fire on the defect just introduced.

        Another assertion noticing too is fine — several of them read the same
        files. What is not fine is the owning assertion staying silent.
        """
        failures = failures_for(self.run.ctx(), name)
        self.assertTrue(failures, f"{name} did not catch its own defect")

    def test_a_correct_phase_two_passes_every_assertion(self) -> None:
        ctx = self.run.ctx()
        for name in ALL_ASSERTIONS:
            with self.subTest(assertion=name):
                self.assertEqual(failures_for(ctx, name), [])

    def test_the_case_file_names_exactly_these_assertions(self) -> None:
        case = json.loads((run.CASES_DIR / "two-phase-extension.json").read_text(encoding="utf-8"))
        self.assertEqual(case["assertions"], ALL_ASSERTIONS)
        self.assertEqual(len(case["steps"]), 5)

    def test_a_broken_phase_one_behaviour_is_caught(self) -> None:
        self.run.write_source(
            "src/digest/format-entry.js",
            '"use strict";\nfunction formatEntry(e) { return e.title; }\nmodule.exports = { formatEntry };\n',
        )
        self.assert_caught_by("two_phase_one_behaviour_survives")

    def test_a_rewritten_phase_one_file_is_caught(self) -> None:
        path = self.tmp / "src" / "digest" / "format-entry.js"
        path.write_text(path.read_text(encoding="utf-8") + "\n// tidied up\n", encoding="utf-8")
        self.assert_caught_by("two_phase_source_untouched_regions_preserved")

    def test_a_dropped_phase_one_line_in_index_is_caught(self) -> None:
        self.run.write_source(
            "src/digest/index.js",
            EXTENDED_INDEX.replace("// sentinel: phase-1-public-surface-must-survive\n\n", ""),
        )
        self.assert_caught_by("two_phase_source_untouched_regions_preserved")

    def test_wrong_group_order_is_caught(self) -> None:
        self.run.write_source(
            "src/digest/group-entries.js",
            GROUP_ENTRIES.replace('["open", "blocked", "done"]', '["done", "blocked", "open"]'),
        )
        self.assert_caught_by("two_phase_extension_behaviour_works")

    def test_an_empty_status_group_that_is_kept_is_caught(self) -> None:
        self.run.write_source(
            "src/digest/group-entries.js",
            GROUP_ENTRIES.replace("    .filter((group) => group.entries.length > 0);", "    ;"),
        )
        self.assert_caught_by("two_phase_extension_behaviour_works")

    def test_a_render_that_stops_using_the_phase_one_line_is_caught(self) -> None:
        self.run.write_source(
            "src/digest/render-digest.js",
            RENDER_DIGEST.replace("`- ${formatEntry(entry)}`", "`- ${entry.title}`"),
        )
        self.assert_caught_by("two_phase_extension_behaviour_works")

    def test_a_re_emitted_artifact_that_loses_a_phase_one_line_is_caught(self) -> None:
        self.run.write_output(
            "tech-spec.md",
            "# Tech Spec — Signal Digest\n\n## Grouping and Rendering\n\nOnly the new thing.\n",
        )
        self.assert_caught_by("two_phase_artifacts_extended_not_reemitted")

    def test_an_artifact_that_was_never_extended_is_caught(self) -> None:
        fixture = run.FIXTURES_DIR / "two-phase-extension" / "ux-flow.md"
        self.run.write_output("ux-flow.md", fixture.read_text(encoding="utf-8"))
        self.assert_caught_by("two_phase_artifacts_extended_not_reemitted")

    def test_a_duplicated_section_is_caught(self) -> None:
        self.run.append_output("design-brief.md", "\n### EntryLine\n\n- Duplicated by a re-emit.\n")
        self.assert_caught_by("two_phase_no_duplicated_or_reordered_sections")

    def test_a_reordered_artifact_is_caught(self) -> None:
        text = (self.run.out / "ux-flow.md").read_text(encoding="utf-8")
        moved = text.replace("<!-- sentinel: ux-phase-1-must-survive -->\n\n", "")
        self.run.write_output("ux-flow.md", moved + "\n<!-- sentinel: ux-phase-1-must-survive -->\n")
        self.assert_caught_by("two_phase_no_duplicated_or_reordered_sections")

    def test_an_open_ledger_row_is_caught(self) -> None:
        self.run.write_output(
            "phase-2/progress.md", PHASE_2_LEDGER.replace("| S3 | Public surface | done |", "| S3 | Public surface | pending |")
        )
        self.assert_caught_by("two_phase_identity_and_ledger_held")

    def test_an_edited_closed_phase_is_caught(self) -> None:
        self.run.append_output("phase-1/progress.md", "\n| S3 | Snuck in | done |\n")
        self.assert_caught_by("two_phase_identity_and_ledger_held")

    def test_an_edited_phase_brief_is_caught(self) -> None:
        self.run.append_output("phase-2/phase-brief.md", "\n- Built, by the way.\n")
        self.assert_caught_by("two_phase_identity_and_ledger_held")

    def test_a_ledger_written_into_the_wrong_phase_is_caught(self) -> None:
        (self.run.out / "phase-2" / "progress.md").unlink()
        self.assert_caught_by("two_phase_identity_and_ledger_held")

    def test_the_cross_phase_canary_in_a_response_is_caught(self) -> None:
        self.run.steps[-1].final_response = "…as the kestrel-spike-parked note explains."
        self.assert_caught_by("two_phase_did_not_read_other_phase_brief")

    def test_the_cross_phase_canary_in_an_artifact_is_caught(self) -> None:
        self.run.append_output("ux-flow.md", "\nSee kestrel-spike-parked for the earlier layout.\n")
        self.assert_caught_by("two_phase_did_not_read_other_phase_brief")

    def test_a_step_writing_another_skills_artifact_is_caught(self) -> None:
        # Rebuild the chain with `mano ux` also touching the design brief.
        tmp = Path(tempfile.mkdtemp(prefix="mano-two-phase-trespass-"))
        self.addCleanup(shutil.rmtree, tmp, True)
        r = Phase2Run(tmp)
        r.append_output("tech-spec.md", "\n## Grouping and Rendering\n\nNew.\n")
        r.step("mano spec")
        r.append_output("project-rules.md", "\n## Rendered Headings\n\n**What:** Title Case.\n")
        r.step("mano rules")
        r.append_output("ux-flow.md", "\n## Phase 2 — Scan by status\n\n1. Grouped.\n")
        r.append_output("design-brief.md", "\n### Phase 2 — Grouped Digest\n\n- Not ux's file.\n")
        r.step("mano ux")
        failures = failures_for(r.ctx(), "two_phase_each_step_wrote_only_its_own_artifact")
        self.assertTrue(any("design-brief.md" in f.detail for f in failures))

    def test_a_missing_step_is_caught(self) -> None:
        self.run.steps = self.run.steps[:3]
        failures = failures_for(self.run.ctx(), "two_phase_each_step_wrote_only_its_own_artifact")
        self.assertTrue(any("never ran" in f.detail for f in failures))


if __name__ == "__main__":
    unittest.main()
