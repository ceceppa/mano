"""Guard the cross-contract boundaries that scripts cannot decide."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent


def read(name):
    return (ROOT / name).read_text()


class AutoRepairContractTests(unittest.TestCase):
    def test_implementation_and_planning_share_the_same_exception(self):
        def paragraph(name):
            return read(name).split('**Automatic pre-flight repair.**', 1)[1].split('\n\n', 1)[0]
        self.assertEqual(paragraph('src/rules/auto.md'), paragraph('src/rules/implement.md'))
        build = read('src/skills/build.md')
        self.assertIn('### Automatic pre-flight repair', build)
        self.assertIn('never per-row gates, corrections, terminal sweeps, or `mano dev`', build)
        self.assertIn('not a deviation stop', build)

    def test_automatic_routing_cannot_decide_product_scope_or_waive_readiness(self):
        build = read('src/skills/build.md')
        repair = build.split('### Automatic pre-flight repair', 1)[1].split('**0⊘.', 1)[0]
        for guard in ['no scope or Exit Criteria change', 'competing product outcomes',
                      'owner was not explicitly skipped', 'absent from `CHAIN_REPAIRS`',
                      'never substitute `save` to bypass it', 'Rerun the entire pre-flight',
                      'hook triage', '❓ Decide:']:
            self.assertIn(guard, repair)
        self.assertIn('invoke the exact owning Mano skill now', repair)
        self.assertIn('never lets build invent or edit an input contract', repair)

    def test_task_chain_repairs_only_its_own_gaps_and_never_picks_work(self):
        task = read('src/skills/task.md')
        repair = task.split('## Auto mode: gap repair', 1)[1].split('\n## ', 1)[0]
        for guard in ['R2, R3, or R4\'s missing scaffold command', 'never chain',
                      'One attempt per owner per run', '❓ Decide:', 'hook triage',
                      'run R2–R5 in full again before any edit', 'never runs `mano start`',
                      'keeps no `chain.js` record']:
            self.assertIn(guard, repair)
        self.assertIn('Auto mode never chains into it, `mano continue` never selects it', task)
        self.assertIn('[mano auto]: task "<item title>"', task)
        self.assertIn('**Task chains.**', read('src/rules/auto.md'))
        self.assertIn('**The one arming outside a phase is `mano task`.**', read('src/workflow.md'))

    def test_start_accounts_for_removed_state_and_resets_only_on_scope_approval(self):
        start = read('src/skills/start.md')
        self.assertIn('State removal and replacement require spec coverage', start)
        self.assertIn('even without a new API or dependency', start)
        self.assertIn('Never clear on a routine handoff or a reply to a paused question', start)
