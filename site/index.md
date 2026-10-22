---
layout: home
title: Mano — Planning for AI-assisted development
titleTemplate: false
description: Plan and build software with your coding agent one item, or one small approved phase, at a time. Mano keeps scope, technical decisions, and implementation progress in your repository.

hero:
  name: Mano
  text: A fast planning loop for AI-assisted development
  tagline: Build one small step at a time and validate each assumption before it becomes code. Correct course at one item or one brief — not after dozens of tasks have already shipped.
  image:
    src: /mano.svg
    alt: Mano
  actions:
    - theme: brand
      text: Get started
      link: /getting-started
    - theme: alt
      text: See real output
      link: /examples

features:
  - title: Small steps, not a big upfront plan
    details: Software rarely moves in a straight line. Build one item and try it, or scope a small phase and review it, so a wrong turn costs one step instead of a rewrite.
  - title: You approve the direction
    details: You say how each item or phase will be checked, approve its scope, and decide when it is finished. Work one action at a time, or enable auto mode to chain approved work until a question needs you.
  - title: Artifacts you can actually read
    details: Briefs, specs, and rules are plain-language files on disk, not agent scratch. They survive compaction, a restart, and a change of model.
---

## From an idea to an approved plan

Mano gives your coding agent a repeatable way to plan and implement small pieces of work. Describe a change, review the proposed scope, and let the agent build against the decisions you approved. The plans and progress stay in your repository as readable files.

## Start in your project

In a terminal, from your project's root directory:

```bash
npx mano-plan install
```

Then open your coding agent's chat in the same project and describe your first change. One idea you want to try:

```text
mano task "the contact form shows an inline error for an invalid email"
```

Or a change that needs several pieces to land together:

```text
mano start
I want to add a contact form. Keep the first phase small.
```

Either way, Mano writes the work down and asks how you'll check it before any code. **Installation runs in the terminal; `mano` commands go in chat.**

[Follow the setup guide →](/getting-started) · [See a real phase →](/first-phase)

## Two loops

Both loops read and write the same backlog.

**One item.** For an idea you can only judge by trying it:

```
mano task "…"   →  write the item and your check, build it, hand it back to you to try
```

[More on tasks →](/features/task)

**One phase.** When several items have to land together, or the direction needs a review:

```
mano start      →  scope a phase, and approve it yourself
mano spec       →  settle the technical decisions
mano rules      →  pin the conventions so stories stay consistent
mano stories    →  decompose into self-contained units
mano dev        →  implement the next story
mano review     →  record what held, what didn't, and close the phase
```

Nothing forces that order. Every action checks its own inputs and tells you when it would be guessing.

For a phase that doesn't need story files, [`mano build`](/features/build) implements the brief's approved scope items directly, tracked in a ledger on disk.

## Beyond the loop

Optional, none of it on by default:

| | |
| --- | --- |
| [**Build mode**](/features/build) | Implement a phase straight from its approved brief, no story files |
| [**Auto mode**](/features/auto-mode) | Chain the commands you'd otherwise type — armed only by your scope approval |
| [**Import**](/features/import) | Turn an existing PRD or document into a backlog, then stop |
| [**Team owners**](/features/owners) | Namespaced phases per person, so two people don't both scope "phase 7" |
| [**Tracks & filters**](/features/tracks) | Narrow what a phase is allowed to contain |
| [**Hooks**](/features/hooks) | Wire your own review checklist into any skill |

## Built with Mano

Mano is not a demo. These are real projects, and their planning artifacts are public:

| Project | What it is | Phases |
| --- | --- | --- |
| [react-native-ama](https://github.com/FormidableLabs/react-native-ama) | React Native accessibility library | 14 |
| [anima](https://github.com/ceceppa/anima) | Godot animation add-on, GDScript | 20 |

Two unrelated stacks, the same loop. [Read the actual artifacts →](/examples)
