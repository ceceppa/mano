from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

import assertions


REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "eval" / "fixtures"


class DevYoloAssertionTests(unittest.TestCase):
    def _ctx(
        self,
        statuses: dict[str, str],
        modules: set[str],
        transcript: str,
        fixture: str = "dev-yolo",
    ) -> assertions.Ctx:
        temp = tempfile.TemporaryDirectory(prefix="mano-dev-assertion-")
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        output = root / "_mano_output"
        phase = output / "phase-1"
        stories = phase / "stories"
        stories.mkdir(parents=True)

        snapshot = {
            path.name: path.read_text(encoding="utf-8")
            for path in (FIXTURES_DIR / fixture).iterdir()
            if path.is_file()
        }
        (phase / "phase-brief.md").write_text(
            snapshot["phase-brief.md"], encoding="utf-8"
        )
        for name, content in snapshot.items():
            if name.startswith("story-") and name.endswith(".md"):
                (stories / name).write_text(content, encoding="utf-8")

        readme = snapshot["stories-README.md"]
        for story, status in statuses.items():
            readme = re.sub(
                rf"^(\|\s*{re.escape(story)}\s*\|\s*[^|]+\|\s*[^|]+\|)"
                r"\s*[^|]+(\|\s*)$",
                rf"\1 {status} \2",
                readme,
                flags=re.MULTILINE | re.IGNORECASE,
            )
        (stories / "README.md").write_text(readme, encoding="utf-8")

        for relative in modules:
            path = root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            signals = assertions.DEV_YOLO_MODULES[relative]
            path.write_text("\n".join(signals) + "\n", encoding="utf-8")

        return assertions.Ctx(
            output,
            phase=1,
            fixture_snapshot=snapshot,
            transcript=transcript,
        )

    def test_accepts_full_yolo_batch(self):
        ctx = self._ctx(
            {"1": "done", "2": "done", "3": "done"},
            set(assertions.DEV_YOLO_MODULES),
            "Stories 1, 2, 3 done — statuses updated in stories/README.md",
        )
        self.assertEqual(assertions.dev_yolo_completed_all_pending(ctx), [])
        self.assertEqual(assertions.dev_yolo_output_discipline(ctx), [])

    def test_rejects_yolo_stopping_after_first_story(self):
        ctx = self._ctx(
            {"1": "done", "2": "pending", "3": "pending"},
            {"src/yolo/base.js"},
            "Story 1 done — status updated in stories/README.md",
        )
        self.assertTrue(assertions.dev_yolo_completed_all_pending(ctx))
        self.assertTrue(assertions.dev_yolo_output_discipline(ctx))

    def test_accepts_default_single_story(self):
        ctx = self._ctx(
            {"1": "done", "2": "pending", "3": "pending"},
            {"src/yolo/base.js"},
            "Story 1 done — status updated in stories/README.md",
        )
        self.assertEqual(assertions.dev_default_completed_only_next(ctx), [])
        self.assertEqual(assertions.dev_default_output_discipline(ctx), [])

    def test_rejects_default_mode_accidentally_batching(self):
        ctx = self._ctx(
            {"1": "done", "2": "done", "3": "done"},
            set(assertions.DEV_YOLO_MODULES),
            "Stories 1, 2, 3 done — statuses updated in stories/README.md",
        )
        self.assertTrue(assertions.dev_default_completed_only_next(ctx))
        self.assertTrue(assertions.dev_default_output_discipline(ctx))

    def test_accepts_yolo_stopping_at_first_blocker(self):
        ctx = self._ctx(
            {"1": "done", "2": "pending", "3": "pending"},
            {"src/yolo/base.js"},
            "Story 1 done; YOLO stopped with Story 2 pending because the Feature "
            "prefix is missing — run mano spec.",
            fixture="dev-yolo-blocker",
        )
        self.assertEqual(assertions.dev_yolo_stopped_at_first_blocker(ctx), [])
        self.assertEqual(
            assertions.dev_yolo_interrupted_output_discipline(ctx), []
        )

    def test_rejects_yolo_skipping_past_blocker(self):
        ctx = self._ctx(
            {"1": "done", "2": "done", "3": "done"},
            set(assertions.DEV_YOLO_MODULES),
            "Stories 1, 2, 3 done — statuses updated in stories/README.md",
            fixture="dev-yolo-blocker",
        )
        self.assertTrue(assertions.dev_yolo_stopped_at_first_blocker(ctx))
        self.assertTrue(assertions.dev_yolo_interrupted_output_discipline(ctx))


if __name__ == "__main__":
    unittest.main()
