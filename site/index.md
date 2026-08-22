---
layout: home

hero:
  name: Mano
  text: A fast planning loop for AI-assisted development
  tagline: Plan in small phases and validate each assumption before it becomes code. Correct course at the brief — not after dozens of tasks have already shipped.
  image:
    src: /mano.svg
    alt: Mano
  actions:
    - theme: brand
      text: Your first phase
      link: /first-phase
    - theme: alt
      text: See real output
      link: /examples
    - theme: alt
      text: GitHub
      link: https://github.com/ceceppa/mano

features:
  - title: Small phases, not a big upfront plan
    details: Software rarely moves in a straight line. Each phase is scoped, reviewed, and corrected before the next one starts, so a wrong turn costs one phase instead of a rewrite.
  - title: You approve every seam
    details: Mano never opts into autonomy for you. Scope approval is a hard gate, phase closure is yours, and the batch mode is something you type on purpose.
  - title: Artifacts you can actually read
    details: Briefs, specs, and rules are plain-language files on disk, not agent scratch. They survive compaction, a restart, and a change of model.
---

## Install

```bash
npx mano-plan install
```

Then type `mano start` in your AI IDE's chat.

That drops `_mano/` (skills, templates, rules) and an `AGENTS.md` contract into your project. Mano is not a compiled CLI or an autonomous planner — it is a set of skills your agent reads. You remain the enforcer of scope and quality.

## The loop

```
mano start      →  scope a phase, and approve it yourself
mano spec       →  home the technical decisions
mano rules      →  pin the conventions so stories stay consistent
mano stories    →  decompose into self-contained units
mano dev        →  implement the next story
mano review     →  record what held, what didn't, and close the phase
```

Nothing forces that order. Every action checks its own inputs and tells you when it would be guessing.

For a phase that doesn't need story files, `mano build` implements the brief's approved scope items directly, tracked in a ledger on disk.

## Built with Mano

Mano is not a demo. These are real projects, and their planning artifacts are public:

| Project | What it is | Phases |
| --- | --- | --- |
| [react-native-ama](https://github.com/FormidableLabs/react-native-ama) | React Native accessibility library | 14 |
| [anima](https://github.com/ceceppa/anima) | Godot animation add-on, GDScript | 20 |

Two unrelated stacks, one loop. [Read the actual artifacts →](/examples)
