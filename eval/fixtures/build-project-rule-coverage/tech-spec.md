# Tech Spec — ReportKit

## Public API

- `ReportFormatter` is a public class exported from the CommonJS module `src/api/report-formatter.js`.
- Its `format(report, style)` method returns a string. `report` is `{ title, rows }` where `rows` is an array of strings.
- Supported styles are `plain` and `markdown`. `plain` returns the title on its own line followed by one row per line. `markdown` returns the title as an `# ` heading followed by the rows as `- ` list items.

## Out of Scope

- HTML and PDF output.
