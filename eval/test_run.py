from __future__ import annotations

import contextlib
import io
import unittest
from unittest import mock

import run
import runners
from runners import RunnerResult


class RunnerFailureTests(unittest.TestCase):
    def test_nonzero_runner_cannot_pass_on_unchanged_fixture(self) -> None:
        case = run.CASES_DIR / "hook-triage-no-approval.json"

        with mock.patch.dict(
            run.RUNNERS,
            {"failing": lambda _project, _prompt, _timeout: RunnerResult(1, "", "offline")},
        ):
            with contextlib.redirect_stdout(io.StringIO()):
                passed = run.run_case(
                    case,
                    runner_name="failing",
                    keep=False,
                    timeout=1,
                    without_rules=set(),
                )

        self.assertFalse(passed)

    def test_opencode_runner_pins_the_temp_project(self) -> None:
        raw = "\n".join(
            [
                '{"type":"text","part":{"messageID":"m1","type":"text","text":"working"}}',
                '{"type":"step_finish","part":{"messageID":"m1"}}',
                '{"type":"text","part":{"messageID":"m2","type":"text","text":"final "}}',
                '{"type":"text","part":{"messageID":"m2","type":"text","text":"answer"}}',
            ]
        )
        with mock.patch(
            "runners._run",
            return_value=RunnerResult(0, raw, "tool trace"),
        ) as invoke:
            result = runners.run_opencode("/tmp/mano-eval-project", "mano spec", 30)

        command, cwd, timeout = invoke.call_args.args
        self.assertEqual(cwd, "/tmp/mano-eval-project")
        self.assertEqual(timeout, 30)
        self.assertEqual(
            command,
            [
                "opencode",
                "run",
                "--pure",
                "--dir",
                "/tmp/mano-eval-project",
                "--format",
                "json",
                "mano spec",
            ],
        )
        self.assertEqual(result.final_response, "final answer")


if __name__ == "__main__":
    unittest.main()
