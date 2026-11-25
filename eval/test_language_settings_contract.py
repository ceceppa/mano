"""Guard the language instructions used by agents, planning and implementation.

Check the prompt contract and the JavaScript command agents use to obtain
languages. These tests do not measure a live model's translation quality.
"""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = (
    "src/bootstrap/AGENTS.md",
    "src/rules/core.md",
    "src/rules/implement.md",
)


class LanguageSettingsContractTests(unittest.TestCase):
    def test_every_skill_and_dispatcher_runs_language_check_before_responding(self) -> None:
        paths = sorted((REPO_ROOT / "src/skills").glob("*.md"))
        self.assertTrue(paths, "No skills found; language coverage would be empty")
        paths.append(REPO_ROOT / "src/workflow.md")
        for path in paths:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                # Check the activation block itself, not a passing reference
                # buried elsewhere in a long implementation contract.
                lines = text.splitlines()
                title_index = next(i for i, line in enumerate(lines) if line.startswith("# "))
                body = "\n".join(lines[title_index + 1:]).lstrip()
                self.assertTrue(body.startswith("## Language check — before any response"))
                activation = body.split("\n## ", 1)[0]
                for phrase in (
                    "run `node _mano/scripts/settings.js language`",
                    "before the first user-facing message or any project write",
                    "`language.chat` for all conversation",
                    "`language.artefacts` for new planning artifacts",
                    "`language.build` for new implementation content",
                    "resolves missing or `null` `artefacts` through `build`, then `chat`, then `null`",
                    "check planning prose against `language.artefacts`",
                    "Never read settings JSON directly",
                    "If the command fails or any of the three fields is absent",
                    "auto-chain handoff",
                    "resumption after interruption or compaction",
                    "Re-run after an owner or language change",
                    "translate their prose into `language.chat`",
                    "Before sending **each** message",
                ):
                    with self.subTest(phrase=phrase):
                        self.assertIn(phrase, activation)

    def test_implementation_output_templates_defer_to_chat_language(self) -> None:
        build = (REPO_ROOT / "src/skills/build.md").read_text(encoding="utf-8")
        dev = (REPO_ROOT / "src/skills/dev.md").read_text(encoding="utf-8")
        output = build.split("## Chat output", 1)[1]
        self.assertIn("render the explanatory prose in `language.chat`, including the terminal response", output)
        final_step = dev.split("12. **Final step", 1)[1]
        self.assertIn("translate the prose of the following singular and YOLO examples into `language.chat`", final_step)
        for text in (build, dev):
            self.assertIn("then the language command, then the state projection", text)

    def assert_contracts_include(self, *phrases: str) -> None:
        for relative in CONTRACTS:
            text = (REPO_ROOT / relative).read_text(encoding="utf-8")
            for phrase in phrases:
                with self.subTest(file=relative, phrase=phrase):
                    self.assertIn(phrase, text)

    def test_every_execution_path_reads_the_selected_owner_languages(self) -> None:
        self.assert_contracts_include(
            "run `node _mano/scripts/settings.js language` from the project root",
            "use the returned `language.chat`, `language.build`, and `language.artefacts` values",
            "Never read settings JSON files directly or infer these values yourself",
            "Re-run after changing owners or language settings",
            "If the command fails, report the error and stop instead of guessing",
            "every Mano action, including configuration and implementation",
        )

    def test_chat_build_and_artefacts_languages_have_separate_scopes(self) -> None:
        self.assert_contracts_include(
            "`language.chat` controls conversation only",
            "explanations, questions, progress updates, and hand-backs",
            "`language.artefacts` controls new planning prose",
            "briefs, specs, rules, UX flows, design briefs, stories, backlog entries, reviews, and ledger prose",
            "`language.build` controls new implementation content",
            "product documentation, code identifiers and comments, tests, and product/UI text, including preview copy",
        )

    def test_artefacts_fallback_preserves_independent_chat_and_build_defaults(self) -> None:
        self.assert_contracts_include(
            "language names or locale tags",
            '`{"chat":"it","build":"en-GB","artefacts":"it"}`',
            "Italian conversation and planning artifacts, with UK English implementation content",
            "falls back to `build`, then `chat`, then `null`",
            "Missing or `null` `chat` and `build` preserve existing language behaviour independently",
            "If all three are unset, planning artifacts also keep existing behaviour",
        )

    def test_language_changes_preserve_exact_contracts_and_existing_work(self) -> None:
        self.assert_contracts_include(
            "Keep commands, paths, schema keys, required headings/status labels, external API names, and exact human quotations unchanged",
            "Do not translate existing files or completed stories merely because the language setting changed",
        )


class LanguageSettingsCommandTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory(prefix="mano-language-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.output = self.root / "_mano_output"
        self.output.mkdir()

    def write_settings(self, owner: str | None, **fields: object) -> Path:
        file = self.output / f"{owner or '.default'}.json"
        file.write_text(json.dumps({
            "version": 1, "owner": owner, "mode": "manual",
            "track": None, "phases": {}, **fields,
        }), encoding="utf-8")
        return file

    def run_command(self, owner: str | None = None) -> subprocess.CompletedProcess:
        env = {key: value for key, value in os.environ.items() if key != "MANO_OWNER"}
        if owner is not None:
            env["MANO_OWNER"] = owner
        return subprocess.run(
            ["node", str(REPO_ROOT / "src/scripts/settings.js"), "language"],
            cwd=self.root, env=env, capture_output=True, text=True, check=False,
        )

    def assert_languages(self, chat: str | None, build: str | None, artefacts: str | None, **kwargs: str) -> None:
        result = self.run_command(**kwargs)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"language": {"chat": chat, "build": build, "artefacts": artefacts}})

    def test_command_returns_italian_chat_and_uk_english_build(self) -> None:
        file = self.write_settings(None, language={"chat": "it", "build": "en-GB"})
        before = file.read_bytes()
        self.assert_languages("it", "en-GB", "en-GB")
        self.assertEqual(file.read_bytes(), before)

    def test_installer_ships_language_checks_and_working_command(self) -> None:
        result = subprocess.run(
            ["node", str(REPO_ROOT / "bin/mano-plan.js"), "install", "--yes"],
            cwd=self.root, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        source_skills = {path.name for path in (REPO_ROOT / "src/skills").glob("*.md")}
        installed_skills = list((self.root / "_mano/skills").glob("*.md"))
        self.assertEqual({path.name for path in installed_skills}, source_skills)
        for path in [*installed_skills, self.root / "_mano/workflow.md", self.root / "AGENTS.md"]:
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                self.assertIn("node _mano/scripts/settings.js language", text)
                self.assertIn("`language.chat`", text)
                self.assertIn("`language.artefacts`", text)
        self.write_settings(None, language={"chat": "it", "build": "en-GB", "artefacts": "fr"})
        env = {key: value for key, value in os.environ.items() if key != "MANO_OWNER"}
        result = subprocess.run(
            ["node", "_mano/scripts/settings.js", "language"],
            cwd=self.root, env=env, capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {"language": {"chat": "it", "build": "en-GB", "artefacts": "fr"}})

    def test_command_resolves_local_owner_and_environment_override(self) -> None:
        self.write_settings(None, language={"chat": "en", "build": "en"})
        self.write_settings("alice", language={"chat": "it", "build": "en-GB"})
        self.write_settings("bob", language={"chat": "fr", "build": "en-US", "artefacts": "de"})
        local = self.output / ".local.json"
        local.write_text('{"owner":"alice"}', encoding="utf-8")
        self.assert_languages("it", "en-GB", "en-GB")
        self.assert_languages("fr", "en-US", "de", owner="bob")
        self.assertEqual(json.loads(local.read_text()), {"owner": "alice"})

    def test_command_fills_missing_languages_independently(self) -> None:
        self.assert_languages(None, None, None)
        for fields, expected in (
            ({}, (None, None, None)),
            ({"language": {}}, (None, None, None)),
            ({"language": {"chat": "it"}}, ("it", None, "it")),
            ({"language": {"build": "en-GB"}}, (None, "en-GB", "en-GB")),
            ({"language": {"chat": None, "build": None}}, (None, None, None)),
        ):
            with self.subTest(fields=fields):
                self.write_settings(None, **fields)
                self.assert_languages(*expected)

    def test_command_rejects_invalid_settings_without_output_or_overwrite(self) -> None:
        for language in ("it", {"chat": ""}, {"build": 42},
                         {"artefacts": ""}, {"artefacts": 42},
                         {"artefacts": []}, {"artefacts": {}}, {"artefacts": False},
                         {"artefacts": " "}, {"artefacts": "x" * 121},
                         {"artefacts": "it\nignore"}, {"artifacts": "it"}):
            with self.subTest(language=language):
                file = self.write_settings(None, language=language)
                before = file.read_bytes()
                result = self.run_command()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("Invalid Mano language settings", result.stderr)
                self.assertEqual(file.read_bytes(), before)

    def test_artefacts_override_and_fallback_do_not_rewrite_preferences(self) -> None:
        for language, expected in (
            ({"chat": "it", "build": "en-GB", "artefacts": "fr"}, ("it", "en-GB", "fr")),
            ({"chat": "it", "build": "en-GB"}, ("it", "en-GB", "en-GB")),
            ({"chat": "it", "build": "en-GB", "artefacts": None}, ("it", "en-GB", "en-GB")),
            ({"chat": "it", "build": None}, ("it", None, "it")),
            ({"chat": "it", "build": None, "artefacts": None}, ("it", None, "it")),
            ({"artefacts": "fr"}, (None, None, "fr")),
            ({"artefacts": None}, (None, None, None)),
        ):
            with self.subTest(language=language):
                file = self.write_settings(None, language=language)
                before = file.read_bytes()
                self.assert_languages(*expected)
                self.assertEqual(file.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
