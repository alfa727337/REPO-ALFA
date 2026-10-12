from __future__ import annotations

import json
import re
from bs4 import BeautifulSoup


def extract_framework_details(html: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    details: dict = {}

    next_data = soup.find("script", id="__NEXT_DATA__")
    if next_data and next_data.string:
        try:
            parsed = json.loads(next_data.string)
            details["Next.js"] = {
                "build_id": parsed.get("buildId"),
                "page": parsed.get("page"),
                "query_keys": sorted((parsed.get("query") or {}).keys()),
                "is_fallback": parsed.get("isFallback"),
                "gsp": parsed.get("gsp"),
                "gssp": parsed.get("gssp"),
            }
        except ValueError:
            details["Next.js"] = {"next_data_present": True, "parsed": False}

    angular_root = soup.find(attrs={"ng-version": True})
    if angular_root:
        details["Angular"] = {"version": angular_root.get("ng-version")}

    astro_islands = soup.find_all("astro-island")
    if astro_islands:
        components = []
        for island in astro_islands[:500]:
            components.append(
                {
                    "component_url": island.get("component-url"),
                    "component_export": island.get("component-export"),
                    "renderer_url": island.get("renderer-url"),
                    "client": island.get("client"),
                }
            )
        details["Astro"] = {"islands": components, "count": len(astro_islands)}

    react_roots = soup.select("[data-reactroot], #__next, #root")
    if react_roots:
        details["React"] = {"root_candidates": len(react_roots)}

    vue_scoped = set()
    for tag in soup.find_all(True):
        for attr in tag.attrs:
            if re.fullmatch(r"data-v-[0-9a-fA-F]+", attr):
                vue_scoped.add(attr)
    if vue_scoped:
        details["Vue"] = {"scoped_style_ids": sorted(vue_scoped)[:500]}

    sveltekit_markers = []
    for tag in soup.find_all(True):
        attrs = [name for name in tag.attrs if str(name).startswith("data-sveltekit-")]
        if attrs:
            sveltekit_markers.extend(attrs)
    immutable = sorted(
        {
            node.get("src") or node.get("href")
            for node in soup.find_all(["script", "link"])
            if (node.get("src") or node.get("href"))
            and "/_app/immutable/" in (node.get("src") or node.get("href"))
        }
    )
    if sveltekit_markers or immutable:
        details["SvelteKit"] = {
            "markers": sorted(set(sveltekit_markers)),
            "immutable_assets": immutable,
        }

    nuxt_assets = sorted(
        {
            node.get("src") or node.get("href")
            for node in soup.find_all(["script", "link"])
            if (node.get("src") or node.get("href"))
            and "/_nuxt/" in (node.get("src") or node.get("href"))
        }
    )
    if nuxt_assets:
        details["Nuxt"] = {"assets": nuxt_assets}

    return details
