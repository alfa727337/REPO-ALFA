# Troubleshooting

## Start with doctor

```bash
repo-alfa doctor
```

This checks Python, installed modules, Git and filesystem writability before a scan.

## Chromium does not launch

Install the browser and operating-system dependencies:

```bash
playwright install --with-deps chromium
```

For Docker, rebuild the provided image so the Playwright runtime and Chromium version stay aligned.

## A module failed but the scan continued

This is expected behavior. REPO ALFA isolates module failures, writes a checkpoint and continues independent layers. Inspect:

- `full-report.json`
- `reports/coverage.json`
- `checkpoints/`
- `reports/report.html`

Then retry incomplete stages with:

```bash
repo-alfa resume output/example.com
```

## A target has too many routes

Crawler caps prevent query explosions and unbounded scans. Increase depth deliberately only when the authorized target requires it. Tracking parameters are normalized out before deduplication.

## Source maps are unavailable

Forensic mode only inspects maps that are actually published or referenced by served JavaScript. `reports/sourcemaps.json` records the result rather than treating an unpublished map as a fatal error.

## Reconstruction looks incomplete

A reconstruction can only use artifacts that were captured. Check `assets/manifest.json`, `reports/coverage.json`, `reports/dom-diff.json` and the console/network evidence. Compare screenshots with:

```bash
repo-alfa visual-diff original.png reconstructed.png --output diff.png
```

## Authentication-required applications

Run the framework only with an authorized client context. REPO ALFA does not break login controls or recover server-side data that was not delivered to the authorized browser.
