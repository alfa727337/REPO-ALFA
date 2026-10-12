# REPO ALFA

REPO ALFA is an advanced web reverse-engineering, capture, mapping, reconstruction and forensic analysis framework focused on maximum observable coverage, resilience and reproducibility.

## Core goals

- Static and rendered DOM capture
- Recursive crawling and route discovery
- Browser capture through Playwright/Chromium
- Fetch/XHR/network event recording
- WebSocket, Service Worker and browser storage observation
- Asset collection and hashing
- JavaScript bundle analysis, imports, dynamic imports and URL extraction
- Public source-map discovery and preservation
- Framework fingerprinting for Next.js, React, Nuxt, Vue, Angular, Svelte/SvelteKit, Astro, Remix, Vite and Webpack
- GraphQL endpoint observation
- HAR generation
- Route and endpoint graphs
- HTML, JSON and SQLite forensic reports
- Recovery engine with retries and checkpoints
- Plugin SDK
- Reconstruction and validation workflows

## Commands

```bash
repo-alfa scan https://example.com
repo-alfa capture https://example.com
repo-alfa deep https://example.com
repo-alfa forensic https://example.com
repo-alfa exhaustive https://example.com
repo-alfa reconstruct https://example.com
repo-alfa validate output/example.com
repo-alfa resume output/example.com
```

## Install

```bash
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
playwright install chromium
```

## Output

A typical target produces a structured evidence tree with raw HTML, rendered DOM, screenshots, network events, storage data, downloaded assets, route/API graphs, JavaScript analysis, GraphQL findings, HAR, SQLite index and an HTML report.

## Reliability model

REPO ALFA follows a recovery-first pipeline: detect → capture → analyze → preserve → recover → validate → report. A failure in one module is recorded and does not automatically terminate the full scan. Checkpoints preserve partial progress and raw evidence remains available for later analysis.

## Authorized use

Use REPO ALFA on systems you own or are authorized to assess. The framework is designed for web engineering, migration, compatibility work, research and authorized security assessment. It does not attempt to bypass authentication or obtain server-side data that the browser is not legitimately able to access.
