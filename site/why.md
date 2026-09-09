# Why Mano

## The assumption underneath it

Software projects rarely move in a straight line. Feedback, testing, and technical discovery invalidate early assumptions — so a perfect upfront plan isn't the goal, and never was.

The goal is a tight loop: each small phase gets scoped, reviewed, and corrected before the next one starts. You catch the wrong turn early, while it's still cheap to change.

Here's that happening in a real phase. The scope item said *"exclude React Native's LogBox from AMA's accessibility checks."* Then `mano spec` went and looked:

> `mano spec` investigated a code-level exclusion and found no reliable way to detect LogBox without risking silent coverage gaps elsewhere. **This phase ships the documentation, not a code fix.**

That correction cost one paragraph in a brief. Discovered three days later, it costs a revert, a re-plan, and an argument about whether the half-built version is salvageable.

## What Mano is not

**It runs through your coding agent.** Mano provides skills, templates, and instructions the agent reads, plus local helper scripts that validate project state and maintain progress records. There is no `mano` terminal command or background daemon.

**You control the scope and closure.** Mano waits for your approval before writing a phase's scope and for your judgement before closing it. You can run commands individually, request batch implementation with `mano dev yolo`, or enable auto mode to chain approved work. An approved auto chain can run `mano dev yolo` when the phase already has stories.

**It's not a guarantee.** You are the enforcer of scope, context, and quality. Mano makes the seams visible and cheap to correct; it does not remove your judgement from the loop, and it isn't trying to.

## Honest scope

One maintainer. No company behind it. MIT licensed.

Which is a fair thing to weigh, so here's the counterweight: about 34 phases of real use across two unrelated stacks — a React Native accessibility library and a Godot animation add-on in GDScript. The planning artifacts from both are public and committed. You can read what Mano actually produced, including the parts where it was wrong:

> **What didn't**
>
> Both stories' `Implementation Reference` were written from an incomplete diagnosis and turned out to be wrong once implementation dug deeper.
>
> Manual playground verification could not be performed for story 1 in this shell-only environment — flagged as a gap, not silently skipped or falsely claimed.

That's from a real review log. A tool that can't record its own misses isn't producing a review, it's producing a receipt.

## Who it's for

**A good fit if** you want to steer the work — reading a brief, disagreeing with it, and correcting it before code exists. If you already stop and read what your agent proposes, Mano gives that instinct a structure and a paper trail.

**A bad fit if** you want to describe a feature and come back to a finished PR. That's a real preference and there are tools built around it. Mano's gates would just be friction, because they exist to hold exactly the decisions you'd be trying to delegate.

## On being one of many

There are a lot of spec-driven development tools now. The honest differences:

**Artifacts have size caps and one owner each.** A spec that grows past five minutes of reading is a spec nobody reads before approving, which makes the approval meaningless. Each value lives in exactly one artifact; the others reference it.

**The implementation contract is thin on purpose.** A story carries what an implementing agent needs and nothing else, so a small, cheap model can execute it without the planning context. Planning and implementation don't have to run on the same model — or the same budget.

**À la carte, not a conveyor belt.** No mandatory sequence. Every action checks its own inputs and tells you when it's missing something, rather than producing a confident artifact built on a guess.

**The human is the judge.** Not a reviewer step at the end — the approval gate at the start of every phase, and the close at the end.

---

Ready to try it? [Get started](/getting-started) walks through installation and your first change. [A real phase walkthrough](/first-phase) shows the resulting artifacts.
