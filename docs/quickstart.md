# Quickstart

Run REPO ALFA only against applications you own or are authorized to assess.

## Quick scan

```bash
repo-alfa scan https://example.com
```

This captures the initial HTML, a rendered DOM snapshot, browser evidence and a small route set.

## Deep scan

```bash
repo-alfa deep https://example.com --depth 5
```

Deep mode adds recursive crawling, asset preservation, JavaScript and CSS analysis, DOM comparison, PWA inspection, GraphQL observation, HAR generation and structured reports.

## Forensic scan

```bash
repo-alfa forensic https://example.com --depth 10
```

Forensic mode additionally inspects published source maps and preserves evidence for later review.

## Exhaustive mode

```bash
repo-alfa exhaustive https://example.com --depth 15
```

Exhaustive mode runs the broadest pipeline and also attempts a local reconstruction from captured frontend assets.

## Output

Results are written under `output/<host>/`. Start with:

- `full-report.json`
- `reports/report.html`
- `reports/coverage.json`
- `reports/forensic.sqlite3`
- `reports/network-summary.json`
- `reports/javascript.json`
- `reports/css.json`
- `reports/dom-diff.json`
- `screenshots/desktop.png`
- `screenshots/mobile.png`

## Validate a capture

```bash
repo-alfa validate output/example.com
```

## Compare screenshots

```bash
repo-alfa visual-diff original.png reconstructed.png --output diff.png
```
