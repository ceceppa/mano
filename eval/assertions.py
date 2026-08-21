"""Property assertions over the artifacts and final response a skill produced.

Each assertion is a pure function: (ctx) -> list[Failure]. An empty list means
the assertion passed. ctx gives access to the output dir, seeded fixture
snapshot, final runner response, and convenience readers. Assertions never call
an LLM — they are deterministic text checks after the runner completes.

Assertions are referenced by name from a case file. Add a new check here and it
becomes available to every case.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Failure:
    assertion: str
    detail: str


def _phase_relative(name: str, phase: int | None) -> str:
    """Where an artifact lives under `_mano_output/`, phase-scoped ones included."""
    if phase is not None and name in {"phase-brief.md", "progress.md"}:
        return f"phase-{phase}/{name}"
    return name


def parse_progress_rows(text: str) -> list[tuple[str, str, str]]:
    """Ledger rows as (id, label, status), in file order."""
    rows = []
    for line in (text or "").split("\n"):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        while cells and cells[0] == "":
            cells.pop(0)
        while cells and cells[-1] == "":
            cells.pop()
        # The full row grammar `ledger.js` owns: S2, S2a, S2+1, S2.1, S2a+1.1,
        # E2a, E2a+1, plus R1 rework events.
        if len(cells) < 3 or not re.fullmatch(
            r"(?:[SE]\d+[a-z]*(?:\+\d+)?(?:\.\d+)?|R\d+)", cells[0]
        ):
            continue
        rows.append((cells[0], cells[1], cells[-1].lower()))
    return rows


def parse_row_contracts(text: str) -> dict[str, dict]:
    """`## Row Contracts` as {id: {"attributes": {...}, "text": str | None}}.

    Mirrors `ledger.js`: attributes live outside the fence and the fence holds
    the authored text and nothing else, so a correction whose first line reads
    like `reason:` still round-trips.
    """
    out: dict[str, dict] = {}
    lines = (text or "").split("\n")
    try:
        start = next(i for i, l in enumerate(lines) if l.strip() == "## Row Contracts")
    except StopIteration:
        return out
    row_id = None
    attributes: dict[str, str] = {}
    body: list[str] | None = None
    fence = None
    buffer: list[str] = []

    def flush():
        nonlocal row_id, attributes, body
        if row_id is not None:
            out[row_id] = {"attributes": attributes, "text": None if body is None else "\n".join(body)}
        row_id, attributes, body = None, {}, None

    for line in lines[start + 1:]:
        if fence is not None:
            if line.strip() == fence:
                body = list(buffer)
                fence, buffer = None, []
            else:
                buffer.append(line)
            continue
        if re.match(r"^##\s+(?!#)", line):
            break
        heading = re.match(r"^###\s+(\S+)\s*$", line)
        if heading:
            flush()
            row_id = heading.group(1)
            continue
        if row_id is None:
            continue
        opening = re.match(r"^(`{3,})text\s*$", line.strip())
        if opening:
            fence, buffer = opening.group(1), []
            continue
        attribute = re.match(r"^([a-z][a-z0-9-]*):\s?(.*)$", line)
        if attribute and body is None:
            attributes[attribute.group(1)] = attribute.group(2)
    flush()
    return out


@dataclass
class Step:
    """One prompt of an ordered multi-step case, and the state it left behind.

    A step carries both what the runner said and a snapshot of `_mano_output/`
    taken immediately after it, so an assertion can compare across the session
    boundary — "the row was `doing` after step 1 and `done` after step 2" — not
    only inspect the final state.

    `usage` is a `runners.Usage` or `None`. A step that failed still carries its
    usage: a failed run is real spend and belongs in the manifest.
    """

    index: int
    prompt: str
    session: str = "fresh"
    returncode: int | None = None
    passed: bool = False
    error: str | None = None
    final_response: str = ""
    usage: object | None = None
    resolved_model: str | None = None
    runner_version: str | None = None
    wall_ms: int | None = None
    output_snapshot: dict[str, str] = field(default_factory=dict)
    source_files: tuple[str, ...] = ()
    phase: int | None = None

    def output_files(self) -> set[str]:
        return set(self.output_snapshot)

    def artifact_text(self, name: str) -> str | None:
        """An artifact's text as it stood right after this step, or None."""
        return self.output_snapshot.get(_phase_relative(name, self.phase))

    def progress_rows(self) -> list[tuple[str, str, str]]:
        return parse_progress_rows(self.artifact_text("progress.md") or "")


class Ctx:
    """Read-only view of what a skill produced, plus the inputs it ran against.

    `phase` is only meaningful for phase-scoped skills (stories). Import-style
    skills that produce project-level artifacts (the backlog) pass phase=None.

    `steps` is empty for a single-`prompt` case and holds one `Step` per step,
    in order, for a multi-step case. `transcript` is always the *last* step's
    final assistant message, so every existing single-prompt assertion reads
    exactly as before.
    """

    def __init__(
        self,
        output_dir: Path,
        phase: int | None = None,
        fixture_snapshot: dict[str, str] | None = None,
        transcript: str = "",
        steps: "tuple[Step, ...] | list[Step]" = (),
        baseline: dict[str, str] | None = None,
    ):
        self.output_dir = output_dir
        self.phase = phase
        self.fixture_snapshot = fixture_snapshot or {}
        self.transcript = transcript
        self.steps = tuple(steps)
        # `_mano_output/` as it stood after seeding and before any step ran.
        self.baseline = baseline or {}
        self.stories_dir = output_dir / f"phase-{phase}" / "stories" if phase is not None else None

    def snapshot_before(self, index: int) -> dict[str, str]:
        """`_mano_output/` as it stood just before 1-based step `index` ran."""
        if index <= 1:
            return self.baseline
        return self.steps[index - 2].output_snapshot

    def changed_in_step(self, index: int) -> set[str]:
        """Output paths this step created, edited, or deleted."""
        before = self.snapshot_before(index)
        after = self.step(index).output_snapshot
        return {
            name
            for name in set(before) | set(after)
            if before.get(name) != after.get(name)
        }

    def step(self, index: int) -> Step:
        """The 1-based step `index`. Raises IndexError when a case has no such step."""
        if not 1 <= index <= len(self.steps):
            raise IndexError(f"case has {len(self.steps)} steps; no step {index}")
        return self.steps[index - 1]

    def all_responses(self) -> str:
        """Every step's final assistant message, joined.

        Use this for a canary check that must hold across the whole case;
        `transcript` alone only covers the last step.
        """
        if not self.steps:
            return self.transcript
        return "\n".join(s.final_response for s in self.steps if s.final_response)

    def story_files(self) -> list[Path]:
        if self.stories_dir is None or not self.stories_dir.is_dir():
            return []
        return sorted(p for p in self.stories_dir.glob("story-*.md"))

    def story_texts(self) -> dict[str, str]:
        return {p.name: p.read_text(encoding="utf-8") for p in self.story_files()}

    def readme(self) -> str | None:
        if self.stories_dir is None:
            return None
        r = self.stories_dir / "README.md"
        return r.read_text(encoding="utf-8") if r.is_file() else None

    def backlog(self) -> str | None:
        b = self.output_dir / "backlog.md"
        return b.read_text(encoding="utf-8") if b.is_file() else None

    def progress(self) -> str | None:
        """The build path's ledger for the active phase, or None."""
        if self.phase is None:
            return None
        path = self.output_dir / f"phase-{self.phase}" / "progress.md"
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def progress_rows(self) -> list[tuple[str, str, str]]:
        """Ledger rows as (id, label, status), in file order."""
        return parse_progress_rows(self.progress() or "")

    def project_root(self) -> Path:
        return self.output_dir.parent

    def source_files(self) -> set[str]:
        """Everything the run produced or kept outside Mano's own directories."""
        root = self.project_root()
        skip = {"_mano", "_mano_output", ".git", "node_modules"}
        found = set()
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(root)
            if rel.parts[0] in skip or rel.name in {"AGENTS.md", "CLAUDE.md", ".cursorrules"}:
                continue
            found.add(rel.as_posix())
        return found

    def phase_dirs(self) -> list[Path]:
        if not self.output_dir.is_dir():
            return []
        return sorted(p for p in self.output_dir.glob("phase-*") if p.is_dir())

    def fixture_text(self, name: str) -> str | None:
        return self.fixture_snapshot.get(name)

    def artifact_text(self, name: str) -> str | None:
        if self.phase is not None and name == "phase-brief.md":
            path = self.output_dir / f"phase-{self.phase}" / name
        else:
            path = self.output_dir / name
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def output_text(self, relative: str) -> str | None:
        """Any file under `_mano_output/`, addressed by its relative path."""
        path = self.output_dir / relative
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def source_text(self, relative: str) -> str | None:
        """Any file under the project root, addressed by its relative path."""
        path = self.project_root() / relative
        return path.read_text(encoding="utf-8") if path.is_file() else None

    def output_files(self) -> set[str]:
        if not self.output_dir.is_dir():
            return set()
        return {
            str(path.relative_to(self.output_dir))
            for path in self.output_dir.rglob("*")
            if path.is_file()
        }


# --- Structural / existence ---------------------------------------------------

def stories_were_written(ctx: Ctx) -> list[Failure]:
    if not ctx.story_files():
        return [Failure("stories_were_written", f"no story-*.md files in {ctx.stories_dir}")]
    return []


def readme_index_exists(ctx: Ctx) -> list[Failure]:
    if ctx.readme() is None:
        return [Failure("readme_index_exists", "stories/README.md missing")]
    return []


def filenames_have_slug(ctx: Ctx) -> list[Failure]:
    # story-N-slug.md or story-Nx-slug.md ; reject story-1.md and generic slugs.
    bad = []
    pat = re.compile(r"^story-\d+[a-z]?-[a-z0-9]+(-[a-z0-9]+)*\.md$")
    generic = {"untitled", "story", "task", "feature", "todo"}
    for p in ctx.story_files():
        if not pat.match(p.name):
            bad.append(p.name)
            continue
        slug = p.name[: -len(".md")].split("-", 2)[-1]
        words = slug.split("-")
        if slug in generic or not 2 <= len(words) <= 4:
            bad.append(p.name)
    if bad:
        return [Failure("filenames_have_slug", f"bad filenames: {bad}")]
    return []


# --- Format rules (the ones added this session) -------------------------------

def no_arrows_in_stories(ctx: Ctx) -> list[Failure]:
    fails = []
    for name, text in ctx.story_texts().items():
        if "→" in text:  # →
            lines = [ln.strip() for ln in text.splitlines() if "→" in ln]
            fails.append(Failure("no_arrows_in_stories", f"{name}: arrow in {lines[:2]}"))
    return fails


def no_phase_number_leak(ctx: Ctx) -> list[Failure]:
    # Story bodies should describe behaviour, not narrate phase history.
    # Flag "Phase N" mentions inside story files (the brief owns phase framing).
    fails = []
    pat = re.compile(r"\bPhase\s+\d+\b", re.IGNORECASE)
    for name, text in ctx.story_texts().items():
        hits = pat.findall(text)
        if hits:
            fails.append(Failure("no_phase_number_leak", f"{name}: {hits[:3]}"))
    return fails


def done_when_has_no_code_signature(ctx: Ctx) -> list[Failure]:
    # "Done when" criteria must be observable, not implementation tasks.
    # Heuristic: a Done-when bullet naming a function call / signature is a smell.
    fails = []
    sig = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\s*\([^)]*\)")
    for name, text in ctx.story_texts().items():
        section = _section(text, "Done when")
        if section is None:
            continue
        for ln in section.splitlines():
            if ln.strip().startswith("- ") and sig.search(ln):
                fails.append(Failure("done_when_has_no_code_signature", f"{name}: {ln.strip()[:80]}"))
    return fails


def has_out_of_scope(ctx: Ctx) -> list[Failure]:
    fails = []
    for name, text in ctx.story_texts().items():
        heading = "Not this story" if re.search(r"#+\s*Not this story", text, re.IGNORECASE) else "Out of scope"
        section = _section(text, heading)
        if section is None:
            fails.append(Failure("has_out_of_scope", f"{name}: no scope boundary section"))
            continue
        bullets = [ln.strip()[2:].strip() for ln in section.splitlines() if ln.strip().startswith("- ")]
        meaningful = [b for b in bullets if b and not b.startswith("[")]
        if not meaningful:
            fails.append(Failure("has_out_of_scope", f"{name}: scope boundary has no concrete item"))
    return fails


def has_implementation_reference(ctx: Ctx) -> list[Failure]:
    fails = []
    for name, text in ctx.story_texts().items():
        if "Implementation Reference" not in text:
            fails.append(Failure("has_implementation_reference", f"{name}: missing Implementation Reference"))
    return fails


# --- Behavioural / coverage ---------------------------------------------------

def tests_present_when_rules_require(ctx: Ctx) -> list[Failure]:
    # The fixture's project-rules.md defines a Testing Expectations section, so
    # at least one story should carry a "Test:" acceptance criterion.
    texts = ctx.story_texts()
    if any("Test:" in t for t in texts.values()):
        return []
    return [Failure("tests_present_when_rules_require",
                    "project rules require testing but no story has a 'Test:' AC")]


def phase_goal_quality_covered(ctx: Ctx) -> list[Failure]:
    # The phase goal embeds two qualities: order persistence + correct deletion.
    # At least one Done-when AC should mention persistence/restart, and one deletion.
    done_when = [_section(text, "Done when") or "" for text in ctx.story_texts().values()]
    blob = "\n".join(done_when).lower()
    fails = []
    if not re.search(r"reopen|restart|persist", blob):
        fails.append(Failure("phase_goal_quality_covered", "no story covers persistence/restart"))
    if "delet" not in blob:
        fails.append(Failure("phase_goal_quality_covered", "no story covers deletion"))
    return fails


def public_class_documentation_rule_covered(ctx: Ctx) -> list[Failure]:
    """The fixture introduces ReportFormatter while project rules require both
    source and Markdown documentation. Verify one owning story carries every
    normative detail as acceptance criteria plus narrow ownership pointers.
    """
    candidates = []
    for name, text in ctx.story_texts().items():
        done = _section(text, "Done when") or ""
        implementation = _section(text, "Implementation Reference") or ""
        if not re.search(r"\bReportFormatter\b", implementation):
            continue

        done_items = []
        for line in done.splitlines():
            match = re.match(r"^\s*-\s+(?:\[[ xX]\]\s*)?(.*\S)\s*$", line)
            if match:
                done_items.append(match.group(1))

        page_items = [
            item
            for item in done_items
            if (
                "docs/api/report-formatter.md" in item
                or re.search(
                    r"(?:ReportFormatter.{0,80}(?:page|API\s+reference)|"
                    r"(?:page|API\s+reference).{0,80}ReportFormatter)",
                    item,
                    re.IGNORECASE,
                )
            )
        ]
        page_text = "\n".join(page_items)

        source_items = [
            item
            for item in done_items
            if re.search(
                r"\b(?:source\s+documentation(?:\s+comment)?|"
                r"source\s+doc\s+comment|documentation\s+comment|"
                r"doc\s+comment|JSDoc)\b",
                item,
                re.IGNORECASE,
            )
        ]
        source_text = "\n".join(source_items)

        checks = {
            "source file ownership": "src/api/ReportFormatter.ts" in implementation,
            "Markdown file ownership": "docs/api/report-formatter.md" in implementation,
            "narrow Documentation rule reference": (
                "project-rules.md" in implementation
                and bool(re.search(r"\bDocumentation\b", implementation, re.IGNORECASE))
            ),
            "Markdown page Done-when criterion": bool(page_items),
            "Markdown page overview requirement": bool(re.search(
                r"\boverview\b", page_text, re.IGNORECASE
            )),
            "Markdown page minimal-example requirement": bool(re.search(
                r"\bminimal\s+(?:usage\s+)?example\b", page_text, re.IGNORECASE
            )),
            "Markdown page public-methods requirement": bool(re.search(
                r"\bpublic\s+methods?\b", page_text, re.IGNORECASE
            )),
            "source documentation Done-when criterion": bool(source_items) and bool(
                re.search(
                    r"\b(?:ReportFormatter|public\s+class|exported\s+class|class\s+declaration)\b",
                    source_text,
                    re.IGNORECASE,
                )
            ),
            "source documentation direct-placement requirement": bool(re.search(
                r"(?:source\s+documentation(?:\s+comment)?|source\s+doc\s+comment|"
                r"documentation\s+comment|doc\s+comment|JSDoc).{0,100}"
                r"\b(?:directly\s+|immediately\s+)?above\b"
                r"|\b(?:directly\s+|immediately\s+)?above\b.{0,100}"
                r"(?:source\s+documentation(?:\s+comment)?|source\s+doc\s+comment|"
                r"documentation\s+comment|doc\s+comment|JSDoc)",
                implementation,
                re.IGNORECASE | re.DOTALL,
            )),
            "source documentation one-line-purpose requirement": bool(re.search(
                r"\bone[- ]line\s+(?:purpose|description|summary)\b"
                r"|\b(?:purpose|description|summary).{0,30}\bone[- ]line\b",
                source_text,
                re.IGNORECASE,
            )),
        }

        not_this = _section(text, "Not this story") or ""
        if re.search(
            r"docs/api/report-formatter\.md"
            r"|ReportFormatter.{0,80}(?:documentation|API\s+reference)\s+page"
            r"|\b(?:Markdown\s+|API\s+(?:reference\s+)?)documentation\b"
            r"|\bdocumentation\s+pages?\b",
            not_this,
            re.IGNORECASE | re.DOTALL,
        ):
            checks["Markdown documentation is not deferred"] = False
        if re.search(
            r"ReportFormatter.{0,80}(?:source\s+documentation|source\s+doc\s+comment|"
            r"documentation\s+comment|doc\s+comment|JSDoc)"
            r"|(?:source\s+documentation|source\s+doc\s+comment|"
            r"documentation\s+comment|doc\s+comment|JSDoc).{0,80}ReportFormatter"
            r"|\bsource\s+documentation(?:\s+comments?)?\b"
            r"|\b(?:source\s+)?doc\s+comments?\b|\bJSDoc\b",
            not_this,
            re.IGNORECASE | re.DOTALL,
        ):
            checks["source documentation is not deferred"] = False

        missing = [label for label, present in checks.items() if not present]
        if not missing:
            return []
        candidates.append((name, missing))

    return [Failure(
        "public_class_documentation_rule_covered",
        "no ReportFormatter story fully owns project-rules.md §Documentation; "
        f"candidates: {candidates or 'none'}",
    )]


