### STORY-3: Release stage

#### What and why
Example consumers need the complete release label from the final stage. After this story, loading the release module exercises the full chain.

#### Done when
- [ ] Requiring `src/yolo/release.js` returns an object whose `stage` value is `base:feature:release`.

#### Not this story
- Any stage after release.

#### Notes
- Depends on: story-2.

#### Implementation Reference
- **Files:** `src/yolo/release.js`
- **Contract:** dependency-free CommonJS module; require `./feature.js` and append `:release` to its exported `stage`
- **Do not:** do not duplicate the base or feature labels as independent sources of truth

---
<!-- ⚠️ When this story is implemented, mark it done via `stories.js set-status` (AGENTS.md step 11) — don't hand-edit the index. -->
