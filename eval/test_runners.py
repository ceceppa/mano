from __future__ import annotations

import json
import unittest
from unittest import mock

import runners
from runners import RunnerResult, Usage

CLAUDE_ENVELOPE = {
    "type": "result",
    "subtype": "success",
    "is_error": False,
    "num_turns": 41,
    "result": "[mano build]: phase built.",
    "session_id": "abc-123",
    "usage": {
        "input_tokens": 172,
        "output_tokens": 47077,
        "cache_creation_input_tokens": 168948,
        "cache_read_input_tokens": 11984906,
    },
    "modelUsage": {"claude-opus-5": {"inputTokens": 172}},
}


def fake_run(stdout: str, returncode: int = 0):
    return mock.patch.object(
        runners, "_run", return_value=RunnerResult(returncode, stdout, "")
    )


class UsageTests(unittest.TestCase):
    def test_an_unmeasured_usage_has_no_total(self) -> None:
        self.assertIsNone(Usage().total_tokens())

    def test_a_partly_measured_usage_sums_only_what_exists(self) -> None:
        self.assertEqual(Usage(input=3, cache_read=4).total_tokens(), 7)

    def test_the_record_keeps_nulls_rather_than_dropping_fields(self) -> None:
        record = Usage(input=1).as_record()
        self.assertEqual(
            sorted(record), ["cache_create", "cache_read", "input", "messages", "output"]
        )
        self.assertIsNone(record["cache_read"])
        json.dumps(record)


class ClaudeRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(runners, "cli_version", return_value="2.0.0 (Claude Code)")
        self.addCleanup(patcher.stop)
        patcher.start()

    def test_the_json_envelope_yields_usage_model_and_final_message(self) -> None:
        with fake_run(json.dumps(CLAUDE_ENVELOPE)):
            result = runners.run_claude("/tmp/p", "mano build", 60)

        self.assertEqual(result.final_response, "[mano build]: phase built.")
        self.assertEqual(result.usage.input, 172)
        self.assertEqual(result.usage.output, 47077)
        self.assertEqual(result.usage.cache_create, 168948)
        self.assertEqual(result.usage.cache_read, 11984906)
        self.assertEqual(result.usage.messages, 41)
        self.assertEqual(result.usage.total_tokens(), 12201103)
        self.assertEqual(result.resolved_model, "claude-opus-5")
        self.assertEqual(result.runner_version, "2.0.0 (Claude Code)")

    def test_the_resolved_model_wins_over_the_requested_alias(self) -> None:
        with fake_run(json.dumps(CLAUDE_ENVELOPE)) as invoke:
            result = runners.run_claude("/tmp/p", "mano build", 60, model="opus")
        command = invoke.call_args.args[0]
        self.assertIn("--model", command)
        self.assertEqual(command[command.index("--model") + 1], "opus")
        self.assertEqual(result.resolved_model, "claude-opus-5")

    def test_a_stream_json_transcript_is_parsed_too(self) -> None:
        lines = "\n".join([
            json.dumps({"type": "system", "subtype": "init"}),
            json.dumps({"type": "assistant", "message": {"role": "assistant"}}),
            json.dumps(CLAUDE_ENVELOPE),
        ])
        with fake_run(lines):
            result = runners.run_claude("/tmp/p", "mano build", 60)
        self.assertEqual(result.usage.cache_read, 11984906)
        self.assertEqual(result.final_response, "[mano build]: phase built.")

    def test_an_envelope_without_usage_reports_none_not_zero(self) -> None:
        envelope = {"type": "result", "result": "done"}
        with fake_run(json.dumps(envelope)):
            result = runners.run_claude("/tmp/p", "mano build", 60)
        self.assertIsNone(result.usage)
        self.assertIsNone(result.resolved_model)
        self.assertEqual(result.final_response, "done")

    def test_unparseable_output_keeps_the_text_and_drops_the_metrics(self) -> None:
        with fake_run("something went very wrong"):
            result = runners.run_claude("/tmp/p", "mano build", 60)
        self.assertEqual(result.final_response, "something went very wrong")
        self.assertIsNone(result.usage)
        self.assertIsNone(result.resolved_model)

    def test_a_continue_step_resumes_the_project_session(self) -> None:
        with fake_run(json.dumps(CLAUDE_ENVELOPE)) as invoke:
            runners.run_claude("/tmp/p", "mano review", 60, session="continue")
        self.assertIn("--continue", invoke.call_args.args[0])

    def test_a_fresh_step_does_not_resume_anything(self) -> None:
        with fake_run(json.dumps(CLAUDE_ENVELOPE)) as invoke:
            runners.run_claude("/tmp/p", "mano build", 60)
        command = invoke.call_args.args[0]
        self.assertNotIn("--continue", command)
        self.assertEqual(command[-1], "mano build")
        self.assertEqual(command[command.index("--output-format") + 1], "json")


class OtherRunnerTests(unittest.TestCase):
    def test_codex_reports_no_metrics_rather_than_zeroes(self) -> None:
        with mock.patch.object(runners, "cli_version", return_value="codex 1.0"):
            with fake_run("") as invoke:
                result = runners.run_codex("/tmp/p", "mano spec", 60, model="gpt-5")
        self.assertIsNone(result.usage)
        self.assertIsNone(result.resolved_model)
        self.assertEqual(result.runner_version, "codex 1.0")
        command = invoke.call_args.args[0]
        self.assertEqual(command[command.index("--model") + 1], "gpt-5")

    def test_opencode_runner_pins_the_temp_project(self) -> None:
        raw = "\n".join(
            [
                '{"type":"text","part":{"messageID":"m1","type":"text","text":"working"}}',
                '{"type":"step_finish","part":{"messageID":"m1"}}',
                '{"type":"text","part":{"messageID":"m2","type":"text","text":"final "}}',
                '{"type":"text","part":{"messageID":"m2","type":"text","text":"answer"}}',
            ]
        )
        with mock.patch.object(runners, "cli_version", return_value=None):
            with fake_run(raw) as invoke:
                result = runners.run_opencode("/tmp/mano-eval-project", "mano spec", 30)

        command, cwd, timeout, _env = invoke.call_args.args
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
        self.assertIsNone(result.usage)


class ContinuationSupportTests(unittest.TestCase):
    def test_only_a_runner_that_says_so_can_continue(self) -> None:
        self.assertTrue(runners.supports_continue(runners.run_claude))
        self.assertFalse(runners.supports_continue(runners.run_codex))
        self.assertFalse(runners.supports_continue(runners.run_opencode))

    def test_an_unknown_runner_defaults_to_no(self) -> None:
        self.assertFalse(runners.supports_continue(lambda *a, **k: None))


if __name__ == "__main__":
    unittest.main()