# --- mano dev: default vs explicit YOLO batch -------------------------------

DEV_YOLO_MODULES = {
    "src/yolo/base.js": ("stage", "base"),
    "src/yolo/feature.js": ("stage", "./base", "feature"),
    "src/yolo/release.js": ("stage", "./feature", "release"),
}


def _dev_story_statuses(readme: str) -> dict[str, str]:
    rows = {}
    for match in re.finditer(
        r"^\|\s*(\d+[a-z]*)\s*\|\s*[^|]+\|\s*[^|]+\|\s*([^|]+?)\s*\|\s*$",
        readme,
        re.MULTILINE | re.IGNORECASE,
    ):
        rows[match.group(1).lower()] = match.group(2).strip().lower()
    return rows


def _dev_fixture_inputs_unchanged(ctx: Ctx, assertion: str) -> list[Failure]:
    fails = []
    if ctx.phase is None or ctx.stories_dir is None:
        return [Failure(assertion, "dev fixture needs a phase-scoped stories directory")]

    destinations = {
        "phase-brief.md": ctx.output_dir / f"phase-{ctx.phase}" / "phase-brief.md",
        **{
            name: ctx.stories_dir / name
            for name in ctx.fixture_snapshot
            if name.startswith("story-") and name.endswith(".md")
        },
    }
    for fixture_name, path in destinations.items():
        expected = ctx.fixture_text(fixture_name)
        if expected is None:
            continue
        if not path.is_file():
            fails.append(Failure(assertion, f"planning input removed: {path.name}"))
        elif path.read_text(encoding="utf-8") != expected:
            fails.append(Failure(assertion, f"planning input modified: {path.name}"))
    return fails


def _dev_modules_match(
    ctx: Ctx,
    assertion: str,
    expected_paths: set[str],
) -> list[Failure]:
    fails = []
    root = ctx.output_dir.parent
    for relative, signals in DEV_YOLO_MODULES.items():
        path = root / relative
        should_exist = relative in expected_paths
        if should_exist and not path.is_file():
            fails.append(Failure(assertion, f"expected module missing: {relative}"))
            continue
        if not should_exist and path.exists():
            fails.append(Failure(assertion, f"later story output was written: {relative}"))
            continue
        if should_exist:
            text = path.read_text(encoding="utf-8")
            missing = [signal for signal in signals if signal not in text]
            if missing:
                fails.append(Failure(
                    assertion,
                    f"{relative} is missing contract signals: {missing}",
                ))
    return fails


def _dev_status_and_boundary_check(
    ctx: Ctx,
    assertion: str,
    expected_statuses: dict[str, str],
    expected_modules: set[str],
) -> list[Failure]:
    fails = []
    readme = ctx.readme()
    if readme is None:
        return [Failure(assertion, "stories/README.md missing")]

    actual_statuses = _dev_story_statuses(readme)
    if actual_statuses != expected_statuses:
        fails.append(Failure(
            assertion,
            f"expected statuses {expected_statuses}, got {actual_statuses}",
        ))

    seeded = ctx.fixture_text("stories-README.md")
    if seeded is not None:
        expected_readme = seeded
        for story, status in expected_statuses.items():
            expected_readme = re.sub(
                rf"^(\|\s*{re.escape(story)}\s*\|\s*[^|]+\|\s*[^|]+\|)"
                r"\s*[^|]+(\|\s*)$",
                rf"\1 {status} \2",
                expected_readme,
                flags=re.MULTILINE | re.IGNORECASE,
            )
        if readme != expected_readme:
            fails.append(Failure(
                assertion,
                "stories README changed beyond the expected status cells",
            ))

    fails.extend(_dev_modules_match(ctx, assertion, expected_modules))
    fails.extend(_dev_fixture_inputs_unchanged(ctx, assertion))

    if (ctx.output_dir / "reviews.md").exists():
        fails.append(Failure(assertion, "mano review was run automatically"))
    unexpected_phases = [
        path.name
        for path in ctx.phase_dirs()
        if path.name != f"phase-{ctx.phase}"
    ]
    if unexpected_phases:
        fails.append(Failure(
            assertion,
            f"implementation crossed the active phase boundary: {unexpected_phases}",
        ))
    return fails


def dev_yolo_completed_all_pending(ctx: Ctx) -> list[Failure]:
    return _dev_status_and_boundary_check(
        ctx,
        "dev_yolo_completed_all_pending",
        {"1": "done", "2": "done", "3": "done"},
        set(DEV_YOLO_MODULES),
    )


def dev_default_completed_only_next(ctx: Ctx) -> list[Failure]:
    return _dev_status_and_boundary_check(
        ctx,
        "dev_default_completed_only_next",
        {"1": "done", "2": "pending", "3": "pending"},
        {"src/yolo/base.js"},
    )


def dev_yolo_stopped_at_first_blocker(ctx: Ctx) -> list[Failure]:
    return _dev_status_and_boundary_check(
        ctx,
        "dev_yolo_stopped_at_first_blocker",
        {"1": "done", "2": "pending", "3": "pending"},
        {"src/yolo/base.js"},
    )


def dev_yolo_output_discipline(ctx: Ctx) -> list[Failure]:
    expected = "Stories 1, 2, 3 done — statuses updated in stories/README.md"
    if ctx.transcript.strip() != expected:
        return [Failure(
            "dev_yolo_output_discipline",
            f"expected the one-line aggregate response {expected!r}, got {ctx.transcript.strip()!r}",
        )]
    return []


def dev_yolo_interrupted_output_discipline(ctx: Ctx) -> list[Failure]:
    text = ctx.transcript.strip()
    missing = []
    if not text or len(text.splitlines()) != 1:
        missing.append("one-line response")
    checks = {
        "completed Story 1": bool(re.search(
            r"\bStor(?:y|ies)\s+1\b.{0,80}\bdone\b",
            text,
            re.IGNORECASE,
        )),
        "blocked/pending Story 2": bool(re.search(
            r"\bStory\s+2\b.{0,100}\b(?:blocked|pending|stopped|missing)\b"
            r"|\b(?:blocked|pending|stopped)\b.{0,100}\bStory\s+2\b",
            text,
            re.IGNORECASE,
        )),
        "owning mano spec route": bool(re.search(
            r"mano\s+spec|Feature\s+prefix|tech-spec",
            text,
            re.IGNORECASE,
        )),
    }
    missing.extend(label for label, present in checks.items() if not present)
    if missing:
        return [Failure(
            "dev_yolo_interrupted_output_discipline",
            f"interrupted YOLO response missing {missing}: {text!r}",
        )]
    return []


def dev_default_output_discipline(ctx: Ctx) -> list[Failure]:
    expected = (
        "Story 1 done — status updated in stories/README.md. "
        "Start a fresh session for the next story."
    )
    if ctx.transcript.strip() != expected:
        return [Failure(
            "dev_default_output_discipline",
            f"expected the one-line singular response {expected!r}, got {ctx.transcript.strip()!r}",
        )]
    return []


def dev_plain_words_order_gate(ctx: Ctx) -> list[Failure]:
    """A plain-words "build story 3" must still run the dev contract: with
    stories 1 and 2 pending, the contract's order gate (step 5) stops before
    code and names the story that would be skipped. Implementing story 3, or
    anything at all, proves the contract was not read."""
    assertion = "dev_plain_words_order_gate"
    fails = _dev_status_and_boundary_check(
        ctx,
        assertion,
        {"1": "pending", "2": "pending", "3": "pending"},
        set(),
    )
    text = ctx.transcript
    if not re.search(r"\b(?:story\s*)?1\b", text, re.IGNORECASE):
        compact = " ".join(text.strip().split())
        fails.append(Failure(
            assertion,
            f"response never names story 1 as the skipped earlier story: {compact[-300:]!r}",
        ))
    return fails


# --- mano import: backlog contract --------------------------------------------

def backlog_was_written(ctx: Ctx) -> list[Failure]:
    if ctx.backlog() is None:
        return [Failure("backlog_was_written", f"no backlog.md in {ctx.output_dir}")]
    return []


def backlog_has_items(ctx: Ctx) -> list[Failure]:
    bl = ctx.backlog() or ""
    # Item block format uses `### [title]` headings under `## Items`.
    items = re.findall(r"^###\s+\S", bl, re.MULTILINE)
    if len(items) < 2:
        return [Failure("backlog_has_items", f"expected multiple backlog items, found {len(items)}")]
    return []


def all_items_status_backlog(ctx: Ctx) -> list[Failure]:
    # import must leave every item Status: backlog — never in-phase-N or resolved.
    bl = ctx.backlog() or ""
    bad = re.findall(r"\*\*Status:\*\*\s*(in-phase-\d+|resolved)", bl, re.IGNORECASE)
    if bad:
        return [Failure("all_items_status_backlog", f"items not in 'backlog' status: {bad}")]
    statuses = re.findall(r"\*\*Status:\*\*\s*(\w[\w-]*)", bl)
    nonbacklog = [s for s in statuses if s.lower() != "backlog"]
    if nonbacklog:
        return [Failure("all_items_status_backlog", f"unexpected statuses: {nonbacklog}")]
    return []


def no_phase_brief_written(ctx: Ctx) -> list[Failure]:
    # import produces ONLY a backlog. A phase brief means it overstepped into start's job.
    for pd in ctx.phase_dirs():
        if (pd / "phase-brief.md").is_file():
            return [Failure("no_phase_brief_written",
                            f"import wrote a phase brief ({pd.name}/phase-brief.md) — that is mano start's job")]
    return []


def import_wrote_only_backlog(ctx: Ctx) -> list[Failure]:
    if not ctx.output_dir.is_dir():
        return [Failure("import_wrote_only_backlog", "_mano_output was not created")]
    files = {str(p.relative_to(ctx.output_dir)) for p in ctx.output_dir.rglob("*") if p.is_file()}
    if files != {"backlog.md"}:
        return [Failure("import_wrote_only_backlog",
                        f"import should leave only backlog.md, found {sorted(files)}")]
    return []


def backlog_covers_document_features(ctx: Ctx) -> list[Failure]:
    # The fixture PRD lists four features. Their key nouns should each surface
    # somewhere in the backlog (coverage, not exact wording).
    bl = (ctx.backlog() or "").lower()
    expected = {
        "add a book": r"add\b.*book|book.*add",
        "mark finished": r"finish|mark.*done|complete",
        "next-read suggestion": r"next.?read|suggest|what to read",
        "reading history": r"history|finished books",
    }
    fails = []
    for label, pat in expected.items():
        if not re.search(pat, bl):
            fails.append(Failure("backlog_covers_document_features", f"no item covers '{label}'"))
    return fails


def stated_tech_preference_preserved(ctx: Ctx) -> list[Failure]:
    # B1 pass-through is verbatim: the complete source sentence must survive,
    # not merely the technology noun.
    bl = ctx.backlog() or ""
    stated = "Use a local SQLite database; this is an offline-first app with no account system."
    if stated not in bl:
        return [Failure("stated_tech_preference_preserved",
                        "stated SQLite/offline/account directive was not preserved verbatim")]
    return []


# --- post-hook finding triage -------------------------------------------------

HOOK_TRIAGE_FILES = ("phase-brief.md", "tech-spec.md", "project-rules.md")


def hook_triage_no_approval_left_artifacts_unchanged(ctx: Ctx) -> list[Failure]:
    changed = []
    for name in HOOK_TRIAGE_FILES:
        if ctx.artifact_text(name) != ctx.fixture_text(name):
            changed.append(name)
    expected_files = {
        f"phase-{ctx.phase}/phase-brief.md",
        "tech-spec.md",
        "project-rules.md",
    }
    extras = ctx.output_files() - expected_files
    if extras:
        changed.extend(sorted(extras))
    if changed:
        return [
            Failure(
                "hook_triage_no_approval_left_artifacts_unchanged",
                f"hook findings were not approved, but output changed: {changed}",
            )
        ]
    return []


def _hook_triage_offer(
    ctx: Ctx,
    assertion: str,
    first_artifact: str,
    second_artifact: str,
    route_owner: str,
) -> list[Failure]:
    # This behavior lives in chat, so file assertions alone cannot distinguish a
    # correct triage offer from a runner that simply did nothing.
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    required = {
        "first numbered finding": rf"(?is)\b1\.\s*.{{0,120}}{re.escape(first_artifact)}",
        "second numbered finding": rf"(?is)\b2\.\s*.{{0,120}}{re.escape(second_artifact)}",
        "selection language": r"\b(?:apply|approve|address|reject|skip)\b",
        "cross-owner route": rf"(?:route.{{0,80}})?{re.escape(route_owner)}",
    }
    missing = [
        label
        for label, pattern in required.items()
        if not re.search(pattern, text, re.IGNORECASE)
    ]
    if not missing:
        return []
    compact = " ".join(text.strip().split())
    excerpt = compact[-600:]
    return [
        Failure(
            assertion,
            f"triage response missing {missing}; runner output began: {excerpt!r}",
        )
    ]


def hook_triage_offer_present(ctx: Ctx) -> list[Failure]:
    return _hook_triage_offer(
        ctx,
        "hook_triage_offer_present",
        "tech-spec.md",
        "project-rules.md",
        "mano rules",
    )


def start_hook_triage_offer_present(ctx: Ctx) -> list[Failure]:
    return _hook_triage_offer(
        ctx,
        "start_hook_triage_offer_present",
        "phase-brief.md",
        "tech-spec.md",
        "mano spec",
    )


def rules_hook_triage_offer_present(ctx: Ctx) -> list[Failure]:
    return _hook_triage_offer(
        ctx,
        "rules_hook_triage_offer_present",
        "project-rules.md",
        "tech-spec.md",
        "mano spec",
    )


def selected_hook_finding_applied_only_in_spec(ctx: Ctx) -> list[Failure]:
    spec = ctx.artifact_text("tech-spec.md") or ""
    original_spec = ctx.fixture_text("tech-spec.md") or ""
    failures = []
    if spec == original_spec:
        failures.append(
            Failure(
                "selected_hook_finding_applied_only_in_spec",
                "approved finding did not change tech-spec.md",
            )
        )
    if not re.search(
        r"\b(?:(?:8|eight)(?:-|\s+)(?:seconds?|secs?)|8\s*s)\b",
        spec,
        re.IGNORECASE,
    ):
        response = " ".join(ctx.transcript.strip().split())[-300:]
        failures.append(
            Failure(
                "selected_hook_finding_applied_only_in_spec",
                "tech-spec.md does not contain the approved 8-second retry cap; "
                f"final response: {response!r}",
            )
        )
    if not re.search(r"retry once\b.*\b1 second\b", spec, re.IGNORECASE):
        failures.append(
            Failure(
                "selected_hook_finding_applied_only_in_spec",
                "the narrow cap edit lost the existing retry-once/1-second policy",
            )
        )
    original_unrelated = [
        line
        for line in original_spec.splitlines()
        if not line.startswith("- Retry policy:")
    ]
    missing_lines = [line for line in original_unrelated if line not in spec.splitlines()]
    if missing_lines:
        failures.append(
            Failure(
                "selected_hook_finding_applied_only_in_spec",
                f"the selected edit removed unrelated spec lines: {missing_lines}",
            )
        )
    for name in ("phase-brief.md", "project-rules.md"):
        if ctx.artifact_text(name) != ctx.fixture_text(name):
            failures.append(
                Failure(
                    "selected_hook_finding_applied_only_in_spec",
                    f"unselected/out-of-lane artifact changed: {name}",
                )
            )
    blob = "\n".join(ctx.artifact_text(name) or "" for name in HOOK_TRIAGE_FILES)
    if re.search(r"all services must use exponential backoff", blob, re.IGNORECASE):
        failures.append(
            Failure(
                "selected_hook_finding_applied_only_in_spec",
                "the unselected project-rules finding was applied",
            )
        )
    expected_files = {
        f"phase-{ctx.phase}/phase-brief.md",
        "tech-spec.md",
        "project-rules.md",
    }
    extras = ctx.output_files() - expected_files
    if extras:
        failures.append(
            Failure(
                "selected_hook_finding_applied_only_in_spec",
                f"triage created unexpected tracking/output files: {sorted(extras)}",
            )
        )
    return failures


# --- review hard gate ---------------------------------------------------------

PENDING_REVIEW_BACKLOG = """# Backlog

## Items

### Pending behaviour
- **Type:** feature
- **Context:**
  Finish the behaviour before reviewing the phase.
- **Status:** in-phase-1
"""

PENDING_REVIEW_INDEX = """# Stories — Gate Check — Phase 1

| # | Story | File | Status |
|---|-------|------|--------|
| 1 | Pending behaviour | story-1-pending-behaviour.md | pending |
"""

PENDING_REVIEW_BRIEF = """# Phase Brief — Gate Check — Phase 1

## Phase Goal

The pending behaviour is implemented and reviewed before another phase starts.

## Phase Scope

- Finish the pending behaviour.

## Exit Criteria

1. Pending behaviour
   - Complete the story: behaviour is available
"""


# --- review: rejected scope ---------------------------------------------------

# Items whose only reason to exist was the direction the feedback rejects. The
# unrelated item must NOT be proposed for rejection — over-rejecting is as wrong
# as under-rejecting.
REJECTION_CANDIDATES = ("Panel dock drag handles", "Dock layout presets")
REJECTION_NON_CANDIDATE = "Export rendered output to video"


def review_surfaced_rejection_candidates(ctx: Ctx) -> list[Failure]:
    # Rejection candidates are proposed in chat before any write, so file state
    # alone cannot tell a correct triage from a runner that ignored the
    # rejection half of the feedback entirely.
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    failures = []

    missing = [t for t in REJECTION_CANDIDATES if t.lower() not in text.lower()]
    if missing:
        failures.append(
            Failure(
                "review_surfaced_rejection_candidates",
                f"open backlog items orphaned by the rejected direction were never surfaced: {missing}",
            )
        )

    if REJECTION_NON_CANDIDATE.lower() in text.lower():
        # Naming it is only a failure if it was swept into the rejection list.
        for line in text.splitlines():
            if REJECTION_NON_CANDIDATE.lower() in line.lower() and re.search(
                r"❌|reject", line, re.IGNORECASE
            ):
                failures.append(
                    Failure(
                        "review_surfaced_rejection_candidates",
                        f"unrelated backlog item proposed for rejection: {line.strip()!r}",
                    )
                )
                break

    if not re.search(r"❌|reject", text, re.IGNORECASE):
        failures.append(
            Failure(
                "review_surfaced_rejection_candidates",
                "no rejection bucket in the triage response",
            )
        )

    if failures:
        compact = " ".join(text.strip().split())
        failures.append(
            Failure(
                "review_surfaced_rejection_candidates",
                f"runner output ended: {compact[-600:]!r}",
            )
        )
    return failures


