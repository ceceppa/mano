from pathlib import Path
import tempfile
import unittest

from assertions import Ctx, task_reused_reproduction


class TaskReproductionAssertionsTests(unittest.TestCase):
    def check_reply(self, reply):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "_mano_output"
            output.mkdir()
            return task_reused_reproduction(Ctx(output, transcript=reply))

    def test_accepts_only_missing_decision(self):
        self.assertEqual(self.check_reply(
            'Where should the cargo land when the door closes during flight?'
        ), [])

    def test_rejects_original_redundant_question(self):
        self.assertTrue(self.check_reply(
            'How will you check it and what should you see? '
            'Where should the cargo land?'
        ))

    def test_rejects_silent_product_decision(self):
        self.assertTrue(self.check_reply(
            'I will make the cargo fall on your side of the door.'
        ))
