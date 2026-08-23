# Your first phase

This is a real phase from [react-native-ama](https://github.com/FormidableLabs/react-native-ama), an accessibility library for React Native. Phase 13, three stories, fixing two regressions and one longstanding annoyance. Nothing here is invented for the docs.

## 1. Scope it

```
mano start
```

Mano reads your backlog and proposes a phase. It asks about anything it would otherwise have to guess, then shows you the complete scope and waits. **Nothing is written until you approve it.**

What came out:

```markdown
## Phase Goal

Both regressions are fixed, and the LogBox limitation is documented so
consumers understand it's expected, not a bug in their code.

## Phase Scope

- `useAMADev.ts`'s `itemsWithNoStateUpdated` restores per-parent indexing
  so `NO_ACCESSIBILITY_STATE_SET` detection works correctly again.
- `forms/useFormField.test.tsx`'s suite loads and runs, fixing the
  underlying jest/transform config issue.
- The README documents that AMA may report accessibility issues
  originating from React Native's own LogBox/YellowBox overlay.

## Not This Phase

- Redesigning AMA's node-scanning to exclude LogBox — investigated and
  rejected, not being revisited this phase
- Removing the playground's existing LogBox-disabling workaround
```

`## Not This Phase` is doing real work here. It is the section that stops an agent from helpfully expanding into a refactor you didn't ask for.

## 2. Decide the technical questions

```
mano spec
```

The third scope item started life as *"exclude LogBox from AMA's checks."* Spec investigated it — reading React Native's `AppContainer` and `react-native-screens`' iOS source — and concluded it couldn't be done safely:

> `mano spec` investigated a code-level exclusion and found no reliable way to detect LogBox without risking silent coverage gaps elsewhere — see `tech-spec.md` § "React Native LogBox is not excluded from checks". **This phase ships the documentation, not a code fix.**

The scope item changed *before* anyone wrote code. That is the entire point of the loop: the cheapest place to discover that an approach doesn't work is in a spec, not in a diff.

## 3. Decompose

```
mano stories
```

```markdown
| # | Story                                     | Status |
|---|-------------------------------------------|--------|
| 1 | Fix accessibility state-change detection  | done   |
| 2 | Fix forms test suite failing to load      | done   |
| 3 | Document the LogBox limitation            | done   |
```

Each story is self-contained — an implementing agent opens one file and needs nothing else:

```markdown
### STORY-1: Fix accessibility state-change detection

#### Done when
- [ ] Running `useAMADev.test.ts`: both existing
      `NO_ACCESSIBILITY_STATE_SET` assertions pass
- [ ] Test: with two sibling components present, a state change on one
      does not affect whether the other sibling's issue is flagged
- [ ] Manually verified in playground (per project-rules.md rule 17 —
      checker-flow changes require playground verification)

#### Not this story
- The forms `useFormField.test.tsx` suite failing to load — story 2
- Any LogBox-related work — story 3

#### Implementation Reference
- **Files:** `packages/core/src/internals/useAMADev.ts`
- **Do not:** change the `onUIInteraction` payload shape — this is a
  JS-side comparison-logic fix only.
```

The `Implementation Reference` block is the one deliberately agent-facing part of Mano. Everything else is written for you.

## 4. Implement

```
mano dev
```

One story per run, in order. It refuses to skip ahead, and it will not mark a story done without evidence the acceptance criteria are met.

## 5. Close it

```
mano review
```

Review records what actually happened — including when Mano itself was wrong. From this phase's real review log:

> **What didn't**
>
> Both stories' `Implementation Reference` were written from an incomplete diagnosis and turned out to be wrong once implementation dug deeper: story 1 assumed dropped `parentId` indexing (actual bug, found via `git log`: `before !== settled` compared snapshot objects by reference instead of per-key).
>
> Manual playground verification could not be performed for story 1 in this shell-only environment — **flagged as a gap, not silently skipped or falsely claimed.**

That is a review doing its job. The alternative — a green checkmark and a summary that says everything went fine — is what you get when nothing is checking.

## What you end up with

```
_mano_output/
  backlog.md          # what's next, and why it's not now
  tech-spec.md        # decisions and their reasons
  project-rules.md    # conventions the agent must follow
  reviews.md          # what held, what didn't, per phase
  phase-13/
    phase-brief.md
    stories/
```

All plain markdown, all in your repo, all readable without Mano.

---

Next: [three worked examples](/examples), from a single phase to parallel owners.
