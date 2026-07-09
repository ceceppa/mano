"""Property assertions over the files a skill wrote.

Each assertion is a pure function: (ctx) -> list[Failure]. An empty list means
the assertion passed. ctx gives access to the output dir and convenience
readers. Assertions never call an LLM — they are deterministic text checks.

Assertions are referenced by name from a case file. Add a new check here and it
becomes available to every case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Failure:
    assertion: str
    detail: str


class Ctx:
    """Read-only view of what a skill produced, plus the inputs it ran against.

    `phase` is only meaningful for phase-scoped skills (stories). Import-style
    skills that produce project-level artifacts (the backlog) pass phase=None.
    """

    def __init__(self, output_dir: Path, phase: int | None = None):
        self.output_dir = output_dir
        self.phase = phase
        self.stories_dir = output_dir / f"phase-{phase}" / "stories" if phase is not None else None

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

    def phase_dirs(self) -> list[Path]:
        if not self.output_dir.is_dir():
            return []
        return sorted(p for p in self.output_dir.glob("phase-*") if p.is_dir())


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
    # mano import
    "backlog_was_written": backlog_was_written,
    "backlog_has_items": backlog_has_items,
    "all_items_status_backlog": all_items_status_backlog,
    "no_phase_brief_written": no_phase_brief_written,
    "import_wrote_only_backlog": import_wrote_only_backlog,
    "backlog_covers_document_features": backlog_covers_document_features,
    "stated_tech_preference_preserved": stated_tech_preference_preserved,
    # review hard gate
    "pending_review_gate_held": pending_review_gate_held,
    # stories mid-build
    "midbuild_lettered_story_inserted": midbuild_lettered_story_inserted,
    "existing_stories_unchanged": existing_stories_unchanged,
}
