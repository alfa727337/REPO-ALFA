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
        websockets: list[dict] = []

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

            def on_websocket(ws) -> None:
                record = {"url": ws.url, "frames": []}
                websockets.append(record)
                ws.on(
                    "framesent",
                    lambda payload: record["frames"].append(
                        {"direction": "sent", "payload": str(payload)[:4096]}
                    ),
                )
                ws.on(
                    "framereceived",
                    lambda payload: record["frames"].append(
                        {"direction": "received", "payload": str(payload)[:4096]}
                    ),
                )

            page.on("websocket", on_websocket)

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

            browser_state = await page.evaluate(
                """async () => {
                  const dbs = indexedDB.databases ? await indexedDB.databases() : [];
                  const regs = navigator.serviceWorker
                    ? await navigator.serviceWorker.getRegistrations()
                    : [];
                  return {
                    localStorage: Object.fromEntries(Object.entries(localStorage)),
                    sessionStorage: Object.fromEntries(Object.entries(sessionStorage)),
                    location: location.href,
                    title: document.title,
                    scripts: Array.from(document.scripts).map(s => s.src).filter(Boolean),
                    stylesheets: Array.from(document.styleSheets).map(s => s.href).filter(Boolean),
                    indexedDB: dbs.map(db => ({name: db.name, version: db.version})),
                    serviceWorkers: regs.map(r => ({scope: r.scope, scriptURL: r.active?.scriptURL || null})),
                    performanceResources: performance.getEntriesByType('resource').map(e => ({
                      name: e.name,
                      initiatorType: e.initiatorType,
                      duration: e.duration,
                      transferSize: e.transferSize || 0
                    }))
                  };
                }"""
            )
            cookies = await context.cookies()
            browser_state["cookies"] = cookies

            (output / "network").mkdir(exist_ok=True)
            (output / "network" / "events.json").write_text(
                json.dumps(network, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (output / "websocket").mkdir(exist_ok=True)
            (output / "websocket" / "events.json").write_text(
                json.dumps(websockets, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (output / "storage").mkdir(exist_ok=True)
            (output / "storage" / "browser.json").write_text(
                json.dumps(browser_state, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            (output / "service-workers").mkdir(exist_ok=True)
            (output / "service-workers" / "registrations.json").write_text(
                json.dumps(browser_state.get("serviceWorkers", []), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            await browser.close()

        return {
            "status_code": response.status if response else None,
            "final_url": browser_state.get("location"),
            "title": browser_state.get("title"),
            "scripts": browser_state.get("scripts", []),
            "stylesheets": browser_state.get("stylesheets", []),
            "indexeddb": browser_state.get("indexedDB", []),
            "service_workers": browser_state.get("serviceWorkers", []),
            "network_events": len(network),
            "websockets": websockets,
            "network": network,
        }
