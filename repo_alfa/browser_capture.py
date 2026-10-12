from __future__ import annotations

import json
from pathlib import Path

from playwright.async_api import async_playwright


class BrowserCapture:
    def __init__(self, timeout_ms: int = 30000) -> None:
        self.timeout_ms = timeout_ms

    async def capture(self, url: str, output: Path, screenshot: bool = True) -> dict:
        output.mkdir(parents=True, exist_ok=True)
        network: list[dict] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                viewport={"width": 1440, "height": 1000},
                ignore_https_errors=False,
            )
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)

            page.on(
                "request",
                lambda req: network.append(
                    {
                        "type": "request",
                        "method": req.method,
                        "url": req.url,
                        "resource_type": req.resource_type,
                    }
                ),
            )
            page.on(
                "response",
                lambda res: network.append(
                    {
                        "type": "response",
                        "status": res.status,
                        "url": res.url,
                    }
                ),
            )

            response = await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=min(self.timeout_ms, 10000))
            except Exception:
                pass

            dom = await page.content()
            (output / "dom").mkdir(exist_ok=True)
            (output / "dom" / "rendered.html").write_text(dom, encoding="utf-8")

            if screenshot:
                (output / "screenshots").mkdir(exist_ok=True)
                await page.screenshot(path=str(output / "screenshots" / "desktop.png"), full_page=True)

            storage = await page.evaluate(
                """() => ({
                  localStorage: Object.fromEntries(Object.entries(localStorage)),
                  sessionStorage: Object.fromEntries(Object.entries(sessionStorage)),
                  location: location.href,
                  title: document.title,
                  scripts: Array.from(document.scripts).map(s => s.src).filter(Boolean),
                  stylesheets: Array.from(document.styleSheets).map(s => s.href).filter(Boolean)
                })"""
            )
            cookies = await context.cookies()
            storage["cookies"] = cookies

            (output / "network").mkdir(exist_ok=True)
            (output / "network" / "events.json").write_text(
                json.dumps(network, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (output / "storage").mkdir(exist_ok=True)
            (output / "storage" / "browser.json").write_text(
                json.dumps(storage, ensure_ascii=False, indent=2), encoding="utf-8"
            )

            await browser.close()

        return {
            "status_code": response.status if response else None,
            "final_url": storage.get("location"),
            "title": storage.get("title"),
            "scripts": storage.get("scripts", []),
            "stylesheets": storage.get("stylesheets", []),
            "network_events": len(network),
            "network": network,
        }
