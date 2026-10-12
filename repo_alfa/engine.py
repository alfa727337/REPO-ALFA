from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .analyzers import discover_endpoints, fingerprint
from .browser_capture import BrowserCapture
from .checkpoints import Checkpoint, CheckpointStore
from .models import ModuleResult, ScanConfig, ScanReport
from .recovery import RecoveryEngine
from .static_capture import StaticCapture


class RepoAlfaEngine:
    def __init__(self, config: ScanConfig) -> None:
        self.config = config
        host = urlparse(str(config.target)).netloc.replace(":", "_")
        self.output = config.output_root / host
        self.output.mkdir(parents=True, exist_ok=True)
        self.checkpoints = CheckpointStore(self.output)
        self.recovery = RecoveryEngine(retries=config.retries)
        self.report = ScanReport(target=str(config.target), mode=config.mode)

    async def _module(self, name: str, fn):
        started = datetime.now(timezone.utc)
        try:
            data = await self.recovery.run(name, fn)
            result = ModuleResult(
                name=name,
                status="complete",
                started_at=started,
                finished_at=datetime.now(timezone.utc),
                data=data,
                recovered_failures=sum(1 for e in self.recovery.events if e.operation == name and e.recovered),
            )
            self.checkpoints.save(Checkpoint(stage=name, completed=True, payload=data))
        except Exception as exc:
            result = ModuleResult(
                name=name,
                status="failed",
                started_at=started,
                finished_at=datetime.now(timezone.utc),
                errors=[repr(exc)],
            )
            self.checkpoints.save(
                Checkpoint(stage=name, completed=False, payload={"error": repr(exc)})
            )
        self.report.modules.append(result)
        return result

    async def run(self) -> ScanReport:
        target = str(self.config.target)
        static = StaticCapture(timeout=self.config.timeout_seconds)
        static_result = await self._module("static-capture", lambda: static.fetch(target, self.output))

        browser_result = None
        if self.config.browser:
            browser = BrowserCapture(timeout_ms=int(self.config.timeout_seconds * 1000))
            browser_result = await self._module(
                "browser-capture",
                lambda: browser.capture(target, self.output, screenshot=self.config.screenshot),
            )

        routes: set[str] = set()
        texts: list[str] = []
        urls: list[str] = []
        if static_result.status == "complete":
            routes.update(static_result.data.get("links", []))
            urls.extend(static_result.data.get("assets", []))
            source = self.output / "html" / "source.html"
            if source.exists():
                texts.append(source.read_text(encoding="utf-8", errors="ignore"))

        network_urls: list[str] = []
        if browser_result and browser_result.status == "complete":
            urls.extend(browser_result.data.get("scripts", []))
            urls.extend(browser_result.data.get("stylesheets", []))
            network_urls = [
                item["url"]
                for item in browser_result.data.get("network", [])
                if item.get("url")
            ]
            dom = self.output / "dom" / "rendered.html"
            if dom.exists():
                texts.append(dom.read_text(encoding="utf-8", errors="ignore"))

        tech = fingerprint("\n".join(texts), urls + network_urls)
        endpoints = discover_endpoints(texts, network_urls)

        self.report.routes = sorted(routes)
        self.report.observed_endpoints = endpoints
        self.report.technologies = tech
        self.report.finished_at = datetime.now(timezone.utc)

        report_path = self.output / "full-report.json"
        report_path.write_text(self.report.model_dump_json(indent=2), encoding="utf-8")
        self.report.artifacts.append(str(report_path))
        return self.report

    @classmethod
    def load_report(cls, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
