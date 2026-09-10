"""Exercise the import eval checks against valid output and destructive mutations."""
import tempfile
import unittest
from pathlib import Path

import assertions as A


class ImportReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.output = Path(self.tmp.name)
        self.original = (Path(__file__).parent / 'fixtures/import-existing-conflict/backlog.md').read_text()

    def check(self, text, assertion, response=''):
        (self.output / 'backlog.md').write_text(text)
        return assertion(A.Ctx(self.output, fixture_snapshot={'backlog.md': self.original}, transcript=response))

    def approved(self):
        return self.original.replace(
            'Save and restore named panel dock layouts.',
            'Save and restore named panel dock layouts. Superseded by the timeline in product-brief.md.'
        ).replace('**Status:** backlog', '**Status:** rejected', 1) + (
            '\n### Timeline canvas\n- **Type:** feature\n- **Source:** product-brief.md\n'
            '- **Context:**\n  Add, reorder, and play clips on a timeline.\n- **Status:** backlog\n'
        )

    def test_authorized_reconciliation_passes(self):
        self.assertEqual(self.check(self.approved(), A.import_applied_authorized_rejection), [])

    def test_refusal_and_destructive_changes_fail(self):
        approved = self.approved()
        for text in (
            self.original,
            approved.replace('**Status:** in-phase-2', '**Status:** rejected'),
            approved.replace('**Status:** resolved', '**Status:** rejected'),
            approved.replace('**Status:** rejected', '**Status:** resolved', 1),
            approved.replace('product-brief.md', 'unknown.md'),
            approved.replace('### Export composition as video', '### Unrelated renamed work'),
            approved + approved,
        ):
            with self.subTest(text=text):
                self.assertTrue(self.check(text, A.import_applied_authorized_rejection))

    def test_pending_decision_preserves_items(self):
        response = 'Panel dock presets conflicts with the timeline. Which direction should stand?'
        self.assertEqual(self.check(self.original, A.import_waited_on_conflict, response), [])
        self.assertTrue(self.check(self.approved(), A.import_waited_on_conflict, response))
        self.assertTrue(self.check(self.original, A.import_waited_on_conflict, 'Done.'))