def review_triage_wrote_nothing_yet(ctx: Ctx) -> list[Failure]:
    # STEP 2 presents triage and stops. Nothing may be written before the user
    # confirms — least of all a rejection they have not seen.
    failures = []
    backlog = ctx.backlog()
    original = ctx.fixture_text("backlog.md")
    if backlog != original:
        failures.append(
            Failure(
                "review_triage_wrote_nothing_yet",
                "backlog.md changed before the user confirmed the triage",
            )
        )
    if (ctx.output_dir / "reviews.md").is_file():
        failures.append(
            Failure(
                "review_triage_wrote_nothing_yet",
                "reviews.md was written before the user confirmed the triage",
            )
        )
    return failures


def review_preserved_positive_summary(ctx: Ctx) -> list[Failure]:
    failures = []
    reviews_path = ctx.output_dir / "reviews.md"
    if not reviews_path.is_file():
        return [Failure(
            "review_preserved_positive_summary",
            "reviews.md was not written after the explicit close",
        )]

    review = reviews_path.read_text(encoding="utf-8")
    checks = {
        "summary result": bool(re.search(
            r"\*\*(?:Result|Observed):\*\*[^\n]*(?:all went as planned|everything went as planned)",
            review,
            re.IGNORECASE,
        )),
        "passed phase promise": bool(re.search(
            r"\|[^\n]*save[^\n]*\|\s*passed\s*\|",
            review,
            re.IGNORECASE,
        )),
        "confirmed assumption": bool(re.search(
            r"\|[^\n]*Save button[^\n]*\|\s*confirmed\s*\|",
            review,
            re.IGNORECASE,
        )),
    }
    failures.extend(
        Failure("review_preserved_positive_summary", f"missing {label}")
        for label, present in checks.items()
        if not present
    )

    if re.search(r"\*\*(?:Level|Status|Tried):\*\*", review, re.IGNORECASE):
        failures.append(Failure(
            "review_preserved_positive_summary",
            "review retained the removed evidence grading fields",
        ))
    if "Not recorded" in review:
        failures.append(Failure(
            "review_preserved_positive_summary",
            "review printed a missing-field placeholder",
        ))
    if re.search(r"\*\*Checked with:\*\*", review, re.IGNORECASE):
        failures.append(Failure(
            "review_preserved_positive_summary",
            "review invented optional validation context",
        ))

    backlog = ctx.backlog() or ""
    if "**Status:** resolved" not in backlog or "**Status:** in-phase-1" in backlog:
        failures.append(Failure(
            "review_preserved_positive_summary",
            "the explicit close did not resolve the phase backlog item",
        ))
    return failures


def pending_review_gate_held(ctx: Ctx) -> list[Failure]:
    fails = []
    reviews = ctx.output_dir / "reviews.md"
    if reviews.exists():
        fails.append(Failure("pending_review_gate_held", "reviews.md was written despite a pending story"))

    if (ctx.backlog() or "") != PENDING_REVIEW_BACKLOG:
        fails.append(Failure("pending_review_gate_held", "backlog changed despite the pending-story gate"))

    if (ctx.readme() or "") != PENDING_REVIEW_INDEX:
        fails.append(Failure("pending_review_gate_held", "pending stories index changed"))
    brief = ctx.output_dir / "phase-1" / "phase-brief.md"
    if not brief.is_file() or brief.read_text(encoding="utf-8") != PENDING_REVIEW_BRIEF:
        fails.append(Failure("pending_review_gate_held", "phase brief changed despite the pending-story gate"))
    expected = {
        "backlog.md",
        "phase-1/phase-brief.md",
        "phase-1/stories/README.md",
    }
    actual = {str(p.relative_to(ctx.output_dir)) for p in ctx.output_dir.rglob("*") if p.is_file()}
    if actual != expected:
        fails.append(Failure("pending_review_gate_held",
                             f"unexpected output files added or removed: expected {sorted(expected)}, got {sorted(actual)}"))
    return fails


# --- wave 5: review as a short triage inbox ------------------------------------

# The opening's contract, keyed to the `review-open-phase` fixture: four Exit
# leaves at their brief addresses, two questions, two assumptions, and one leaf
# the ledger marks `needs-human`.
OPENING_EXIT_LEAVES = ("E1a", "E1b", "E2a", "E2b")
OPENING_QUESTIONS = {
    "Q1": "nesting",
    "Q2": "phone",
}
OPENING_ASSUMPTIONS = {
    "A1": "as they write",
    "A2": "one line",
}
OPENING_NEEDS_HUMAN = "E2b"
# Every alternative closer the opening used to offer. One ask means one ask.
BANNED_CLOSERS = (
    "Did I put each outcome in the right section",
    "Tell me what to move or remove",
    "You may add where or how you checked it",
    'Say "close it" to record the review',
    "How did it go?",
    "Reply naturally",
    "close without validation",
)


def _plain(ctx: Ctx) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)


def review_opening_shape(ctx: Ctx) -> list[Failure]:
    """§5.3: one response, one ask, every Exit leaf separately visible.

    The shape is checked on the response itself because the opening is chat and
    nothing else records it.
    """
    assertion = "review_opening_shape"
    text = _plain(ctx)
    fails = []

    for leaf in OPENING_EXIT_LEAVES:
        # Its own line, at the brief's own address — not folded into a category.
        if not re.search(rf"^\s*(?:\d+\.\s*)?{leaf}\b", text, re.MULTILINE):
            fails.append(Failure(assertion, f"Exit leaf {leaf} is not separately visible in the opening"))

    if not re.search(r"^\s*What broke, what you'd change, or \"close it\"\.\s*$", text, re.MULTILINE):
        fails.append(Failure(assertion, "the opening does not end with the one sanctioned ask"))

    for banned in BANNED_CLOSERS:
        if banned.lower() in text.lower():
            fails.append(Failure(assertion, f"opening offered an alternative closer: {banned!r}"))

    # Recording mechanics are the model narrating the file back at the human.
    for mechanic in ("not tested", "inconclusive", "*(assumption)*", "*(decide)*", "passed / failed"):
        if mechanic.lower() in text.lower():
            fails.append(Failure(assertion, f"opening printed recording mechanics: {mechanic!r}"))

    if fails:
        fails.append(Failure(assertion, f"opening was: {' '.join(text.strip().split())[-800:]!r}"))
    return fails


def review_opening_kept_every_promise(ctx: Ctx) -> list[Failure]:
    """Shorter, not weaker: no question, assumption, or `Try` item disappears."""
    assertion = "review_opening_kept_every_promise"
    text = _plain(ctx)
    fails = []

    for qid, needle in OPENING_QUESTIONS.items():
        if qid not in text or needle.lower() not in text.lower():
            fails.append(Failure(assertion, f"Validation Question {qid} ({needle!r}) is missing from the opening"))
    for aid, needle in OPENING_ASSUMPTIONS.items():
        if aid not in text or needle.lower() not in text.lower():
            fails.append(Failure(assertion, f"assumption {aid} ({needle!r}) is missing from the opening"))

    # The needs-human leaf is flagged, and always carries its Try guidance —
    # beside that leaf, not merely somewhere in the message.
    lines = text.splitlines()
    index = next((i for i, l in enumerate(lines) if OPENING_NEEDS_HUMAN in l), None)
    if index is None:
        fails.append(Failure(assertion, f"{OPENING_NEEDS_HUMAN} never appeared"))
    else:
        if "needs human" not in lines[index].lower():
            fails.append(Failure(
                assertion,
                f"{OPENING_NEEDS_HUMAN} is not flagged as needing a human check: {lines[index].strip()!r}",
            ))
        following = " ".join(lines[index:index + 3]).lower()
        if "try:" not in following or "phone" not in following:
            fails.append(Failure(
                assertion,
                f"{OPENING_NEEDS_HUMAN} carries no Try guidance from the brief: {following.strip()[:160]!r}",
            ))

    if "busiest tags" not in text.lower():
        fails.append(Failure(assertion, "the brief's first Try item was not shown beside its promise"))

    if fails:
        fails.append(Failure(assertion, f"opening was: {' '.join(text.strip().split())[-800:]!r}"))
    return fails


def review_sign_off_recorded_human_provenance(ctx: Ctx) -> list[Failure]:
    """D10: `close it` is an attestation, and the ledger records who made it."""
    assertion = "review_sign_off_recorded_human_provenance"
    fails = []
    progress = ctx.progress()
    if progress is None:
        return [Failure(assertion, "the ledger disappeared")]

    statuses = {row_id: status for row_id, _, status in parse_progress_rows(progress)}
    for leaf in OPENING_EXIT_LEAVES:
        if statuses.get(leaf) != "met":
            fails.append(Failure(assertion, f"{leaf} is {statuses.get(leaf)!r} after sign-off, not 'met'"))

    contracts = parse_row_contracts(progress)
    provenance = contracts.get(OPENING_NEEDS_HUMAN, {}).get("attributes", {}).get("provenance", "")
    if "human sign-off at review" not in provenance:
        fails.append(Failure(
            assertion,
            f"{OPENING_NEEDS_HUMAN} was flipped without recorded human provenance: {provenance!r}",
        ))

    # A leaf flipped with nobody's name on it is exactly the record D10 rejects.
    if not (ctx.output_dir / "reviews.md").is_file():
        fails.append(Failure(assertion, "the phase closed without a review entry"))
    backlog = ctx.backlog() or ""
    if "**Status:** in-phase-1" in backlog:
        fails.append(Failure(assertion, "the close sweep did not resolve the in-phase backlog item"))
    return fails


def review_recorded_unanswered_questions(ctx: Ctx) -> list[Failure]:
    """"Ship it" does not answer a question the human was asked."""
    assertion = "review_recorded_unanswered_questions"
    review = ctx.output_text("reviews.md")
    if review is None:
        return [Failure(assertion, "reviews.md was not written")]
    fails = []

    for qid in OPENING_QUESTIONS:
        line = next((l for l in review.splitlines() if re.search(rf"\b{qid}\b", l)), None)
        if line is None:
            fails.append(Failure(assertion, f"{qid} is absent from the review record"))
        elif "unanswered at close" not in line.lower():
            fails.append(Failure(assertion, f"{qid} was not recorded as unanswered at close: {line.strip()!r}"))

    for aid in OPENING_ASSUMPTIONS:
        line = next((l for l in review.splitlines() if re.search(rf"\b{aid}\b", l)), None)
        if line is None:
            fails.append(Failure(assertion, f"assumption {aid} is absent from the review record"))
        elif "inconclusive" in line.lower():
            fails.append(Failure(
                assertion,
                f"{aid} was recorded inconclusive rather than accepted at sign-off: {line.strip()!r}",
            ))
    return fails


def review_echoed_findings_only(ctx: Ctx) -> list[Failure]:
    """§5.6: the echo carries what Mano classified, and one ask — nothing else."""
    assertion = "review_echoed_findings_only"
    text = _plain(ctx)
    fails = []

    # Which bucket a finding lands in is the human's to correct; that one was
    # echoed at all is what this checks.
    if not re.search(r"🐛|🔧|✨|📋|📏|❌|✅", text):
        fails.append(Failure(assertion, "no finding was echoed for confirmation"))
    if not re.search(r"Anything in the wrong bucket\?", text, re.IGNORECASE):
        fails.append(Failure(assertion, "the echo did not end with the one compact ask"))
    for banned in BANNED_CLOSERS:
        if banned.lower() in text.lower():
            fails.append(Failure(assertion, f"the echo offered an alternative closer: {banned!r}"))

    # The record is complete in STEP 3; the echo does not read it back.
    if re.search(r"^\s*Phase checks\s*:?\s*$", text, re.MULTILINE | re.IGNORECASE):
        fails.append(Failure(assertion, "the echo read back the phase-check table"))
    if re.search(r"passed\s*/\s*failed\s*/\s*not tested", text, re.IGNORECASE):
        fails.append(Failure(assertion, "the echo printed the phase-check vocabulary"))

    if fails:
        fails.append(Failure(assertion, f"echo was: {' '.join(text.strip().split())[-800:]!r}"))
    return fails


def review_close_did_not_erase_the_finding(ctx: Ctx) -> list[Failure]:
    """`close it` closes the phase; it is not permission to drop what broke."""
    assertion = "review_close_did_not_erase_the_finding"
    text = _plain(ctx)
    fails = []

    if "tag" not in text.lower() or not re.search(r"remove|reopen|linger|stays on screen", text, re.IGNORECASE):
        fails.append(Failure(assertion, "the finding was not echoed back at all"))

    routed = re.search(r"rework|route|reopen|fix(ed|ing|\b)", text, re.IGNORECASE)
    dismissed = re.search(r"dismiss|intended|by design|leave it|as-is|as is|not doing", text, re.IGNORECASE)
    if not (routed and dismissed):
        fails.append(Failure(
            assertion,
            "the close did not ask whether to route the finding to rework or dismiss it",
        ))

    # Never conclude a dismissal on the human's behalf.
    progress = ctx.progress() or ""
    contracts = parse_row_contracts(progress)
    for row_id, contract in contracts.items():
        if row_id.startswith("R") and "dismissed-reason" in contract.get("attributes", {}):
            fails.append(Failure(assertion, f"{row_id} was dismissed without the human saying so"))

    if fails:
        fails.append(Failure(assertion, f"response was: {' '.join(text.strip().split())[-800:]!r}"))
    return fails


def review_followup_wrote_nothing_yet(ctx: Ctx) -> list[Failure]:
    """The follow-up echo is a confirmation step: no addendum until it lands."""
    assertion = "review_followup_wrote_nothing_yet"
    fails = []
    if (ctx.backlog() or "") != (ctx.fixture_text("backlog.md") or ""):
        fails.append(Failure(assertion, "backlog.md changed before the user confirmed the follow-up triage"))
    if (ctx.output_text("reviews.md") or "") != (ctx.fixture_text("reviews.md") or ""):
        fails.append(Failure(assertion, "the review entry changed before the user confirmed the follow-up triage"))
    return fails


def build_handoff_showed_validate_now(ctx: Ctx) -> list[Failure]:
    """D6: the terminal handoff carries the brief's own `Try` guidance."""
    assertion = "build_handoff_showed_validate_now"
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.step(1).final_response)
    fails = []
    if not re.search(r"Validate now:", text):
        fails.append(Failure(assertion, "the build handoff printed no `Validate now:` block"))
    if "paragraph" not in text.lower() or "editor" not in text.lower():
        fails.append(Failure(assertion, "the brief's Try guidance was not the source of the block"))
    if fails:
        fails.append(Failure(assertion, f"handoff was: {' '.join(text.strip().split())[-600:]!r}"))
    return fails


def review_opening_repeats_the_try_guidance(ctx: Ctx) -> list[Failure]:
    """...and the fresh review session prints it again beside the promise."""
    assertion = "review_opening_repeats_the_try_guidance"
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.step(2).final_response)
    fails = []
    if "Try:" not in text:
        fails.append(Failure(assertion, "the review opening carried no `Try` guidance"))
    if "paragraph" not in text.lower() or "editor" not in text.lower():
        fails.append(Failure(assertion, "the brief's Try guidance is absent from the review opening"))
    if "Q1" not in text:
        fails.append(Failure(assertion, "the Validation Question lost its stable address"))
    if fails:
        fails.append(Failure(assertion, f"opening was: {' '.join(text.strip().split())[-600:]!r}"))
    return fails


def review_one_exchange_close(ctx: Ctx) -> list[Failure]:
    """A clear positive verdict closes in one exchange: no echo-back triage
    confirmation question may appear in the response."""
    assertion = "review_one_exchange_close"
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    fails = []
    for banned in BANNED_CLOSERS + ("Anything in the wrong bucket",):
        if banned.lower() in text.lower():
            fails.append(Failure(
                assertion,
                f"positive close still asked for confirmation: {banned!r}",
            ))
    if not (ctx.output_dir / "reviews.md").is_file():
        fails.append(Failure(assertion, "reviews.md was not written in the same exchange"))
    return fails


# --- done-story immutability (ambient, no mano command typed) ------------------

def done_story_edit_routed(ctx: Ctx) -> list[Failure]:
    """A mid-chat request to edit a done story is refused and routed to
    `mano stories` (lettered follow-up), never applied to the file."""
    assertion = "done_story_edit_routed"
    fails = []
    path = ctx.stories_dir / "story-3-existing-shipped.md" if ctx.stories_dir else None
    if path is None or not path.is_file():
        fails.append(Failure(assertion, "done story file is missing"))
    elif path.read_text(encoding="utf-8") != EXISTING_DONE_STORY:
        fails.append(Failure(assertion, "the done story file was edited"))
    text = ctx.transcript
    if not re.search(r"mano\s+stories", text, re.IGNORECASE):
        compact = " ".join(text.strip().split())
        fails.append(Failure(
            assertion,
            f"refusal does not route to mano stories: {compact[-300:]!r}",
        ))
    return fails


# --- hooks: check mode + legacy suggest ---------------------------------------

def check_hook_ran_without_confirmation(ctx: Ctx) -> list[Failure]:
    """A check-mode hook is the user's own checklist: Mano applies it without
    the suggest-mode `Run it now?` ask, and creates no tracking artifacts."""
    assertion = "check_hook_ran_without_confirmation"
    fails = []
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    if re.search(r"Run it now\?", text, re.IGNORECASE):
        fails.append(Failure(assertion, "check hook was offered with `Run it now?` instead of applied"))
    expected_files = {
        f"phase-{ctx.phase}/phase-brief.md",
        "tech-spec.md",
        "project-rules.md",
    }
    extras = ctx.output_files() - expected_files
    if extras:
        fails.append(Failure(assertion, f"unexpected files created: {sorted(extras)}"))
    return fails


def legacy_blank_suggest_hook_surfaced(ctx: Ctx) -> list[Failure]:
    """A legacy suggest hook with a blank command placeholder is still an
    active hook: it must be surfaced with the ask, never silently skipped."""
    assertion = "legacy_blank_suggest_hook_surfaced"
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    if not re.search(r"post-spec", text, re.IGNORECASE) or not re.search(
        r"Run it now\?|run (?:it|the hook|this hook)", text, re.IGNORECASE
    ):
        compact = " ".join(text.strip().split())
        return [Failure(
            assertion,
            f"active legacy hook was not surfaced: {compact[-400:]!r}",
        )]
    return []


