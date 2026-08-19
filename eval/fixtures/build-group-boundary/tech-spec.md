# Tech Spec — Label Registry

## Runtime

Node 18+, CommonJS, no dependencies. Every module is a plain `module.exports` object.

## Registry module

`src/registry.js` owns the in-memory label list for the life of the process.

| Export | Input | Result |
|---|---|---|
| `list()` | — | the registered labels as an array, in insertion order |
| `add(label)` | a non-empty string | the new number of registered labels |
| `clear()` | — | the number of labels removed |

The list starts empty on first require. No label is normalised, trimmed, or lower-cased.

## Formatting

Not in this phase.
