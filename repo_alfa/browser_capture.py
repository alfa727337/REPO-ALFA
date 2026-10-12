from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from playwright.async_api import async_playwright

SENSITIVE_HEADERS = {"authorization", "cookie", "set-cookie", "proxy-authorization"}


def _redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return {
        key: ("<redacted>" if key.lower() in SENSITIVE_HEADERS else value)
        for key, value in headers.items()
    }


class BrowserCapture:
    def __init__(self, timeout_ms: int = 30000, user_agent: str | None = None) -> None:
        self.timeout_ms = timeout_ms
        self.user_agent = user_agent

    async def capture(
        self,
        url: str,
        output: Path,
        screenshot: bool = True,
        capture_console: bool = True,
    ) -> dict[str, Any]:
        output.mkdir(parents=True, exist_ok=True)
        network: list[dict[str, Any]] = []
        websockets: list[dict[str, Any]] = []
        console_events: list[dict[str, Any]] = []
        page_errors: list[str] = []

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context_kwargs: dict[str, Any] = {
                "viewport": {"width": 1440, "height": 1000},
                "ignore_https_errors": False,
            }
            if self.user_agent:
                context_kwargs["user_agent"] = self.user_agent
            context = await browser.new_context(**context_kwargs)
            page = await context.new_page()
            page.set_default_timeout(self.timeout_ms)

            async def on_request(req) -> None:
                try:
                    headers = await req.all_headers()
                except Exception:
                    headers = {}
                network.append(
                    {
                        "type": "request",
                        "method": req.method,
                        "url": req.url,
                        "resource_type": req.resource_type,
                        "headers": _redact_headers(headers),
                        "is_navigation_request": req.is_navigation_request(),
                    }
                )

            async def on_response(res) -> None:
                try:
                    headers = await res.all_headers()
                except Exception:
                    headers = {}
                network.append(
                    {
                        "type": "response",
                        "status": res.status,
                        "url": res.url,
                        "headers": _redact_headers(headers),
                        "from_service_worker": res.from_service_worker,
                    }
                )

            page.on("request", on_request)
            page.on("response", on_response)

            def on_websocket(ws) -> None:
                record: dict[str, Any] = {"url": ws.url, "frames": []}
                websockets.append(record)
                ws.on(
                    "framesent",
                    lambda payload: record["frames"].append(
                        {"direction": "sent", "payload_preview": str(payload)[:4096]}
                    ),
                )
                ws.on(
                    "framereceived",
                    lambda payload: record["frames"].append(
                        {"direction": "received", "payload_preview": str(payload)[:4096]}
                    ),
                )

            page.on("websocket", on_websocket)
            if capture_console:
                page.on(
                    "console",
                    lambda msg: console_events.append(
                        {"type": msg.type, "text": msg.text[:8192], "location": msg.location}
                    ),
                )
                page.on("pageerror", lambda exc: page_errors.append(str(exc)[:8192]))

            response = await page.goto(url, wait_until="domcontentloaded")
            try:
                await page.wait_for_load_state("networkidle", timeout=min(self.timeout_ms, 10000))
            except Exception:
                pass

            dom = await page.content()
            (output / "dom").mkdir(exist_ok=True)
            (output / "dom" / "rendered.html").write_text(dom, encoding="utf-8")

            if screenshot:
                screenshots = output / "screenshots"
                screenshots.mkdir(exist_ok=True)
                await page.screenshot(path=str(screenshots / "desktop.png"), full_page=True)
                await page.set_viewport_size({"width": 390, "height": 844})
                await page.screenshot(path=str(screenshots / "mobile.png"), full_page=True)
                await page.set_viewport_size({"width": 1440, "height": 1000})

            browser_state = await page.evaluate(
                """async () => {
                  const dbs = indexedDB.databases ? await indexedDB.databases() : [];
                  const regs = navigator.serviceWorker
                    ? await navigator.serviceWorker.getRegistrations()
                    : [];
                  const elements = Array.from(document.querySelectorAll(
                    'a,button,input,select,textarea,[role],[tabindex],details,summary'
                  )).slice(0, 5000).map((el, index) => ({
                    index,
                    tag: el.tagName.toLowerCase(),
                    id: el.id || null,
                    role: el.getAttribute('role'),
                    type: el.getAttribute('type'),
                    name: el.getAttribute('name'),
                    href: el.href || null,
                    text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 500),
                    disabled: !!el.disabled,
                    hidden: !!el.hidden,
                    ariaExpanded: el.getAttribute('aria-expanded'),
                    ariaControls: el.getAttribute('aria-controls')
                  }));
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
                      transferSize: e.transferSize || 0,
                      encodedBodySize: e.encodedBodySize || 0,
                      decodedBodySize: e.decodedBodySize || 0
                    })),
                    interactiveElements: elements,
                    meta: Array.from(document.querySelectorAll('meta')).map(m => ({
                      name: m.name || null,
                      property: m.getAttribute('property'),
                      content: m.content || null
                    })),
                    links: Array.from(document.querySelectorAll('link')).map(l => ({
                      rel: l.rel,
                      href: l.href,
                      as: l.as || null,
                      type: l.type || null
                    }))
                  };
                }"""
            )
            # Keep browser cookie metadata but never persist cookie values.
            cookies = await context.cookies()
            browser_state["cookies"] = [
                {
                    "name": item.get("name"),
                    "domain": item.get("domain"),
                    "path": item.get("path"),
                    "expires": item.get("expires"),
                    "httpOnly": item.get("httpOnly"),
                    "secure": item.get("secure"),
                    "sameSite": item.get("sameSite"),
                }
                for item in cookies
            ]

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
            (output / "ui").mkdir(exist_ok=True)
            (output / "ui" / "interactive-elements.json").write_text(
                json.dumps(browser_state.get("interactiveElements", []), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (output / "console").mkdir(exist_ok=True)
            (output / "console" / "events.json").write_text(
                json.dumps(
                    {"console": console_events, "page_errors": page_errors},
                    ensure_ascii=False,
                    indent=2,
                ),
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
            "interactive_elements": len(browser_state.get("interactiveElements", [])),
            "network_events": len(network),
            "console_events": len(console_events),
            "page_errors": len(page_errors),
            "websockets": websockets,
            "network": network,
        }
