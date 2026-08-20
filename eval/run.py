#!/usr/bin/env python3
"""Mano eval harness — minimal proof.

For each case:
  1. Install Mano into a throwaway temp project via the real installer
     (guarantees the fixture matches a true install — no drift).
  2. Copy the case's fixture input files into _mano_output/ (and phase-N/).
  3. Invoke the chosen CLI headless with the case prompt (e.g. "mano stories"),
     or with each prompt of an ordered `steps` list, in one retained project.
  4. Run the case's assertions over artifacts, per-step state, and any
     chat-native final response.
  5. Report a pass/fail table and append one manifest record per run.

Usage:
  python3 eval/run.py                       # all cases, claude runner
  python3 eval/run.py --runner opencode     # pick a different CLI
  python3 eval/run.py --case stories-bugfix # one case
  python3 eval/run.py --model opus          # pin the model; record what resolved
  python3 eval/run.py --rerun-failures      # re-run each failure once (flake check)
  python3 eval/run.py --list-rules          # incident-backed rule inventory
  python3 eval/run.py --probe-rule RULE_ID  # all mapped cases, rule removed
  python3 eval/run.py --case X --without-rule RULE_ID
                                            # low-level partial/debug probe
  python3 eval/run.py --keep                # keep temp dirs for inspection

No Anthropic API key needed — it drives whichever CLI you already use.
Most assertions inspect output files. Chat-native contracts may also inspect the
runner's final response, without depending on hidden reasoning or tool traces.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import assertions as A  # noqa: E402
import provenance as P  # noqa: E402
from runners import RUNNERS, supports_continue  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "eval"
CASES_DIR = EVAL_DIR / "cases"
FIXTURES_DIR = EVAL_DIR / "fixtures"
RESULTS_DIR = EVAL_DIR / "results"
EXPECTED_RED = EVAL_DIR / "expected-red.json"
INSTALLER = REPO_ROOT / "bin" / "mano-plan.js"

# Which flat fixture input files map to phase-scoped destinations. Story files
# and the specially named stories-README.md seed an existing current story set;
# progress.md seeds the build path's ledger; all other files remain
# project-level under _mano_output/.
PHASE_SCOPED = {"phase-brief.md", "progress.md"}

# A per-step snapshot exists to be diffed by assertions, not to archive blobs.
SNAPSHOT_BYTE_CAP = 512 * 1024

SESSION_MODES = ("fresh", "continue")


def install_mano(project: Path, keep_markers: bool = False) -> None:
    """Run the real installer non-interactively into `project`.

    keep_markers installs with provenance markers intact so rule-retirement
    probes can strip whole rules from the installed files; production installs
    (and ordinary eval runs) are marker-free.
    """
    cmd = ["node", str(INSTALLER), "install", "--yes"]
    if keep_markers:
        cmd.append("--keep-rule-markers")
    subprocess.run(
        cmd,
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
    )


def seed_fixture(project: Path, fixture: str, mode: str, phase: int | None) -> None:
    """Place fixture files into the temp project.

    mode "seed":     fixture files are existing project state → copied into
                     _mano_output/ (phase-scoped ones under phase-{N}/).
    mode "document": the fixture is a raw input document the skill will read →
                     copied to the project root as-is (e.g. a PRD for mano import).
    """
    src = FIXTURES_DIR / fixture
    files = sorted(path for path in src.rglob("*") if path.is_file())
    if mode == "document":
        for f in files:
            relative = f.relative_to(src)
            dest = project / relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(f, dest)
        return

    out = project / "_mano_output"
    phase_dir = out / f"phase-{phase}" if phase is not None else out
    phase_dir.mkdir(parents=True, exist_ok=True)
    for f in files:
        relative = f.relative_to(src)
        if relative.parts[0] == "project":
            # `project/` is an explicit fixture escape from planning output for
            # brownfield checks that need a tiny existing source/declaration
            # surface. The prefix itself is not copied.
            dest = project.joinpath(*relative.parts[1:])
        elif relative.parts[0] == "hooks":
            # `hooks/` seeds custom active hook files (e.g. a legacy-shaped
            # hook) into the installed _mano/hooks/ directory. Use
            # `active_hook` instead when the shipped example is the fixture.
            dest = project.joinpath("_mano", "hooks", *relative.parts[1:])
        elif relative.parent != Path("."):
            # Nested fixture paths model existing multi-phase output verbatim,
            # e.g. phase-1/design-preview.html while phase-2 is active.
            dest = out / relative
        elif phase is not None and f.name == "stories-README.md":
            dest = phase_dir / "stories" / "README.md"
        elif phase is not None and f.name.startswith("story-") and f.suffix == ".md":
            dest = phase_dir / "stories" / f.name
        else:
            dest = (phase_dir if f.name in PHASE_SCOPED else out) / f.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(f, dest)


def activate_hook(project: Path, skill: str) -> None:
    """Activate one installed example hook for a hook-flow case."""
    if not skill.replace("-", "").isalnum():
        raise ValueError(f"invalid active_hook value {skill!r}")
    hooks = project / "_mano" / "hooks"
    example = hooks / f"post-{skill}.example.md"
    active = hooks / f"post-{skill}.md"
    if not example.is_file():
        raise FileNotFoundError(f"hook example not found: {example}")
    shutil.copyfile(example, active)


def case_steps(case: dict) -> list[dict]:
    """The case's ordered steps — one synthesised step for a single-prompt case.

    A case has `prompt` **or** `steps`, never both: two ways to say the same
    thing is how a case silently runs something other than what it reads like.
    """
    name = case.get("name", "<unnamed>")
    has_prompt = "prompt" in case
    has_steps = "steps" in case
    if has_prompt and has_steps:
        raise ValueError(f"case {name!r} sets both 'prompt' and 'steps'; use one")
    if not has_prompt and not has_steps:
        raise ValueError(f"case {name!r} has neither 'prompt' nor 'steps'")
    if has_prompt:
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            raise ValueError(f"case {name!r} has an empty 'prompt'")
        return [{"prompt": case["prompt"], "session": "fresh"}]

    steps = case["steps"]
    if not isinstance(steps, list) or not steps:
        raise ValueError(f"case {name!r} has an empty 'steps' list")
    resolved = []
    for i, step in enumerate(steps, 1):
        if not isinstance(step, dict) or not isinstance(step.get("prompt"), str) \
                or not step["prompt"].strip():
            raise ValueError(f"case {name!r} step {i} has no non-empty 'prompt' string")
        session = step.get("session", "fresh")
        if session not in SESSION_MODES:
            raise ValueError(
                f"case {name!r} step {i} has session {session!r}; "
                f"use one of {', '.join(SESSION_MODES)}"
            )
        if i == 1 and session == "continue":
            raise ValueError(f"case {name!r} step 1 cannot continue — there is no prior session")
        resolved.append({"prompt": step["prompt"], "session": session})
    return resolved


def snapshot_output(project: Path) -> dict[str, str]:
    """Every text file under `_mano_output/`, keyed by its relative path."""
    out = project / "_mano_output"
    if not out.is_dir():
        return {}
    snapshot = {}
    for path in sorted(out.rglob("*")):
        if not path.is_file() or path.stat().st_size > SNAPSHOT_BYTE_CAP:
            continue
        try:
            snapshot[path.relative_to(out).as_posix()] = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return snapshot


def snapshot_sources(project: Path) -> tuple[str, ...]:
    """Everything outside Mano's own directories, as project-relative paths."""
    skip = {"_mano", "_mano_output", ".git", "node_modules"}
    found = []
    for path in project.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(project)
        if rel.parts[0] in skip or rel.name in {"AGENTS.md", "CLAUDE.md", ".cursorrules"}:
            continue
        found.append(rel.as_posix())
    return tuple(sorted(found))


