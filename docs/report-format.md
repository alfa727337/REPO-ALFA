# Report format

Every scan has a canonical `full-report.json` plus specialized evidence files under `reports/`.

## full-report.json

Top-level fields include:

- `target`
- `mode`
- `started_at`
- `finished_at`
- `modules`
- `routes`
- `observed_endpoints`
- `technologies`
- `framework_matches`
- `artifacts`
- `coverage`
- `fatal_errors`

Each module records status, timestamps, structured data, errors and the number of recovered failures.

## Specialized reports

- `route-graph.json` — route relationship graph.
- `endpoint-graph.json` — observed endpoint graph.
- `frameworks.json` — framework matches with confidence and evidence.
- `network-summary.json` — request classes, hosts and methods.
- `capture.har` — HAR-compatible network summary.
- `graphql.json` — observed GraphQL endpoints.
- `javascript.json` — imports, dynamic imports, URLs and source-map hints.
- `css.json` — CSS variables, fonts, media queries, URLs and keyframes.
- `dom-diff.json` — static vs rendered DOM deltas.
- `sourcemaps.json` — public source-map results.
- `security-audit.json` — passive header and cookie-attribute findings.
- `coverage.json` — coverage matrix for evidence layers.
- `forensic.sqlite3` — queryable index.
- `report.html` — portable human-readable report.

Raw evidence is kept outside `reports/` in directories such as `html/`, `dom/`, `network/`, `storage/`, `assets/`, `screenshots/`, `websocket/`, `console/`, `pwa/` and `sourcemaps/`.
