---
description: Install Mano in your project, scope your first change, and choose how your coding agent implements it.
---

# Get started

Mano helps you turn a change into a small, approved plan your coding agent can implement. You review the scope before code is written, and the decisions and progress live in your repository.

## 1. Install in your project

You'll need Node.js 18 or newer, npm, and a coding agent that can read project instructions, edit files, and run commands. Your project can use any language; Node.js runs Mano's installer and helper scripts.

Open a terminal in the project's root directory and run:

```bash
npx mano-plan install
```

The installer adds `_mano/` with the workflow and helper scripts, and a Mano section in `AGENTS.md`. It also offers `CLAUDE.md` and `.cursorrules` entry points. Choose the files your editor uses; existing instructions outside Mano's section are preserved.

## 2. Describe one small change

Open your coding agent's chat in the same project. From here on, type commands **in chat**, not the terminal:

```text
mano start
I want to add a contact form with name, email, and message fields.
Help me scope a small first phase.
```

Use your own goal. An existing project is fine: describe the feature or fix you want. If you already have a requirements document, [import it into a backlog](/features/import) first.

Mano asks about missing decisions, proposes what belongs in the phase and what stays out, and waits for your approval before writing the phase artifacts. Read that scope and request changes until it matches your intent.

## 3. Follow the next action

Manual mode is the default: each command finishes and hands back to you. Follow its suggested next action, or type:

```text
mano continue
```

This runs the next action when the choice is clear. If it needs a decision, it asks. Depending on the work, you'll settle technical decisions with `mano spec`, conventions with `mano rules`, and user flows or visual design with `mano ux` and `mano ui`.

You don't need every planning document for every change. Each action checks the inputs it needs.

## 4. Choose how to implement

Each phase uses one implementation path:

| Choose | How it works |
| --- | --- |
| `mano build` | Implements the approved scope directly and tracks progress in `progress.md`. Use it when the phase is small enough to build from its brief. |
| `mano stories`, then `mano dev` | Creates story files, then implements one pending story per `mano dev` run. Use it when you want to review work in smaller units. |

`mano build` continues through the phase until it finishes or reaches a question or blocker. [Build mode](/features/build) explains progress and corrections.

Prefer to chain approved actions? [Auto mode](/features/auto-mode) does that after you enable it and approve the phase scope. It pauses for decisions and stops before review.

## 5. Review the result

Check the working change and any verification the agent could not complete, then type:

```text
mano review
```

Review records the outcome and asks for your judgement before closing the phase. Starting another phase is your decision.

Your planning files are in `_mano_output/`: the phase brief, supporting decisions, implementation progress, and review history. [See what those files look like in a real project →](/first-phase)

## Common questions

### Where did I leave off?

Type `mano status` in chat to see the current state without advancing it. Use `mano continue` when you're ready to run the next clear action.

### My agent says Mano isn't available

Check that you installed in the project the agent has open, and that `_mano/` and the Mano section in `AGENTS.md` exist. Ask the agent to read `AGENTS.md` and follow the repo-local workflow. Commands such as `mano start` refer to those local instructions; they don't require a separately installed platform skill or a `mano` terminal binary.

### How do I update Mano?

Reinstalling without `--force` leaves existing files untouched. To replace the installed framework with the latest published version, review or save any customizations in `_mano/`, then run in your terminal:

```bash
npx mano-plan@latest install --force
```

This overwrites bundled framework files and replaces installed Mano instruction sections. It does not replace your `_mano_output/` planning artifacts.

### Does Mano replace my coding agent?

No. Your agent reads Mano's instructions and performs the work using its existing tools. Local helper scripts validate state and maintain progress records. You still review the scope, the implementation, and the evidence that it works.

---

Continue with [a real phase walkthrough](/first-phase), or keep the [command reference](/commands) nearby.
