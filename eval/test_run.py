from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import assertions as A
import run
from runners import RunnerResult, Usage

MINI_BRIEF = """# Phase Brief — Mini — Phase 1

## Phase Goal

Nothing is built; this fixture exists to exercise the harness itself.

## Phase Scope

1. **Nothing** — no work.

## Exit Criteria

1. **Nothing**
   a. Nothing happened
"""


class HarnessCase:
    """A throwaway fixture + case file so a harness test needs no real case."""

    def __init__(self, stack: contextlib.ExitStack, **case: object):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        fixtures = root / "fixtures"
        (fixtures / "mini").mkdir(parents=True)
        (fixtures / "mini" / "phase-brief.md").write_text(MINI_BRIEF, encoding="utf-8")
        body = {
            "name": "mini",
            "fixture": "mini",
            "phase": 1,
            "assertions": [],
            **case,
        }
        self.path = root / "mini.json"
        self.path.write_text(json.dumps(body), encoding="utf-8")
        stack.enter_context(mock.patch.object(run, "FIXTURES_DIR", fixtures))


def recording_runner(log: list[dict], *, usage_for=None, returncode_for=None):
    """A fake CLI that records every invocation instead of spending tokens."""

    def invoke(project, prompt, timeout, env=None, *, model=None, session="fresh"):
        step = len(log) + 1
        log.append({
            "project": project, "prompt": prompt, "model": model, "session": session,
        })
        Path(project, f"step-{step}.txt").write_text(prompt, encoding="utf-8")
        code = returncode_for(step) if returncode_for else 0
        return RunnerResult(
            code,
            "",
            "",
            final_response=f"done {step}",
            usage=usage_for(step) if usage_for else None,
            resolved_model="claude-opus-5",
            runner_version="9.9.9",
        )

    return invoke


def run_mini(case_path: Path, runner, runner_name="fake", **kwargs) -> run.CaseOutcome:
    with mock.patch.dict(run.RUNNERS, {runner_name: runner}):
        with contextlib.redirect_stdout(io.StringIO()):
            return run.run_case(
                case_path,
                runner_name=runner_name,
                keep=False,
                timeout=5,
                without_rules=set(),
                **kwargs,
            )


class RunnerFailureTests(unittest.TestCase):
    def test_nonzero_runner_cannot_pass_on_unchanged_fixture(self) -> None:
        case = run.CASES_DIR / "hook-triage-no-approval.json"

        def failing(_project, _prompt, _timeout, _env=None, *, model=None, session="fresh"):
            return RunnerResult(1, "", "offline")

        with mock.patch.dict(run.RUNNERS, {"failing": failing}):
            with contextlib.redirect_stdout(io.StringIO()):
                outcome = run.run_case(
                    case,
                    runner_name="failing",
                    keep=False,
                    timeout=1,
                    without_rules=set(),
                )

        self.assertFalse(outcome.passed)


class CaseSchemaTests(unittest.TestCase):
    def test_prompt_and_steps_together_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "both 'prompt' and 'steps'"):
            run.case_steps({"name": "x", "prompt": "mano build", "steps": [{"prompt": "a"}]})

    def test_a_case_needs_one_of_them(self) -> None:
        with self.assertRaisesRegex(ValueError, "neither 'prompt' nor 'steps'"):
            run.case_steps({"name": "x"})

    def test_single_prompt_becomes_one_fresh_step(self) -> None:
        self.assertEqual(
            run.case_steps({"name": "x", "prompt": "mano build"}),
            [{"prompt": "mano build", "session": "fresh"}],
        )

    def test_session_defaults_to_fresh_and_rejects_anything_else(self) -> None:
        steps = run.case_steps({"name": "x", "steps": [{"prompt": "a"}, {"prompt": "b"}]})
        self.assertEqual([s["session"] for s in steps], ["fresh", "fresh"])
        with self.assertRaisesRegex(ValueError, "session 'resume'"):
            run.case_steps({"name": "x", "steps": [{"prompt": "a", "session": "resume"}]})

    def test_an_empty_prompt_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "empty 'prompt'"):
            run.case_steps({"name": "x", "prompt": "   "})
        with self.assertRaisesRegex(ValueError, "non-empty 'prompt'"):
            run.case_steps({"name": "x", "steps": [{"prompt": ""}]})

    def test_first_step_cannot_continue_a_session_that_does_not_exist(self) -> None:
        with self.assertRaisesRegex(ValueError, "no prior session"):
            run.case_steps({"name": "x", "steps": [{"prompt": "a", "session": "continue"}]})

    def test_every_shipped_case_parses_and_names_known_assertions(self) -> None:
        for path in sorted(run.CASES_DIR.glob("*.json")):
            case = json.loads(path.read_text(encoding="utf-8"))
            with self.subTest(case=path.stem):
                self.assertEqual(case["name"], path.stem)
                self.assertTrue(run.case_steps(case))
                unknown = [a for a in case["assertions"] if a not in A.REGISTRY]
                self.assertEqual(unknown, [], f"unknown assertion(s) in {path.name}")
                self.assertTrue((run.FIXTURES_DIR / case["fixture"]).is_dir())


