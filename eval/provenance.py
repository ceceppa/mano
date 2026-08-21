"""Incident provenance for removable Mano prompt rules.

Behavior patches are fenced in the shipped Markdown:

    <!-- mano-rule: id=...; incident=...; model=...; date=YYYY-MM-DD; eval=... -->
    ...prompt rule...
    <!-- /mano-rule: id -->

The opening marker explains why the rule exists. The paired closing marker lets
the eval harness remove the complete patch temporarily, without editing the
working tree, to test whether a newer model still needs it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


REQUIRED_FIELDS = ("id", "incident", "model", "date", "eval")
RULE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
OPEN = re.compile(
    r"^[ \t]*<!--\s*mano-rule:\s*(?P<meta>[^\n]*?)\s*-->[ \t]*$",
    re.MULTILINE,
)
CLOSE = re.compile(
    r"^[ \t]*<!--\s*/mano-rule:\s*(?P<id>[a-z0-9]+(?:-[a-z0-9]+)*)\s*-->[ \t]*$",
    re.MULTILINE,
)
TOKEN = re.compile(
    rf"(?P<open>{OPEN.pattern})|(?P<close>{CLOSE.pattern})",
    re.MULTILINE,
)


class ProvenanceError(ValueError):
    """A malformed or inconsistent provenance marker."""


@dataclass(frozen=True)
class Occurrence:
    path: Path
    line: int
    start: int
    end: int


@dataclass
class Rule:
    id: str
    incident: str
    model: str
    observed: str
    evals: tuple[str, ...]
    occurrences: list[Occurrence] = field(default_factory=list)

    def metadata_key(self) -> tuple[str, str, str, tuple[str, ...]]:
        return (self.incident, self.model, self.observed, self.evals)


def _metadata(raw: str, path: Path, line: int) -> dict[str, str]:
    fields: dict[str, str] = {}
    for part in raw.split(";"):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise ProvenanceError(f"{path}:{line}: malformed marker field {part!r}")
        key, value = (piece.strip() for piece in part.split("=", 1))
        if not key or not value:
            raise ProvenanceError(f"{path}:{line}: empty marker field in {part!r}")
        if key in fields:
            raise ProvenanceError(f"{path}:{line}: duplicate marker field {key!r}")
        fields[key] = value

    missing = [name for name in REQUIRED_FIELDS if name not in fields]
    if missing:
        raise ProvenanceError(f"{path}:{line}: marker missing {', '.join(missing)}")
    if not RULE_ID.fullmatch(fields["id"]):
        raise ProvenanceError(f"{path}:{line}: invalid rule id {fields['id']!r}")
    try:
        date.fromisoformat(fields["date"])
    except ValueError as exc:
        raise ProvenanceError(
            f"{path}:{line}: date must be ISO YYYY-MM-DD, got {fields['date']!r}"
        ) from exc
    return fields


def _parse_file(path: Path) -> list[tuple[dict[str, str], Occurrence]]:
    text = path.read_text(encoding="utf-8")
    found: list[tuple[dict[str, str], Occurrence]] = []
    active: tuple[dict[str, str], int, int] | None = None

    for token in TOKEN.finditer(text):
        if token.group("open") is not None:
            if active is not None:
                prior = active[0]["id"]
                line = text.count("\n", 0, token.start()) + 1
                raise ProvenanceError(
                    f"{path}:{line}: nested rule {token.group('meta')!r} inside {prior!r}"
                )
            line = text.count("\n", 0, token.start()) + 1
            meta = _metadata(token.group("meta"), path, line)
            active = (meta, token.start(), line)
            continue

        close_id = token.group("id")
        line = text.count("\n", 0, token.start()) + 1
        if active is None:
            raise ProvenanceError(f"{path}:{line}: closing marker for unopened rule {close_id!r}")
        meta, start, start_line = active
        if close_id != meta["id"]:
            raise ProvenanceError(
                f"{path}:{line}: closes {close_id!r}, expected {meta['id']!r}"
            )
        end = token.end()
        if end < len(text) and text[end] == "\n":
            end += 1
        found.append((meta, Occurrence(path, start_line, start, end)))
        active = None

    if active is not None:
        meta, _, line = active
        raise ProvenanceError(f"{path}:{line}: rule {meta['id']!r} has no closing marker")
    return found


def _source_files(root: Path) -> list[Path]:
    src = root / "src"
    return sorted(
        path
        for path in src.rglob("*")
        if path.is_file() and (path.suffix == ".md" or path.name == "cursorrules")
    )


def discover_rules(root: Path, *, validate_cases: bool = True) -> dict[str, Rule]:
    """Read, validate, and group every source provenance block by stable id."""
    rules: dict[str, Rule] = {}
    for path in _source_files(root):
        for meta, occurrence in _parse_file(path):
            evals = tuple(item.strip() for item in meta["eval"].split(",") if item.strip())
            if not evals:
                raise ProvenanceError(f"{path}:{occurrence.line}: eval field is empty")
            candidate = Rule(
                id=meta["id"],
                incident=meta["incident"],
                model=meta["model"],
                observed=meta["date"],
                evals=evals,
                occurrences=[occurrence],
            )
            existing = rules.get(candidate.id)
            if existing is None:
                rules[candidate.id] = candidate
            elif existing.metadata_key() != candidate.metadata_key():
                first = existing.occurrences[0]
                raise ProvenanceError(
                    f"{path}:{occurrence.line}: metadata for {candidate.id!r} differs "
                    f"from {first.path}:{first.line}"
                )
            else:
                existing.occurrences.append(occurrence)

    if validate_cases:
        cases_dir = root / "eval" / "cases"
        case_names = {path.stem for path in cases_dir.glob("*.json")}
        for rule in rules.values():
            for eval_name in rule.evals:
                if eval_name != "pending" and eval_name not in case_names:
                    first = rule.occurrences[0]
                    raise ProvenanceError(
                        f"{first.path}:{first.line}: rule {rule.id!r} references "
                        f"missing eval case {eval_name!r}"
                    )
    return rules


CONDITION_KEYS = {"requires-in-auto": "auto"}


def conditional_fragments(root: Path) -> dict[str, str]:
    """Rule fragments a skill loads only under a condition → the run mode.

    Derived from the skills' own front matter rather than a second hard-coded
    list, so adding a conditional fragment cannot forget to update this.
    """
    found: dict[str, str] = {}
    for path in sorted((root / "src" / "skills").glob("*.md")):
        head = path.read_text(encoding="utf-8")[:600]
        for key, mode in CONDITION_KEYS.items():
            match = re.search(rf"^{key}:\s*\[(.*?)\]\s*$", head, re.MULTILINE)
            if not match:
                continue
            for name in (n.strip() for n in match.group(1).split(",")):
                if name:
                    found[name] = mode
    return found


def check_conditional_coverage(root: Path, rules: dict[str, "Rule"] | None = None) -> None:
    """A rule inside a conditionally-loaded fragment needs a case in that mode.

    `--probe-rule` strips a rule from a temp install and runs the cases the
    marker names. If the rule lives in `rules/auto.md` and every named case runs
    in `manual`, the probe never loads the file it just emptied: the cases pass
    whether or not the rule exists, and the result reads as "safe to retire".
    """
    import json

    rules = discover_rules(root) if rules is None else rules
    conditional = conditional_fragments(root)
    if not conditional:
        return
    modes: dict[str, str] = {}
    for path in sorted((root / "eval" / "cases").glob("*.json")):
        case = json.loads(path.read_text(encoding="utf-8"))
        modes[case.get("name", path.stem)] = case.get("run_mode", "manual")

    problems = []
    for rule in rules.values():
        fragments = {
            path.stem
            for path in (occurrence.path for occurrence in rule.occurrences)
            if path.parent.name == "rules" and path.stem in conditional
        }
        if not fragments:
            continue
        needed = sorted({conditional[name] for name in fragments})
        for eval_name in rule.evals:
            if eval_name == "pending":
                continue
            if modes.get(eval_name, "manual") not in needed:
                problems.append(
                    f"rule {rule.id!r} lives in {sorted(fragments)} (loaded only under "
                    f"{'/'.join(needed)}) but case {eval_name!r} runs in "
                    f"{modes.get(eval_name, 'manual')!r}; the probe would never load it"
                )
    if problems:
        raise ProvenanceError("\n".join(problems))


PENDING_ALLOWLIST = "pending-evals.json"


def check_pending(root: Path, rules: dict[str, "Rule"] | None = None) -> None:
    """The ship guard: `eval=pending` needs a recorded, temporary exception.

    A provenance marker's promise is that the rule can be probed for
    retirement. `eval=pending` suspends that promise, and a suspension nobody
    can see is how three rules quietly reached a release unprobed. So the
    exception is explicit, carries a reason and an owner, and is visible in one
    file — and a stale entry fails just as loudly as a missing one, the same
    way `expected-red.json` treats a case that started passing.
    """
    rules = discover_rules(root) if rules is None else rules
    path = root / "eval" / PENDING_ALLOWLIST
    allowed: dict[str, dict] = {}
    if path.is_file():
        import json

        allowed = json.loads(path.read_text(encoding="utf-8")).get("rules", {})

    pending = {rule_id for rule_id, rule in rules.items() if "pending" in rule.evals}

    problems = []
    for rule_id in sorted(pending - set(allowed)):
        first = rules[rule_id].occurrences[0]
        problems.append(
            f"{first.path}:{first.line}: rule {rule_id!r} ships with eval=pending and no "
            f"recorded exception in eval/{PENDING_ALLOWLIST}"
        )
    for rule_id in sorted(set(allowed) - pending):
        problems.append(
            f"eval/{PENDING_ALLOWLIST}: {rule_id!r} is listed but no longer pending — "
            "delete the entry rather than editing it"
        )
    for rule_id, entry in sorted(allowed.items()):
        missing = [field for field in ("reason", "owner") if not str(entry.get(field, "")).strip()]
        if missing:
            problems.append(
                f"eval/{PENDING_ALLOWLIST}: {rule_id!r} exception is missing {', '.join(missing)}"
            )

    if problems:
        raise ProvenanceError("\n".join(problems))


def _installed_files(project: Path) -> list[Path]:
    files: list[Path] = []
    mano = project / "_mano"
    if mano.is_dir():
        files.extend(path for path in mano.rglob("*") if path.is_file())
    for name in ("AGENTS.md", "CLAUDE.md", ".cursorrules"):
        path = project / name
        if path.is_file():
            files.append(path)
    return sorted(set(files))


def strip_rules(project: Path, rule_ids: set[str]) -> dict[str, int]:
    """Remove all installed occurrences of `rule_ids` from a temp project."""
    removed = {rule_id: 0 for rule_id in rule_ids}
    for path in _installed_files(project):
        try:
            occurrences = _parse_file(path)
        except UnicodeDecodeError:
            continue
        selected = [
            (meta["id"], occurrence)
            for meta, occurrence in occurrences
            if meta["id"] in rule_ids
        ]
        if not selected:
            continue
        text = path.read_text(encoding="utf-8")
        for rule_id, occurrence in sorted(selected, key=lambda item: item[1].start, reverse=True):
            text = text[: occurrence.start] + text[occurrence.end :]
            removed[rule_id] += 1
        path.write_text(text, encoding="utf-8")
    return removed


MARKER_LINE = re.compile(
    r"^[ \t]*<!--\s*/?mano-rule:[^>]*-->[ \t]*\r?\n?",
    re.MULTILINE,
)


def strip_markers(project: Path) -> int:
    """Remove bare provenance marker lines (not rule bodies) from an install.

    Production installs are marker-free (the installer strips them); a probe
    install keeps them so `strip_rules` can remove whole rules, then calls this
    to normalise the remaining files back to the production shape.
    """
    removed = 0
    for path in _installed_files(project):
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        stripped, count = MARKER_LINE.subn("", text)
        if count:
            path.write_text(stripped, encoding="utf-8")
            removed += count
    return removed


def format_rule_table(root: Path, rules: dict[str, Rule]) -> str:
    """Compact human-readable inventory for `eval/run.py --list-rules`."""
    lines = [
        "TAGGED RULES — partial inventory; untagged legacy patches are not shown",
        "",
        "RULE                              DATE        MODEL          INCIDENT / EVAL",
    ]
    lines.append("-" * 108)
    for rule in sorted(rules.values(), key=lambda item: item.id):
        model = rule.model if len(rule.model) <= 14 else rule.model[:13] + "…"
        evals = ",".join(rule.evals)
        lines.append(
            f"{rule.id:<33} {rule.observed:<11} {model:<14} "
            f"{rule.incident} / {evals}"
        )
        for occurrence in rule.occurrences:
            rel = occurrence.path.relative_to(root)
            lines.append(f"  ↳ {rel}:{occurrence.line}")
    return "\n".join(lines)
