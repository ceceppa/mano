# Phase Brief — ReportKit — Phase 1

## Why This Phase

Plugin authors currently format report output with ad-hoc functions. This phase gives them one stable public formatter they can configure and reuse.

## Vision

A plugin author creates a formatter, selects a built-in output style, and receives predictable report text without rebuilding formatting logic in every plugin.

## Phase Goal

Plugin authors can format report data through a stable public `ReportFormatter` class.

## Phase Scope

- Add the public `ReportFormatter` class.
- Support plain-text and Markdown output styles.

## Exit Criteria

1. Public formatter
   - Format the same report as plain text and Markdown: each result follows the selected style and contains the report title and rows

## Acknowledged Risks

- None.