class MultiStepTests(unittest.TestCase):
    def test_two_ordered_fresh_steps_share_one_project_and_are_both_visible(self) -> None:
        seen: list[A.Ctx] = []

        def probe(ctx: A.Ctx) -> list[A.Failure]:
            seen.append(ctx)
            return []

        log: list[dict] = []
        with contextlib.ExitStack() as stack:
            case = HarnessCase(
                stack,
                steps=[{"prompt": "mano build"}, {"prompt": "mano review"}],
                assertions=["probe"],
            )
            stack.enter_context(mock.patch.dict(A.REGISTRY, {"probe": probe}))
            outcome = run_mini(case.path, recording_runner(log))

        self.assertTrue(outcome.passed)
        self.assertEqual([entry["prompt"] for entry in log], ["mano build", "mano review"])
        self.assertEqual(len({entry["project"] for entry in log}), 1)

        ctx = seen[0]
        self.assertEqual([s.index for s in ctx.steps], [1, 2])
        self.assertEqual([s.final_response for s in ctx.steps], ["done 1", "done 2"])
        # The last step's message is what a single-prompt assertion would read.
        self.assertEqual(ctx.transcript, "done 2")
        self.assertIn("done 1", ctx.all_responses())
        # Per-step project state, not just the final state.
        self.assertIn("step-1.txt", ctx.step(1).source_files)
        self.assertNotIn("step-2.txt", ctx.step(1).source_files)
        self.assertIn("step-2.txt", ctx.step(2).source_files)

    def test_per_step_snapshots_attribute_a_change_to_its_step(self) -> None:
        seen: list[A.Ctx] = []

        def probe(ctx: A.Ctx) -> list[A.Failure]:
            seen.append(ctx)
            return []

        def writer(project, prompt, timeout, env=None, *, model=None, session="fresh"):
            out = Path(project, "_mano_output")
            (out / "phase-1").mkdir(parents=True, exist_ok=True)
            if prompt == "one":
                (out / "phase-1" / "progress.md").write_text(
                    "| S1 | Row | doing |\n", encoding="utf-8"
                )
            else:
                (out / "phase-1" / "progress.md").write_text(
                    "| S1 | Row | done |\n", encoding="utf-8"
                )
            return RunnerResult(0, "", "", final_response="ok")

        with contextlib.ExitStack() as stack:
            case = HarnessCase(
                stack,
                steps=[{"prompt": "one"}, {"prompt": "two"}],
                assertions=["probe"],
            )
            stack.enter_context(mock.patch.dict(A.REGISTRY, {"probe": probe}))
            run_mini(case.path, writer)

        ctx = seen[0]
        self.assertEqual(ctx.step(1).progress_rows(), [("S1", "Row", "doing")])
        self.assertEqual(ctx.step(2).progress_rows(), [("S1", "Row", "done")])
        self.assertEqual(ctx.changed_in_step(2), {"phase-1/progress.md"})
        self.assertNotIn("phase-1/progress.md", ctx.baseline)

    def test_continue_fails_loudly_on_a_runner_that_cannot_resume(self) -> None:
        log: list[dict] = []
        runner = recording_runner(log)
        with contextlib.ExitStack() as stack:
            case = HarnessCase(
                stack,
                steps=[{"prompt": "a"}, {"prompt": "b", "session": "continue"}],
            )
            outcome = run_mini(case.path, runner)

        self.assertFalse(outcome.passed)
        self.assertEqual([entry["prompt"] for entry in log], ["a"])
        self.assertEqual(len(outcome.steps), 2)
        self.assertFalse(outcome.steps[1].passed)
        self.assertIn("cannot continue a session", outcome.steps[1].error)

    def test_continue_is_passed_through_to_a_runner_that_supports_it(self) -> None:
        log: list[dict] = []
        runner = recording_runner(log)
        runner.supports_continue = True
        with contextlib.ExitStack() as stack:
            case = HarnessCase(
                stack,
                steps=[{"prompt": "a"}, {"prompt": "b", "session": "continue"}],
            )
            outcome = run_mini(case.path, runner)

        self.assertTrue(outcome.passed)
        self.assertEqual([entry["session"] for entry in log], ["fresh", "continue"])

    def test_a_failed_step_stops_the_chain_but_still_records_its_cost(self) -> None:
        log: list[dict] = []
        runner = recording_runner(
            log,
            usage_for=lambda step: Usage(input=10, output=5, cache_create=1, cache_read=100),
            returncode_for=lambda step: 1 if step == 2 else 0,
        )
        with contextlib.ExitStack() as stack:
            case = HarnessCase(
                stack,
                steps=[{"prompt": "a"}, {"prompt": "b"}, {"prompt": "c"}],
            )
            outcome = run_mini(case.path, runner)

        self.assertFalse(outcome.passed)
        self.assertEqual([entry["prompt"] for entry in log], ["a", "b"])
        self.assertEqual(len(outcome.steps), 2)
        self.assertFalse(outcome.steps[1].passed)
        self.assertEqual(outcome.total_tokens(), 232)

    def test_the_model_option_reaches_the_runner(self) -> None:
        log: list[dict] = []
        with contextlib.ExitStack() as stack:
            case = HarnessCase(stack, prompt="mano build")
            run_mini(case.path, recording_runner(log), model="opus")
        self.assertEqual(log[0]["model"], "opus")


