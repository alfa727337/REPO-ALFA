# Security Policy

REPO ALFA is intended for public-web analysis, internal research, QA, incident response, migration, archival/reconstruction work, and authorized security testing.

Use it only against systems you own or have explicit permission to assess. Do not use the project to steal credentials, hijack sessions, bypass access controls on third-party systems, or retrieve private server-side data that is not legitimately exposed to the browser.

## Reporting a vulnerability

If you discover a vulnerability in REPO ALFA itself, open a GitHub issue with a minimal reproduction that does not expose third-party secrets or production credentials.

## Design rule

Security-oriented modules should prefer evidence collection, configuration analysis, reproducibility, and safe validation. Potentially destructive behavior must never be enabled silently.
