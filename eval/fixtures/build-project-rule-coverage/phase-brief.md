# Phase Brief — ReportKit — Phase 1

## Why This Phase

Plugin authors currently format report output with ad-hoc functions. This phase gives them one stable public formatter they can configure and reuse.

## Phase Goal

Plugin authors can format report data through a stable public `ReportFormatter` class.

## Phase Scope

1. **Public formatter**
   a. **Plain text output** — a caller formats a report as plain text and gets the title and one line per row
   b. **Markdown output** — the same caller formats the same report as Markdown and gets a heading and a list

## Not This Phase

- HTML and PDF output, and any styling options beyond the two named ones.

## Exit Criteria

1. **Public formatter**
   a. Format a report with the plain style: the result contains the report title and one line per row
   b. Format the same report with the markdown style: the result contains the title as a heading and the rows as a list

## Acknowledged Risks

- None.