def run_steps(
    project: Path,
    steps: list[dict],
    runner_name: str,
    timeout: int,
    env: dict[str, str] | None,
    model: str | None,
    phase: int | None,
) -> tuple[list[A.Step], str]:
    """Run each step in order in the one retained project.

    A step that fails stops the chain: the later steps of a scenario are
    meaningless once an earlier one did not run, and continuing spends real
    tokens to produce noise. Every step that *did* run is returned with its
    cost, failures included.

    Returns the steps plus the last invocation's raw stdout. Raw stdout stays
    out of `Step` on purpose: assertions read files and the final assistant
    message, never tool traces. It exists here only as a diagnostic to print
    when a run produced no final message at all.
    """
    runner = RUNNERS[runner_name]
    outcomes: list[A.Step] = []
    last_stdout = ""
    for i, step in enumerate(steps, 1):
        prompt, session = step["prompt"], step["session"]
        label = f"  [step {i}/{len(steps)}] {session}: {prompt.splitlines()[0][:80]}"
        if len(steps) > 1:
            print(label)
        if session == "continue" and not supports_continue(runner):
            print(
                f"  ✗  step {i} asked to continue the previous session, but the "
                f"{runner_name!r} runner cannot resume one. Rewrite the step as "
                "`fresh` or add continuation support to the runner."
            )
            outcomes.append(A.Step(
                index=i,
                prompt=prompt,
                session=session,
                returncode=None,
                passed=False,
                error=f"runner {runner_name!r} cannot continue a session",
                output_snapshot=snapshot_output(project),
                source_files=snapshot_sources(project),
                phase=phase,
            ))
            break

        started = time.monotonic()
        result = runner(str(project), prompt, timeout, env, model=model, session=session)
        wall_ms = int((time.monotonic() - started) * 1000)
        failed = result.returncode != 0
        if failed:
            print(f"  runner exited {result.returncode} on step {i}")
            if result.stderr.strip():
                print("  stderr:", result.stderr.strip().splitlines()[-1])
        outcomes.append(A.Step(
            index=i,
            prompt=prompt,
            session=session,
            returncode=result.returncode,
            passed=not failed,
            error=None if not failed else f"runner exited {result.returncode}",
            final_response=result.final_response,
            usage=result.usage,
            resolved_model=result.resolved_model,
            runner_version=result.runner_version,
            wall_ms=wall_ms,
            output_snapshot=snapshot_output(project),
            source_files=snapshot_sources(project),
            phase=phase,
        ))
        last_stdout = result.stdout
        if failed:
            break
    return outcomes, last_stdout