# --- start: SCOPE INPUT is the only backlog read ------------------------------

BACKLOG_READ_CANARY = "CANARY-BACKLOG-DIRECT-READ"


def start_did_not_mine_backlog(ctx: Ctx) -> list[Failure]:
    """The projection never prints resolved items, so the canary title can
    reach a transcript only through a direct backlog.md read. (Absence of the
    canary cannot prove no read happened — this is the strongest signal a
    file-and-response harness can check.)"""
    if BACKLOG_READ_CANARY.lower() in ctx.transcript.lower():
        return [Failure(
            "start_did_not_mine_backlog",
            "a resolved backlog item surfaced in the response — backlog.md was read directly",
        )]
    return []


# --- stories mid-build path ---------------------------------------------------

EXISTING_DONE_STORY = """### STORY-3: Existing shipped story

#### What and why
Existing behaviour is already shipped and must not be rewritten.

#### Done when
- [ ] Existing shipped behaviour remains available.

#### Not this story
- No archive filtering changes.

#### Implementation Reference
- **Files:** existing.txt

---
<!-- sentinel: done-story-must-remain-byte-identical -->
"""

EXISTING_PENDING_STORY = """### STORY-4: Upcoming export

#### What and why
Readers can export their current notes after the earlier list work is stable.

#### Done when
- [ ] Exporting creates a readable notes file.

#### Not this story
- No archive filtering changes.

#### Implementation Reference
- **Files:** export.txt

---
<!-- sentinel: pending-story-must-remain-byte-identical -->
"""

MIDBUILD_PHASE_BRIEF = """# Phase Brief — Notes — Phase 2

## Phase Goal

The note list remains trustworthy while export work continues.

## Phase Scope

- Preserve the shipped note list behaviour.
- Add note export.

## Exit Criteria

1. Existing list
   - Open the list: shipped notes remain available
2. Export
   - Export notes: a readable file is created
"""


def midbuild_lettered_story_inserted(ctx: Ctx) -> list[Failure]:
    fails = []
    story_files = ctx.story_files()
    inserted = [p for p in story_files if re.match(r"story-3a-[a-z0-9-]+\.md$", p.name)]
    if len(story_files) != 3:
        fails.append(Failure("midbuild_lettered_story_inserted",
                             f"expected two existing stories plus one insertion, found {[p.name for p in story_files]}"))
    if len(inserted) != 1:
        fails.append(Failure("midbuild_lettered_story_inserted",
                             f"expected exactly one story-3a insertion, found {[p.name for p in inserted]}"))
    elif inserted:
        done_when = _section(inserted[0].read_text(encoding="utf-8"), "Done when") or ""
        if not re.search(r"archive", done_when, re.IGNORECASE) or not re.search(r"completed|hidden|hide", done_when, re.IGNORECASE):
            fails.append(Failure("midbuild_lettered_story_inserted",
                                 "inserted story has no Done-when AC for hiding completed archive items"))

    readme = ctx.readme() or ""
    rows = {}
    for num in ("3", "3a", "4"):
        match = re.search(rf"^\|\s*{num}\s*\|\s*[^|]+\|\s*([^|]+)\|\s*([^|]+)\|\s*$", readme, re.MULTILINE)
        if match:
            rows[num] = (match.start(), match.group(1).strip(), match.group(2).strip())
    if set(rows) != {"3", "3a", "4"}:
        fails.append(Failure("midbuild_lettered_story_inserted", "README is missing row 3, 3a, or 4"))
    else:
        if not rows["3"][0] < rows["3a"][0] < rows["4"][0]:
            fails.append(Failure("midbuild_lettered_story_inserted", "README row 3a is not between 3 and 4"))
        if rows["3a"][2].lower() != "pending":
            fails.append(Failure("midbuild_lettered_story_inserted", "README row 3a is not pending"))
    if len(inserted) == 1:
        expected = {
            "phase-2/phase-brief.md",
            "phase-2/stories/README.md",
            "phase-2/stories/story-3-existing-shipped.md",
            "phase-2/stories/story-4-upcoming-export.md",
            f"phase-2/stories/{inserted[0].name}",
        }
        actual = {str(p.relative_to(ctx.output_dir)) for p in ctx.output_dir.rglob("*") if p.is_file()}
        if actual != expected:
            fails.append(Failure("midbuild_lettered_story_inserted",
                                 f"unexpected output files added or removed: expected {sorted(expected)}, got {sorted(actual)}"))
    return fails


def existing_stories_unchanged(ctx: Ctx) -> list[Failure]:
    fails = []
    expected = {
        "story-3-existing-shipped.md": EXISTING_DONE_STORY,
        "story-4-upcoming-export.md": EXISTING_PENDING_STORY,
    }
    for name, content in expected.items():
        path = ctx.stories_dir / name if ctx.stories_dir else None
        if path is None or not path.is_file():
            fails.append(Failure("existing_stories_unchanged", f"{name} was removed"))
        elif path.read_text(encoding="utf-8") != content:
            fails.append(Failure("existing_stories_unchanged", f"{name} was modified"))
    brief = ctx.output_dir / "phase-2" / "phase-brief.md"
    if not brief.is_file() or brief.read_text(encoding="utf-8") != MIDBUILD_PHASE_BRIEF:
        fails.append(Failure("existing_stories_unchanged", "phase brief input was modified"))
    return fails


# --- mano stories: pulling a backlog item into an already-open phase ---------

MIDPHASE_PULLED_ITEM = "Show export progress while a file is written"
MIDPHASE_OUT_OF_GOAL_ITEM = "Sync notes to a hosted account"


def _backlog_status_of(text: str, title: str) -> str | None:
    """The Status of one exact `### title` block, or None if absent."""
    blocks = re.split(r"^###\s+", text or "", flags=re.MULTILINE)
    for block in blocks[1:]:
        lines = block.split("\n")
        if lines[0].strip().lower() != title.lower():
            continue
        found = re.search(r"^-\s*\*\*Status:\*\*\s*(.+?)\s*$", block, re.MULTILINE)
        return found.group(1).strip().lower() if found else None
    return None


def midphase_item_assigned_to_open_phase(ctx: Ctx) -> list[Failure]:
    failures = []
    backlog = ctx.backlog() or ""

    status = _backlog_status_of(backlog, MIDPHASE_PULLED_ITEM)
    if status is None:
        failures.append(
            Failure(
                "midphase_item_assigned_to_open_phase",
                f'backlog item "{MIDPHASE_PULLED_ITEM}" is gone from the backlog',
            )
        )
    elif status != "in-phase-2":
        # Still `backlog` means the story was written over an unassigned item;
        # anything else means a status was invented.
        failures.append(
            Failure(
                "midphase_item_assigned_to_open_phase",
                f'named item was not assigned to the open phase: Status is "{status}", expected "in-phase-2"',
            )
        )

    # Only the item the user named may move. The out-of-goal item is the trap.
    untouched = _backlog_status_of(backlog, MIDPHASE_OUT_OF_GOAL_ITEM)
    if untouched != "backlog":
        failures.append(
            Failure(
                "midphase_item_assigned_to_open_phase",
                f'an item the user did not name changed status: "{MIDPHASE_OUT_OF_GOAL_ITEM}" is "{untouched}"',
            )
        )

    # A story must exist for the pulled-in work, and the index must know it.
    readme = ctx.readme() or ""
    story_rows = [r for r in readme.split("\n") if "|" in r and "progress" in r.lower()]
    if not story_rows:
        failures.append(
            Failure(
                "midphase_item_assigned_to_open_phase",
                "no story row was added to the index for the pulled-in item",
            )
        )
    if not any("progress" in name.lower() for name in ctx.story_texts()):
        failures.append(
            Failure(
                "midphase_item_assigned_to_open_phase",
                f"no story file was written for the pulled-in item; files: {sorted(ctx.story_texts())}",
            )
        )
    return failures


def midphase_brief_untouched_and_flagged(ctx: Ctx) -> list[Failure]:
    failures = []

    # The brief belongs to mano start. Growing the phase must be flagged, never
    # written into an artifact this skill does not own.
    brief = ctx.output_dir / f"phase-{ctx.phase}" / "phase-brief.md"
    if not brief.is_file():
        failures.append(Failure("midphase_brief_untouched_and_flagged", "phase brief is missing"))
    elif brief.read_text(encoding="utf-8") != MIDBUILD_PHASE_BRIEF:
        failures.append(
            Failure(
                "midphase_brief_untouched_and_flagged",
                "mano stories edited the phase brief; it must flag the scope change instead",
            )
        )

    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    if not re.search(r"⚠\s*Verify", text, re.IGNORECASE):
        compact = " ".join(text.strip().split())
        failures.append(
            Failure(
                "midphase_brief_untouched_and_flagged",
                f"phase scope grew with no ⚠ Verify flag; runner output ended: {compact[-400:]!r}",
            )
        )
    return failures


# --- mano ui: project brief + phase-local preview ownership -----------------

def _ui_fixture_destination(ctx: Ctx, fixture_name: str) -> Path:
    relative = Path(fixture_name)
    if relative.parent != Path("."):
        return ctx.output_dir / relative
    if ctx.phase is not None and fixture_name == "phase-brief.md":
        return ctx.output_dir / f"phase-{ctx.phase}" / fixture_name
    return ctx.output_dir / fixture_name


def ui_prior_and_legacy_previews_unchanged(ctx: Ctx) -> list[Failure]:
    assertion = "ui_prior_and_legacy_previews_unchanged"
    fails = []
    for fixture_name in ("design-preview.html", "phase-1/design-preview.html"):
        expected = ctx.fixture_text(fixture_name)
        path = _ui_fixture_destination(ctx, fixture_name)
        if expected is None:
            fails.append(Failure(assertion, f"fixture is missing {fixture_name}"))
        elif not path.is_file():
            fails.append(Failure(assertion, f"existing preview was removed: {fixture_name}"))
        elif path.read_text(encoding="utf-8") != expected:
            fails.append(Failure(assertion, f"existing preview changed: {fixture_name}"))

    allowed = {"design-preview.html", "phase-1/design-preview.html"}
    if ctx.phase is not None:
        allowed.add(f"phase-{ctx.phase}/design-preview.html")
    actual = {
        path.relative_to(ctx.output_dir).as_posix()
        for path in ctx.output_dir.rglob("design-preview.html")
        if path.is_file()
    }
    unexpected = sorted(actual - allowed)
    if unexpected:
        fails.append(Failure(
            assertion,
            f"preview written outside the current phase: {unexpected}",
        ))
    return fails


def ui_phase_preview_owned_by_current_phase(ctx: Ctx) -> list[Failure]:
    assertion = "ui_phase_preview_owned_by_current_phase"
    if ctx.phase is None:
        return [Failure(assertion, "case requires an active phase")]

    fails = []
    preview = ctx.output_dir / f"phase-{ctx.phase}" / "design-preview.html"
    if not preview.is_file():
        return [Failure(
            assertion,
            f"current preview missing: phase-{ctx.phase}/design-preview.html",
        )]

    text = preview.read_text(encoding="utf-8")
    for signal in ("Insight Inbox", "Monday launch signal"):
        if signal.lower() not in text.lower():
            fails.append(Failure(
                assertion,
                f"current phase preview is missing phase content: {signal!r}",
            ))
    if "Source Queue preview approved in Phase 1" in text:
        fails.append(Failure(assertion, "current preview copied the prior phase demo"))

    for fixture_name in ("phase-brief.md", "ux-flow.md"):
        expected = ctx.fixture_text(fixture_name)
        path = _ui_fixture_destination(ctx, fixture_name)
        if expected is not None and (
            not path.is_file() or path.read_text(encoding="utf-8") != expected
        ):
            fails.append(Failure(assertion, f"read-only UI input changed: {fixture_name}"))
    return fails


def ui_cumulative_brief_extended(ctx: Ctx) -> list[Failure]:
    assertion = "ui_cumulative_brief_extended"
    path = ctx.output_dir / "design-brief.md"
    if not path.is_file():
        return [Failure(assertion, "project design-brief.md is missing")]

    text = path.read_text(encoding="utf-8")
    original = ctx.fixture_text("design-brief.md")
    fails = []
    if original is not None and text == original:
        fails.append(Failure(assertion, "project design brief was not extended for Phase 2"))

    preserved = (
        "sentinel: cumulative-brief-phase-1-must-survive",
        "Phase 1 — Source Queue",
        "#2457D6",
        "### PrimaryButton",
        "### InsightCard",
    )
    for signal in preserved:
        if signal not in text:
            fails.append(Failure(assertion, f"existing brief content was lost: {signal!r}"))

    if not re.search(
        r"^###\s+Phase\s+2\s+—\s+Insight Inbox\s*$",
        text,
        re.IGNORECASE | re.MULTILINE,
    ):
        fails.append(Failure(
            assertion,
            "brief has no `### Phase 2 — Insight Inbox` composition ownership",
        ))

    for heading in ("### PrimaryButton", "### InsightCard"):
        if text.count(heading) != 1:
            fails.append(Failure(
                assertion,
                f"reused component definition was duplicated or removed: {heading}",
            ))
    return fails


def ui_phase_preview_output_paths(ctx: Ctx) -> list[Failure]:
    assertion = "ui_phase_preview_output_paths"
    if ctx.phase is None:
        return [Failure(assertion, "case requires an active phase")]
    expected = (
        "_mano_output/design-brief.md",
        f"_mano_output/phase-{ctx.phase}/design-preview.html",
    )
    missing = [path for path in expected if path not in ctx.transcript]
    if missing:
        return [Failure(
            assertion,
            f"completion response is missing artifact path(s) {missing}: {ctx.transcript!r}",
        )]
    return []


def ui_no_phase_preview_wrote_nothing(ctx: Ctx) -> list[Failure]:
    assertion = "ui_no_phase_preview_wrote_nothing"
    fails = []
    expected_files = set(ctx.fixture_snapshot)
    actual_files = ctx.output_files()
    if actual_files != expected_files:
        fails.append(Failure(
            assertion,
            f"expected only seeded artifacts {sorted(expected_files)}, got {sorted(actual_files)}",
        ))
    for fixture_name, expected in ctx.fixture_snapshot.items():
        path = _ui_fixture_destination(ctx, fixture_name)
        if not path.is_file():
            fails.append(Failure(assertion, f"seeded artifact removed: {fixture_name}"))
        elif path.read_text(encoding="utf-8") != expected:
            fails.append(Failure(assertion, f"seeded artifact changed: {fixture_name}"))
    return fails


def ui_no_phase_preview_routes_to_start(ctx: Ctx) -> list[Failure]:
    assertion = "ui_no_phase_preview_routes_to_start"
    text = ctx.transcript.strip()
    missing = []
    if not re.search(
        r"phase[- ]brief|\bBRIEF:\s*missing\b|\bno active phase\b",
        text,
        re.IGNORECASE,
    ):
        missing.append("missing phase/brief explanation")
    if not re.search(r"mano\s+start", text, re.IGNORECASE):
        missing.append("mano start route")
    if missing:
        return [Failure(assertion, f"response missing {missing}: {text!r}")]
    return []


# --- mano start: rules visibility for a new category -------------------------

def start_kept_rules_visible_for_new_category(ctx: Ctx) -> list[Failure]:
    """`mano rules` must survive the existence filter when the phase adds a category.

    The fixture ships a substantive project-rules.md and a current tech-spec.md
    on purpose: an existence-only next-action filter skips both, which is the
    exact shape that hid `mano rules` in the reported incident.
    """
    assertion = "start_kept_rules_visible_for_new_category"
    text = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", ctx.transcript)
    failures = []

    # Only the next-action block counts. Naming the skill while explaining that
    # rules already exist is the failure, not the pass.
    tail = text
    marker = re.search(r"^\s*Next:", text, re.IGNORECASE | re.MULTILINE)
    if marker:
        tail = text[marker.start():]
    if not re.search(r"mano[\s-]+rules", tail, re.IGNORECASE):
        compact = " ".join(text.strip().split())
        failures.append(
            Failure(
                assertion,
                "next actions omitted `mano rules` although the phase introduces a new "
                f"example category; output ended: {compact[-500:]!r}",
            )
        )

    # The brief is still mano start's deliverable — a next-action fix must not
    # come at the cost of skipping the phase itself.
    brief = ctx.output_dir / f"phase-{ctx.phase}" / "phase-brief.md"
    if not brief.is_file():
        failures.append(Failure(assertion, "no phase brief was written for the approved scope"))

    # project-rules.md belongs to mano rules; mano start may not write it.
    rules = ctx.output_dir / "project-rules.md"
    if rules.is_file() and rules.read_text(encoding="utf-8") != (ctx.fixture_text("project-rules.md") or ""):
        failures.append(
            Failure(assertion, "mano start edited project-rules.md; it may only suggest `mano rules`")
        )
    return failures


# --- public-interface planning readiness ------------------------------------

def _interface_matrix_rows(text: str) -> list[dict[str, str]]:
    """Extract interface rows by their Markdown header, not physical proximity.

    This accepts both the shipped five-column matrix (with Surface) and a
    compact four-column operation/input/result/mapping table. It intentionally
    does not use neighboring prose or rows to fill a cell.
    """
    rows: list[dict[str, str]] = []
    header: dict[str, int] | None = None

    for line in text.splitlines():
        stripped = line.strip()
        if not (stripped.startswith("|") and stripped.endswith("|")):
            header = None
            continue
        cells = [cell.strip() for cell in stripped[1:-1].split("|")]
        lowered = [cell.lower() for cell in cells]

        def find_header(*needles: str) -> int | None:
            return next(
                (i for i, cell in enumerate(lowered) if any(n in cell for n in needles)),
                None,
            )

        operation = find_header("operation", "method", "command / event")
        inputs = find_header("input", "argument", "request")
        result = find_header("result", "response")
        mapping = find_header("mapping", "canonical", "ownership")
        if None not in (operation, inputs, result, mapping):
            header = {
                "operation": int(operation),
                "inputs": int(inputs),
                "result": int(result),
                "mapping": int(mapping),
            }
            surface = find_header("surface")
            if surface is not None:
                header["surface"] = surface
            continue

        if header is None or all(re.fullmatch(r":?-{3,}:?", cell) for cell in cells):
            continue
        if max(header.values()) >= len(cells):
            continue
        rows.append({name: cells[index] for name, index in header.items()})
    return rows


