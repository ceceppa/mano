"""Swappable headless runners for the three supported CLIs.

A runner takes a project directory and a prompt, invokes the CLI in
non-interactive mode inside that directory, and lets the agent write files. It
returns captured stdout/stderr for diagnostics plus the isolated last assistant
message, so a case can assert a genuinely chat-native contract without matching
tool traces.

It also returns whatever the CLI reports about the *cost* of that invocation —
token usage, the model the provider actually resolved, and the CLI's own
version. A runner that exposes none of it returns `None` for every field.
`None` is not `0`: a zero is indistinguishable from a real measurement and
would silently poison an average.

Session continuation is opt-in per runner. `run_x.supports_continue` says
whether the CLI can resume its previous session in the same project; the
harness fails a `continue` step outright rather than silently starting fresh.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path


@dataclass
class Usage:
    """What one CLI invocation cost, as the CLI itself reported it.

    Every field is `None` when the runner does not expose that number. Never
    write `0` for an unavailable metric.

    `messages` is the assistant-message count when the runner exposes one; the
    `claude` runner reports the envelope's `num_turns`, which is the closest
    thing that CLI exposes.
    """

    input: int | None = None
    output: int | None = None
    cache_create: int | None = None
    cache_read: int | None = None
    messages: int | None = None

    def total_tokens(self) -> int | None:
        """Sum of every token field that was actually measured.

        `None` when the runner reported no token counts at all — an unmeasured
        run has no total, it does not have a total of zero.
        """
        parts = [self.input, self.output, self.cache_create, self.cache_read]
        measured = [p for p in parts if p is not None]
        return sum(measured) if measured else None

    def as_record(self) -> dict[str, int | None]:
        return {
            "input": self.input,
            "output": self.output,
            "cache_create": self.cache_create,
            "cache_read": self.cache_read,
            "messages": self.messages,
        }


@dataclass
class RunnerResult:
    returncode: int
    stdout: str
    stderr: str
    final_response: str = ""
    usage: Usage | None = None
    resolved_model: str | None = None
    runner_version: str | None = None


class SessionUnsupported(RuntimeError):
    """Raised when a case asks a runner to continue a session it cannot."""


def _run(cmd: list[str], cwd: str, timeout: int, env: dict[str, str] | None = None) -> RunnerResult:
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env={**os.environ, **env} if env else None,
    )
    return RunnerResult(proc.returncode, proc.stdout, proc.stderr)


_VERSION_CACHE: dict[str, str | None] = {}


def cli_version(binary: str) -> str | None:
    """`<binary> --version`, or None when the CLI does not answer.

    Cached per process: the version cannot change mid-run, and a baseline
    manifest records it once per run anyway.
    """
    if binary in _VERSION_CACHE:
        return _VERSION_CACHE[binary]
    try:
        proc = subprocess.run(
            [binary, "--version"], capture_output=True, text=True, timeout=30
        )
        version = proc.stdout.strip() or proc.stderr.strip() or None
    except (OSError, subprocess.SubprocessError):
        version = None
    _VERSION_CACHE[binary] = version
    return version


def _int_or_none(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _claude_envelope(raw: str) -> dict | None:
    """The `result` object from `claude --output-format json`.

    Accepts the single JSON object that `--output-format json` prints and the
    JSONL that `--output-format stream-json` prints, so a future switch to
    streaming does not silently lose usage. Returns None when neither parses.
    """
    text = raw.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    if isinstance(parsed, list):
        events = [e for e in parsed if isinstance(e, dict)]
        results = [e for e in events if e.get("type") == "result"]
        return (results or events or [None])[-1]

    results: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            results.append(event)
    if not results:
        return None
    final = [e for e in results if e.get("type") == "result"]
    return (final or results)[-1]


def _claude_usage(envelope: dict) -> Usage | None:
    usage = envelope.get("usage")
    turns = _int_or_none(envelope.get("num_turns"))
    if not isinstance(usage, dict):
        return Usage(messages=turns) if turns is not None else None
    parsed = Usage(
        input=_int_or_none(usage.get("input_tokens")),
        output=_int_or_none(usage.get("output_tokens")),
        cache_create=_int_or_none(usage.get("cache_creation_input_tokens")),
        cache_read=_int_or_none(usage.get("cache_read_input_tokens")),
        messages=turns,
    )
    if parsed == Usage():
        return None
    return parsed


def _claude_resolved_model(envelope: dict) -> str | None:
    """The model the provider actually billed, never the alias we asked for."""
    model = envelope.get("model")
    if isinstance(model, str) and model.strip():
        return model.strip()
    model_usage = envelope.get("modelUsage")
    if isinstance(model_usage, dict):
        names = sorted(str(k) for k in model_usage if str(k).strip())
        if names:
            return ", ".join(names)
    return None


def run_claude(
    project_dir: str,
    prompt: str,
    timeout: int,
    env: dict[str, str] | None = None,
    *,
    model: str | None = None,
    session: str = "fresh",
) -> RunnerResult:
    # --print runs headless to completion. --permission-mode bypassPermissions
    # lets the agent write files without interactive approval. --output-format
    # json wraps the final message in an envelope that also carries usage and
    # the resolved model, so measurement costs no extra invocation.
    cmd = [
        "claude",
        "--print",
        "--output-format",
        "json",
        "--permission-mode",
        "bypassPermissions",
    ]
    if model:
        cmd += ["--model", model]
    if session == "continue":
        # The temp project is exclusive to this case, so "the most recent
        # conversation in this directory" is unambiguously the previous step.
        cmd.append("--continue")
    cmd.append(prompt)
    result = _run(cmd, project_dir, timeout, env)
    envelope = _claude_envelope(result.stdout)
    if envelope is None:
        # Envelope missing (crash, truncated output): fall back to raw stdout
        # for the response and report every metric as unavailable.
        return replace(
            result,
            final_response=result.stdout.strip(),
            runner_version=cli_version("claude"),
        )
    final = envelope.get("result")
    return replace(
        result,
        final_response=final.strip() if isinstance(final, str) else "",
        usage=_claude_usage(envelope),
        resolved_model=_claude_resolved_model(envelope),
        runner_version=cli_version("claude"),
    )


run_claude.supports_continue = True


def run_codex(
    project_dir: str,
    prompt: str,
    timeout: int,
    env: dict[str, str] | None = None,
    *,
    model: str | None = None,
    session: str = "fresh",
) -> RunnerResult:
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
    ]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    result = _run(cmd, project_dir, timeout, env)
    try:
        final_response = final_path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        final_response = ""
    finally:
        final_path.unlink(missing_ok=True)
    # No usage envelope: every metric stays None rather than a fabricated 0.
    return replace(
        result,
        final_response=final_response,
        runner_version=cli_version("codex"),
    )


run_codex.supports_continue = False


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


def run_opencode(
    project_dir: str,
    prompt: str,
    timeout: int,
    env: dict[str, str] | None = None,
    *,
    model: str | None = None,
    session: str = "fresh",
) -> RunnerResult:
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
    ]
    if model:
        cmd += ["--model", model]
    cmd.append(prompt)
    result = _run(cmd, project_dir, timeout, env)
    # The JSONL event stream carries no per-run usage totals: metrics stay None.
    return replace(
        result,
        final_response=_opencode_final_response(result.stdout),
        runner_version=cli_version("opencode"),
    )


run_opencode.supports_continue = False


RUNNERS = {
    "claude": run_claude,
    "codex": run_codex,
    "opencode": run_opencode,
}


def supports_continue(runner) -> bool:
    """Whether this runner can resume its previous session in the same project.

    Defaults to False for anything that does not say otherwise, so an unknown
    or stubbed runner fails a `continue` step loudly instead of silently
    running it fresh.
    """
    return bool(getattr(runner, "supports_continue", False))