class CaseOutcome:
    """One measured run of one case: verdict, per-step cost, assertion tally."""

    def __init__(self, name: str, case: dict, steps: list[A.Step]):
        self.name = name
        self.case = case
        self.steps = steps
        self.passed = False
        self.assertions_passed = 0
        self.assertions_failed = 0
        self.notes: list[str] = []
        self.attempt = 1

    @property
    def resolved_model(self) -> str | None:
        return next((s.resolved_model for s in reversed(self.steps) if s.resolved_model), None)

    @property
    def runner_version(self) -> str | None:
        return next((s.runner_version for s in reversed(self.steps) if s.runner_version), None)

    def total_tokens(self) -> int | None:
        measured = [
            step.usage.total_tokens()
            for step in self.steps
            if step.usage is not None and step.usage.total_tokens() is not None
        ]
        return sum(measured) if measured else None


def run_case(
    case_path: Path,
    runner_name: str,
    keep: bool,
    timeout: int,
    without_rules: set[str],
    model: str | None = None,
) -> CaseOutcome:
    case = json.loads(case_path.read_text())
    name = case["name"]
    phase = case.get("phase")  # None for non-phase-scoped skills (import)
    mode = case.get("fixture_mode", "seed")
    steps = case_steps(case)
    fixture_dir = FIXTURES_DIR / case["fixture"]
    fixture_snapshot = {
        path.relative_to(fixture_dir).as_posix(): path.read_text(encoding="utf-8")
        for path in fixture_dir.rglob("*")
        if path.is_file()
    }
    removed_note = f", without: {','.join(sorted(without_rules))}" if without_rules else ""
    print(f"\n=== case: {name} (runner: {runner_name}{removed_note}) ===")

    tmp = Path(tempfile.mkdtemp(prefix=f"mano-eval-{name}-"))
    try:
        # A probe needs markers present to strip whole rules; afterwards the
        # remaining markers are removed so the runner sees a production-shaped
        # install either way.
        install_mano(tmp, keep_markers=bool(without_rules))
        if without_rules:
            removed = P.strip_rules(tmp, without_rules)
            missing = [rule_id for rule_id, count in removed.items() if count == 0]
            if missing:
                print(f"  could not remove installed rule(s): {', '.join(missing)}")
                outcome = CaseOutcome(name, case, [])
                outcome.notes.append(f"could not remove installed rule(s): {', '.join(missing)}")
                return outcome
            for rule_id, count in sorted(removed.items()):
                print(f"  -  stripped {rule_id} ({count} occurrence{'s' if count != 1 else ''})")
            P.strip_markers(tmp)
        if case.get("active_hook"):
            activate_hook(tmp, case["active_hook"])
        seed_fixture(tmp, case["fixture"], mode, phase)
        # What `_mano_output/` looked like before any step ran, so an assertion
        # can attribute a change to the step that made it.
        baseline = snapshot_output(tmp)

        # A case may pin the run mode; the temp project has no git config to
        # read it from, so it travels as the documented MANO_MODE override.
        env = {"MANO_MODE": case["run_mode"]} if case.get("run_mode") else None
        step_outcomes, last_stdout = run_steps(tmp, steps, runner_name, timeout, env, model, phase)
        outcome = CaseOutcome(name, case, step_outcomes)

        runner_failed = any(not step.passed for step in step_outcomes) or not step_outcomes
        for step in step_outcomes:
            if step.error:
                outcome.notes.append(f"step {step.index}: {step.error}")
        mutated_fixtures = [
            fname
            for fname, original in fixture_snapshot.items()
            if not (fixture_dir / fname).is_file()
            or (fixture_dir / fname).read_text(encoding="utf-8") != original
        ]
        isolation_failed = bool(mutated_fixtures)
        if isolation_failed:
            print(
                "  runner escaped the temp project and changed eval fixture(s): "
                + ", ".join(mutated_fixtures)
            )
            outcome.notes.append("fixture isolation failed: " + ", ".join(mutated_fixtures))

        final_response = step_outcomes[-1].final_response if step_outcomes else ""
        ctx = A.Ctx(
            tmp / "_mano_output",
            phase,
            fixture_snapshot,
            final_response,
            steps=step_outcomes,
            baseline=baseline,
        )

        all_failures: list[A.Failure] = []
        for aname in case["assertions"]:
            fn = A.REGISTRY.get(aname)
            if fn is None:
                print(f"  ?  {aname}: UNKNOWN ASSERTION")
                all_failures.append(A.Failure(aname, "unknown assertion name"))
                continue
            failures = fn(ctx)
            if failures:
                print(f"  ✗  {aname}")
                for f in failures:
                    print(f"       {f.detail}")
                all_failures.extend(failures)
            else:
                print(f"  ✓  {aname}")

        if all_failures and not final_response and last_stdout.strip():
            last_event = last_stdout.strip().splitlines()[-1]
            print(f"  runner emitted no final assistant message; last event: {last_event[:500]}")

        failed_names = {f.assertion for f in all_failures}
        outcome.assertions_failed = len(failed_names)
        outcome.assertions_passed = len(case["assertions"]) - len(failed_names)
        outcome.passed = not runner_failed and not isolation_failed and not all_failures
        runner_note = "; runner step failed" if runner_failed else ""
        isolation_note = "; fixture isolation failed" if isolation_failed else ""
        print(f"  → {'PASS' if outcome.passed else 'FAIL'} "
              f"({outcome.assertions_passed}"
              f"/{len(case['assertions'])} assertions{runner_note}{isolation_note})")
        total = outcome.total_tokens()
        print("  tokens: " + (f"{total:,}" if total is not None else "unavailable (runner reports none)"))
        if keep:
            print(f"  (kept temp project: {tmp})")
        return outcome
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


