"""Swappable headless runners for the three supported CLIs.

A runner takes a project directory and a prompt, invokes the CLI in
non-interactive mode inside that directory, and lets the agent write files.
The harness asserts on the files afterwards — it does not parse stdout.

Each runner returns the CompletedProcess so the caller can surface failures.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass


@dataclass
class RunnerResult:
    returncode: int
    stdout: str
    stderr: str


def _run(cmd: list[str], cwd: str, timeout: int) -> RunnerResult:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return RunnerResult(proc.returncode, proc.stdout, proc.stderr)


def run_claude(project_dir: str, prompt: str, timeout: int) -> RunnerResult:
    # --print runs headless to completion. --permission-mode bypassPermissions
    # lets the agent write files without interactive approval.
    cmd = [
        "claude",
        "--print",
        "--permission-mode",
        "bypassPermissions",
        prompt,
    ]
    return _run(cmd, project_dir, timeout)


def run_codex(project_dir: str, prompt: str, timeout: int) -> RunnerResult:
    # `codex exec` is the non-interactive subcommand. --skip-git-repo-check
    # avoids refusing to run outside a git repo; --dangerously-bypass... lets
    # it edit files without prompting (this is a throwaway temp dir).
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        prompt,
    ]
    return _run(cmd, project_dir, timeout)


def run_opencode(project_dir: str, prompt: str, timeout: int) -> RunnerResult:
    cmd = ["opencode", "run", prompt]
    return _run(cmd, project_dir, timeout)


RUNNERS = {
    "claude": run_claude,
    "codex": run_codex,
    "opencode": run_opencode,
}
