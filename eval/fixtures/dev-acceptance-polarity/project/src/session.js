"use strict";

// The session store. `signOut` destroys the record: a signed-out device stays
// locked and is expected to obtain a new code, per tech-spec §Session lifecycle.
const sessions = new Map();

function signIn(deviceId, now) {
  sessions.set(deviceId, { deviceId, signedInAt: now });
  return sessions.get(deviceId);
}

function signOut(deviceId) {
  sessions.delete(deviceId);
}

module.exports = { signIn, signOut, sessions };
