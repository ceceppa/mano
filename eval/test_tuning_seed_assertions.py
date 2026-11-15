from pathlib import Path
import tempfile
import unittest

from assertions import Ctx, spec_tuning_seed_authority


VALID = """capture_duration in seconds is tuning, owned by GameTuning.capture_duration.
Per-instance overrides take precedence. The initial seed is 6 seconds,
non-normative; the current value lives in configuration with no spec sync.
Countdown starts after the field ends.
Release occurs when the configured duration expires.
Behaviour checks use explicit fixtures; configuration wiring is checked separately.
"""


class TuningSeedAssertionsTests(unittest.TestCase):
    def check_text(self, text):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'tech-spec.md').write_text(text)
            return spec_tuning_seed_authority(Ctx(output, phase=None))

    def test_accepts_delegation_with_binding_behaviour(self):
        self.assertEqual(self.check_text(VALID), [])

    def test_rejects_seed_promoted_to_contract(self):
        failures = self.check_text(VALID.replace('non-normative', 'binding'))
        self.assertTrue(any('non-normative' in f.detail for f in failures))

    def test_rejects_tuning_that_drops_required_timing(self):
        failures = self.check_text(VALID.replace('Countdown starts after the field ends.', ''))
        self.assertTrue(any('field ends' in f.detail for f in failures))
