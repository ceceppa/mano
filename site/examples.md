# Examples

Three ways to run Mano, from the default loop to the parts you only need once a project grows. All artifact excerpts are real, from [react-native-ama](https://github.com/FormidableLabs/react-native-ama) and [anima](https://github.com/ceceppa/anima).

[[toc]]

## 1. One small phase, by hand

The default. You type each command, read each artifact, and correct anything wrong before the next step.

```
mano start        # scope it — nothing is written until you approve
mano spec         # technical decisions and their reasons
mano stories      # decompose into self-contained units
mano dev          # implement story 1
mano dev          # implement story 2
mano review       # record outcomes, close the phase
```

Walked through in full on [Your first phase](/first-phase).

**When to use it:** always, at first. Read what the artifacts say. Mano's whole value is that you can disagree with a brief in thirty seconds instead of finding out from a diff two hours later.

## 2. From an existing document, mostly hands-off

You already have a PRD, a spec, a long issue. You don't want to retype it into a conversation.

```
mano import prd.md
```

[Import](/features/import) turns the document into a backlog and **stops** — including the project-wide directives no single feature owns, which is exactly what usually vanishes between a document and the first line of code.

Then hand off the typing:

```
mano mode auto
mano start
```

[Auto mode](/features/auto-mode) chains the commands you'd otherwise type, armed by one thing only — your explicit approval of a phase scope. It never scopes for you, never runs `mano review`, and stops at any open question.

```text
→ Auto mode: spec → rules → build
  Reply `1` or `go` — both approve this scope and run the chain above.
  Edit and approve together (`go, skip rules`; `1, add ux`). Pauses for
  questions; stops before review.
```

The chain ends at [`mano build`](/features/build), which works straight from the numbered `## Phase Scope` items you already approved — so nothing invents a decomposition and nothing can drift from the brief. Progress is tracked in a ledger on disk, and **built is not proven**: a criterion that is inherently visual is handed back to you as `needs-human` with a reason, rather than claimed.

```markdown
| #   | What                              | Status  |
|-----|-----------------------------------|---------|
| S1a | Demo selector                     | done    |
| S1b | Consistent scaling across demos   | pending |

| #   | Criterion                                          | Status |
|-----|----------------------------------------------------|--------|
| E1a | Open the playground: a 2D/3D selector is visible    | met    |
| E2a | Any demo on a high-DPI display renders consistently | pending |
```

**When to use it:** `mano build` whenever the phase is small enough to hold in one contract — with or without auto mode. Auto mode itself once you've read enough briefs to trust their shape.

## 3. When the project gets bigger

Three things you only need once a repo has more than one person, more than one document, or a correction you keep making by hand.

**[Team owners](/features/owners)** — two people, one repo, independent phase sequences:

```
mano owner alice     # → _mano_output/alice-phase-1/
```

Ownership selects *work*, not *isolation*. Mano namespaces identity; git handles execution.

**[Tracks & filters](/features/tracks)** — narrow what a phase is allowed to contain:

```
mano track "offline-mode"
mano start from source "onboarding-prd.md"
```

Neither is an approval, a priority, or an epic. They narrow what Mano *proposes*; the scope gate is unchanged.

**[Hooks](/features/hooks)** — your own review checklist, run automatically after any skill:

```
_mano/hooks/post-spec.example.md   → inactive
_mano/hooks/post-spec.md           → active
```

Three kinds — `check`, `suggest`, `command`. Findings still go through triage and still need your approval per item.

---

Not sure which applies? Start with [one phase by hand](/first-phase), or browse [all features](/features/).
