# Backlog — Preview Service

## Core Product Principles

- Layout stays authoritative; motion only makes the change readable.

## Items

### Automatic thumbnail settling
- **Type:** feature
- **Context:**
  Thumbnails should settle into their final layout instead of jumping.
- **Status:** resolved

### Open decision: watcher lifetime
- **Type:** spec-gap
- **Source:** phase-1 review
- **Context:**
  Tech spec must state ThumbnailWatcher's lifetime and how it stays registered.
  A plain value object never receives the resize notification at all.
- **Status:** backlog

### Open decision: settle progress feedback
- **Type:** ux-gap
- **Source:** phase-1 review
- **Context:**
  UX flow must state what the panel shows while thumbnails are still settling.
- **Status:** backlog

### Export presets
- **Type:** feature
- **Context:**
  Let people save export settings as reusable presets.
- **Status:** backlog

### Batch rename
- **Type:** feature
- **Context:**
  Let people rename many thumbnails at once.
- **Status:** backlog
