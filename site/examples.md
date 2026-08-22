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

Import turns the document into a backlog and **stops**. It doesn't scope, decide, or read your source to guess at work — it converts what the document says into items, including the project-wide directives no single feature owns:

> A document's project-wide technical directives — a runtime or version constraint, a module system, a folder structure, a file-naming scheme, where tests live — belong to every item and therefore to none, which is exactly how they vanish between the document and the first line of code.

Those become their own items, carrying the directive verbatim, so `mano spec` and `mano rules` pick them up later instead of losing them.

Then hand off the typing:

```
mano mode auto
mano start
```

Auto mode chains the commands you'd otherwise type. It is armed by **one thing only** — your explicit approval of a phase scope:

```text
→ Auto mode: spec → rules → build
  Reply `1` or `go` — both approve this scope and run the chain above.
  Edit and approve together (`go, skip rules`; `1, add ux`). Pauses for
  questions; stops before review.
```

What auto mode does **not** do:

- It never scopes a phase for you. Approval is always yours.
- It never runs `mano review`. Closing a phase is a judgement call.
- It stops at any open question or missing artifact.
- "stop" or "wait" ends it immediately.

The chain ends at `mano build` — but that pairing is a convenience, not a coupling. `mano build` is one of the two ways into code and you can type it yourself in manual mode any time a phase doesn't need story files:

```
mano build
```

It works straight from the numbered `## Phase Scope` items you already approved, so nothing invents a decomposition and nothing can drift from the brief. Progress is tracked in a ledger on disk:

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

Two status vocabularies, and the writer enforces the difference: scope rows are `pending | doing | done`, criteria are `pending | met | needs-human`. **Built is not proven.** A criterion that is inherently visual gets handed to you as `needs-human` with a reason, rather than claimed.

**When to use it:** `mano build` whenever the phase is small enough to hold in one contract — with or without auto mode. Auto mode itself once you've read enough briefs to trust their shape.

## 3. When the project gets bigger

### Two people, one repo, independent phases

By default a phase is `_mano_output/phase-7/`. In a team that collides immediately — two people both scoping "phase 7".

```
mano owner alice
```

Now phase-scoped commands use `_mano_output/alice-phase-1/` and `in-alice-phase-1` backlog statuses, on Alice's own number sequence. Bob's `mano owner bob` runs an independent sequence in the same repo.

The slug lives in repository-local git config (`mano.owner`), isn't committed, and `MANO_OWNER` overrides it per shell — so linked worktrees can differ.

::: warning What this is not
Ownership selects *work*, not *isolation*. You still use branches and worktrees for merge isolation, and you still coordinate changes to the shared backlog, spec, and rules files. Mano namespaces identity; git handles execution.
:::

### Narrowing what a phase can contain

A backlog that has absorbed three imported documents and two rounds of review feedback will happily offer `mano start` fifty candidates. Two filters cut that down.

**By where an item came from:**

```
mano start from source "onboarding-prd.md"
```

Only items whose backlog `Source` contains that text become phase candidates.

**By what you're currently working on:**

```
mano track "offline-mode"
```

A track is a named direction or experiment. Once set it applies to every `mano start` automatically, until you `mano track clear`. Use `mano start from track "<name>"` to borrow a different one for a single run, and combine it with `from source` when both origin and direction matter.

Neither filter is an approval, a priority, or an epic. They narrow what Mano *proposes* — Start still suggests a subset, still runs its contradiction checks, and still waits for you to approve the scope. No matches means the filter is too narrow; Mano won't quietly fall back to the whole backlog.

### Wiring your own review into the loop

Every skill has one hook slot — `post-spec`, `post-stories`, `post-review`, and so on. A hook is inactive until you rename it:

```
_mano/hooks/post-spec.example.md   → inactive
_mano/hooks/post-spec.md           → active
```

Three kinds, and the difference is judgement versus mechanism:

| Mode | Body is | Runs | Approval |
| --- | --- | --- | --- |
| `check` | a checklist Mano applies itself | always | findings need per-item approval |
| `suggest` | a pointer to an external skill | asks first, unless in an auto chain | findings need per-item approval |
| `command` | one shell command | always | writing the file *is* the authorization |

A `check` hook is your own review, written once:

```markdown
## Mode
check

## Inputs
- `_mano_output/tech-spec.md`
- the exact `BRIEF` path from the state projection

## Checklist
- No contradiction or omission relative to the phase brief.
- Install commands match the actual package manager evidence.
```

`## Inputs` is a reading scope, not a permission to change things — findings still go through triage and still need your approval per item.

**When to use it:** when you've noticed yourself making the same correction three phases running. That's a checklist item, not a habit.

---

Not sure which applies? Start with [one phase by hand](/first-phase).
