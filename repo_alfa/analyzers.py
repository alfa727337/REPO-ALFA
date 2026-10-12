from __future__ import annotations

import re
from urllib.parse import urlparse


TECH_SIGNATURES: dict[str, tuple[str, ...]] = {
    "React": ("react", "__REACT_DEVTOOLS_GLOBAL_HOOK__"),
    "Next.js": ("/_next/", "__NEXT_DATA__"),
    "Vue": ("vue", "__VUE__"),
    "Nuxt": ("/_nuxt/", "__NUXT__"),
    "Angular": ("ng-version", "angular"),
    "Svelte": ("svelte",),
    "Astro": ("astro-island", "/_astro/"),
    "Remix": ("__remixContext",),
    "Vite": ("/@vite/", "__vite__"),
    "Webpack": ("webpackChunk", "__webpack_require__"),
}

API_PATTERN = re.compile(r"https?://[^\s\"'<>]+|/(?:api|graphql|v\d+|rest)/[^\s\"'<>]*", re.I)


def fingerprint(text: str, urls: list[str] | None = None) -> list[str]:
    haystack = text + "\n" + "\n".join(urls or [])
    found = [name for name, signatures in TECH_SIGNATURES.items() if any(sig in haystack for sig in signatures)]
    return sorted(set(found))


def discover_endpoints(texts: list[str], observed_urls: list[str]) -> list[str]:
    endpoints: set[str] = set(observed_urls)
    for text in texts:
        endpoints.update(match.rstrip("),;]") for match in API_PATTERN.findall(text))
    return sorted(endpoints)


def same_origin(url: str, target: str) -> bool:
    a, b = urlparse(url), urlparse(target)
    return a.scheme == b.scheme and a.netloc == b.netloc