class ManifestTests(unittest.TestCase):
    def _case_outcome(self, usages) -> run.CaseOutcome:
        case = {"fixture": "two-phase-extension", "assertions": []}
        steps = [
            A.Step(index=i, prompt=f"p{i}", session="fresh", returncode=0,
                   passed=True, usage=u, wall_ms=1000 * i)
            for i, u in enumerate(usages, 1)
        ]
        outcome = run.CaseOutcome("two-phase-extension", case, steps)
        outcome.assertions_passed = 8
        outcome.passed = True
        return outcome

    def test_record_carries_per_step_usage_and_a_real_total(self) -> None:
        outcome = self._case_outcome([
            Usage(input=172, output=47077, cache_create=168948, cache_read=11984906, messages=41),
        ])
        record = run.manifest_record(outcome, "claude", "opus", "1993155", False, set())
        self.assertEqual(record["case"], "two-phase-extension")
        self.assertEqual(record["requested_model"], "opus")
        self.assertEqual(record["steps"][0]["usage"]["cache_read"], 11984906)
        self.assertEqual(record["steps"][0]["usage"]["messages"], 41)
        self.assertEqual(record["assertions"], {"passed": 8, "failed": 0})
        self.assertEqual(record["total_tokens"], 172 + 47077 + 168948 + 11984906)
        json.dumps(record)  # a record must always be serialisable

    def test_an_unmeasured_run_reports_null_not_zero(self) -> None:
        record = run.manifest_record(self._case_outcome([None]), "codex", None, "abc", True, set())
        self.assertIsNone(record["steps"][0]["usage"])
        self.assertIsNone(record["total_tokens"])
        self.assertIsNone(record["requested_model"])

    def test_a_partly_measured_run_sums_only_what_was_measured(self) -> None:
        record = run.manifest_record(
            self._case_outcome([Usage(input=None, output=7, cache_create=None, cache_read=3)]),
            "claude", "opus", "abc", False, set(),
        )
        self.assertEqual(record["total_tokens"], 10)
        self.assertIsNone(record["steps"][0]["usage"]["input"])

    def test_manifest_is_written_as_a_json_array(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "results" / "stamp.json"
            run.write_manifest(path, [{"case": "a"}, {"case": "b"}])
            self.assertEqual(
                [r["case"] for r in json.loads(path.read_text(encoding="utf-8"))],
                ["a", "b"],
            )


class ExpectedRedTests(unittest.TestCase):
    def _write(self, tmp: str, payload: dict) -> Path:
        path = Path(tmp) / "expected-red.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_the_shipped_allowlist_loads(self) -> None:
        self.assertIsInstance(run.load_expected_red(), dict)

    def test_an_entry_needs_a_reason_and_an_owning_fix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = self._write(tmp, {"cases": {"x": {"fixed_by": "wave 2"}}})
            with self.assertRaisesRegex(ValueError, "non-empty 'reason'"):
                run.load_expected_red(path)
            path = self._write(tmp, {"cases": {"x": {"reason": "known gap"}}})
            with self.assertRaisesRegex(ValueError, "'fixed_by'"):
                run.load_expected_red(path)

    def test_an_allowlisted_failure_does_not_break_the_baseline(self) -> None:
        allowlist = {"x": {"reason": "known gap", "fixed_by": "wave 2"}}
        self.assertEqual(run.verdict("x", False, allowlist), ("RED (expected)", False))

    def test_an_allowlisted_case_that_passes_breaks_the_run(self) -> None:
        allowlist = {"x": {"reason": "known gap", "fixed_by": "wave 2"}}
        self.assertEqual(run.verdict("x", True, allowlist), ("RED-PASSED", True))

    def test_an_ordinary_case_is_unaffected(self) -> None:
        self.assertEqual(run.verdict("y", True, {}), ("PASS", False))
        self.assertEqual(run.verdict("y", False, {}), ("FAIL", True))


class MainIntegrationTests(unittest.TestCase):
    """main() end to end with a fake CLI: manifest on disk, exit code honest."""

    def _harness(self, stack: contextlib.ExitStack, cases: dict[str, dict], allowlist: dict):
        root = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        fixtures, case_dir, results = root / "fixtures", root / "cases", root / "results"
        (fixtures / "mini").mkdir(parents=True)
        (fixtures / "mini" / "phase-brief.md").write_text(MINI_BRIEF, encoding="utf-8")
        case_dir.mkdir()
        for name, body in cases.items():
            (case_dir / f"{name}.json").write_text(
                json.dumps({"name": name, "fixture": "mini", "phase": 1, **body}),
                encoding="utf-8",
            )
        red = root / "expected-red.json"
        red.write_text(json.dumps({"cases": allowlist}), encoding="utf-8")
        stack.enter_context(mock.patch.object(run, "FIXTURES_DIR", fixtures))
        stack.enter_context(mock.patch.object(run, "CASES_DIR", case_dir))
        stack.enter_context(mock.patch.object(run, "RESULTS_DIR", results))
        stack.enter_context(mock.patch.object(run, "EXPECTED_RED", red))
        return results

    def _run_main(self, argv: list[str]) -> tuple[int, str]:
        buffer = io.StringIO()
        with mock.patch("sys.argv", ["run.py", *argv]):
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
                code = run.main()
        return code, buffer.getvalue()

    def test_a_green_run_writes_one_manifest_record_per_case(self) -> None:
        log: list[dict] = []
        with contextlib.ExitStack() as stack:
            results = self._harness(
                stack,
                {
                    "one": {"prompt": "mano build", "assertions": []},
                    "two": {"steps": [{"prompt": "a"}, {"prompt": "b"}], "assertions": []},
                },
                {},
            )
            stack.enter_context(mock.patch.dict(
                run.RUNNERS,
                {"claude": recording_runner(
                    log, usage_for=lambda step: Usage(input=1, output=2, cache_read=3, messages=4)
                )},
            ))
            code, out = self._run_main(["--model", "opus"])

            self.assertEqual(code, 0)
            manifests = list(results.glob("*.json"))
            self.assertEqual(len(manifests), 1)
            records = json.loads(manifests[0].read_text(encoding="utf-8"))
            self.assertEqual([r["case"] for r in records], ["one", "two"])
            self.assertEqual(len(records[1]["steps"]), 2)
            self.assertEqual(records[0]["requested_model"], "opus")
            self.assertEqual(records[0]["resolved_model"], "claude-opus-5")
            self.assertEqual(records[0]["runner_version"], "9.9.9")
            self.assertEqual(records[1]["total_tokens"], 12)
            self.assertIn("PASS", out)

    def test_an_allowlisted_red_case_does_not_break_the_run(self) -> None:
        def failing(_p, _prompt, _t, _env=None, *, model=None, session="fresh"):
            return RunnerResult(1, "", "boom")

        with contextlib.ExitStack() as stack:
            self._harness(
                stack,
                {"red": {"prompt": "mano build", "assertions": []}},
                {"red": {"reason": "fixed in wave 2", "fixed_by": "wave 2 resume fix"}},
            )
            stack.enter_context(mock.patch.dict(run.RUNNERS, {"claude": failing}))
            code, out = self._run_main([])

        self.assertEqual(code, 0)
        self.assertIn("RED (expected)", out)

    def test_an_allowlisted_case_that_starts_passing_breaks_the_run(self) -> None:
        with contextlib.ExitStack() as stack:
            self._harness(
                stack,
                {"red": {"prompt": "mano build", "assertions": []}},
                {"red": {"reason": "fixed in wave 2", "fixed_by": "wave 2 resume fix"}},
            )
            stack.enter_context(mock.patch.dict(run.RUNNERS, {"claude": recording_runner([])}))
            code, out = self._run_main([])

        self.assertEqual(code, 1)
        self.assertIn("RED-PASSED", out)

    def test_an_allowlist_entry_for_a_case_that_does_not_exist_is_rejected(self) -> None:
        with contextlib.ExitStack() as stack:
            self._harness(
                stack,
                {"one": {"prompt": "mano build", "assertions": []}},
                {"ghost": {"reason": "typo", "fixed_by": "nothing"}},
            )
            code, _ = self._run_main([])
        self.assertEqual(code, 2)

    def test_baseline_names_a_committable_manifest_and_reruns_failures(self) -> None:
        attempts: list[str] = []

        def failing(_p, prompt, _t, _env=None, *, model=None, session="fresh"):
            attempts.append(prompt)
            return RunnerResult(1, "", "boom")

        with contextlib.ExitStack() as stack:
            results = self._harness(stack, {"one": {"prompt": "mano build", "assertions": []}}, {})
            stack.enter_context(mock.patch.dict(run.RUNNERS, {"claude": failing}))
            code, out = self._run_main(["--baseline"])

            self.assertEqual(code, 1)
            self.assertEqual(len(attempts), 2)
            manifest = next(results.glob("*.json"))
            self.assertTrue(manifest.name.startswith("baseline-"))
            records = json.loads(manifest.read_text(encoding="utf-8"))
            self.assertEqual([r["attempt"] for r in records], [1, 2])
            self.assertIn("deterministic", out)

    def test_a_seeded_ledger_is_never_reported_stale_by_copy_order(self) -> None:
        # `state.js` flags an optional artifact modified after the ledger. Copy
        # order alone decided that before, so any fixture pairing progress.md
        # with tech-spec.md carried a permanent, meaningless advisory.
        with tempfile.TemporaryDirectory() as tmp:
            fixture = Path(tmp) / "fixtures" / "paired"
            fixture.mkdir(parents=True)
            (fixture / "phase-brief.md").write_text(MINI_BRIEF, encoding="utf-8")
            (fixture / "progress.md").write_text("# Progress\n", encoding="utf-8")
            (fixture / "tech-spec.md").write_text("# Tech Spec\n", encoding="utf-8")
            project = Path(tmp) / "project"
            project.mkdir()
            with mock.patch.object(run, "FIXTURES_DIR", fixture.parent):
                run.seed_fixture(project, "paired", "seed", 1)
            out = project / "_mano_output"
            ledger = (out / "phase-1" / "progress.md").stat().st_mtime_ns
            spec = (out / "tech-spec.md").stat().st_mtime_ns
            self.assertGreaterEqual(ledger, spec)

    def test_no_manifest_leaves_the_results_directory_alone(self) -> None:
        with contextlib.ExitStack() as stack:
            results = self._harness(stack, {"one": {"prompt": "mano build", "assertions": []}}, {})
            stack.enter_context(mock.patch.dict(run.RUNNERS, {"claude": recording_runner([])}))
            code, _ = self._run_main(["--no-manifest"])
            self.assertEqual(code, 0)
            self.assertFalse(results.exists())


if __name__ == "__main__":
    unittest.main()
