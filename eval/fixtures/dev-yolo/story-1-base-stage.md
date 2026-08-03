### STORY-1: Base stage

#### What and why
Example consumers need the first stable label in the stage chain. After this story, they can load the base module without any package setup.

#### Done when
- [ ] Requiring `src/yolo/base.js` returns an object whose `stage` value is `base`.

#### Not this story
- The feature and release stages.

#### Implementation Reference
- **Files:** `src/yolo/base.js`
- **Contract:** dependency-free CommonJS module; export `stage` with value `base`
- **Do not:** no package manifest or third-party dependency

---
<!-- ⚠️ When this story is implemented, mark it done via `stories.js set-status` (AGENTS.md step 11) — don't hand-edit the index. -->
