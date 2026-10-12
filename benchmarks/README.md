# Benchmarks

REPO ALFA benchmarks should use local or explicitly authorized fixtures so results remain reproducible and do not depend on third-party production sites.

Measure at least:

- total scan wall-clock time;
- pages visited and routes discovered;
- assets captured and bytes preserved;
- network observations;
- recovered failures and retries;
- evidence coverage score;
- reconstruction asset rewrite count;
- peak memory where available.

Recommended fixture classes:

1. static HTML/CSS site;
2. SPA with client-side routing;
3. SSR/hydrated application;
4. PWA with Service Worker and manifest;
5. application with WebSocket traffic;
6. GraphQL client using observable GET/POST endpoint traffic;
7. minified bundle with a published source map;
8. deliberately degraded fixture with timeouts and missing assets to verify recovery.

Benchmark reports should record the REPO ALFA commit SHA, Python version, platform, target fixture version and scan mode.
