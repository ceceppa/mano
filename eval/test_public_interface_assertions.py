from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import assertions
import run


def _snapshot(name: str) -> dict[str, str]:
    root = run.FIXTURES_DIR / name
    return {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in root.rglob("*")
        if path.is_file()
    }


class PublicInterfaceSpecAssertionTests(unittest.TestCase):
    def _passing_context(self, project: Path) -> assertions.Ctx:
        run.seed_fixture(project, "spec-public-interface-completeness", "seed", phase=3)
        spec = project / "_mano_output" / "tech-spec.md"
        spec.write_text(
            spec.read_text(encoding="utf-8")
            + """

## Public interface contracts

| Surface | Exact operation | Inputs and defaults | Result / failure | Canonical mapping |
|---|---|---|---|---|
| bound factory | `Motion.for(target: MotionTarget)` | null target fails with `target required` | `BoundMotion` | owns no playback state |
| opacity | `opacity(destination: number, durationSeconds?: number)` | `durationSeconds` is optional; omitted inherits | `PropertyMotion`; invalid combinations produce a validation failure before playback | `style.opacity` via `CanonicalMotion.to(target, property, destination)` |
| relative movement | `moveBy(offset: Point, durationSeconds?: number)` | omitted duration inherits; captures current position at motion start | `PropertyMotion`; unsupported targets fail before playback | relative `position` via `CanonicalMotion.to(target, property, destination)` |
| arbitrary property | `property(path: string, destination: unknown, durationSeconds?: number)` | omitted duration inherits; supplied path passes through unchanged | `PropertyMotion`; invalid paths fail before playback | supplied path via `CanonicalMotion.to(target, property, destination)` |
""",
            encoding="utf-8",
        )
        return assertions.Ctx(
            project / "_mano_output",
            phase=3,
            fixture_snapshot=_snapshot("spec-public-interface-completeness"),
        )

    def test_project_prefix_seeds_existing_source_at_project_root(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-seed-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "spec-public-interface-completeness", "seed", phase=3)
            self.assertTrue((project / "src" / "motion.d.ts").is_file())
            self.assertFalse((project / "_mano_output" / "project").exists())

    def test_accepts_complete_reconciled_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-spec-") as raw:
            ctx = self._passing_context(Path(raw))
            for check in (
                assertions.spec_public_interface_contract_complete,
                assertions.spec_existing_interface_reconciled,
                assertions.spec_preserved_unrelated_decisions,
                assertions.spec_wrote_no_stories,
            ):
                with self.subTest(check=check.__name__):
                    self.assertEqual(check(ctx), [])

    def test_accepts_types_split_into_their_interface_columns(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-columns-") as raw:
            ctx = self._passing_context(Path(raw))
            spec_path = ctx.output_dir / "tech-spec.md"
            text = spec_path.read_text(encoding="utf-8")
            replacements = {
                "| bound factory | `Motion.for(target: MotionTarget)` | null target fails with `target required` |": (
                    "| Motion | `for` | `target: MotionTarget`; null target fails with `target required` |"
                ),
                "`opacity(destination: number, durationSeconds?: number)` | `durationSeconds` is optional; omitted inherits": (
                    "`opacity` | `destination: number`; `durationSeconds?: number`; omitted inherits"
                ),
                "`moveBy(offset: Point, durationSeconds?: number)` | omitted duration inherits; captures": (
                    "`moveBy` | `offset: Point`; `durationSeconds?: number`; omitted duration inherits; captures"
                ),
                "`property(path: string, destination: unknown, durationSeconds?: number)` | omitted duration inherits; supplied": (
                    "`property` | `path: string`; `destination: unknown`; `durationSeconds?: number`; omitted duration inherits; supplied"
                ),
            }
            for before, after in replacements.items():
                self.assertIn(before, text)
                text = text.replace(before, after)
            spec_path.write_text(text, encoding="utf-8")

            self.assertEqual(assertions.spec_public_interface_contract_complete(ctx), [])

    def test_rejects_capability_phrases_as_exact_operation_names(self) -> None:
        mutations = {
            "factory for target binding": "Motion.for(target: MotionTarget)",
            "opacity convenience family": "opacity(destination: number, durationSeconds?: number)",
        }
        for phrase, exact_operation in mutations.items():
            with self.subTest(phrase=phrase), tempfile.TemporaryDirectory(
                prefix="mano-interface-operation-name-"
            ) as raw:
                ctx = self._passing_context(Path(raw))
                spec_path = ctx.output_dir / "tech-spec.md"
                text = spec_path.read_text(encoding="utf-8")
                self.assertIn(exact_operation, text)
                spec_path.write_text(
                    text.replace(exact_operation, phrase),
                    encoding="utf-8",
                )

                self.assertTrue(assertions.spec_public_interface_contract_complete(ctx))

    def test_rejects_inline_types_that_conflict_with_neighbor_cells(self) -> None:
        conflicting_operations = (
            "opacity(destination: string, durationSeconds?: number) -> WrongMotion",
            "opacity(destination: number & Branded, durationSeconds?: number) -> PropertyMotion",
            "opacity(destination: number, durationSeconds?: number) -> Promise<PropertyMotion>",
            "opacity(destination: number, durationSeconds?: number) -> PropertyMotion | WrongMotion",
        )
        for operation in conflicting_operations:
            with self.subTest(operation=operation), tempfile.TemporaryDirectory(
                prefix="mano-interface-conflicting-cells-"
            ) as raw:
                ctx = self._passing_context(Path(raw))
                spec_path = ctx.output_dir / "tech-spec.md"
                text = spec_path.read_text(encoding="utf-8")
                before = (
                    "`opacity(destination: number, durationSeconds?: number)` | "
                    "`durationSeconds` is optional; omitted inherits"
                )
                after = (
                    f"`{operation}` | `destination: number`; "
                    "`durationSeconds?: number`; omitted inherits"
                )
                self.assertIn(before, text)
                spec_path.write_text(text.replace(before, after), encoding="utf-8")

                failures = assertions.spec_public_interface_contract_complete(ctx)
                self.assertTrue(failures)
                self.assertIn("opacity(destination: number", failures[0].detail)

    def test_rejects_neighbor_cells_that_conflict_with_exact_signature(self) -> None:
        transformations = (
            (
                "`durationSeconds` is optional; omitted inherits",
                "`destination: string`; `durationSeconds?: number`; omitted inherits",
            ),
            (
                "`opacity(destination: number, durationSeconds?: number)` | "
                "`durationSeconds` is optional; omitted inherits | "
                "`PropertyMotion`; invalid combinations",
                "`opacity(destination: number, durationSeconds?: number) -> PropertyMotion` | "
                "`durationSeconds` is optional; omitted inherits | "
                "`Promise<PropertyMotion>`; invalid combinations",
            ),
        )
        for before, after in transformations:
            with self.subTest(after=after), tempfile.TemporaryDirectory(
                prefix="mano-interface-reverse-conflict-"
            ) as raw:
                ctx = self._passing_context(Path(raw))
                spec_path = ctx.output_dir / "tech-spec.md"
                text = spec_path.read_text(encoding="utf-8")
                self.assertIn(before, text)
                spec_path.write_text(text.replace(before, after, 1), encoding="utf-8")

                failures = assertions.spec_public_interface_contract_complete(ctx)
                self.assertTrue(failures)
                self.assertIn("opacity(destination: number", failures[0].detail)

    def test_rejects_mapping_borrowed_from_a_neighbor_row(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-decoy-map-") as raw:
            ctx = self._passing_context(Path(raw))
            spec_path = ctx.output_dir / "tech-spec.md"
            text = spec_path.read_text(encoding="utf-8")
            text = text.replace("`style.opacity` via", "`style.visibility` via")
            text = text.replace(
                "relative `position` via",
                "unrelated `style.opacity`; relative `position` via",
            )
            spec_path.write_text(text, encoding="utf-8")

            failures = assertions.spec_public_interface_contract_complete(ctx)
            self.assertTrue(failures)
            self.assertIn("opacity canonical mapping", failures[0].detail)

    def test_rejects_timing_borrowed_from_a_neighbor_row(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-decoy-time-") as raw:
            ctx = self._passing_context(Path(raw))
            spec_path = ctx.output_dir / "tech-spec.md"
            text = spec_path.read_text(encoding="utf-8")
            text = text.replace(
                "captures current position at motion start",
                "captures current position at call time",
            )
            text = text.replace(
                "omitted inherits | `PropertyMotion`; invalid combinations",
                "omitted inherits; unrelated capture occurs at motion start | `PropertyMotion`; invalid combinations",
            )
            spec_path.write_text(text, encoding="utf-8")

            failures = assertions.spec_public_interface_contract_complete(ctx)
            self.assertTrue(failures)
            self.assertIn("moveBy captures position at motion start", failures[0].detail)

    def test_rejects_capability_families_without_exact_contract(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-spec-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "spec-public-interface-completeness", "seed", phase=3)
            ctx = assertions.Ctx(project / "_mano_output", phase=3)
            self.assertTrue(assertions.spec_public_interface_contract_complete(ctx))
            self.assertTrue(assertions.spec_existing_interface_reconciled(ctx))

    def test_rejects_each_behavior_driving_contract_mutation(self) -> None:
        mutations = {
            "factory target type": ("target: MotionTarget", "target: unknown"),
            "factory result": ("`BoundMotion`", "`unknown`"),
            "opacity destination type": (
                "opacity(destination: number, durationSeconds?: number)",
                "opacity(destination: string, durationSeconds?: number)",
            ),
            "opacity optional duration": (
                "opacity(destination: number, durationSeconds?: number)",
                "opacity(destination: number, durationSeconds: number)",
            ),
            "duration inheritance": ("omitted inherits", "omitted uses zero"),
            "moveBy offset type": (
                "moveBy(offset: Point, durationSeconds?: number)",
                "moveBy(offset: number, durationSeconds?: number)",
            ),
            "property parameter order": (
                "property(path: string, destination: unknown, durationSeconds?: number)",
                "property(destination: unknown, path: string, durationSeconds?: number)",
            ),
            "property result": ("`PropertyMotion`", "`MotionResult`"),
            "opacity mapping": ("`style.opacity`", "`style.visibility`"),
            "moveBy mapping": (
                "relative `position` via",
                "relative `rotation` via",
            ),
            "moveBy timing": ("at motion start", "at authoring time"),
            "path passthrough": (
                "supplied path passes through unchanged",
                "supplied path may be rewritten",
            ),
            "canonical delegation argument order": (
                "CanonicalMotion.to(target, property, destination)",
                "CanonicalMotion.to(property, target, destination)",
            ),
            "null-target failure": (
                "null target fails with `target required`",
                "null target is accepted",
            ),
            "pre-playback validation": (
                "before playback",
                "after playback",
            ),
        }

        for label, (before, after) in mutations.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory(
                prefix="mano-interface-mutation-"
            ) as raw:
                ctx = self._passing_context(Path(raw))
                spec_path = ctx.output_dir / "tech-spec.md"
                text = spec_path.read_text(encoding="utf-8")
                self.assertIn(before, text)
                spec_path.write_text(text.replace(before, after), encoding="utf-8")

                self.assertTrue(
                    assertions.spec_public_interface_contract_complete(ctx),
                    f"mutation {label!r} was not rejected",
                )

    def test_rejects_a_timing_contradiction_even_when_the_right_value_remains(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-contradiction-") as raw:
            ctx = self._passing_context(Path(raw))
            spec_path = ctx.output_dir / "tech-spec.md"
            spec_path.write_text(
                spec_path.read_text(encoding="utf-8")
                + "\n- `moveBy` captures the target position at call time.\n",
                encoding="utf-8",
            )

            failures = assertions.spec_public_interface_contract_complete(ctx)
            self.assertTrue(failures)
            self.assertIn("call/build time", failures[0].detail)

    def test_accepts_offset_call_time_with_position_motion_start(self) -> None:
        valid_statements = (
            "`moveBy` resolves the supplied offset at call time and captures the current target position at motion start.",
            "`moveBy` does not capture the position at call time; it captures the current target position at motion start.",
        )
        for statement in valid_statements:
            with self.subTest(statement=statement), tempfile.TemporaryDirectory(
                prefix="mano-interface-valid-timing-"
            ) as raw:
                ctx = self._passing_context(Path(raw))
                spec_path = ctx.output_dir / "tech-spec.md"
                spec_path.write_text(
                    spec_path.read_text(encoding="utf-8") + f"\n- {statement}\n",
                    encoding="utf-8",
                )

                self.assertEqual(assertions.spec_public_interface_contract_complete(ctx), [])


class PublicInterfaceStoryGapAssertionTests(unittest.TestCase):
    def test_accepts_no_write_and_spec_route(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-stories-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "stories-public-interface-gap", "seed", phase=4)
            ctx = assertions.Ctx(
                project / "_mano_output",
                phase=4,
                fixture_snapshot=_snapshot("stories-public-interface-gap"),
                transcript=(
                    "[mano stories]: Story readiness gap: Relay.listen lacks exact event "
                    "names, argument and payload shapes, return/failure behavior, and "
                    "canonical mappings. Run mano spec before generating stories."
                ),
            )
            self.assertEqual(assertions.stories_public_interface_gap_wrote_nothing(ctx), [])
            self.assertEqual(assertions.stories_public_interface_gap_routes_to_spec(ctx), [])

    def test_rejects_story_files_written_through_the_gap(self) -> None:
        with tempfile.TemporaryDirectory(prefix="mano-interface-stories-") as raw:
            project = Path(raw)
            run.seed_fixture(project, "stories-public-interface-gap", "seed", phase=4)
            stories = project / "_mano_output" / "phase-4" / "stories"
            stories.mkdir(parents=True)
            (stories / "story-1-relay-listen.md").write_text("underspecified", encoding="utf-8")
            ctx = assertions.Ctx(
                project / "_mano_output",
                phase=4,
                fixture_snapshot=_snapshot("stories-public-interface-gap"),
            )
            self.assertTrue(assertions.stories_public_interface_gap_wrote_nothing(ctx))


if __name__ == "__main__":
    unittest.main()
