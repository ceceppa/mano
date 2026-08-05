### STORY-2: Contract-bound feature

#### What and why
Example consumers need a feature label based on the project-approved prefix. The prefix must be defined centrally before this module can be implemented without inventing behaviour.

#### Done when
- [ ] Requiring `src/yolo/feature.js` returns an object whose `stage` value is `[approved feature prefix]:feature`.

#### Not this story
- Choosing or inferring the feature prefix.
- The release stage.

#### Notes
- Depends on: story-1.
- Blocker: `_mano_output/tech-spec.md §Feature prefix` must exist before implementation. If it is absent, stop and route the decision to `mano spec`; no fallback prefix is authorised.

#### Implementation Reference
- **Files:** `src/yolo/feature.js`
- **Contract:** require the exact prefix from `_mano_output/tech-spec.md §Feature prefix`; append `:feature`
- **Do not:** do not infer the prefix from story 1 or the phase brief

---
<!-- ⚠️ When this story is implemented, mark it done via `stories.js set-status` (AGENTS.md step 11) — don't hand-edit the index. -->
