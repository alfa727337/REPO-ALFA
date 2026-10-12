# Forensic mode

Forensic mode is designed for high-fidelity evidence preservation from the client-visible surface of an authorized web application.

```bash
repo-alfa forensic https://example.com --depth 10
```

## Pipeline

1. Static HTTP capture.
2. Chromium render and runtime observation.
3. Public robots/sitemap discovery.
4. Same-origin crawl.
5. Network, WebSocket, console and storage metadata capture.
6. Asset preservation with hashes and URL-to-local manifest.
7. JavaScript import, dynamic import, URL and source-map hint analysis.
8. CSS variable, font, media-query, URL and keyframe analysis.
9. Static-vs-rendered DOM comparison.
10. Framework fingerprinting.
11. GraphQL and generic API observation.
12. PWA manifest and registered Service Worker analysis.
13. Published source-map inspection.
14. Security-header and cookie-attribute review.
15. Route/API graphs, HAR, JSON, HTML and SQLite reports.

## Evidence policy

REPO ALFA keeps raw artifacts when possible and records module failures instead of silently dropping them. Authentication headers and cookie values are redacted from persisted evidence by default.

## Source maps

Only source maps explicitly published or referenced by JavaScript already served to the browser are inspected. If a map includes `sourcesContent`, forensic mode can preserve those mapped sources as evidence.

## Coverage

`reports/coverage.json` distinguishes completed evidence layers from unavailable layers. A missing source map is reported as unavailable rather than treated as a fatal scan failure.
