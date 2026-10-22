from pathlib import Path
import tempfile
import unittest

from assertions import Ctx, Step, task_done_when_quotes_request, task_skipped_stated_check

BASELINE = {"backlog.md": "# Backlog\n\n## Items\n"}

ITEM = (
    "# Backlog\n\n## Items\n\n"
    "### Safe respawn with temporary immunity\n"
    "- **Type:** feature\n"
    "- **Source:** mano task\n"
    "- **Context:**\n"
    "  On respawn the host picks a reachable point far from monsters.\n"
    "  Done when: {done}\n"
    "- **Status:** backlog\n"
)


class TaskStatedCheckAssertionsTests(unittest.TestCase):
    def step_one(self, reply, snapshot=BASELINE):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "_mano_output"
            output.mkdir()
            step = Step(index=1, prompt="mano task", final_response=reply,
                        output_snapshot=dict(snapshot))
            return task_skipped_stated_check(
                Ctx(output, baseline=dict(BASELINE), steps=[step], transcript=reply))

    def backlog(self, done):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "_mano_output"
            output.mkdir()
            (output / "backlog.md").write_text(ITEM.format(done=done))
            return task_done_when_quotes_request(Ctx(output))

    def test_accepts_only_the_open_question(self):
        self.assertEqual(self.step_one(
            "1. During the immunity, can you throw, interact or sprint, "
            "and does any of those end it at once?"
        ), [])

    def test_rejects_the_generic_check_question(self):
        self.assertTrue(self.step_one(
            "1. What will you do to check it works, and what should you see?\n"
            "2. Does any action end the immunity at once?"
        ))

    def test_rejects_the_action_half_alone(self):
        self.assertTrue(self.step_one(
            "1. How will you test the respawn in a game?\n"
            "2. Does sprinting end the immunity?"
        ))

    def test_rejects_a_silent_exploit_decision(self):
        self.assertTrue(self.step_one("I'll make any action end the immunity."))

    def test_rejects_writes_before_the_answer(self):
        written = {"backlog.md": ITEM.format(done="whatever")}
        self.assertTrue(self.step_one("Does any action end the immunity?", written))

    def test_accepts_the_goal_line_quoted(self):
        self.assertEqual(self.backlog(
            "**Goal:** Prevent spawn-killing and unavoidable death loops without making "
            "respawning an exploitable escape mechanic."
        ), [])

    def test_rejects_a_paraphrased_goal(self):
        self.assertTrue(self.backlog("The player is not killed right after respawning."))


if __name__ == "__main__":
    unittest.main()
