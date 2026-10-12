from __future__ import annotations

import hashlib
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


def _safe_state_id(kind: str, index: int, label: str) -> str:
    digest = hashlib.sha1(label.encode("utf-8", errors="ignore")).hexdigest()[:8]
    return f"{kind}-{index:03d}-{digest}"


class BrowserCapture:
    def __init__(
        self,
        timeout_ms: int = 30000,
        user_agent: str | None = None,
        storage_state: Path | None = None,
    ) -> None:
        self.timeout_ms = timeout_ms
        self.user_agent = user_agent
        self.storage_state = storage_state

    async def _explore_ui_states(
        self,
        page,
        output: Path,
        max_states: int,
    ) -> list[dict[str, Any]]:
        """Explore low-risk disclosure states without submitting forms or generic buttons."""
        if max_states <= 0:
            return []

        state_root = output / "ui" / "states"
        state_root.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []
        candidates = await page.locator(
            '[role="tab"], button[aria-expanded], summary'
        ).all()

        for index, locator in enumerate(candidates[:max_states]):
            try:
                if not await locator.is_visible() or not await locator.is_enabled():
                    continue
                tag = await locator.evaluate("el => el.tagName.toLowerCase()")
                role = await locator.get_attribute("role")
                expanded_before = await locator.get_attribute("aria-expanded")
                text = ((await locator.inner_text()) or "").strip()[:300]
                aria_label = (await locator.get_attribute("aria-label") or "").strip()[:300]
                label = text or aria_label or f"{tag}-{index}"
                state_id = _safe_state_id(role or tag or "state", index, label)

                # Only known low-risk interactive surfaces are clicked.
                await locator.click(timeout=min(self.timeout_ms, 5000))
                try:
                    await page.wait_for_timeout(250)
                except Exception:
                    pass

                state_dir = state_root / state_id
                state_dir.mkdir(parents=True, exist_ok=True)
                dom_path = state_dir / "dom.html"
                dom_path.write_text(await page.content(), encoding="utf-8")
                screenshot_path = state_dir / "screenshot.png"
                try:
                    await page.screenshot(path=str(screenshot_path), full_page=True)
                    screenshot_written = True
                except Exception:
                    screenshot_written = False

                expanded_after = await locator.get_attribute("aria-expanded")
                results.append(
                    {
                        "id": state_id,
                        "selector_class": "safe-disclosure",
                        "tag": tag,
                        "role": role,
                        "label": label,
                        "aria_expanded_before": expanded_before,
                        "aria_expanded_after": expanded_after,
                        "url": page.url,
                        "dom": str(dom_path),
                        "screenshot": str(screenshot_path) if screenshot_written else None,
                    }
                )

                # Restore expandable disclosure state when possible so later states are independent.
                if expanded_before == "false" and expanded_after == "true":
                    try:
                        await locator.click(timeout=min(self.timeout_ms, 3000))
                    except Exception:
                        pass
            except Exception as exc:
                results.append(
                    {
                        "id": f"candidate-{index:03d}",
                        "selector_class": "safe-disclosure",
                        "status": "failed",
                        "error": repr(exc),
                    }
                )

        (output / "ui" / "states.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return results

    async def capture(
        self,
        url: str,
        output: Path,
        screenshot: bool = True,
        capture_console: bool = True,
        explore_ui_states: bool = True,
        max_ui_states: int = 30,
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
            if self.storage_state:
                if not self.storage_state.exists():
                    raise FileNotFoundError(f"storage state not found: {self.storage_state}")
                context_kwargs["storage_state"] = str(self.storage_state)

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

            ui_states: list[dict[str, Any]] = []
            if explore_ui_states:
                ui_states = await self._explore_ui_states(page, output, max_ui_states)

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
            "ui_states": len(ui_states),
            "network_events": len(network),
            "console_events": len(console_events),
            "page_errors": len(page_errors),
            "websockets": websockets,
            "network": network,
            "authorized_storage_state": bool(self.storage_state),
        }