# --- manifest -----------------------------------------------------------------

def git_revision() -> tuple[str | None, bool | None]:
    """(short commit, dirty) for the repo under test, or (None, None)."""
    def git(*args: str) -> str | None:
        try:
            proc = subprocess.run(
                ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True, timeout=30
            )
        except (OSError, subprocess.SubprocessError):
            return None
        return proc.stdout.strip() if proc.returncode == 0 else None

    commit = git("rev-parse", "--short", "HEAD")
    if commit is None:
        return None, None
    status = git("status", "--porcelain")
    return commit, bool(status) if status is not None else None


def manifest_record(
    outcome: CaseOutcome,
    runner_name: str,
    requested_model: str | None,
    commit: str | None,
    dirty: bool | None,
    without_rules: set[str],
) -> dict:
    """One JSON record for one measured run. Unavailable metrics stay null."""
    return {
        "commit": commit,
        "dirty": dirty,
        "runner": runner_name,
        "runner_version": outcome.runner_version,
        "requested_model": requested_model,
        "resolved_model": outcome.resolved_model,
        "fixture": outcome.case.get("fixture"),
        "case": outcome.name,
        "attempt": outcome.attempt,
        "without_rules": sorted(without_rules) or None,
        "steps": [
            {
                "prompt": step.prompt,
                "session": step.session,
                "usage": step.usage.as_record() if step.usage is not None else None,
                "wall_ms": step.wall_ms,
                "passed": step.passed,
                "error": step.error,
            }
            for step in outcome.steps
        ],
        "assertions": {
            "passed": outcome.assertions_passed,
            "failed": outcome.assertions_failed,
        },
        "notes": outcome.notes or None,
        "passed": outcome.passed,
        "total_tokens": outcome.total_tokens(),
    }


