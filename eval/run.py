#!/usr/bin/env python3
"""Mano eval harness — minimal proof.

For each case:
  1. Install Mano into a throwaway temp project via the real installer
     (guarantees the fixture matches a true install — no drift).
  2. Copy the case's fixture input files into _mano_output/ (and phase-N/).
  3. Invoke the chosen CLI headless with the case prompt (e.g. "mano stories").
  4. Run the case's assertions over the files the skill wrote.
  5. Report a pass/fail table.

Usage:
  python3 eval/run.py                       # all cases, claude runner
  python3 eval/run.py --runner opencode     # pick a different CLI
  python3 eval/run.py --case stories-bugfix # one case
  python3 eval/run.py --keep                # keep temp dirs for inspection

No Anthropic API key needed — it drives whichever CLI you already use.
The harness asserts on output files, so it is model- and runner-agnostic.
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
from runners import RUNNERS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_DIR = REPO_ROOT / "eval"
CASES_DIR = EVAL_DIR / "cases"
FIXTURES_DIR = EVAL_DIR / "fixtures"
INSTALLER = REPO_ROOT / "bin" / "mano-plan.js"

# Which fixture input files map to which destination under _mano_output/.
# Phase-scoped files go under phase-{N}/, project-level files at the root.
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
        dest = (phase_dir if f.name in PHASE_SCOPED else out) / f.name
        shutil.copyfile(f, dest)


def run_case(case_path: Path, runner_name: str, keep: bool, timeout: int) -> bool:
    case = json.loads(case_path.read_text())
    name = case["name"]
    phase = case.get("phase")  # None for non-phase-scoped skills (import)
    mode = case.get("fixture_mode", "seed")
    print(f"\n=== case: {name} (runner: {runner_name}) ===")

    tmp = Path(tempfile.mkdtemp(prefix=f"mano-eval-{name}-"))
    try:
        install_mano(tmp)
        seed_fixture(tmp, case["fixture"], mode, phase)

        runner = RUNNERS[runner_name]
        result = runner(str(tmp), case["prompt"], timeout)
        if result.returncode != 0:
            print(f"  runner exited {result.returncode}")
            if result.stderr.strip():
                print("  stderr:", result.stderr.strip().splitlines()[-1])

        ctx = A.Ctx(tmp / "_mano_output", phase)

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

        passed = not all_failures
        print(f"  → {'PASS' if passed else 'FAIL'} "
              f"({len(case['assertions']) - len({f.assertion for f in all_failures})}"
              f"/{len(case['assertions'])} assertions)")
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
    ap.add_argument("--keep", action="store_true", help="keep temp projects")
    ap.add_argument("--timeout", type=int, default=600, help="per-case CLI timeout (s)")
    args = ap.parse_args()

    if not INSTALLER.is_file():
        print(f"installer not found at {INSTALLER}", file=sys.stderr)
        return 2

    cases = sorted(CASES_DIR.glob("*.json"))
    if args.case:
        cases = [c for c in cases if c.stem == args.case]
        if not cases:
            print(f"no case named {args.case!r}", file=sys.stderr)
            return 2

    results = {c.stem: run_case(c, args.runner, args.keep, args.timeout) for c in cases}

    print("\n=== summary ===")
    for n, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {n}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
