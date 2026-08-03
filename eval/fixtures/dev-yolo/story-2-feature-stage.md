### STORY-2: Feature stage

#### What and why
Example consumers need a feature label derived from the base stage. After this story, the second module proves the ordered stage chain composes.

#### Done when
- [ ] Requiring `src/yolo/feature.js` returns an object whose `stage` value is `base:feature`.

#### Not this story
- The release stage.

#### Notes
- Depends on: story-1.

#### Implementation Reference
- **Files:** `src/yolo/feature.js`
- **Contract:** dependency-free CommonJS module; require `./base.js` and append `:feature` to its exported `stage`
- **Do not:** do not duplicate the base label as an independent source of truth

---
<!-- ⚠️ When this story is implemented, mark it done via `stories.js set-status` (AGENTS.md step 11) — don't hand-edit the index. -->