def _ordered_patterns(text: str, patterns: tuple[str, ...]) -> bool:
    cursor = 0
    for pattern in patterns:
        match = re.search(pattern, text[cursor:], re.IGNORECASE)
        if match is None:
            return False
        cursor += match.end()
    return True


def _input_annotations_consistent(
    cell: str,
    params: tuple[str, ...],
    typed_inputs: tuple[str, ...],
) -> bool:
    plain = cell.replace("`", "").replace("**", "")
    for index, param in enumerate(params):
        annotation = re.compile(
            rf"\b{re.escape(param)}\s*\??\s*:",
            re.IGNORECASE,
        )
        for occurrence in annotation.finditer(plain):
            remainder = plain[occurrence.start():]
            exact = re.match(typed_inputs[index], remainder, re.IGNORECASE)
            if exact is None:
                return False
            tail = remainder[exact.end():].lstrip()
            if tail.startswith(("&", "|", "<", "[", "]", "?", "/")):
                return False
            if re.match(r"(?:or|and)\b", tail, re.IGNORECASE):
                return False
    return True


def _result_cell_has_exact_type(cell: str, result_type: str) -> bool:
    plain = cell.replace("`", "").replace("**", "")
    name = re.escape(result_type)
    conflicts = (
        rf"\b[A-Za-z_][A-Za-z0-9_]*\s*<\s*{name}\s*>",
        rf"(?:\||&)\s*\b{name}\b",
        rf"\b{name}\b\s*(?:\||&|\[\]|\?)",
    )
    if any(re.search(pattern, plain, re.IGNORECASE) for pattern in conflicts):
        return False
    return bool(re.search(rf"\b{name}\b", plain, re.IGNORECASE))


def _operation_row(
    rows: list[dict[str, str]],
    *,
    name: str,
    params: tuple[str, ...],
    typed_inputs: tuple[str, ...],
    result_type: str,
) -> dict[str, str] | None:
    short_name = name.rsplit(".", 1)[-1]
    callable_pattern = (
        rf"(?:(?P<qualifier>[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*)?"
        rf"{re.escape(short_name)}"
        r"(?:\s*\((?P<params>[^)]*)\))?"
        r"(?:\s*(?::|->|→)\s*(?P<return_type>[A-Za-z_][A-Za-z0-9_<>, |?]*))?"
    )

    for row in rows:
        operation = row["operation"].replace("`", "").replace("**", "").strip()
        surface = row.get("surface", "").replace("`", "")
        callable_match = re.fullmatch(callable_pattern, operation, re.IGNORECASE)
        if callable_match is None:
            continue
        qualifier = callable_match.group("qualifier")
        expected_qualifier = "Motion" if name == "Motion.for" else "BoundMotion"
        if qualifier is not None and qualifier.lower() != expected_qualifier.lower():
            continue
        if name == "Motion.for" and qualifier is None and not re.search(
            r"\bMotion\b", surface, re.IGNORECASE
        ):
            continue

        signature_params = callable_match.group("params")
        if signature_params is not None:
            actual_params = []
            annotated_params_match = True
            body = signature_params.strip()
            if body:
                parts = body.split(",")
                for index, part in enumerate(parts):
                    token = part.strip().split(":", 1)[0].strip().rstrip("?")
                    actual_params.append(token)
                    if ":" in part and (
                        index >= len(typed_inputs)
                        or not re.fullmatch(
                            typed_inputs[index], part.strip(), re.IGNORECASE
                        )
                    ):
                        annotated_params_match = False
            if tuple(actual_params) != params:
                continue
            if not annotated_params_match:
                continue

        annotated_return = callable_match.group("return_type")
        if annotated_return is not None and not re.fullmatch(
            re.escape(result_type), annotated_return.strip(), re.IGNORECASE
        ):
            continue

        if not _input_annotations_consistent(row["inputs"], params, typed_inputs):
            continue

        typed_source = f"{operation} {row['inputs']}"
        if not _ordered_patterns(typed_source, typed_inputs):
            continue
        if not _result_cell_has_exact_type(row["result"], result_type):
            continue
        return row
    return None


def _wrong_moveby_position_timing(text: str) -> bool:
    subject = (
        r"(?:the\s+)?(?:(?:current|base)\s+)?"
        r"(?:target(?:'s)?\s+)?(?:current\s+)?position"
    )
    verb = (
        r"(?<!not )(?<!n't )(?<!never )"
        r"\b(?:captur\w*|read\w*|resolv\w*)\b"
    )
    wrong_time = (
        r"(?<!not )(?<!n't )(?<!never )"
        r"\b(?:at|during)\s+(?:the\s+)?(?:authoring|call|build)\s+time\b"
    )
    active = re.compile(
        rf"{verb}(?:(?!{wrong_time}).){{0,100}}{subject}.{{0,80}}{wrong_time}",
        re.IGNORECASE,
    )
    passive = re.compile(
        rf"{subject}.{{0,60}}{verb}.{{0,80}}{wrong_time}",
        re.IGNORECASE,
    )
    return any(
        re.search(r"\bmoveBy\b", line, re.IGNORECASE)
        and (active.search(line) or passive.search(line))
        for line in text.splitlines()
    )


def spec_public_interface_contract_complete(ctx: Ctx) -> list[Failure]:
    assertion = "spec_public_interface_contract_complete"
    spec = ctx.artifact_text("tech-spec.md") or ""
    rows = _interface_matrix_rows(spec)
    factory = _operation_row(
        rows,
        name="Motion.for",
        params=("target",),
        typed_inputs=(r"\btarget\s*:\s*MotionTarget\b",),
        result_type="BoundMotion",
    )
    opacity = _operation_row(
        rows,
        name="opacity",
        params=("destination", "durationSeconds"),
        typed_inputs=(
            r"\bdestination\s*:\s*number\b",
            r"\bdurationSeconds\s*\?\s*:\s*number\b",
        ),
        result_type="PropertyMotion",
    )
    move_by = _operation_row(
        rows,
        name="moveBy",
        params=("offset", "durationSeconds"),
        typed_inputs=(
            r"\boffset\s*:\s*Point\b",
            r"\bdurationSeconds\s*\?\s*:\s*number\b",
        ),
        result_type="PropertyMotion",
    )
    property_row = _operation_row(
        rows,
        name="property",
        params=("path", "destination", "durationSeconds"),
        typed_inputs=(
            r"\bpath\s*:\s*string\b",
            r"\bdestination\s*:\s*unknown\b",
            r"\bdurationSeconds\s*\?\s*:\s*number\b",
        ),
        result_type="PropertyMotion",
    )

    exact_contracts = {
        "Motion.for(target: MotionTarget) -> BoundMotion": factory is not None,
        "opacity(destination: number, durationSeconds?: number) -> PropertyMotion": opacity is not None,
        "moveBy(offset: Point, durationSeconds?: number) -> PropertyMotion": move_by is not None,
        "property(path: string, destination: unknown, durationSeconds?: number) -> PropertyMotion": property_row is not None,
    }
    row_checks = {
        "Motion.for null-target failure": bool(
            factory and re.search(
                r"(?:null.{0,80}(?:reject|fail|error)|target required)",
                f"{factory['inputs']} {factory['result']}",
                re.IGNORECASE,
            )
        ),
        "opacity inherited-duration default": bool(
            opacity
            and re.search(r"\binherit\w*\b", f"{opacity['inputs']} {opacity['mapping']}", re.IGNORECASE)
        ),
        "opacity canonical mapping": bool(
            opacity and re.search(r"\bstyle\.opacity\b", opacity["mapping"], re.IGNORECASE)
        ),
        "moveBy inherited-duration default": bool(
            move_by
            and re.search(r"\binherit\w*\b", f"{move_by['inputs']} {move_by['mapping']}", re.IGNORECASE)
        ),
        "moveBy relative position mapping": bool(
            move_by and re.search(r"\bposition\b", move_by["mapping"], re.IGNORECASE)
        ),
        "moveBy captures position at motion start": bool(
            move_by and re.search(
                r"(?:captur\w*|evaluat\w*|read\w*).{0,160}"
                r"(?:at|when)\s+(?:the\s+)?motion\s+start|"
                r"(?:at|when)\s+(?:the\s+)?motion\s+start.{0,160}"
                r"(?:captur\w*|evaluat\w*|read\w*)",
                f"{move_by['inputs']} {move_by['mapping']}",
                re.IGNORECASE,
            )
        ),
        "property inherited-duration default": bool(
            property_row
            and re.search(r"\binherit\w*\b", f"{property_row['inputs']} {property_row['mapping']}", re.IGNORECASE)
        ),
        "generic path passthrough": bool(
            property_row and re.search(
                r"\bpath\b.{0,100}(?:\bunchanged\b|\bpass(?:ed|es)?\s+through\b)|"
                r"(?:\bunchanged\b|\bpass(?:ed|es)?\s+through\b).{0,100}\bpath\b",
                f"{property_row['inputs']} {property_row['mapping']}",
                re.IGNORECASE,
            )
        ),
    }
    checks = {
        "CanonicalMotion.to(target, property, destination) delegation": (
            r"\bCanonicalMotion\s*\.\s*to\s*\(\s*target\s*,\s*"
            r"(?:property(?:Path)?|path|[\"'][^\"']+[\"'])\s*,\s*destination\s*\)|"
            r"\bCanonicalMotion\b[^\n]{0,120}\bto\s*\(\s*"
            r"target\s*:\s*MotionTarget\s*,\s*property\s*:\s*string\s*,\s*"
            r"destination\s*:\s*unknown\s*\)[^\n]{0,160}\bPropertyMotion\b"
        ),
        "pre-playback validation failure": (
            r"(?:unsupported|invalid).{0,220}\bbefore playback\b|"
            r"\bbefore playback\b.{0,220}(?:unsupported|invalid)"
        ),
    }
    flags = re.IGNORECASE | re.DOTALL
    missing = [label for label, present in exact_contracts.items() if not present]
    missing.extend(label for label, present in row_checks.items() if not present)
    missing.extend(
        label for label, pattern in checks.items() if not re.search(pattern, spec, flags)
    )
    if missing:
        return [Failure(assertion, f"tech-spec.md missing interface fields: {missing}")]
    if _wrong_moveby_position_timing(spec):
        return [Failure(
            assertion,
            "spec also assigns moveBy base-position capture to authoring/call/build time",
        )]
    if re.search(r"Deferred spring presets|named spring presets", spec, re.IGNORECASE):
        return [Failure(assertion, "unrelated deferred backlog item leaked into tech-spec.md")]
    return []


def spec_existing_interface_reconciled(ctx: Ctx) -> list[Failure]:
    assertion = "spec_existing_interface_reconciled"
    spec = ctx.artifact_text("tech-spec.md") or ""
    if not re.search(
        r"CanonicalMotion\s*\.\s*to\s*\(\s*target\s*,\s*"
        r"(?:property(?:Path)?|path|[\"'][^\"']+[\"'])\s*,\s*destination\s*\)|"
        r"\bCanonicalMotion\b[^\n]{0,120}\bto\s*\(\s*"
        r"target\s*:\s*MotionTarget\s*,\s*property\s*:\s*string\s*,\s*"
        r"destination\s*:\s*unknown\s*\)[^\n]{0,160}\bPropertyMotion\b",
        spec,
        re.IGNORECASE | re.DOTALL,
    ):
        return [Failure(
            assertion,
            "spec did not reconcile the convenience surface with existing CanonicalMotion.to(target, property, destination)",
        )]
    return []


def spec_preserved_unrelated_decisions(ctx: Ctx) -> list[Failure]:
    assertion = "spec_preserved_unrelated_decisions"
    spec = ctx.artifact_text("tech-spec.md") or ""
    if not re.search(
        r"serialized definitions.{0,120}stable string IDs?.{0,120}"
        r"never retain live target objects?",
        spec,
        re.IGNORECASE | re.DOTALL,
    ):
        return [Failure(assertion, "spec rerun removed or rewrote an unrelated existing decision")]
    return []


def spec_wrote_no_stories(ctx: Ctx) -> list[Failure]:
    if ctx.story_files() or ctx.readme() is not None:
        return [Failure("spec_wrote_no_stories", "mano spec wrote story artifacts")]
    return []


def stories_public_interface_gap_wrote_nothing(ctx: Ctx) -> list[Failure]:
    assertion = "stories_public_interface_gap_wrote_nothing"
    failures = []
    if ctx.story_files() or ctx.readme() is not None:
        failures.append(Failure(assertion, "story files/index were written despite incomplete public contract"))
    current_spec = ctx.artifact_text("tech-spec.md")
    original_spec = ctx.fixture_text("tech-spec.md")
    if current_spec != original_spec:
        failures.append(Failure(assertion, "mano stories changed the read-only tech spec"))
    return failures


def stories_public_interface_gap_routes_to_spec(ctx: Ctx) -> list[Failure]:
    assertion = "stories_public_interface_gap_routes_to_spec"
    response = ctx.transcript.strip()
    missing = []
    if not re.search(r"mano\s+spec", response, re.IGNORECASE):
        missing.append("mano spec route")
    categories = (
        r"method|operation|event name",
        r"argument|input|parameter|payload|shape",
        r"return|result|failure|error|validation",
        r"mapping|canonical|ownership|lifetime",
    )
    category_hits = sum(bool(re.search(pattern, response, re.IGNORECASE)) for pattern in categories)
    if category_hits < 2:
        missing.append("at least two concrete missing contract categories")
    if missing:
        return [Failure(assertion, f"response missing {missing}: {response!r}")]
    return []


# --- helpers ------------------------------------------------------------------

def _section(text: str, heading: str) -> str | None:
    """Return the body under a markdown heading matching `heading`, until the
    next heading of the same or higher level. Heading match is case-insensitive
    and ignores the leading #'s."""
    lines = text.splitlines()
    start = None
    start_level = None
    for i, ln in enumerate(lines):
        m = re.match(r"^(#+)\s*(.+?)\s*$", ln)
        if m and m.group(2).strip().lower() == heading.lower():
            start = i + 1
            start_level = len(m.group(1))
            break
    if start is None:
        return None
    end = len(lines)
    for j in range(start, len(lines)):
        m = re.match(r"^(#+)\s", lines[j])
        if m and len(m.group(1)) <= start_level:
            end = j
            break
    return "\n".join(lines[start:end])


# --- mano build ---------------------------------------------------------------

def _ledger_rows_unchanged(ctx: Ctx, assertion: str, *, allow_status_change: bool) -> list[Failure]:
    """Row ids and text are the brief's, not the model's.

    The seeded ledger came from `progress.js init`, so any id or label that
    differs afterwards is a row the model composed, paraphrased, or dropped —
    the one thing the whole design forbids.
    """
    seeded = ctx.fixture_text("progress.md")
    if seeded is None:
        return [Failure(assertion, "fixture has no progress.md to compare against")]
    before = [(rid, label) for rid, label, _ in _rows_of(seeded)]
    after = [(rid, label) for rid, label, _ in ctx.progress_rows()]
    if before != after:
        added = [r for r in after if r not in before]
        lost = [r for r in before if r not in after]
        return [Failure(
            assertion,
            f"ledger rows changed — added {added}, removed/reworded {lost}",
        )]
    if not allow_status_change:
        if [s for _, _, s in _rows_of(seeded)] != [s for _, _, s in ctx.progress_rows()]:
            return [Failure(assertion, "a row status changed when nothing should have been written")]
    return []


def _rows_of(text: str) -> list[tuple[str, str, str]]:
    rows = []
    for line in text.split("\n"):
        if "|" not in line:
            continue
        cells = [c.strip() for c in line.split("|")]
        while cells and cells[0] == "":
            cells.pop(0)
        while cells and cells[-1] == "":
            cells.pop()
        if len(cells) < 3 or not re.fullmatch(r"[SE]\d+[a-z]*(?:\.\d+)?", cells[0]):
            continue
        rows.append((cells[0], cells[1], cells[-1].lower()))
    return rows


def build_ledger_rows_are_the_briefs(ctx: Ctx) -> list[Failure]:
    """No row was added, reworded, or dropped; only statuses may move."""
    return _ledger_rows_unchanged(ctx, "build_ledger_rows_are_the_briefs", allow_status_change=True)


def build_wrote_no_story_files(ctx: Ctx) -> list[Failure]:
    assertion = "build_wrote_no_story_files"
    stray = [f for f in ctx.output_files() if "/stories/" in f or f.endswith("stories/README.md")]
    return [Failure(assertion, f"build touched the stories path: {sorted(stray)}")] if stray else []


def build_completed_the_phase(ctx: Ctx) -> list[Failure]:
    """Every Scope row done and every Exit Criterion met, with the modules the
    brief names actually present and correct — and the already-done row left
    exactly as it was."""
    assertion = "build_completed_the_phase"
    fails = []
    rows = ctx.progress_rows()
    if not rows:
        return [Failure(assertion, "no progress.md ledger after the run")]
    open_rows = [f"{rid} ({status})" for rid, _, status in rows
                 if (rid.startswith("S") and status != "done") or (rid.startswith("E") and status != "met")]
    if open_rows:
        fails.append(Failure(assertion, f"ledger still open: {', '.join(open_rows)}"))

    root = ctx.project_root()
    expected = {
        "src/base-stage.js": "base",
        "src/feature-stage.js": "base+feature",
        "src/release-stage.js": "base+feature+release",
    }
    for rel, label in expected.items():
        path = root / rel
        if not path.is_file():
            fails.append(Failure(assertion, f"{rel} was never written"))
            continue
        proc = subprocess.run(
            ["node", "-e", f"process.stdout.write(String(require({str(path)!r})))"],
            cwd=root, capture_output=True, text=True,
        )
        if proc.stdout.strip() != label:
            fails.append(Failure(assertion, f"{rel} exports {proc.stdout.strip()!r}, expected {label!r}"))
    return fails


def build_did_not_rebuild_done_row(ctx: Ctx) -> list[Failure]:
    """A resumed build starts at the first non-done row; it does not re-derive
    work an earlier session already finished."""
    assertion = "build_did_not_rebuild_done_row"
    seeded = ctx.fixture_text("project/src/base-stage.js")
    path = ctx.project_root() / "src" / "base-stage.js"
    if not path.is_file():
        return [Failure(assertion, "the already-done row's file is gone")]
    if seeded is not None and path.read_text(encoding="utf-8") != seeded:
        return [Failure(assertion, "the already-done row's file was rewritten")]
    return []


