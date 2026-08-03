"""Property assertions over the artifacts and final response a skill produced.

Each assertion is a pure function: (ctx) -> list[Failure]. An empty list means
the assertion passed. ctx gives access to the output dir, seeded fixture
snapshot, final runner response, and convenience readers. Assertions never call
an LLM — they are deterministic text checks after the runner completes.

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

    def __init__(
        self,
        output_dir: Path,
        phase: int | None = None,
        fixture_snapshot: dict[str, str] | None = None,
        transcript: str = "",
    ):
        self.output_dir = output_dir
        self.phase = phase
        self.fixture_snapshot = fixture_snapshot or {}
        self.transcript = transcript
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

    def fixture_text(self, name: str) -> str | None:
        return self.fixture_snapshot.get(name)

    def artifact_text(self, name: str) -> str | None:
        if self.phase is not None and name == "phase-brief.md":
            path = self.output_dir / f"phase-{self.phase}" / name
        else:
            path = self.output_dir / name
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
    expected = "Story 1 done — status updated in stories/README.md"
    if ctx.transcript.strip() != expected:
        return [Failure(
            "dev_default_output_discipline",
            f"expected the one-line singular response {expected!r}, got {ctx.transcript.strip()!r}",
        )]
    return []


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
    # review hard gate
    "pending_review_gate_held": pending_review_gate_held,
    # stories mid-build
    "midbuild_lettered_story_inserted": midbuild_lettered_story_inserted,
    "existing_stories_unchanged": existing_stories_unchanged,
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
}
