from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import assertions
import run


def _fixture_snapshot(name: str) -> dict[str, str]:
    root = run.FIXTURES_DIR / name
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in root.rglob("*")
        if path.is_file()
    }


class UiPhasePreviewAssertionTests(unittest.TestCase):
    def _passing_phase_context(self, project: Path) -> assertions.Ctx:
        run.seed_fixture(project, "ui-phase-preview", "seed", phase=2)
        output = project / "_mano_output"

        brief = output / "design-brief.md"
        brief.write_text(
            brief.read_text(encoding="utf-8")
            + """

### Phase 2 — Insight Inbox

- **Purpose:** Present Monday launch signal for action.
- **Shared components used:** InsightCard; PrimaryButton.
""",
            encoding="utf-8",
        )
        preview = output / "phase-2" / "design-preview.html"
        preview.write_text(
            "<!doctype html><title>Phase 2 — Insight Inbox</title>"
            "<main><h1>Insight Inbox</h1><article>Monday launch signal</article></main>",
            encoding="utf-8",
        )
        return assertions.Ctx(
            output,
            phase=2,
            fixture_snapshot=_fixture_snapshot("ui-phase-preview"),
            transcript=(
                "[mano ui]: mano ui — _mano_output/design-brief.md, "
                "_mano_output/phase-2/design-preview.html"
            ),
        )

    def test_nested_fixture_seeds_prior_phase_verbatim(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-fixture-test-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "ui-phase-preview", "seed", phase=2)
            output = project / "_mano_output"

            self.assertEqual(
                (output / "phase-1" / "design-preview.html").read_text(encoding="utf-8"),
                _fixture_snapshot("ui-phase-preview")["phase-1/design-preview.html"],
            )
            self.assertTrue((output / "phase-2" / "phase-brief.md").is_file())
            self.assertTrue((output / "design-preview.html").is_file())

    def test_accepts_phase_local_preview_with_cumulative_brief(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-assertion-test-") as raw:
            ctx = self._passing_phase_context(Path(raw))
            checks = (
                assertions.ui_phase_preview_owned_by_current_phase,
                assertions.ui_cumulative_brief_extended,
                assertions.ui_prior_and_legacy_previews_unchanged,
                assertions.ui_phase_preview_output_paths,
            )
            for check in checks:
                with self.subTest(assertion=check.__name__):
                    self.assertEqual(check(ctx), [])

    def test_rejects_mutating_a_prior_phase_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-assertion-test-") as raw:
            project = Path(raw)
            ctx = self._passing_phase_context(project)
            prior = ctx.output_dir / "phase-1" / "design-preview.html"
            prior.write_text("replaced by phase 2", encoding="utf-8")

            failures = assertions.ui_prior_and_legacy_previews_unchanged(ctx)
            self.assertEqual(len(failures), 1)
            self.assertIn("phase-1/design-preview.html", failures[0].detail)

    def test_rejects_skipping_preview_when_components_are_reused(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-assertion-test-") as raw:
            project = Path(raw)
            ctx = self._passing_phase_context(project)
            (ctx.output_dir / "phase-2" / "design-preview.html").unlink()

            failures = assertions.ui_phase_preview_owned_by_current_phase(ctx)
            self.assertEqual(len(failures), 1)
            self.assertIn("current preview missing", failures[0].detail)

    def test_rejects_writing_an_unrelated_phase_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-assertion-test-") as raw:
            project = Path(raw)
            ctx = self._passing_phase_context(project)
            unrelated = ctx.output_dir / "phase-3" / "design-preview.html"
            unrelated.parent.mkdir(parents=True)
            unrelated.write_text("cross-phase write", encoding="utf-8")

            failures = assertions.ui_prior_and_legacy_previews_unchanged(ctx)
            self.assertEqual(len(failures), 1)
            self.assertIn("phase-3/design-preview.html", failures[0].detail)


class UiNoPhasePreviewAssertionTests(unittest.TestCase):
    def test_accepts_no_write_and_mano_start_route(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-no-phase-test-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "ui-no-phase-preview", "seed", phase=None)
            ctx = assertions.Ctx(
                project / "_mano_output",
                fixture_snapshot=_fixture_snapshot("ui-no-phase-preview"),
                transcript=(
                    "[mano ui]: No phase-brief.md exists, so a phase preview has no owner. "
                    "Run `mano start` first."
                ),
            )

            self.assertEqual(assertions.ui_no_phase_preview_wrote_nothing(ctx), [])
            self.assertEqual(assertions.ui_no_phase_preview_routes_to_start(ctx), [])

    def test_rejects_writing_an_unowned_preview(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-ui-no-phase-test-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "ui-no-phase-preview", "seed", phase=None)
            unowned = project / "_mano_output" / "phase-1" / "design-preview.html"
            unowned.parent.mkdir(parents=True)
            unowned.write_text("unowned", encoding="utf-8")
            ctx = assertions.Ctx(
                project / "_mano_output",
                fixture_snapshot=_fixture_snapshot("ui-no-phase-preview"),
            )

            failures = assertions.ui_no_phase_preview_wrote_nothing(ctx)
            self.assertTrue(failures)
            self.assertIn("phase-1/design-preview.html", failures[0].detail)


if __name__ == "__main__":
    unittest.main()
