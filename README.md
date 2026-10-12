# REPO ALFA

[![CI](https://github.com/alfa727337/REPO-ALFA/actions/workflows/ci.yml/badge.svg)](https://github.com/alfa727337/REPO-ALFA/actions/workflows/ci.yml)

**Advanced Web Reverse Engineering, Deep Analysis, Reconstruction and Resilient Capture Framework.**

REPO ALFA is a modular framework for high-fidelity analysis of the browser-visible surface of modern web applications. It combines static HTTP analysis, real Chromium rendering, runtime observation, recursive discovery, asset preservation, JavaScript/CSS/DOM analysis, published source-map inspection, PWA inspection, reconstruction and forensic reporting.

The design goal is not to depend on one technique. If one evidence layer fails, the pipeline records that failure, preserves completed work, attempts recovery where appropriate and continues with independent layers.

> **Core rule:** Detect → Capture → Analyze → Preserve → Recover → Reconstruct → Validate → Report.

## What it captures

- raw HTML and response metadata;
- final rendered DOM;
- desktop and mobile screenshots;
- same-origin routes and sitemap-discovered routes;
- client-visible assets with SHA-256 hashes and a URL-to-local manifest;
- scripts, stylesheets, images, fonts and other downloaded resources;
- browser network events and a HAR-compatible report;
- generic API and GraphQL endpoint observations;
- WebSocket metadata and bounded frame previews;
- localStorage/sessionStorage inventory, IndexedDB database metadata and cookie attributes;
- Service Worker registrations and PWA manifest metadata;
- console messages and page errors;
- interactive UI element inventory;
- JavaScript imports, dynamic imports, URLs and source-map hints;
- CSS variables, fonts, media queries, keyframes and referenced URLs;
- static-versus-rendered DOM deltas;
- framework fingerprints with confidence/evidence;
- public source maps referenced by served JavaScript;
- route and endpoint graphs;
- passive security-header and cookie-attribute findings;
- JSON, HTML and SQLite forensic reports;
- reconstruction artifacts and visual-diff metrics.

## Framework fingerprints

Built-in signatures currently cover React, Next.js, Vue, Nuxt, Angular, Svelte, SvelteKit, Astro, Remix, Vite and Webpack. The plugin SDK can add specialized analyzers without modifying the core engine.

## Scan modes

| Mode | Purpose | Typical depth |
| --- | --- | ---: |
| `scan` | Fast first-pass capture | 1 |
| `capture` | Standard browser + static capture | 2 |
| `deep` | Assets, JS/CSS/DOM and PWA analysis | 5 |
| `forensic` | Deep analysis + published source maps | 10 |
| `reconstruct` | Deep capture + local frontend reconstruction | 8 |
| `exhaustive` | Broadest available pipeline + reconstruction | 15 |

## Commands

```bash
repo-alfa scan https://example.com
repo-alfa capture https://example.com
repo-alfa map https://example.com
repo-alfa assets https://example.com
repo-alfa scripts https://example.com
repo-alfa endpoints https://example.com
repo-alfa technologies https://example.com
repo-alfa deep https://example.com --depth 5
repo-alfa forensic https://example.com --depth 10
repo-alfa exhaustive https://example.com --depth 15
repo-alfa reconstruct https://example.com
repo-alfa validate output/example.com
repo-alfa resume output/example.com
repo-alfa visual-diff original.png reconstructed.png --output diff.png
```

Plugins can be attached to forensic/exhaustive scans:

```bash
repo-alfa forensic https://example.com --plugin my_plugin:plugin
```

## Installation

```bash
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e '.[dev]'
playwright install chromium
```

Or with Docker:

```bash
docker build -t repo-alfa .
docker run --rm -v "$PWD/output:/app/output" repo-alfa deep https://example.com
```

See [docs/installation.md](docs/installation.md) for platform-specific instructions.

## Evidence tree

A deep/forensic scan can produce an output similar to:

```text
output/example.com/
├── scan-config.json
├── full-report.json
├── checkpoints/
├── html/
│   ├── source.html
│   └── metadata.json
├── dom/
│   └── rendered.html
├── headers/
├── network/
├── websocket/
├── storage/
├── service-workers/
├── console/
├── ui/
├── screenshots/
│   ├── desktop.png
│   └── mobile.png
├── discovery/
├── assets/
│   └── manifest.json
├── pwa/
├── sourcemaps/
├── reconstructed/
└── reports/
    ├── report.html
    ├── forensic.sqlite3
    ├── coverage.json
    ├── route-graph.json
    ├── endpoint-graph.json
    ├── network-summary.json
    ├── capture.har
    ├── graphql.json
    ├── javascript.json
    ├── css.json
    ├── dom-diff.json
    ├── frameworks.json
    ├── sourcemaps.json
    └── security-audit.json
```

## Recovery and resume

Each recoverable module writes an atomic checkpoint. Re-running with:

```bash
repo-alfa resume output/example.com
```

loads `scan-config.json`, restores completed checkpoint payloads and re-runs incomplete modules. This prevents a late-stage error from forcing the entire target to be captured again.

## Reconstruction

`reconstruct` and `exhaustive` modes build a local preview from captured frontend artifacts. The reconstruction engine reads the asset manifest, rewrites references that have a captured local equivalent and emits a local server helper.

```bash
cd output/example.com/reconstructed
python serve.py
```

See [docs/reconstruction.md](docs/reconstruction.md).

## Reports

`full-report.json` is the canonical machine-readable summary. Additional reports provide focused evidence layers. `forensic.sqlite3` makes routes, endpoints, technologies and module state queryable; `report.html` provides a portable human-readable view; and `coverage.json` explicitly identifies completed and unavailable evidence layers.

See [docs/report-format.md](docs/report-format.md).

## Development

```bash
make dev
make check
```

CI runs Ruff and Pytest for every push to `main` and every pull request. New analyzers should include unit tests and must fail independently rather than crashing unrelated stages.

## Documentation

- [Installation](docs/installation.md)
- [Quickstart](docs/quickstart.md)
- [Architecture](docs/architecture.md)
- [Forensic mode](docs/forensic-mode.md)
- [Reconstruction](docs/reconstruction.md)
- [Plugin development](docs/plugin-development.md)
- [Report format](docs/report-format.md)
- [Security policy](SECURITY.md)
- [Roadmap](ROADMAP.md)
- [Contributing](CONTRIBUTING.md)

## Scope and authorization

Use REPO ALFA only on applications you own or have permission to analyze. It is built for web engineering, migration, compatibility research, observability, reconstruction of authorized client-visible frontends and authorized security assessment. It does not attempt to break authentication, steal sessions or recover server-side/private data that was never delivered to the authorized client.

No web analysis framework can truthfully guarantee access to information a server does not expose. REPO ALFA instead targets maximum observable coverage, explicit diagnostics, evidence preservation and no silent failure.
