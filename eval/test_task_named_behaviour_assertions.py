from pathlib import Path
import tempfile
import unittest

from assertions import Ctx, task_skipped_check_for_named_behaviour


class TaskNamedBehaviourAssertionsTests(unittest.TestCase):
    def check_reply(self, reply):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "_mano_output"
            output.mkdir()
            return task_skipped_check_for_named_behaviour(Ctx(output, transcript=reply))

    def test_accepts_only_the_open_questions(self):
        self.assertEqual(self.check_reply(
            "Outcome so far: the player changes their name, and it stays after a restart\n"
            "1. Where does the player change it: the lobby Options entry, the Esc menu, or both?\n"
            "2. Do other players see the new name in their panels?\n"
            "3. If the name is left empty, does it go back to \"Player\"?"
        ), [])

    def test_rejects_the_original_redundant_question(self):
        self.assertTrue(self.check_reply(
            "1. What will you do to check it works, and what should you see?\n"
            "2. Where does the player change it: the lobby Options entry or the Esc menu?"
        ))

    def test_rejects_the_action_half_alone(self):
        self.assertTrue(self.check_reply(
            "1. How will you verify the rename after a restart?\n"
            "2. Do other players see the new name?"
        ))

    def test_rejects_a_silent_product_decision(self):
        self.assertTrue(self.check_reply(
            "I'll add a name field to the Options screen and show it to everyone."
        ))


if __name__ == "__main__":
    unittest.main()
