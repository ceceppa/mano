"""Swappable headless runners for the three supported CLIs.

A runner takes a project directory and a prompt, invokes the CLI in
non-interactive mode inside that directory, and lets the agent write files. It
returns captured stdout/stderr for diagnostics plus the isolated last assistant
message, so a case can assert a genuinely chat-native contract without matching
tool traces.

Each runner returns the CompletedProcess so the caller can surface failures.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass
class RunnerResult:
    returncode: int
    stdout: str
    stderr: str
    final_response: str = ""


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
    result = _run(cmd, project_dir, timeout)
    # `claude --print` writes the last assistant message to stdout.
    return replace(result, final_response=result.stdout.strip())


def run_codex(project_dir: str, prompt: str, timeout: int) -> RunnerResult:
    # `codex exec` is the non-interactive subcommand. --skip-git-repo-check
    # avoids refusing to run outside a git repo; --dangerously-bypass... lets
    # it edit files without prompting (this is a throwaway temp dir).
    final_path = Path(project_dir) / ".mano-eval-codex-final.txt"
    cmd = [
        "codex",
        "exec",
        "--skip-git-repo-check",
        "--dangerously-bypass-approvals-and-sandbox",
        "--output-last-message",
        str(final_path),
        prompt,
    ]
    result = _run(cmd, project_dir, timeout)
    try:
        final_response = final_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        final_response = ""
    finally:
        final_path.unlink(missing_ok=True)
    return replace(result, final_response=final_response)


def _opencode_final_response(raw: str) -> str:
    """Extract the last assistant message from OpenCode JSONL events."""
    messages: dict[str, list[str]] = {}
    order: list[str] = []
    for line in raw.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "text":
            continue
        part = event.get("part") or {}
        if part.get("type") != "text" or not isinstance(part.get("text"), str):
            continue
        message_id = str(part.get("messageID") or event.get("messageID") or "")
        if not message_id:
            continue
        if message_id not in messages:
            messages[message_id] = []
            order.append(message_id)
        messages[message_id].append(part["text"])
    if not order:
        return ""
    return "".join(messages[order[-1]]).strip()


def run_opencode(project_dir: str, prompt: str, timeout: int) -> RunnerResult:
    # --dir is explicit even though subprocess.cwd is also set: a long-lived or
    # plugin-backed OpenCode process can otherwise retain the parent repository
    # as its project and edit the eval fixture instead of the throwaway install.
    # --pure keeps external plugins from reintroducing that ambient workspace.
    cmd = [
        "opencode",
        "run",
        "--pure",
        "--dir",
        project_dir,
        "--format",
        "json",
        prompt,
    ]
    result = _run(cmd, project_dir, timeout)
    return replace(result, final_response=_opencode_final_response(result.stdout))


RUNNERS = {
    "claude": run_claude,
    "codex": run_codex,
    "opencode": run_opencode,
}
