import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCAFFOLD_SCRIPT = REPO_ROOT / "src" / "scripts" / "scaffold.js"
INSTALLER = REPO_ROOT / "bin" / "mano-plan.js"


@unittest.skipUnless(shutil.which("node"), "Node.js is required for scaffold tests")
class ScaffoldScriptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "my-app"
        self.root.mkdir()
        (self.root / "_mano").mkdir()
        (self.root / "_mano" / "sentinel.md").write_text("MANO_SENTINEL\n")
        (self.root / "_mano_output").mkdir()
        (self.root / "_mano_output" / "phase-plan.md").write_text("PHASE_SENTINEL\n")
        (self.root / "AGENTS.md").write_text("AGENT_SENTINEL\n")
        self.stages = []

    def tearDown(self):
        for stage in self.stages:
            shutil.rmtree(stage, ignore_errors=True)
        self.temp_dir.cleanup()

    def run_generator(self, javascript, *extra):
        result = subprocess.run(
            [
                "node",
                str(SCAFFOLD_SCRIPT),
                "run",
                "--project-root",
                str(self.root),
                "--name",
                "my-app",
                *extra,
                "--",
                "node",
                "-e",
                javascript,
                "{target}",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
        )
        combined = result.stdout + result.stderr
        for match in re.finditer(r"(?:outside the project|kept at): ([^\n]+)", combined):
            stage = Path(match.group(1).strip())
            if stage.exists() and stage not in self.stages:
                self.stages.append(stage)
        return result

    def assert_mano_preserved(self):
        self.assertEqual((self.root / "_mano" / "sentinel.md").read_text(), "MANO_SENTINEL\n")
        self.assertEqual(
            (self.root / "_mano_output" / "phase-plan.md").read_text(),
            "PHASE_SENTINEL\n",
        )
        self.assertEqual((self.root / "AGENTS.md").read_text(), "AGENT_SENTINEL\n")

    def test_stages_generator_and_merges_new_files_without_touching_mano(self):
        (self.root / ".git").mkdir()
        (self.root / ".git" / "config").write_text("ROOT_GIT_SENTINEL\n")
        script = r"""
const fs = require('node:fs');
const path = require('node:path');
const target = process.argv[1];
fs.mkdirSync(path.join(target, 'src'), {recursive: true});
fs.mkdirSync(path.join(target, '.git'), {recursive: true});
fs.writeFileSync(path.join(target, 'package.json'), '{"name":"my-app"}\n');
fs.writeFileSync(path.join(target, 'src', 'index.js'), 'console.log("ready");\n');
fs.writeFileSync(path.join(target, '.gitignore'), 'node_modules\n');
fs.writeFileSync(path.join(target, '.git', 'config'), 'STAGED_GIT_MUST_NOT_COPY\n');
"""

        result = self.run_generator(script)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("no existing project file was overwritten or deleted", result.stdout)
        self.assertEqual((self.root / "package.json").read_text(), '{"name":"my-app"}\n')
        self.assertEqual((self.root / "src" / "index.js").read_text(), 'console.log("ready");\n')
        self.assertEqual((self.root / ".gitignore").read_text(), "node_modules\n")
        self.assertEqual((self.root / ".git" / "config").read_text(), "ROOT_GIT_SENTINEL\n")
        self.assert_mano_preserved()

    def test_passes_relative_target_for_generators_that_join_target_to_cwd(self):
        script = r"""
const fs = require('node:fs');
const path = require('node:path');
const suppliedTarget = process.argv[1];
const target = path.join(process.cwd(), suppliedTarget);
fs.mkdirSync(target, {recursive: true});
fs.writeFileSync(path.join(target, 'package.json'), JSON.stringify({
  name: 'my-app',
  suppliedTarget,
  targetWasRelative: !path.isAbsolute(suppliedTarget),
}) + '\n');
"""

        result = self.run_generator(script)

        self.assertEqual(result.returncode, 0, result.stderr)
        package = (self.root / "package.json").read_text()
        self.assertIn('"suppliedTarget":"my-app"', package)
        self.assertIn('"targetWasRelative":true', package)
        self.assert_mano_preserved()

    def test_differing_collision_aborts_before_any_generated_file_is_copied(self):
        (self.root / "README.md").write_text("KEEP THIS README\n")
        script = r"""
const fs = require('node:fs');
const path = require('node:path');
const target = process.argv[1];
fs.mkdirSync(target, {recursive: true});
fs.writeFileSync(path.join(target, 'README.md'), 'REPLACE THE README\n');
fs.writeFileSync(path.join(target, 'package.json'), '{"name":"must-not-copy"}\n');
"""

        result = self.run_generator(script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("merge blocked", result.stderr)
        self.assertIn("README.md", result.stderr)
        self.assertIn("project was not touched", result.stderr)
        self.assertEqual((self.root / "README.md").read_text(), "KEEP THIS README\n")
        self.assertFalse((self.root / "package.json").exists())
        self.assert_mano_preserved()

    def test_identical_existing_file_is_retained_while_missing_files_are_added(self):
        (self.root / ".gitignore").write_text("node_modules\n")
        script = r"""
const fs = require('node:fs');
const path = require('node:path');
const target = process.argv[1];
fs.mkdirSync(target, {recursive: true});
fs.writeFileSync(path.join(target, '.gitignore'), 'node_modules\n');
fs.writeFileSync(path.join(target, 'package.json'), '{"name":"my-app"}\n');
"""

        result = self.run_generator(script)

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("retained 1 identical existing file(s)", result.stdout)
        self.assertEqual((self.root / ".gitignore").read_text(), "node_modules\n")
        self.assertTrue((self.root / "package.json").exists())
        self.assert_mano_preserved()

    def test_reserved_mano_output_from_generator_is_rejected_before_merge(self):
        script = r"""
const fs = require('node:fs');
const path = require('node:path');
const target = process.argv[1];
fs.mkdirSync(path.join(target, '_mano_output'), {recursive: true});
fs.writeFileSync(path.join(target, '_mano_output', 'bad.md'), 'BAD\n');
fs.writeFileSync(path.join(target, 'package.json'), '{"name":"must-not-copy"}\n');
"""

        result = self.run_generator(script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generator created reserved path", result.stderr)
        self.assertFalse((self.root / "package.json").exists())
        self.assert_mano_preserved()

    def test_failed_generator_leaves_project_untouched(self):
        script = r"""
const fs = require('node:fs');
const path = require('node:path');
const target = process.argv[1];
fs.mkdirSync(target, {recursive: true});
fs.writeFileSync(path.join(target, 'partial.txt'), 'PARTIAL\n');
process.exit(7);
"""

        result = self.run_generator(script)

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("generator exited with status 7", result.stderr)
        self.assertIn("project was not touched", result.stderr)
        self.assertFalse((self.root / "partial.txt").exists())
        self.assert_mano_preserved()

    def test_command_requires_target_placeholder(self):
        result = subprocess.run(
            [
                "node",
                str(SCAFFOLD_SCRIPT),
                "run",
                "--project-root",
                str(self.root),
                "--",
                "node",
                "--version",
            ],
            cwd=self.root,
            text=True,
            capture_output=True,
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("must contain {target}", result.stderr)
        self.assert_mano_preserved()


class ScaffoldContractTests(unittest.TestCase):
    def test_installer_ships_scaffold_runner(self):
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            result = subprocess.run(
                ["node", str(INSTALLER), "install", "--yes"],
                cwd=project,
                text=True,
                capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            installed = project / "_mano" / "scripts" / "scaffold.js"
            self.assertTrue(installed.exists())
            self.assertIn("Existing files are never overwritten", installed.read_text())

    def test_planning_and_implementation_surfaces_share_the_guarded_contract(self):
        spec = (REPO_ROOT / "src" / "skills" / "spec.md").read_text()
        stories = (REPO_ROOT / "src" / "skills" / "stories.md").read_text()
        dev = (REPO_ROOT / "src" / "skills" / "dev.md").read_text()
        agents = (REPO_ROOT / "src" / "bootstrap" / "AGENTS.md").read_text()
        workflow = (REPO_ROOT / "src" / "workflow.md").read_text()
        template = (REPO_ROOT / "src" / "templates" / "tech-spec.md").read_text()

        self.assertIn("## Project Scaffold", template)
        self.assertIn("scaffold.js run", spec)
        self.assertIn("literal required token", spec)
        self.assertIn("Greenfield scaffold gate", stories)
        self.assertIn("route the missing guarded command to `mano spec`", stories)
        self.assertIn("Never empty the project for a scaffold", dev)
        self.assertIn("Greenfield scaffold safety is a hard stop", agents)
        self.assertIn("`yolo` and auto mode do not relax this rule", agents)
        self.assertIn("Greenfield scaffolding is staged, never destructive", workflow)
        for text in (spec, stories, dev, agents, workflow):
            self.assertIn("_mano_output", text)
            self.assertIn("scaffold", text.lower())

    def test_public_docs_explain_collision_behavior_and_literal_target(self):
        readme = (REPO_ROOT / "README.md").read_text()
        changelog = (REPO_ROOT / "CHANGELOG.md").read_text()

        self.assertIn("### Safe greenfield scaffolding", readme)
        self.assertIn("`{target}` must remain literal", readme)
        self.assertIn("stops before copying", readme)
        self.assertIn("Greenfield scaffolding now has a non-destructive runner", changelog)


if __name__ == "__main__":
    unittest.main()
