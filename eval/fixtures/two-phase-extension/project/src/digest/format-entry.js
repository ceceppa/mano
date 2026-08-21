"use strict";

// sentinel: phase-1-entry-format-must-stay-byte-identical

/** Render one digest entry as its title, an em dash, then its status. */
function formatEntry(entry) {
  return `${entry.title} — ${entry.status}`;
}

module.exports = { formatEntry };
