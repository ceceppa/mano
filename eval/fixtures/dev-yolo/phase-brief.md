# Phase Brief — Stage Chain — Phase 1

## Why This Phase

The project needs a tiny dependency-free stage chain that downstream examples can load without setup.

## Phase Goal

Consumers can load base, feature, and release stage labels from three ordered CommonJS modules.

## Phase Scope

- Add the base stage module.
- Build the feature stage from the base stage.
- Build the release stage from the feature stage.

## Exit Criteria

1. Loading each module returns its expected cumulative stage label.

## Acknowledged Risks

- None.
