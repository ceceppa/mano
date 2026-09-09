"use strict";

// Portable preferences and chain records. Git config is read only for migration.
const fs = require("node:fs");
const path = require("node:path");
const { spawnSync } = require("node:child_process");
const own = (object, key) => Object.prototype.hasOwnProperty.call(object, key);
const object = value => value !== null && typeof value === "object" && !Array.isArray(value);

function ownerSlug(value) {
  if (value === null) return null;
  if (typeof value !== "string" || !/^[a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?$/.test(value)) {
    throw new Error(`invalid Mano owner ${JSON.stringify(value)}`);
  }
  return value;
}
function readJson(file) {
  let text;
  try { text = fs.readFileSync(file, "utf8"); }
  catch (error) { if (error.code === "ENOENT") return null; throw error; }
  try {
    const value = JSON.parse(text);
    if (!object(value)) throw new Error("expected an object");
    return value;
  } catch (error) { throw new Error(`Invalid Mano settings in ${file}: ${error.message}`); }
}
function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  const temporary = `${file}.${process.pid}.tmp`;
  try {
    fs.writeFileSync(temporary, JSON.stringify(value, null, 2) + "\n", { flag: "wx" });
    fs.renameSync(temporary, file);
  } finally { if (fs.existsSync(temporary)) fs.unlinkSync(temporary); }
}
function legacy(root, key) {
  const result = spawnSync("git", ["config", "--local", "--get", key], { cwd: root, encoding: "utf8" });
  if (result.status === 1 || result.status === 128 || result.error?.code === "ENOENT") return null;
  if (result.status !== 0) throw new Error(`Unable to read legacy Mano settings: ${result.stderr || result.error}`);
  return result.stdout.trim();
}
function writeLocal(root, owner) {
  const output = path.join(root, "_mano_output");
  fs.mkdirSync(output, { recursive: true });
  const ignore = path.join(output, ".gitignore");
  const existing = fs.existsSync(ignore) ? fs.readFileSync(ignore, "utf8") : "";
  if (!existing.split(/\r?\n/).includes("/.local.json")) {
    fs.writeFileSync(ignore, existing + (existing && !existing.endsWith("\n") ? "\n" : "") + "/.local.json\n");
  }
  writeJson(path.join(output, ".local.json"), { owner });
}
function selectedOwner(root) {
  if (own(process.env, "MANO_OWNER")) return ownerSlug(process.env.MANO_OWNER.trim());
  const local = readJson(path.join(root, "_mano_output", ".local.json"));
  if (local) return ownerSlug(local.owner);
  const old = legacy(root, "mano.owner");
  const owner = old ? ownerSlug(old) : null;
  if (owner) writeLocal(root, owner);
  return owner;
}
function relativeFile(root, owner = selectedOwner(root)) {
  return `_mano_output/${ownerSlug(owner) ?? ".default"}.json`;
}
function phaseOwner(id) {
  const match = /^(?:([a-z0-9](?:[a-z0-9-]{0,46}[a-z0-9])?)-)?phase-(\d+)$/.exec(id);
  if (!match) throw new Error(`Invalid phase id: ${id}`);
  return match[1] ?? null;
}
function legacyPhases(root) {
  const result = spawnSync("git", ["config", "--local", "--name-only", "--get-regexp", "^mano\\.(chain|run)\\."], { cwd: root, encoding: "utf8" });
  return [...new Set((result.stdout || "").trim().split("\n").filter(Boolean).map(key => key.replace(/^mano\.(chain|run)\./, "")))];
}
function readOwner(root, owner = selectedOwner(root)) {
  const file = path.join(root, relativeFile(root, owner));
  const saved = readJson(file);
  const data = saved ?? { version: 1, owner };
  if (data.version !== 1 || data.owner !== owner || (own(data, "phases") && !object(data.phases))) {
    throw new Error(`Invalid Mano settings schema in ${file}`);
  }
  // A complete JSON record is authoritative, including nulls and empty arrays.
  let migrated = false;
  const oldOwner = !own(data, "mode") || !own(data, "track") ? (legacy(root, "mano.owner") || null) : null;
  for (const key of ["mode", "track"]) {
    if (!own(data, key)) {
      const old = owner === oldOwner ? legacy(root, `mano.${key}`) : null;
      data[key] = old || (key === "mode" ? "manual" : null);
      migrated ||= old !== null;
    }
  }
  if (!own(data, "phases")) data.phases = {};
  for (const id of legacyPhases(root)) {
    if (phaseOwner(id) !== owner) continue;
    const record = data.phases[id] ?? {};
    if (!object(record)) throw new Error(`Invalid Mano phase record in ${file}: ${id}`);
    if (!own(record, "skipped")) {
      const skipped = legacy(root, `mano.chain.${id}`);
      record.skipped = skipped ? skipped.split(",").map(s => s.trim()).filter(Boolean) : [];
      migrated = true;
    }
    if (!own(record, "run")) {
      const run = legacy(root, `mano.run.${id}`);
      record.run = run === null ? null : JSON.parse(run);
      migrated = true;
    }
    data.phases[id] = record;
  }
  if (!["manual", "auto"].includes(data.mode) || (data.track !== null && (typeof data.track !== "string" || !data.track.trim() || data.track.length > 120 || /[\u0000-\u001f\u007f]/.test(data.track)))) {
    throw new Error(`Invalid Mano preferences in ${file}`);
  }
  for (const [id, record] of Object.entries(data.phases)) {
    if (phaseOwner(id) !== owner || !object(record) || !Array.isArray(record.skipped) || record.skipped.some(a => !["spec", "ux", "rules", "ui", "stories"].includes(a))) {
      throw new Error(`Invalid Mano phase record in ${file}: ${id}`);
    }
  }
  if (migrated) writeJson(file, data);
  return data;
}
function selectOwner(root, owner) {
  ownerSlug(owner);
  // Capture the old clone's preferences before changing its selection.
  const old = legacy(root, "mano.owner") || null;
  readOwner(root, old);
  const data = readOwner(root, owner);
  writeJson(path.join(root, relativeFile(root, owner)), data);
  writeLocal(root, owner);
}
function readSetting(root, key) { return readOwner(root)[key]; }
function writeSetting(root, key, value) {
  const owner = selectedOwner(root);
  const data = readOwner(root, owner);
  data[key] = value;
  writeJson(path.join(root, relativeFile(root, owner)), data);
}
function readPhase(root, id) { return readOwner(root, phaseOwner(id)).phases[id] ?? {}; }
function writePhase(root, id, patch) {
  const owner = phaseOwner(id);
  const data = readOwner(root, owner);
  data.phases[id] = { skipped: [], run: null, ...data.phases[id], ...patch };
  writeJson(path.join(root, relativeFile(root, owner)), data);
}
function allPhases(root) {
  const owners = new Set(legacyPhases(root).map(phaseOwner));
  const output = path.join(root, "_mano_output");
  if (fs.existsSync(output)) for (const name of fs.readdirSync(output)) {
    if (name === ".default.json") owners.add(null);
    else if (/^[a-z0-9][a-z0-9-]*\.json$/.test(name)) owners.add(ownerSlug(name.slice(0, -5)));
  }
  return [...owners].flatMap(owner => Object.entries(readOwner(root, owner).phases).map(([phaseId, record]) => ({ phaseId, ...record })));
}
module.exports = { selectedOwner, selectOwner, relativeFile, readSetting, writeSetting, readPhase, writePhase, allPhases };