def build_wrote_no_ledger(ctx: Ctx) -> list[Failure]:
    """A gap found at pre-flight stops before the ledger exists — the cheapest
    possible place, and the point of running the check first."""
    assertion = "build_wrote_no_ledger"
    fails = []
    if ctx.progress() is not None:
        fails.append(Failure(assertion, "progress.md was written despite a pre-flight gap"))
    if ctx.source_files():
        fails.append(Failure(assertion, f"source was written despite a pre-flight gap: {sorted(ctx.source_files())}"))
    return fails


def build_routed_to_spec(ctx: Ctx) -> list[Failure]:
    assertion = "build_routed_to_spec"
    if not re.search(r"mano\s+spec", ctx.transcript, re.IGNORECASE):
        compact = " ".join(ctx.transcript.split())
        return [Failure(assertion, f"the gap was not routed to mano spec: {compact[-300:]!r}")]
    return []


def build_routed_to_start(ctx: Ctx) -> list[Failure]:
    assertion = "build_routed_to_start"
    if not re.search(r"mano\s+start", ctx.transcript, re.IGNORECASE):
        compact = " ".join(ctx.transcript.split())
        return [Failure(assertion, f"the request was not routed to mano start: {compact[-300:]!r}")]
    return []


def build_wrote_no_source(ctx: Ctx) -> list[Failure]:
    """A stop before code means before code — the row may exist, the file may
    not."""
    assertion = "build_wrote_no_source"
    written = sorted(ctx.source_files() - set(ctx.fixture_snapshot))
    stale = {name[len("project/"):] for name in ctx.fixture_snapshot if name.startswith("project/")}
    written = [w for w in written if w not in stale]
    return [Failure(assertion, f"code was written before the stop: {written}")] if written else []


def build_stopped_before_code(ctx: Ctx) -> list[Failure]:
    """The ledger may exist (init runs before the coverage check) but nothing
    was implemented and no status moved."""
    assertion = "build_stopped_before_code"
    fails = build_wrote_no_source(ctx)
    fails = [Failure(assertion, f.detail) for f in fails]
    seeded = ctx.fixture_text("progress.md")
    expected = {rid: status for rid, _, status in _rows_of(seeded)} if seeded else {}
    for rid, _, status in ctx.progress_rows():
        want = expected.get(rid, "pending")
        if status != want:
            fails.append(Failure(assertion, f"{rid} moved {want!r} → {status!r} before the deviation was resolved"))
    return fails


def build_named_the_uncovered_criterion(ctx: Ctx) -> list[Failure]:
    assertion = "build_named_the_uncovered_criterion"
    text = ctx.transcript.lower()
    if "stages.js" not in text and "stage listing" not in text:
        compact = " ".join(ctx.transcript.split())
        return [Failure(assertion, f"the uncovered exit criterion was not named: {compact[-300:]!r}")]
    return []


def build_refused_both_ledgers(ctx: Ctx) -> list[Failure]:
    """A phase holding both ledgers is reported, never silently resolved."""
    assertion = "build_refused_both_ledgers"
    fails = _ledger_rows_unchanged(ctx, assertion, allow_status_change=False)
    if ctx.source_files():
        fails.append(Failure(assertion, f"code was written for an ambiguous phase: {sorted(ctx.source_files())}"))
    seeded_index = ctx.fixture_text("stories-README.md")
    if (ctx.readme() or "") != (seeded_index or ""):
        fails.append(Failure(assertion, "the stories index was changed instead of reported"))
    text = ctx.transcript.lower()
    if "progress.md" not in text or "stories" not in text:
        compact = " ".join(ctx.transcript.split())
        fails.append(Failure(assertion, f"the conflict was not reported: {compact[-300:]!r}"))
    return fails


def build_refused_free_text_scope(ctx: Ctx) -> list[Failure]:
    """`mano build "..."` is a correction channel, never a scope channel.

    An argument naming an outcome the phase does not contain is case (B): no
    row, no code, and the backlog offered — not a brief amendment and not a
    quiet build of whatever was asked for.
    """
    assertion = "build_refused_free_text_scope"
    fails = _ledger_rows_unchanged(ctx, assertion, allow_status_change=False)
    banned = re.compile(r"dark[ _-]?mode|theme", re.IGNORECASE)
    for rel in ctx.source_files():
        if banned.search(rel) or banned.search((ctx.project_root() / rel).read_text(encoding="utf-8", errors="ignore")):
            fails.append(Failure(assertion, f"the argument's work was implemented in {rel}"))
    fails.extend(Failure(assertion, f.detail) for f in build_offered_backlog_defer(ctx))
    return fails


def build_review_gate_held(ctx: Ctx) -> list[Failure]:
    """Built is not proven: review refuses while any Exit Criterion is pending,
    and never edits the ledger to clear its own gate."""
    assertion = "build_review_gate_held"
    fails = _ledger_rows_unchanged(ctx, assertion, allow_status_change=False)
    if (ctx.output_dir / "reviews.md").is_file():
        fails.append(Failure(assertion, "reviews.md was written despite a pending exit criterion"))
    if "E1c" not in ctx.transcript:
        compact = " ".join(ctx.transcript.split())
        fails.append(Failure(assertion, f"the pending exit criterion was not named: {compact[-300:]!r}"))
    return fails


def build_reopened_instead_of_appending(ctx: Ctx) -> list[Failure]:
    """Case (A): a defect in work already marked done is a status correction.
    The rows are reopened and fixed under them; nothing is appended."""
    assertion = "build_reopened_instead_of_appending"
    fails = _ledger_rows_unchanged(ctx, assertion, allow_status_change=True)
    proc = subprocess.run(
        ["node", "-e", "process.stdout.write(String(require('./src/release-stage.js')))"],
        cwd=ctx.project_root(), capture_output=True, text=True,
    )
    if proc.stdout.strip() != "base+feature+release":
        fails.append(Failure(assertion, f"the defect was not fixed: release stage exports {proc.stdout.strip()!r}"))
    return fails


def build_appended_the_users_words(ctx: Ctx) -> list[Failure]:
    """Case (C): an in-goal nuance is appended as a lettered row carrying the
    user's own words — never a paraphrase, never a rewritten existing row."""
    assertion = "build_appended_the_users_words"
    fails = []
    seeded = _rows_of(ctx.fixture_text("progress.md") or "")
    after = ctx.progress_rows()
    before_ids = {rid for rid, _, _ in seeded}
    added = [(rid, label) for rid, label, _ in after if rid not in before_ids]
    for rid, label, _ in seeded:
        match = [r for r in after if r[0] == rid]
        if not match or match[0][1] != label:
            fails.append(Failure(assertion, f"existing row {rid} was reworded or removed"))
    if not added:
        fails.append(Failure(assertion, "no correction row was appended"))
        return fails
    if len(added) > 1:
        fails.append(Failure(assertion, f"more than one row was appended: {added}"))
    rid, _label = added[0]
    if not re.fullmatch(r"S\d+[a-z]*\+\d+", rid):
        fails.append(Failure(
            assertion,
            f"correction row {rid} is not a `+N` correction under an existing normal row",
        ))
        return fails

    # The table cell is a derived handle; `## Row Contracts` is authoritative.
    contracts = parse_row_contracts(ctx.progress() or "")
    body = contracts.get(rid)
    if body is None or not body["text"]:
        fails.append(Failure(assertion, f"{rid} has no exact text in `## Row Contracts`"))
        return fails
    verbatim = "compose the feature label from the base module's value rather than hard-coding the word base"
    if verbatim.lower() not in body["text"].lower():
        fails.append(Failure(assertion, f"the recorded contract paraphrases the request: {body['text']!r}"))
    affects = [v.strip() for v in body["attributes"].get("affects", "").split(",") if v.strip()]
    if not affects:
        fails.append(Failure(assertion, f"{rid} names no affected Exit Criterion — the fix could close unproven"))
    else:
        exit_ids = {rid_ for rid_, _, _ in after if rid_.startswith("E")}
        for target in affects:
            if target not in exit_ids:
                fails.append(Failure(assertion, f"{rid} affects {target}, which is not a row in the ledger"))
    return fails


def build_no_row_appended(ctx: Ctx) -> list[Failure]:
    """Case (B): a distinct outcome the phase does not contain adds no row and
    writes no code, in auto mode as much as in manual.

    The route is the backlog. Wave 3 closed the `mano start` loop — with a
    ledger present, start refuses and sends the human straight back here — so
    naming it is a defect, not a courtesy.
    """
    assertion = "build_no_row_appended"
    fails = _ledger_rows_unchanged(ctx, assertion, allow_status_change=False)
    banned = re.compile(r"debug|timing", re.IGNORECASE)
    for rel in ctx.source_files():
        if banned.search(rel) or banned.search((ctx.project_root() / rel).read_text(encoding="utf-8", errors="ignore")):
            fails.append(Failure(assertion, f"out-of-phase work was implemented in {rel}"))
    fails.extend(Failure(assertion, f.detail) for f in build_offered_backlog_defer(ctx))
    return fails


# --- wave 3: the build path's contracts ---------------------------------------


def _seeded_sources(ctx: Ctx) -> set[str]:
    """Project-relative paths the fixture seeded through its `project/` prefix."""
    return {name[len("project/"):] for name in ctx.fixture_snapshot if name.startswith("project/")}


def _seeded_output_path(name: str, phase: int | None) -> str:
    """Where `run.seed_fixture` puts a fixture file under `_mano_output/`."""
    if "/" in name:
        return name  # nested fixture paths are copied verbatim
    if phase is not None and name == "stories-README.md":
        return f"phase-{phase}/stories/README.md"
    if phase is not None and name.startswith("story-") and name.endswith(".md"):
        return f"phase-{phase}/stories/{name}"
    return _phase_relative(name, phase)


def _wrote_nothing(ctx: Ctx, assertion: str) -> list[Failure]:
    """No source appeared and no Mano artifact changed, byte for byte.

    A refusal that leaves a half-written ledger, an edited brief, or one stray
    source file is not a refusal — it is a partial action the human now has to
    unpick.
    """
    fails = []
    new_source = sorted(ctx.source_files() - _seeded_sources(ctx))
    if new_source:
        fails.append(Failure(assertion, f"source was written despite the refusal: {new_source}"))
    for name, original in sorted(ctx.fixture_snapshot.items()):
        if name.startswith("project/"):
            continue
        current = ctx.output_text(_seeded_output_path(name, ctx.phase))
        if current is None:
            fails.append(Failure(assertion, f"{name} was deleted"))
        elif current != original:
            fails.append(Failure(assertion, f"{name} was modified despite the refusal"))
    return fails


