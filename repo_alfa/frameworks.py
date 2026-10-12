from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(slots=True)
class FrameworkMatch:
    name: str
    confidence: float
    evidence: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


SIGNATURES: dict[str, tuple[str, ...]] = {
    "Next.js": ("__NEXT_DATA__", "/_next/static/", "next/router", "next/navigation"),
    "React": ("react-dom", "__REACT_DEVTOOLS_GLOBAL_HOOK__", "data-reactroot"),
    "Nuxt": ("__NUXT__", "/_nuxt/", "nuxt-link"),
    "Vue": ("__VUE__", "data-v-", "vue-router"),
    "Angular": ("ng-version", "zone.js", "@angular/core"),
    "SvelteKit": ("__sveltekit", "/_app/immutable/", "data-sveltekit"),
    "Svelte": ("svelte/internal", "svelte-h"),
    "Astro": ("astro-island", "astro-slot", "/_astro/"),
    "Remix": ("__remixContext", "@remix-run/", "__remixManifest"),
    "Vite": ("/@vite/client", "import.meta.env", "/@id/"),
    "Webpack": ("webpackChunk", "__webpack_require__", "webpackJsonp"),
}


def analyze_frameworks(html: str, urls: list[str], js_text: str = "") -> list[dict]:
    haystack = "\n".join([html, js_text, *urls])
    results: list[FrameworkMatch] = []
    for name, signatures in SIGNATURES.items():
        hits = [sig for sig in signatures if sig in haystack]
        if not hits:
            continue
        confidence = min(0.99, 0.45 + (len(hits) / len(signatures)) * 0.55)
        results.append(FrameworkMatch(name=name, confidence=round(confidence, 2), evidence=hits))
    results.sort(key=lambda item: item.confidence, reverse=True)
    return [item.to_dict() for item in results]
