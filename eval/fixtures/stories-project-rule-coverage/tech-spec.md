# Tech Spec — ReportKit

## Public API

- `ReportFormatter` is a public TypeScript class declared in `src/api/ReportFormatter.ts`.
- Its `format(report, style)` method returns a string.
- Supported styles are `plain` and `markdown`.

## Out of Scope

- HTML and PDF output.
