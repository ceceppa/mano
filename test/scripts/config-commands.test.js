"use strict";

const assert = require("node:assert/strict");
const path = require("node:path");
const test = require("node:test");

const mode = require("../../src/scripts/mode.js");
const owner = require("../../src/scripts/owner.js");
const track = require("../../src/scripts/track.js");
const language = require("../../src/scripts/language.js");

test("mode parser accepts the documented command shapes", () => {
	assert.deepEqual(mode.parseArgs([]).command, "show");
	assert.equal(mode.parseArgs(["auto"]).command, "auto");
	assert.equal(mode.parseArgs(["set", "manual", "/tmp/project"]).value, "manual");
	assert.equal(mode.parseArgs(["set", "manual", "/tmp/project"]).root, path.resolve("/tmp/project"));
	assert.equal(mode.parseArgs(["--help"]).help, true);
});

test("owner parser separates commands, slugs, and project roots", () => {
	assert.equal(owner.parseArgs([]).command, "show");
	const parsed = owner.parseArgs(["set", "gameplay", "/tmp/project"]);
	assert.equal(parsed.command, "set");
	assert.equal(parsed.slug, "gameplay");
	assert.equal(parsed.root, path.resolve("/tmp/project"));
	assert.equal(owner.parseArgs(["clear", "/tmp/project"]).command, "clear");
	assert.equal(owner.parseArgs(["-h"]).help, true);
});

test("track parser separates commands, names, and project roots", () => {
	assert.equal(track.parseArgs([]).command, "show");
	const parsed = track.parseArgs(["set", "Option B", "/tmp/project"]);
	assert.equal(parsed.command, "set");
	assert.equal(parsed.value, "Option B");
	assert.equal(parsed.root, path.resolve("/tmp/project"));
	assert.equal(track.parseArgs(["Option B", "/tmp/project"]).command, "set");
	assert.equal(track.parseArgs(["clear", "/tmp/project"]).command, "clear");
	assert.equal(track.parseArgs(["-h"]).help, true);
});

test("language parser requires a channel for every language", () => {
	assert.equal(language.parseArgs([]).command, "show");
	const many = language.parseArgs(["chat", "it", "build", "en-GB", "artefacts", "it"]);
	assert.equal(many.command, "set");
	assert.deepEqual(many.pairs, [["chat", "it"], ["build", "en-GB"], ["artefacts", "it"]]);
	assert.deepEqual(language.parseArgs(["set", "build", "en-GB"]).pairs, [["build", "en-GB"]]);
	assert.match(language.parseArgs(["it"]).error, /name a channel/);
	assert.match(language.parseArgs(["set", "it"]).error, /needs a channel/);
	assert.match(language.parseArgs(["chat"]).error, /needs a language/);
	assert.deepEqual(language.parseArgs(["clear", "build", "artefacts"]).channels, ["build", "artefacts"]);
	assert.deepEqual(language.parseArgs(["clear"]).channels, []);
	assert.match(language.parseArgs(["chat", "it", "extra"]).error, /unexpected argument/);
	assert.equal(language.parseArgs(["-h"]).help, true);
});

test("configuration scripts import without executing their command entry points", () => {
	assert.equal(typeof mode.main, "function");
	assert.equal(typeof owner.main, "function");
	assert.equal(typeof track.main, "function");
	assert.equal(typeof language.main, "function");
});