def build_refused_invalid_ledger(ctx: Ctx) -> list[Failure]:
    """B4: a ledger that exists and does not validate is a hard stop.

    The failure this pins is the *quiet* one: a versionless or malformed ledger
    used to read as no ledger at all, so build cheerfully ran `init` over the
    top of work someone had already done.
    """
    assertion = "build_refused_invalid_ledger"
    fails = _wrote_nothing(ctx, assertion)
    response = ctx.transcript
    if not re.search(r"invalid", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the response never says the ledger is invalid"))
    if not re.search(r"delete", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the response does not give the one repair instruction (delete and re-run)"))
    if re.search(r"\bmigrat", response, re.IGNORECASE) and not re.search(
        r"no migration|not supported|cannot be migrated", response, re.IGNORECASE
    ):
        fails.append(Failure(assertion, "the response offers a migration; there is no migration path"))
    return fails


def build_refused_two_ledgers_when_invalid(ctx: Ctx) -> list[Failure]:
    """B4's second half: the dual-ledger refusal used to be skipped in exactly
    the state that most needed it, because it only fired when progress parsed."""
    assertion = "build_refused_two_ledgers_when_invalid"
    fails = _wrote_nothing(ctx, assertion)
    response = ctx.transcript
    if not re.search(r"both|two ledgers|one ledger", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the response does not report that the phase holds both ledgers"))
    return fails


def build_refused_edited_brief(ctx: Ctx) -> list[Failure]:
    """D12: the addressed brief is immutable once a ledger exists."""
    assertion = "build_refused_edited_brief"
    fails = _wrote_nothing(ctx, assertion)
    response = ctx.transcript
    if not re.search(r"brief.{0,40}chang|chang.{0,40}brief|contract", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the response does not name the brief change as the cause"))
    if re.search(r"i(?:'ll| will) (?:update|re-?fingerprint|migrate|reconcile)", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the response offers to reconcile or migrate the ledger"))
    return fails


def build_worked_the_pending_rework(ctx: Ctx) -> list[Failure]:
    """D4: a pending review finding routes to build even though every row is
    already `done` — and it is resolved by fixing the thing, not by editing the
    event."""
    assertion = "build_worked_the_pending_rework"
    fails = []
    contracts = parse_row_contracts(ctx.progress() or "")
    rows = ctx.progress_rows()
    rework = [(rid, status) for rid, _, status in rows if rid.startswith("R")]
    if not rework:
        return [Failure(assertion, "the rework event disappeared from the ledger")]
    if any(status == "pending" for _, status in rework):
        fails.append(Failure(assertion, f"the finding was never resolved: {rework}"))
    if any(status == "dismissed" for _, status in rework):
        fails.append(Failure(assertion, "the finding was dismissed; only the human may dismiss one"))
    body = contracts.get("R1")
    if body is None or "base+feature+release" not in (body["text"] or ""):
        fails.append(Failure(assertion, "R1's exact text no longer round-trips"))

    # The defect the finding names is actually fixed.
    proc = subprocess.run(
        ["node", "-e", "process.stdout.write(String(require('./src/release-stage.js')))"],
        cwd=ctx.project_root(), capture_output=True, text=True,
    )
    if proc.stdout.strip() != "base+feature+release":
        fails.append(Failure(assertion, f"the defect was not fixed: release stage exports {proc.stdout.strip()!r}"))

    # Case (A): a defect in work already promised reopens existing rows. It does
    # not append a correction row, and it does not create stories.
    seeded_ids = {rid for rid, _, _ in _rows_of(ctx.fixture_text("progress.md") or "")}
    added = [rid for rid, _, _ in rows if rid not in seeded_ids]
    if added:
        fails.append(Failure(assertion, f"rows were appended for work an existing row already required: {added}"))
    if ctx.story_files() or ctx.readme() is not None:
        fails.append(Failure(assertion, "story files were written on the build path"))
    return fails


def review_persisted_findings_as_rework(ctx: Ctx) -> list[Failure]:
    """D4 + B6: a confirmed build-path finding becomes durable ledger state, and
    review never routes it through the stories path."""
    assertion = "review_persisted_findings_as_rework"
    fails = []
    rows = ctx.progress_rows()
    rework = [(rid, status) for rid, _, status in rows if rid.startswith("R")]
    if not rework:
        fails.append(Failure(
            assertion,
            "no R… rework event was written — the finding lives only in the conversation, "
            "which a compaction or a restart loses",
        ))
    else:
        contracts = parse_row_contracts(ctx.progress() or "")
        for rid, _ in rework:
            body = contracts.get(rid)
            if body is None or not (body["text"] or "").strip():
                fails.append(Failure(assertion, f"{rid} has no exact text in `## Row Contracts`"))

    # No Scope row may move: review does not decide work is done or undone.
    seeded = [(rid, status) for rid, _, status in _rows_of(ctx.fixture_text("progress.md") or "")]
    after = {rid: status for rid, _, status in rows}
    for rid, status in seeded:
        if after.get(rid) != status:
            fails.append(Failure(assertion, f"review changed {rid} from {status} to {after.get(rid)}"))

    if ctx.story_files() or ctx.readme() is not None:
        fails.append(Failure(assertion, "review created story artifacts on a build-path phase"))
    if re.search(r"mano\s+stories|mano\s+dev\b", ctx.transcript, re.IGNORECASE):
        fails.append(Failure(
            assertion,
            "review routed a build-path finding to mano stories / mano dev, which would "
            "give the phase a second ledger",
        ))
    if not re.search(r"mano\s+build", ctx.transcript, re.IGNORECASE):
        fails.append(Failure(assertion, "review does not route the finding to mano build"))
    return fails


def start_amend_previewed_before_writing(ctx: Ctx) -> list[Failure]:
    """The amendment shows the complete proposed scope and writes nothing.

    Checked against the state after step 1 specifically: comparing only the
    final state cannot tell a preview-then-write from a write-then-describe.
    """
    assertion = "start_amend_previewed_before_writing"
    if not ctx.steps:
        return [Failure(assertion, "case ran no steps")]
    fails = []
    changed = ctx.changed_in_step(1)
    if changed:
        fails.append(Failure(assertion, f"step 1 wrote before any approval: {sorted(changed)}"))
    proposal = ctx.step(1).final_response
    for section in ("Phase Goal", "Phase Scope", "Exit Criteria"):
        if section.lower() not in proposal.lower():
            fails.append(Failure(assertion, f"the proposal omits `## {section}` — it is not the complete revised scope"))
    return fails


def start_amend_wrote_only_after_approval(ctx: Ctx) -> list[Failure]:
    """After approval the brief is revised in place — and nothing else moves."""
    assertion = "start_amend_wrote_only_after_approval"
    fails = []
    brief = ctx.artifact_text("phase-brief.md")
    if brief is None:
        return [Failure(assertion, "the phase brief is gone")]
    seeded = ctx.fixture_text("phase-brief.md") or ""
    if brief == seeded:
        fails.append(Failure(assertion, "the brief was never amended"))
    if "release" not in brief.lower():
        fails.append(Failure(assertion, "the amended brief does not contain the requested change"))

    # An amendment creates no phase, writes no ledger, and moves no backlog item.
    phases = sorted(p.name for p in ctx.phase_dirs())
    if phases != ["phase-1"]:
        fails.append(Failure(assertion, f"phase directories are {phases}; an amendment creates no phase"))
    if ctx.progress() is not None or ctx.readme() is not None:
        fails.append(Failure(assertion, "an amendment wrote a ledger"))
    if (ctx.backlog() or "") != (ctx.fixture_text("backlog.md") or ""):
        fails.append(Failure(assertion, "an amendment changed a backlog item's status"))
    return fails


def start_amend_refused_with_ledger(ctx: Ctx) -> list[Failure]:
    """B5: with a ledger present the brief is frozen — and the refusal must not
    point back at a command that points back here."""
    assertion = "start_amend_refused_with_ledger"
    fails = _wrote_nothing(ctx, assertion)
    response = ctx.transcript
    if not re.search(r"ledger|progress\.md|being built|already", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the refusal does not say why the brief is frozen"))
    # The loop: start → stories → sees progress.md → start.
    if re.search(r"mano\s+stories", response, re.IGNORECASE):
        fails.append(Failure(
            assertion,
            "the refusal routes to `mano stories`, which refuses a build-path phase and routes back here",
        ))
    if not re.search(r"mano\s+build|backlog|next phase", response, re.IGNORECASE):
        fails.append(Failure(assertion, "the refusal names no onward route"))
    return fails


# --- two-phase extension ------------------------------------------------------
#
# One fixture, one ordered case: a finished Phase 1 (source plus four cumulative
# artifacts) and an active Phase 2 that extends the same feature. Phase 2 must
# edit each artifact it owns rather than re-emit it, must leave every untouched
# region byte-identical, and must never reach into Phase 1's own brief.

# The canary lives only in phase-1/phase-brief.md. Phase 2 has no route to it,
# so its appearance anywhere means that non-cumulative artifact was read.
CROSS_PHASE_BRIEF_CANARY = "kestrel-spike-parked"

# Which artifact each step of the chain is allowed to write. `mano rules`
# additionally resolves its projected rule-gap through the backlog writer.
TWO_PHASE_STEP_OWNERSHIP = {
    1: ("mano spec", {"tech-spec.md"}),
    2: ("mano rules", {"project-rules.md", "backlog.md"}),
    3: ("mano ux", {"ux-flow.md"}),
    4: ("mano ui", {"design-brief.md", "phase-2/design-preview.html"}),
    5: ("mano build", {"phase-2/progress.md"}),
}

# Lines that existed before Phase 2 ran and that no Phase 2 edit has any reason
# to touch. Order matters too — these must still appear in this sequence.
TWO_PHASE_ARTIFACT_ANCHORS = {
    "tech-spec.md": [
        "<!-- sentinel: spec-phase-1-must-survive -->",
        "- Node.js 18+, CommonJS, no runtime dependencies.",
        "An entry is a plain object: `{ title: string, status: \"open\" | \"blocked\" | \"done\" }`.",
        "- Persistence, HTTP transport, HTML output, and colour.",
    ],
    "project-rules.md": [
        "<!-- sentinel: rules-phase-1-must-survive -->",
        "Accessibility level: WCAG 2.1 AA",
        "## Module Shape",
        "## Composition",
    ],
    "ux-flow.md": [
        "<!-- sentinel: ux-phase-1-must-survive -->",
        "## Phase 1 — Read one entry",
        "2. Every entry appears as a single line: its title, then its status.",
    ],
    "design-brief.md": [
        "<!-- sentinel: design-phase-1-must-survive -->",
        "| Primary | Signal blue | `#2457D6` |",
        "### Phase 1 — Digest List",
        "### EntryLine",
    ],
}

TWO_PHASE_ENTRIES = [
    {"title": "Launch review", "status": "open"},
    {"title": "Data migration", "status": "done"},
    {"title": "Vendor contract", "status": "blocked"},
    {"title": "Pricing page", "status": "open"},
]

TWO_PHASE_EXPECTED_RENDER = [
    "## Open",
    "- Launch review — open",
    "- Pricing page — open",
    "## Blocked",
    "- Vendor contract — blocked",
    "## Done",
    "- Data migration — done",
]


def _node_probe(root: Path, script: str) -> tuple[object | None, str]:
    """Run a tiny node script in the built project and parse its JSON stdout."""
    try:
        proc = subprocess.run(
            ["node", "-e", script], cwd=root, capture_output=True, text=True, timeout=60
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"could not run node: {exc}"
    if proc.returncode != 0:
        detail = (proc.stderr.strip().splitlines() or [""])[-1]
        return None, f"node exited {proc.returncode}: {detail[:300]}"
    try:
        return json.loads(proc.stdout.strip()), ""
    except json.JSONDecodeError:
        return None, f"probe printed non-JSON: {proc.stdout.strip()[:200]!r}"


def two_phase_one_behaviour_survives(ctx: Ctx) -> list[Failure]:
    """Phase 1's promise still holds after Phase 2 built on top of it."""
    assertion = "two_phase_one_behaviour_survives"
    root = ctx.project_root()
    entry = root / "src" / "digest" / "format-entry.js"
    index = root / "src" / "digest" / "index.js"
    for path in (entry, index):
        if not path.is_file():
            return [Failure(assertion, f"{path.relative_to(root).as_posix()} is gone after Phase 2")]
    script = (
        f"const fe = require({str(entry)!r});"
        f"const ix = require({str(index)!r});"
        "process.stdout.write(JSON.stringify({"
        "direct: fe.formatEntry({ title: 'Launch review', status: 'open' }),"
        "viaIndex: typeof ix.formatEntry === 'function'"
        " ? ix.formatEntry({ title: 'Launch review', status: 'open' }) : null"
        "}));"
    )
    data, error = _node_probe(root, script)
    if data is None:
        return [Failure(assertion, f"Phase 1 entry line no longer loads — {error}")]
    fails = []
    if data.get("direct") != "Launch review — open":
        fails.append(Failure(
            assertion,
            f"formatEntry now returns {data.get('direct')!r}, not 'Launch review — open'",
        ))
    if data.get("viaIndex") != "Launch review — open":
        fails.append(Failure(
            assertion,
            f"index.js no longer re-exports the Phase 1 entry line (got {data.get('viaIndex')!r})",
        ))
    return fails


def two_phase_extension_behaviour_works(ctx: Ctx) -> list[Failure]:
    """Every Phase 2 Exit Criterion, exercised rather than inferred."""
    assertion = "two_phase_extension_behaviour_works"
    root = ctx.project_root()
    index = root / "src" / "digest" / "index.js"
    if not index.is_file():
        return [Failure(assertion, "src/digest/index.js is missing")]
    entries = json.dumps(TWO_PHASE_ENTRIES)
    script = (
        f"const ix = require({str(index)!r});"
        f"const entries = {entries};"
        "const out = { exports: Object.keys(ix).sort() };"
        "if (typeof ix.groupEntries === 'function') {"
        "  out.groups = ix.groupEntries(entries);"
        "  out.empty = ix.groupEntries([]);"
        "}"
        "if (typeof ix.renderDigest === 'function') {"
        "  out.rendered = ix.renderDigest(entries);"
        "}"
        "process.stdout.write(JSON.stringify(out));"
    )
    data, error = _node_probe(root, script)
    if data is None:
        return [Failure(assertion, f"the Phase 2 surface does not load — {error}")]

    fails = []
    missing = [
        name for name in ("formatEntry", "groupEntries", "renderDigest")
        if name not in (data.get("exports") or [])
    ]
    if missing:
        fails.append(Failure(assertion, f"index.js does not export {', '.join(missing)}"))

    groups = data.get("groups")
    if groups is None:
        fails.append(Failure(assertion, "groupEntries is not callable from index.js"))
    else:
        got = [(g.get("status"), [e.get("title") for e in (g.get("entries") or [])]) for g in groups]
        want = [
            ("open", ["Launch review", "Pricing page"]),
            ("blocked", ["Vendor contract"]),
            ("done", ["Data migration"]),
        ]
        if got != want:
            fails.append(Failure(assertion, f"groupEntries returned {got!r}, expected {want!r}"))
        if data.get("empty") != []:
            fails.append(Failure(
                assertion,
                f"groupEntries([]) returned {data.get('empty')!r}, expected an empty array",
            ))

    rendered = data.get("rendered")
    if rendered is None:
        fails.append(Failure(assertion, "renderDigest is not callable from index.js"))
    else:
        lines = [line for line in str(rendered).split("\n") if line.strip()]
        if lines != TWO_PHASE_EXPECTED_RENDER:
            fails.append(Failure(
                assertion,
                f"renderDigest produced {lines!r}, expected {TWO_PHASE_EXPECTED_RENDER!r}",
            ))
    return fails


def two_phase_source_untouched_regions_preserved(ctx: Ctx) -> list[Failure]:
    """A file Phase 2 had no reason to open is byte-identical; the one file it
    must extend keeps its pre-existing lines exactly."""
    assertion = "two_phase_source_untouched_regions_preserved"
    fails = []
    for relative in (
        "src/digest/format-entry.js",
        "spec/format-entry.spec.js",
        "package.json",
    ):
        seeded = ctx.fixture_text(f"project/{relative}")
        current = ctx.source_text(relative)
        if current is None:
            fails.append(Failure(assertion, f"{relative} was deleted"))
        elif current != seeded:
            fails.append(Failure(assertion, f"{relative} was rewritten; Phase 2 does not own it"))

    index = ctx.source_text("src/digest/index.js")
    if index is None:
        return fails + [Failure(assertion, "src/digest/index.js was deleted")]
    for line in (
        '"use strict";',
        "// sentinel: phase-1-public-surface-must-survive",
        'const { formatEntry } = require("./format-entry.js");',
    ):
        if line not in index:
            fails.append(Failure(
                assertion,
                f"index.js lost a pre-existing line it should have kept: {line!r}",
            ))
    return fails


def two_phase_artifacts_extended_not_reemitted(ctx: Ctx) -> list[Failure]:
    """Each cumulative artifact grew, and every anchored Phase 1 line survived
    verbatim. A re-emitted artifact drops or paraphrases those lines."""
    assertion = "two_phase_artifacts_extended_not_reemitted"
    fails = []
    for name, anchors in TWO_PHASE_ARTIFACT_ANCHORS.items():
        current = ctx.output_text(name)
        if current is None:
            fails.append(Failure(assertion, f"{name} is missing after Phase 2"))
            continue
        seeded = ctx.fixture_text(name)
        if seeded is not None and current == seeded:
            fails.append(Failure(assertion, f"{name} was never extended for Phase 2"))
        for anchor in anchors:
            if anchor not in current:
                fails.append(Failure(assertion, f"{name} lost a Phase 1 line: {anchor!r}"))
    return fails


def two_phase_no_duplicated_or_reordered_sections(ctx: Ctx) -> list[Failure]:
    """Extension adds sections; re-emission duplicates or reshuffles them."""
    assertion = "two_phase_no_duplicated_or_reordered_sections"
    fails = []
    for name, anchors in TWO_PHASE_ARTIFACT_ANCHORS.items():
        current = ctx.output_text(name)
        if current is None:
            continue
        headings = [
            m.group(1).strip()
            for m in re.finditer(r"^#{1,6}\s+(.*?)\s*$", current, re.MULTILINE)
        ]
        duplicates = sorted({h for h in headings if headings.count(h) > 1})
        if duplicates:
            fails.append(Failure(assertion, f"{name} has duplicated heading(s): {duplicates}"))
        positions = [current.find(a) for a in anchors if a in current]
        if positions != sorted(positions):
            fails.append(Failure(assertion, f"{name} reordered its pre-existing sections"))

    ids = [rid for rid, _, _ in ctx.progress_rows()]
    repeated = sorted({rid for rid in ids if ids.count(rid) > 1})
    if repeated:
        fails.append(Failure(assertion, f"ledger has duplicate row id(s): {repeated}"))

    backlog = ctx.backlog() or ""
    titles = re.findall(r"^###\s+(.*?)\s*$", backlog, re.MULTILINE)
    dupe_items = sorted({t for t in titles if titles.count(t) > 1})
    if dupe_items:
        fails.append(Failure(assertion, f"backlog has duplicate item(s): {dupe_items}"))
    return fails


def two_phase_identity_and_ledger_held(ctx: Ctx) -> list[Failure]:
    """Five fresh sessions in a row, and the active phase never drifted."""
    assertion = "two_phase_identity_and_ledger_held"
    fails = []
    phase_dirs = sorted(p.name for p in ctx.phase_dirs())
    if phase_dirs != ["phase-1", "phase-2"]:
        fails.append(Failure(assertion, f"phase directories are {phase_dirs}, expected phase-1 and phase-2"))

    for name in ("phase-1/phase-brief.md", "phase-1/progress.md"):
        if ctx.output_text(name) != ctx.fixture_text(name):
            fails.append(Failure(assertion, f"{name} was modified — Phase 1 is closed"))
    if ctx.output_text("phase-2/phase-brief.md") != ctx.fixture_text("phase-brief.md"):
        fails.append(Failure(assertion, "phase-2/phase-brief.md was edited; no step owns the brief"))

    if (ctx.output_dir / "phase-2" / "stories").is_dir():
        fails.append(Failure(assertion, "a stories/ directory appeared in a build-path phase"))

    rows = ctx.progress_rows()
    if not rows:
        fails.append(Failure(assertion, "no phase-2/progress.md ledger after the build step"))
    else:
        open_rows = [
            f"{rid} ({status})" for rid, _, status in rows
            if (rid.startswith("S") and status != "done") or (rid.startswith("E") and status != "met")
        ]
        if open_rows:
            fails.append(Failure(assertion, f"ledger still open: {', '.join(open_rows)}"))
    return fails


def two_phase_did_not_read_other_phase_brief(ctx: Ctx) -> list[Failure]:
    """The canary reaches a response or an artifact only by opening Phase 1's
    own brief, which no Phase 2 action may do. (Absence cannot prove no read
    happened — it is the strongest signal a file-and-response harness has.)"""
    assertion = "two_phase_did_not_read_other_phase_brief"
    fails = []
    if CROSS_PHASE_BRIEF_CANARY.lower() in ctx.all_responses().lower():
        fails.append(Failure(
            assertion,
            "Phase 1's brief-only content surfaced in a response — that brief was read",
        ))
    for name in sorted(ctx.output_files()):
        if name == "phase-1/phase-brief.md":
            continue
        text = ctx.output_text(name) or ""
        if CROSS_PHASE_BRIEF_CANARY.lower() in text.lower():
            fails.append(Failure(assertion, f"Phase 1's brief-only content was copied into {name}"))
    for relative in ctx.source_files():
        text = ctx.source_text(relative) or ""
        if CROSS_PHASE_BRIEF_CANARY.lower() in text.lower():
            fails.append(Failure(assertion, f"Phase 1's brief-only content was copied into {relative}"))
    return fails


def two_phase_each_step_wrote_only_its_own_artifact(ctx: Ctx) -> list[Failure]:
    """Per-step ownership across the session boundary: each command changed the
    artifact it owns and nothing else."""
    assertion = "two_phase_each_step_wrote_only_its_own_artifact"
    if not ctx.steps:
        return [Failure(assertion, "case ran no steps")]
    fails = []
    for index, (label, allowed) in TWO_PHASE_STEP_OWNERSHIP.items():
        if index > len(ctx.steps):
            fails.append(Failure(assertion, f"step {index} ({label}) never ran"))
            continue
        changed = ctx.changed_in_step(index)
        trespass = sorted(changed - allowed)
        if trespass:
            fails.append(Failure(
                assertion,
                f"step {index} ({label}) wrote artifacts it does not own: {trespass}",
            ))
    return fails



# --- wave 4: implementation entry, grouping, invocation arguments -------------


def _row_status(rows: list[tuple[str, str, str]], row_id: str) -> str | None:
    for rid, _label, status in rows:
        if rid == row_id:
            return status
    return None


def _registry_probe(root: Path, body: str) -> tuple[object | None, str]:
    """Exercise one registry criterion in a fresh node process.

    Each criterion gets its own process on purpose: the registry is in-memory
    and process-lived, so sharing one probe between criteria would let an
    earlier call's state stand in as the later one's evidence.
    """
    script = (
        "const r = require('./src/registry.js');"
        + body
        + "process.stdout.write(JSON.stringify(out));"
    )
    return _node_probe(root, script)


# Every Exit leaf of the build-single-pass fixture, exercised on its own.
SINGLE_PASS_CRITERIA: dict[str, tuple[str, object]] = {
    "E1a": ("const n = r.add('alpha'); const out = [n, r.list()];", [1, ["alpha"]]),
    "E1b": ("r.add('alpha'); const n = r.add('alpha'); const out = [n, r.list()];", [-1, ["alpha"]]),
    "E1c": ("r.add('alpha'); r.add('beta'); const n = r.clear(); const out = [n, r.list()];", [2, []]),
}

SINGLE_PASS_FORMAT_CRITERIA: dict[str, tuple[str, object]] = {
    "E2a": ("r.add('alpha'); r.add('beta'); const out = require('./src/format.js').line();", "alpha, beta"),
    "E2b": ("const out = require('./src/format.js').line();", ""),
}


def single_pass_rows_are_the_briefs_two_levels(ctx: Ctx) -> list[Failure]:
    """4.2: the ledger's addresses and labels are derived from the brief's two
    levels, not composed. A model that flattened, renumbered, or relabelled the
    scope shows up here before any behaviour is checked."""
    assertion = "single_pass_rows_are_the_briefs_two_levels"
    rows = ctx.progress_rows()
    if not rows:
        return [Failure(assertion, "no progress.md ledger after the run")]
    expected_scope = {
        "S1a": "Registry core — List",
        "S1b": "Registry core — Add",
        "S1c": "Registry core — Reject a duplicate",
        "S1d": "Registry core — Clear",
        "S2a": "Formatting — Joined line",
    }
    fails = []
    actual_scope = {rid: label for rid, label, _ in rows if rid.startswith("S")}
    if actual_scope != expected_scope:
        fails.append(Failure(
            assertion,
            f"scope rows are not the brief's category+leaf derivation: {actual_scope}",
        ))
    exit_ids = [rid for rid, _, _ in rows if rid.startswith("E")]
    if exit_ids != ["E1a", "E1b", "E1c", "E2a", "E2b"]:
        fails.append(Failure(assertion, f"exit rows are not the brief's leaves: {exit_ids}"))
    return fails


def single_pass_every_leaf_has_its_own_evidence(ctx: Ctx) -> list[Failure]:
    """4.3: a pass may cover several rows, but every leaf is proven separately.

    Each Exit leaf marked `met` is exercised in its own process. A leaf that is
    `met` and does not hold is exactly the failure grouping could introduce:
    one shared verification standing in for evidence it never produced.
    """
    assertion = "single_pass_every_leaf_has_its_own_evidence"
    rows = ctx.progress_rows()
    if not rows:
        return [Failure(assertion, "no progress.md ledger after the run")]
    root = ctx.project_root()
    fails = []
    for row_id, (body, expected) in {**SINGLE_PASS_CRITERIA, **SINGLE_PASS_FORMAT_CRITERIA}.items():
        status = _row_status(rows, row_id)
        if status != "met":
            continue
        value, error = _registry_probe(root, body)
        if error:
            fails.append(Failure(assertion, f"{row_id} is met but could not be exercised — {error}"))
        elif value != expected:
            fails.append(Failure(assertion, f"{row_id} is met but returned {value!r}, expected {expected!r}"))
    # A Scope row marked done whose behaviour is missing is the same defect
    # seen from the other table.
    for row_id, symbol in (("S1a", "list"), ("S1b", "add"), ("S1c", "add"), ("S1d", "clear")):
        if _row_status(rows, row_id) != "done":
            continue
        value, error = _node_probe(
            root,
            "const r = require('./src/registry.js');"
            f"process.stdout.write(JSON.stringify(typeof r[{symbol!r}]));",
        )
        if error or value != "function":
            fails.append(Failure(assertion, f"{row_id} is done but registry.{symbol}() is not callable"))
    if _row_status(rows, "S2a") == "done":
        value, error = _node_probe(
            root,
            "process.stdout.write(JSON.stringify(typeof require('./src/format.js').line));",
        )
        if error or value != "function":
            fails.append(Failure(assertion, "S2a is done but format.line() is not callable"))
    return fails


def single_pass_completed_the_phase(ctx: Ctx) -> list[Failure]:
    """The phase is genuinely built: every Scope leaf done, every Exit leaf met
    or needs-human, and no leaf left open behind a completion claim."""
    assertion = "single_pass_completed_the_phase"
    rows = ctx.progress_rows()
    if not rows:
        return [Failure(assertion, "no progress.md ledger after the run")]
    open_rows = [
        f"{rid} ({status})"
        for rid, _, status in rows
        if (rid.startswith("S") and status != "done")
        or (rid.startswith("E") and status not in {"met", "needs-human"})
    ]
    if open_rows:
        return [Failure(assertion, f"ledger still open: {', '.join(open_rows)}")]
    return []


def group_stopped_at_the_category_gate(ctx: Ctx) -> list[Failure]:
    """4.3: a pass never crosses a category, and a per-row gate ends it.

    The fixture's category 2 needs a capacity default no artifact owns, so gate
    6.2 fires on `S2a`. The rows before it are ordinary work and must close and
    be proven; `S2a` must stay open with none of its behaviour written.
    """
    assertion = "group_stopped_at_the_category_gate"
    rows = ctx.progress_rows()
    if not rows:
        return [Failure(assertion, "no progress.md ledger after the run")]
    fails = _ledger_rows_unchanged(ctx, assertion, allow_status_change=True)
    if _row_status(rows, "S2a") != "pending":
        fails.append(Failure(assertion, "S2a moved despite the spec-owned default it needs being missing"))
    if _row_status(rows, "E2a") not in {"pending", None}:
        fails.append(Failure(assertion, "E2a was marked without the capacity behaviour existing"))
    root = ctx.project_root()
    # The rows the pass did close must actually work — a partial pass closes
    # only what it proved.
    for row_id, body, expected in (
        ("S1b", "const n = r.add('alpha'); const out = [n, r.list()];", [1, ["alpha"]]),
        ("S1c", "r.add('alpha'); r.add('beta'); const n = r.clear(); const out = [n, r.list()];", [2, []]),
    ):
        if _row_status(rows, row_id) != "done":
            continue
        value, error = _registry_probe(root, body)
        if error:
            fails.append(Failure(assertion, f"{row_id} is done but could not be exercised — {error}"))
        elif value != expected:
            fails.append(Failure(assertion, f"{row_id} is done but returned {value!r}, expected {expected!r}"))
    # No capacity behaviour may exist: the gate fired before any of it.
    registry = ctx.source_text("src/registry.js") or ""
    if re.search(r"\b(?:max|capacity|limit|cap)\w*\s*[=:]", registry, re.IGNORECASE):
        fails.append(Failure(assertion, "a capacity value was invented in src/registry.js"))
    fails.extend(Failure(assertion, f.detail) for f in build_routed_to_spec(ctx))
    return fails


def group_resumed_without_reopening_proven_rows(ctx: Ctx) -> list[Failure]:
    """A second run after a partial pass resumes at the first unresolved leaf.

    It must not rebuild what step 1 proved, and must not close the row whose
    gate is still unanswered — a blocked row does not become buildable because
    the command was typed again.
    """
    assertion = "group_resumed_without_reopening_proven_rows"
    fails = []
    after_one = ctx.step(1).progress_rows()
    after_two = ctx.step(2).progress_rows()
    if not after_one or not after_two:
        return [Failure(assertion, "a step left no ledger to compare")]
    for rid, _label, status in after_one:
        if status in {"done", "met"}:
            now = _row_status(after_two, rid)
            if now != status:
                fails.append(Failure(assertion, f"{rid} went {status!r} → {now!r} on the resumed run"))
    if _row_status(after_two, "S2a") != "pending":
        fails.append(Failure(assertion, "the blocked row S2a closed on a re-run without its gap being answered"))
    return fails


def build_flat_rows_stayed_flat(ctx: Ctx) -> list[Failure]:
    """4.2: a flat brief is never migrated into categories.

    The ledger's addresses come from the brief's own shape, so a flat scope
    yields `S1`, `S2`, `S3` — inventing leaf letters would silently rewrite the
    human's decomposition.
    """
    assertion = "build_flat_rows_stayed_flat"
    scope_ids = [rid for rid, _, _ in ctx.progress_rows() if rid.startswith("S")]
    if not scope_ids:
        return [Failure(assertion, "no scope rows in the ledger")]
    lettered = [rid for rid in scope_ids if re.fullmatch(r"S\d+[a-z]+", rid)]
    if lettered:
        return [Failure(assertion, f"a flat brief grew lettered leaves: {lettered}")]
    return []


def build_offered_backlog_defer(ctx: Ctx) -> list[Failure]:
    """Case B's route is the backlog, not `mano start`.

    Sending the human to `mano start` with a ledger present is the loop wave 3
    closed: start refuses, and they arrive back here. Nothing may be written
    either — the defer flow previews the item and waits for approval of its
    fields.
    """
    assertion = "build_offered_backlog_defer"
    fails = []
    if not re.search(r"backlog", ctx.transcript, re.IGNORECASE):
        compact = " ".join(ctx.transcript.split())
        fails.append(Failure(assertion, f"the distinct outcome was not offered to the backlog: {compact[-300:]!r}"))
    if re.search(r"`?mano[ -]start", ctx.transcript, re.IGNORECASE):
        fails.append(Failure(assertion, "the human was routed to mano start, which refuses while a ledger exists"))
    before = ctx.baseline.get("backlog.md")
    after = ctx.backlog()
    if before != after:
        fails.append(Failure(assertion, "a backlog item was written before its fields were approved"))
    return fails


def build_arg_stopped_for_the_pending_rework(ctx: Ctx) -> list[Failure]:
    """4.4: durable state outranks a new argument.

    A pending `R…` event is the work the ledger already routes to. A new
    correction typed at invocation must write nothing at all — not a row, not a
    status, not code — until that event is resolved or dismissed.
    """
    assertion = "build_arg_stopped_for_the_pending_rework"
    fails = _wrote_nothing(ctx, assertion)
    ledger = ctx.progress() or ""
    if not re.search(r"^\|\s*R1\s*\|.*\|\s*pending\s*\|", ledger, re.M):
        fails.append(Failure(assertion, "R1 is no longer pending — the argument displaced the open event"))
    return fails


def build_no_ledger_argument_created_nothing(ctx: Ctx) -> list[Failure]:
    """4.4: with no ledger there is nothing to correct.

    Pre-flight must not run and `init` must not be called, so the refusal is
    visible as the absence of a ledger. The route is `mano start`, which is the
    one command that may still revise an unimplemented brief.
    """
    assertion = "build_no_ledger_argument_created_nothing"
    fails = []
    if ctx.progress() is not None:
        fails.append(Failure(assertion, "a ledger was created to hold the rejected argument"))
    written = sorted(ctx.source_files() - _seeded_sources(ctx))
    if written:
        fails.append(Failure(assertion, f"code was written for a rejected argument: {written}"))
    if ctx.backlog() != ctx.baseline.get("backlog.md"):
        fails.append(Failure(assertion, "a backlog item was written for a rejected argument"))
    fails.extend(Failure(assertion, f.detail) for f in build_routed_to_start(ctx))
    return fails


def auto_reached_build_without_story_files(ctx: Ctx) -> list[Failure]:
    """4.1: import → start → approve, in auto, ends at `mano build`.

    The path exists to produce a built phase from a document with no story
    files at all, so a `stories/` folder anywhere is proof the chain took the
    other path — and a missing ledger is proof it never reached build.
    """
    assertion = "auto_reached_build_without_story_files"
    fails = []
    stray = [f for f in ctx.output_files() if "stories/" in f.replace("\\", "/")]
    if stray:
        fails.append(Failure(assertion, f"the auto chain wrote story files: {sorted(stray)}"))
    if ctx.backlog() is None:
        fails.append(Failure(assertion, "mano import never wrote the backlog"))
    if ctx.artifact_text("phase-brief.md") is None:
        fails.append(Failure(assertion, "no phase brief — the chain never got past scope approval"))
    if ctx.progress() is None:
        fails.append(Failure(assertion, "no progress.md — the chain never reached mano build"))
    return fails


def auto_chain_stopped_before_review(ctx: Ctx) -> list[Failure]:
    """The chain's terminal action is implementation. Closing the phase is the
    human's, so a review entry means the chain ran one action too far."""
    assertion = "auto_chain_stopped_before_review"
    fails = []
    # The case starts from a bare document, so `reviews.md` can only exist if
    # the chain ran the one action it may never run.
    if ctx.output_text("reviews.md") is not None:
        fails.append(Failure(assertion, "the auto chain wrote reviews.md — it must stop before mano review"))
    if len(ctx.phase_dirs()) > 1:
        fails.append(Failure(assertion, "the auto chain scoped a second phase"))
    return fails


REGISTRY = {
    "stories_were_written": stories_were_written,
    "readme_index_exists": readme_index_exists,
    "filenames_have_slug": filenames_have_slug,
    "no_arrows_in_stories": no_arrows_in_stories,
    "no_phase_number_leak": no_phase_number_leak,
    "done_when_has_no_code_signature": done_when_has_no_code_signature,
    "has_out_of_scope": has_out_of_scope,
    "has_implementation_reference": has_implementation_reference,
    "tests_present_when_rules_require": tests_present_when_rules_require,
    "phase_goal_quality_covered": phase_goal_quality_covered,
    "public_class_documentation_rule_covered": public_class_documentation_rule_covered,
    # mano dev
    "dev_yolo_completed_all_pending": dev_yolo_completed_all_pending,
    "dev_yolo_output_discipline": dev_yolo_output_discipline,
    "dev_yolo_stopped_at_first_blocker": dev_yolo_stopped_at_first_blocker,
    "dev_yolo_interrupted_output_discipline": dev_yolo_interrupted_output_discipline,
    "dev_default_completed_only_next": dev_default_completed_only_next,
    "dev_default_output_discipline": dev_default_output_discipline,
    "dev_plain_words_order_gate": dev_plain_words_order_gate,
    # mano import
    "backlog_was_written": backlog_was_written,
    "backlog_has_items": backlog_has_items,
    "all_items_status_backlog": all_items_status_backlog,
    "no_phase_brief_written": no_phase_brief_written,
    "import_wrote_only_backlog": import_wrote_only_backlog,
    "backlog_covers_document_features": backlog_covers_document_features,
    "stated_tech_preference_preserved": stated_tech_preference_preserved,
    # post-hook finding triage
    "hook_triage_no_approval_left_artifacts_unchanged":
        hook_triage_no_approval_left_artifacts_unchanged,
    "hook_triage_offer_present": hook_triage_offer_present,
    "start_hook_triage_offer_present": start_hook_triage_offer_present,
    "rules_hook_triage_offer_present": rules_hook_triage_offer_present,
    "selected_hook_finding_applied_only_in_spec": selected_hook_finding_applied_only_in_spec,
    # review as a short triage inbox (wave 5)
    "review_opening_shape": review_opening_shape,
    "review_opening_kept_every_promise": review_opening_kept_every_promise,
    "review_sign_off_recorded_human_provenance": review_sign_off_recorded_human_provenance,
    "review_recorded_unanswered_questions": review_recorded_unanswered_questions,
    "review_echoed_findings_only": review_echoed_findings_only,
    "review_close_did_not_erase_the_finding": review_close_did_not_erase_the_finding,
    "review_followup_wrote_nothing_yet": review_followup_wrote_nothing_yet,
    "build_handoff_showed_validate_now": build_handoff_showed_validate_now,
    "review_opening_repeats_the_try_guidance": review_opening_repeats_the_try_guidance,
    # review hard gate
    "pending_review_gate_held": pending_review_gate_held,
    # mano start: rules visibility
    "start_kept_rules_visible_for_new_category": start_kept_rules_visible_for_new_category,
    # review: rejected scope
    "review_surfaced_rejection_candidates": review_surfaced_rejection_candidates,
    "review_triage_wrote_nothing_yet": review_triage_wrote_nothing_yet,
    "review_preserved_positive_summary": review_preserved_positive_summary,
    "review_one_exchange_close": review_one_exchange_close,
    # done-story immutability (ambient)
    "done_story_edit_routed": done_story_edit_routed,
    # hooks: check mode + legacy suggest
    "check_hook_ran_without_confirmation": check_hook_ran_without_confirmation,
    "legacy_blank_suggest_hook_surfaced": legacy_blank_suggest_hook_surfaced,
    # start: projection is the only backlog read
    "start_did_not_mine_backlog": start_did_not_mine_backlog,
    # stories mid-build
    "midbuild_lettered_story_inserted": midbuild_lettered_story_inserted,
    "existing_stories_unchanged": existing_stories_unchanged,
    # stories: pulling a backlog item into an already-open phase
    "midphase_item_assigned_to_open_phase": midphase_item_assigned_to_open_phase,
    "midphase_brief_untouched_and_flagged": midphase_brief_untouched_and_flagged,
    # mano ui
    "ui_phase_preview_owned_by_current_phase": ui_phase_preview_owned_by_current_phase,
    "ui_cumulative_brief_extended": ui_cumulative_brief_extended,
    "ui_prior_and_legacy_previews_unchanged": ui_prior_and_legacy_previews_unchanged,
    "ui_phase_preview_output_paths": ui_phase_preview_output_paths,
    "ui_no_phase_preview_wrote_nothing": ui_no_phase_preview_wrote_nothing,
    "ui_no_phase_preview_routes_to_start": ui_no_phase_preview_routes_to_start,
    # public-interface planning readiness
    "spec_public_interface_contract_complete": spec_public_interface_contract_complete,
    "spec_existing_interface_reconciled": spec_existing_interface_reconciled,
    "spec_preserved_unrelated_decisions": spec_preserved_unrelated_decisions,
    "spec_wrote_no_stories": spec_wrote_no_stories,
    "stories_public_interface_gap_wrote_nothing": stories_public_interface_gap_wrote_nothing,
    "stories_public_interface_gap_routes_to_spec": stories_public_interface_gap_routes_to_spec,
    # mano build
    "build_ledger_rows_are_the_briefs": build_ledger_rows_are_the_briefs,
    "build_wrote_no_story_files": build_wrote_no_story_files,
    "build_completed_the_phase": build_completed_the_phase,
    "build_did_not_rebuild_done_row": build_did_not_rebuild_done_row,
    "build_wrote_no_ledger": build_wrote_no_ledger,
    "build_routed_to_spec": build_routed_to_spec,
    "build_routed_to_start": build_routed_to_start,
    "build_stopped_before_code": build_stopped_before_code,
    "build_wrote_no_source": build_wrote_no_source,
    "build_named_the_uncovered_criterion": build_named_the_uncovered_criterion,
    "build_refused_both_ledgers": build_refused_both_ledgers,
    "build_refused_free_text_scope": build_refused_free_text_scope,
    "build_review_gate_held": build_review_gate_held,
    "build_reopened_instead_of_appending": build_reopened_instead_of_appending,
    "build_appended_the_users_words": build_appended_the_users_words,
    "build_no_row_appended": build_no_row_appended,
    # mano build — wave 3 contracts
    "build_refused_invalid_ledger": build_refused_invalid_ledger,
    "build_refused_two_ledgers_when_invalid": build_refused_two_ledgers_when_invalid,
    "build_refused_edited_brief": build_refused_edited_brief,
    "build_worked_the_pending_rework": build_worked_the_pending_rework,
    "review_persisted_findings_as_rework": review_persisted_findings_as_rework,
    "start_amend_previewed_before_writing": start_amend_previewed_before_writing,
    "start_amend_wrote_only_after_approval": start_amend_wrote_only_after_approval,
    "start_amend_refused_with_ledger": start_amend_refused_with_ledger,
    # mano build — wave 4: entry, grouping, invocation arguments
    "single_pass_rows_are_the_briefs_two_levels": single_pass_rows_are_the_briefs_two_levels,
    "single_pass_every_leaf_has_its_own_evidence": single_pass_every_leaf_has_its_own_evidence,
    "single_pass_completed_the_phase": single_pass_completed_the_phase,
    "group_stopped_at_the_category_gate": group_stopped_at_the_category_gate,
    "group_resumed_without_reopening_proven_rows": group_resumed_without_reopening_proven_rows,
    "build_flat_rows_stayed_flat": build_flat_rows_stayed_flat,
    "build_offered_backlog_defer": build_offered_backlog_defer,
    "build_arg_stopped_for_the_pending_rework": build_arg_stopped_for_the_pending_rework,
    "build_no_ledger_argument_created_nothing": build_no_ledger_argument_created_nothing,
    "auto_reached_build_without_story_files": auto_reached_build_without_story_files,
    "auto_chain_stopped_before_review": auto_chain_stopped_before_review,
    # two-phase extension
    "two_phase_one_behaviour_survives": two_phase_one_behaviour_survives,
    "two_phase_extension_behaviour_works": two_phase_extension_behaviour_works,
    "two_phase_source_untouched_regions_preserved": two_phase_source_untouched_regions_preserved,
    "two_phase_artifacts_extended_not_reemitted": two_phase_artifacts_extended_not_reemitted,
    "two_phase_no_duplicated_or_reordered_sections": two_phase_no_duplicated_or_reordered_sections,
    "two_phase_identity_and_ledger_held": two_phase_identity_and_ledger_held,
    "two_phase_did_not_read_other_phase_brief": two_phase_did_not_read_other_phase_brief,
    "two_phase_each_step_wrote_only_its_own_artifact": two_phase_each_step_wrote_only_its_own_artifact,
}