def write_manifest(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")


# --- expected-red allowlist ---------------------------------------------------

def load_expected_red(path: Path = EXPECTED_RED) -> dict[str, dict]:
    """Cases written before their fix: they must fail now and pass only later.

    Each entry is excluded from the green baseline. An entry that *passes* is
    itself a failure — the allowlist is stale and the case has to be promoted.
    """
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    cases = data.get("cases", {})
    if not isinstance(cases, dict):
        raise ValueError(f"{path}: 'cases' must be an object keyed by case name")
    for name, entry in cases.items():
        if not isinstance(entry, dict) or not str(entry.get("reason", "")).strip():
            raise ValueError(f"{path}: case {name!r} needs a non-empty 'reason'")
        if not str(entry.get("fixed_by", "")).strip():
            raise ValueError(f"{path}: case {name!r} needs a 'fixed_by' naming the owning fix")
    return cases


def verdict(name: str, passed: bool, expected_red: dict[str, dict]) -> tuple[str, bool]:
    """(label, counts_as_failure) for the summary table.

    An allowlisted case is red on purpose and does not break the baseline.
    An allowlisted case that passes does: its fix landed and the entry is stale.
    """
    if name not in expected_red:
        return ("PASS" if passed else "FAIL"), (not passed)
    if passed:
        return "RED-PASSED", True
    return "RED (expected)", False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner", default="claude", choices=list(RUNNERS))
    ap.add_argument("--case", help="run a single case by name")
    ap.add_argument(
        "--model",
        help="model passed through to the runner; the resolved model is recorded",
    )
    ap.add_argument(
        "--without-rule",
        action="append",
        default=[],
        metavar="RULE_ID",
        help="low-level: remove a tagged rule from temp installs (repeatable)",
    )
    ap.add_argument(
        "--probe-rule",
        metavar="RULE_ID",
        help="run every eval mapped to one rule with all its occurrences removed",
    )
    ap.add_argument(
        "--list-rules",
        action="store_true",
        help="list incident-tagged rules and their mapped eval cases, then exit",
    )
    ap.add_argument(
        "--rerun-failures",
        action="store_true",
        help="re-run each failing case once to separate a deterministic failure from a flake",
    )
    ap.add_argument(
        "--baseline",
        action="store_true",
        help="record a committable baseline: names the manifest baseline-<commit>-<stamp>.json "
             "and re-runs every failure once",
    )
    ap.add_argument(
        "--no-manifest",
        action="store_true",
        help="do not write eval/results/<timestamp>.json for this run",
    )
    ap.add_argument("--keep", action="store_true", help="keep temp projects")
    ap.add_argument("--timeout", type=int, default=600, help="per-step CLI timeout (s)")
    args = ap.parse_args()

    if not INSTALLER.is_file():
        print(f"installer not found at {INSTALLER}", file=sys.stderr)
        return 2

    try:
        rules = P.discover_rules(REPO_ROOT)
    except P.ProvenanceError as exc:
        print(f"invalid rule provenance: {exc}", file=sys.stderr)
        return 2

    if args.list_rules:
        print(P.format_rule_table(REPO_ROOT, rules))
        return 0

    if args.probe_rule and (args.case or args.without_rule):
        print(
            "--probe-rule cannot be combined with --case or --without-rule",
            file=sys.stderr,
        )
        return 2

    try:
        expected_red = load_expected_red(EXPECTED_RED)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"invalid expected-red allowlist: {exc}", file=sys.stderr)
        return 2

    without_rules = set(args.without_rule)
    if args.probe_rule:
        without_rules.add(args.probe_rule)
    unknown_rules = sorted(without_rules - set(rules))
    if unknown_rules:
        print(f"unknown rule id(s): {', '.join(unknown_rules)}", file=sys.stderr)
        print("run with --list-rules to see valid ids", file=sys.stderr)
        return 2
    if without_rules and not args.probe_rule:
        print(
            "=== partial/debug removal run — not complete retirement evidence ==="
        )
    if without_rules:
        # A probe deliberately removes behaviour, so "expected red" says nothing
        # about it. Judge a probe on its own mapped cases only.
        expected_red = {}

    all_cases = {path.stem: path for path in sorted(CASES_DIR.glob("*.json"))}
    unknown_red = sorted(set(expected_red) - set(all_cases))
    if unknown_red:
        print(
            f"expected-red names case(s) that do not exist: {', '.join(unknown_red)}",
            file=sys.stderr,
        )
        return 2

    if args.probe_rule:
        mapped = rules[args.probe_rule].evals
        if "pending" in mapped:
            print(
                f"rule {args.probe_rule!r} still has eval=pending; "
                "capture every surface before treating a removal run as retirement evidence",
                file=sys.stderr,
            )
            return 2
        cases = [all_cases[name] for name in mapped]
        print(
            f"=== retirement probe: {args.probe_rule} "
            f"({len(cases)} mapped cases, runner: {args.runner}) ==="
        )
    elif args.case:
        cases = [path for name, path in all_cases.items() if name == args.case]
        if not cases:
            print(f"no case named {args.case!r}", file=sys.stderr)
            return 2
    else:
        cases = list(all_cases.values())

    commit, dirty = git_revision()
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    # Only a baseline is committed; ad-hoc manifests are ignored by Git.
    name = f"baseline-{commit or 'unknown'}-{stamp}" if args.baseline else stamp
    manifest_path = RESULTS_DIR / f"{name}.json"
    records: list[dict] = []
    if args.baseline and dirty:
        print(
            "⚠ working tree is dirty — a baseline recorded here does not describe "
            "any commit anyone else can check out."
        )

    def record(outcome: CaseOutcome) -> None:
        records.append(
            manifest_record(outcome, args.runner, args.model, commit, dirty, without_rules)
        )
        if not args.no_manifest:
            write_manifest(manifest_path, records)

    results: dict[str, CaseOutcome] = {}
    for path in cases:
        outcome = run_case(path, args.runner, args.keep, args.timeout, without_rules, args.model)
        record(outcome)
        results[path.stem] = outcome

    if args.rerun_failures or args.baseline:
        reruns = [p for p in cases if not results[p.stem].passed]
        if reruns:
            print(
                f"\n=== re-running {len(reruns)} failure(s) once "
                "— a failure that repeats is deterministic, one that clears is a flake ==="
            )
        for path in reruns:
            second = run_case(path, args.runner, args.keep, args.timeout, without_rules, args.model)
            second.attempt = 2
            record(second)
            results[path.stem].rerun = second

    print("\n=== summary ===")
    failures = 0
    for n, outcome in results.items():
        label, counts = verdict(n, outcome.passed, expected_red)
        rerun = getattr(outcome, "rerun", None)
        suffix = ""
        if rerun is not None:
            suffix = "  (re-run: passed — flake)" if rerun.passed else "  (re-run: failed — deterministic)"
        print(f"  {label:<14}  {n}{suffix}")
        if counts:
            failures += 1
    if expected_red:
        print(f"  ({len(expected_red)} case(s) on the expected-red allowlist)")
    if not args.no_manifest:
        try:
            shown = manifest_path.relative_to(REPO_ROOT)
        except ValueError:
            shown = manifest_path
        print(f"\nmanifest: {shown}")

    passed = failures == 0
    if args.probe_rule:
        if passed:
            print(
                "\nAll mapped cases passed without the rule. Repeat on every target "
                "model tier before considering deletion."
            )
        else:
            print(
                "\nAt least one mapped case failed without the rule; "
                "the patch re-earned its place on this runner."
            )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
