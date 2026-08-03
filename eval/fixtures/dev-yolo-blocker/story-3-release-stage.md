### STORY-3: Release stage

#### What and why
Example consumers need the complete release label from the final stage. After this story, loading the release module exercises the full chain.

#### Done when
- [ ] Requiring `src/yolo/release.js` appends `:release` to the stage exported by `src/yolo/feature.js`.

#### Not this story
- Choosing the feature prefix.

#### Notes
- Depends on: story-2.

#### Implementation Reference
- **Files:** `src/yolo/release.js`
- **Contract:** dependency-free CommonJS module; require `./feature.js` and append `:release`
- **Do not:** do not duplicate or infer the feature prefix

---
<!-- ⚠️ When this story is implemented, mark it done via `stories.js set-status` (AGENTS.md step 11) — don't hand-edit the index. -->
