#!/usr/bin/env python3
"""Mano eval harness — minimal proof.

For each case:
  1. Install Mano into a throwaway temp project via the real installer
     (guarantees the fixture matches a true install — no drift).
  2. Copy the case's fixture input files into _mano_output/ (and phase-N/).
  3. Invoke the chosen CLI headless with the case prompt (e.g. "mano stories").
  4. Run the case's assertions over artifacts and any chat-native final response.
  5. Report a pass/fail table.

Usage:
  python3 eval/run.py                       # all cases, claude runner
  python3 eval/run.py --runner opencode     # pick a different CLI
  python3 eval/run.py --case stories-bugfix # one case
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
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import assertions as A  # noqa: E402
import provenance as P  # noqa: E402
from runners import RUNNERS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "eval"
CASES_DIR = EVAL_DIR / "cases"
FIXTURES_DIR = EVAL_DIR / "fixtures"
INSTALLER = REPO_ROOT / "bin" / "mano-plan.js"

# Which flat fixture input files map to phase-scoped destinations. Story files
# and the specially named stories-README.md seed an existing current story set;
# all other files remain project-level under _mano_output/.
PHASE_SCOPED = {"phase-brief.md"}


def install_mano(project: Path) -> None:
    """Run the real installer non-interactively into `project`."""
    subprocess.run(
        ["node", str(INSTALLER), "install", "--yes"],
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
    if mode == "document":
        for f in src.iterdir():
            if f.is_file():
                shutil.copyfile(f, project / f.name)
        return

    out = project / "_mano_output"
    phase_dir = out / f"phase-{phase}" if phase is not None else out
    phase_dir.mkdir(parents=True, exist_ok=True)
    for f in src.iterdir():
        if not f.is_file():
            continue
        if phase is not None and f.name == "stories-README.md":
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


def run_case(
    case_path: Path,
    runner_name: str,
    keep: bool,
    timeout: int,
    without_rules: set[str],
) -> bool:
    case = json.loads(case_path.read_text())
    name = case["name"]
    phase = case.get("phase")  # None for non-phase-scoped skills (import)
    mode = case.get("fixture_mode", "seed")
    fixture_dir = FIXTURES_DIR / case["fixture"]
    fixture_snapshot = {
        path.name: path.read_text(encoding="utf-8")
        for path in fixture_dir.iterdir()
        if path.is_file()
    }
    removed_note = f", without: {','.join(sorted(without_rules))}" if without_rules else ""
    print(f"\n=== case: {name} (runner: {runner_name}{removed_note}) ===")

    tmp = Path(tempfile.mkdtemp(prefix=f"mano-eval-{name}-"))
    try:
        install_mano(tmp)
        if without_rules:
            removed = P.strip_rules(tmp, without_rules)
            missing = [rule_id for rule_id, count in removed.items() if count == 0]
            if missing:
                print(f"  could not remove installed rule(s): {', '.join(missing)}")
                return False
            for rule_id, count in sorted(removed.items()):
                print(f"  -  stripped {rule_id} ({count} occurrence{'s' if count != 1 else ''})")
        if case.get("active_hook"):
            activate_hook(tmp, case["active_hook"])
        seed_fixture(tmp, case["fixture"], mode, phase)

        runner = RUNNERS[runner_name]
        result = runner(str(tmp), case["prompt"], timeout)
        runner_failed = result.returncode != 0
        if runner_failed:
            print(f"  runner exited {result.returncode}")
            if result.stderr.strip():
                print("  stderr:", result.stderr.strip().splitlines()[-1])
        mutated_fixtures = [
            name
            for name, original in fixture_snapshot.items()
            if not (fixture_dir / name).is_file()
            or (fixture_dir / name).read_text(encoding="utf-8") != original
        ]
        isolation_failed = bool(mutated_fixtures)
        if isolation_failed:
            print(
                "  runner escaped the temp project and changed eval fixture(s): "
                + ", ".join(mutated_fixtures)
            )

        ctx = A.Ctx(
            tmp / "_mano_output",
            phase,
            fixture_snapshot,
            result.final_response,
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

        if all_failures and not result.final_response and result.stdout.strip():
            last_event = result.stdout.strip().splitlines()[-1]
            print(f"  runner emitted no final assistant message; last event: {last_event[:500]}")

        passed = not runner_failed and not isolation_failed and not all_failures
        runner_note = f"; runner exited {result.returncode}" if runner_failed else ""
        isolation_note = "; fixture isolation failed" if isolation_failed else ""
        print(f"  → {'PASS' if passed else 'FAIL'} "
              f"({len(case['assertions']) - len({f.assertion for f in all_failures})}"
              f"/{len(case['assertions'])} assertions{runner_note}{isolation_note})")
        if keep:
            print(f"  (kept temp project: {tmp})")
        return passed
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runner", default="claude", choices=list(RUNNERS))
    ap.add_argument("--case", help="run a single case by name")
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
    ap.add_argument("--keep", action="store_true", help="keep temp projects")
    ap.add_argument("--timeout", type=int, default=600, help="per-case CLI timeout (s)")
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

    all_cases = {path.stem: path for path in sorted(CASES_DIR.glob("*.json"))}
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

    results = {
        c.stem: run_case(c, args.runner, args.keep, args.timeout, without_rules)
        for c in cases
    }

    print("\n=== summary ===")
    for n, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    passed = all(results.values())
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
