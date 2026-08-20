"use strict";

const test = require("node:test");
const assert = require("node:assert");
const { formatEntry } = require("../src/digest/format-entry.js");

test("formatEntry renders title, em dash, status", () => {
  assert.equal(formatEntry({ title: "Launch review", status: "open" }), "Launch review — open");
});

test("formatEntry keeps an empty title", () => {
  assert.equal(formatEntry({ title: "", status: "done" }), " — done");
});
