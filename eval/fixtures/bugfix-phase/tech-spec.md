# Tech Spec — Notekeeper

## Current Technical Summary

| | |
|---|---|
| Runtime / framework | React Native (Expo) |
| Language | TypeScript |
| Data / storage | Local, AsyncStorage, JSON-serialized notes array |
| Main interfaces | Note list screen, note editor screen |
| Testing | Jest + React Native Testing Library |
| Key constraints | Offline-only; no backend |

## Tech stack

- React Native via Expo, TypeScript.

## Libraries & dependencies

| Category | Decision | Why | Install |
|----------|----------|-----|---------|
| Storage | `@react-native-async-storage/async-storage` | Local persistence, no backend | `npx expo install @react-native-async-storage/async-storage` |
| Testing | Jest + `@testing-library/react-native` | Standard RN test stack | `npm install -D @testing-library/react-native@latest` |

## Data model

| Entity | Fields | Notes |
|--------|--------|-------|
| Note | `id` (string, uuid), `body` (string), `createdAt` (number, epoch ms) | `id` is the stable key; `createdAt` defines order |

## Storage strategy

- Notes persisted as a JSON array under a single AsyncStorage key `notes`.
- List is sorted by `createdAt` ascending on read.

## Key technical decisions

- Notes are identified and deleted by `id`, never by list index.

## Out of Scope

- No backend sync.
- No rich-text formatting.
