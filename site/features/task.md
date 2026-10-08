---
title: "Tasks: one item, no phase"
description: "Use mano task to build one narrow backlog item without a phase. It writes and clarifies the item before any code, follows your artifacts, and closes only on evidence."
---

# Tasks

Phases suit work whose scope you already know: several items land together, and a review checks you're still heading somewhere you want to go. Some work is the opposite: one narrow idea you can only judge by trying it. A game mechanic that has to feel right, or an interaction you need to see before you build on it. Writing a brief and closing a review for every tweak costs more than the tweak.

```
mano task "Attractor ball throw with impact activation"
mano task "the ball changes colour when it captures something"
```

Pass an existing backlog item's exact title, or describe new work in plain words. New work becomes a backlog item first, so the backlog still records everything that was built.

## The item is written down before any code

Before touching code, `mano task` writes the outcome the item has to deliver: what you, a test, or a caller can see happen once it's done. Every part of that outcome has to come from the item, an artifact it names, or what you said, never from what such a feature usually does.

When part of it would be a guess, it asks you first, all questions at once:

- the item names an open detail ("what the ball does when it reaches the floor");
- it uses a noun nothing defines ("the active ball");
- a list may be just examples;
- something starts but never says when it stops or what reverts.

It asks *what*, never *how*. Your answers go into the item's context in your words, and it carries on in the same turn. When the item is already clear, it asks nothing.

## Same gates as a phase

A missing default (a duration, a radius, a speed) stops the run and goes to `mano spec`. An unwritten player choice goes to `mano ux`. A stack decision, or work too big for one item, goes to `mano start`. `mano task` never edits the tech spec, rules, UX flow, or design brief itself.

When the item asks for the opposite of what the UX flow, the design brief, or a value in the tech spec says, both are your decisions, so the run stops and asks which one stands. To keep the item's version, run the command it prints. The command carries the change, not just the title:

```text
mano ui "Visible shield glow: the glow stays on for the whole immunity window (replaces: the shield shows only on a blocked hit)"
```

That replaces the old line in the design brief. Then run `mano task` again.

## Closing the item

Right before its first edit, `mano task` moves the item to `in-task`. If a run changes code and stops before it can close the item (a failing check, an outcome it couldn't prove, or the run just ending), the item stays `in-task`, so the backlog always shows what was started and not finished. Run `mano task "<title>"` again to pick it up from there.

The item becomes `resolved` only when every part of the outcome has evidence from that run. When what's left can only be judged by you (how it looks, how it feels, a device the agent doesn't have), the item becomes `needs-human` with a one-line `Check:` that says what to try:

| You reply | The item |
| --- | --- |
| `works` | `resolved`. The `Check:` line stays as the record of how it was verified |
| what's broken | back to `backlog`, with `Human check failed: <your words>` in its context |
| how you want it different | back to `backlog`, with `Human redirection: <your words>`. The next run clarifies it again |
| didn't check | stays `needs-human` |

Reply in the same conversation, or run `mano task "<title>"` again later. Every status change goes through `backlog.js task-status`, which refuses any move outside that table.

## When it's refused

`mano task` is refused while a phase is open, from its first draft until `mano review` closes it. The phase's stories or ledger were planned against the code as it was, and a task changing that code underneath them is exactly the drift phases exist to prevent. Finish or close the phase, then run the task.

## In auto mode

Auto mode never starts a task, and `mano continue` never picks one. You always type `mano task` yourself, because choosing what to build next is your call.

Once you've typed it, auto mode saves you the next two commands. When the run stops on a missing default or an unwritten player choice, it runs the `mano spec` or `mano ux` command it would otherwise have handed you, then comes back to the item and runs every gate again. A contradiction with an artifact asks you first, and on your answer it runs the replacement and carries on:

```text
[mano auto]: task "Attractor ball throw with impact activation" — spec → task
- Ran: spec "Attractor ball throw with impact activation: throw speed, activation radius", task
- Stopped: needs-human, check above
```

- Each owner runs at most once per task. If the gates stop on the same owner a second time, the run stops and shows you what's still missing.
- A question or a `❓ Decide:` from `mano spec` or `mano ux` still stops the run. Answer it and the task carries on.
- Escalations still stop. A stack decision, or work too big for one item, goes to `mano start`, and you run that yourself.
- Nothing is saved as a chain, because there's no phase. If the session ends mid-run, type `mano task "<title>"` again. Whatever `mano spec` or `mano ux` already wrote stays written.

One trade to know about: in manual mode you can put the value in the command yourself (`mano spec "<title>: throw speed 12 m/s"`). In auto mode `mano spec` picks it and lists it in its log, the same as it does inside an auto phase. If you'd rather choose, stay in manual, or answer the `needs-human` check with how you want it different.
