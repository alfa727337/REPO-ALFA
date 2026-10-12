from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .analyzers import discover_endpoints, fingerprint
from .assets import AssetDownloader
from .browser_capture import BrowserCapture
from .checkpoints import Checkpoint, CheckpointStore
from .crawler import Crawler
from .frameworks import analyze_frameworks
from .graphql_capture import detect_graphql, write_report as write_graphql_report
from .graphing import build_endpoint_graph, build_route_graph, export_graph
from .har import build_har
from .html_report import render_html_report
from .javascript_analysis import aggregate as aggregate_js, analyze_directory
from .models import ModuleResult, ScanConfig, ScanReport
from .recovery import RecoveryEngine
from .sqlite_index import build_index
from .static_capture import StaticCapture

MODE_RANK = {
    "quick": 0,
    "standard": 1,
    "deep": 2,
    "forensic": 3,
    "reconstruction": 4,
    "exhaustive": 5,
}


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
                recovered_failures=sum(
                    1 for e in self.recovery.events if e.operation == name and e.recovered
                ),
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
        rank = MODE_RANK[self.config.mode]

        static = StaticCapture(timeout=self.config.timeout_seconds)
        static_result = await self._module(
            "static-capture", lambda: static.fetch(target, self.output)
        )

        browser_result = None
        if self.config.browser:
            browser = BrowserCapture(timeout_ms=int(self.config.timeout_seconds * 1000))
            browser_result = await self._module(
                "browser-capture",
                lambda: browser.capture(target, self.output, screenshot=self.config.screenshot),
            )

        crawl_result = None
        if rank >= 1 and self.config.max_depth > 0:
            crawler = Crawler(
                max_depth=self.config.max_depth,
                timeout=self.config.timeout_seconds,
                same_origin_only=self.config.same_origin_only,
            )
            crawl_result = await self._module("crawler", lambda: crawler.crawl(target))

        routes: set[str] = set()
        texts: list[str] = []
        asset_urls: list[str] = []
        if static_result.status == "complete":
            routes.update(static_result.data.get("links", []))
            asset_urls.extend(static_result.data.get("assets", []))
            source = self.output / "html" / "source.html"
            if source.exists():
                texts.append(source.read_text(encoding="utf-8", errors="ignore"))

        if crawl_result and crawl_result.status == "complete":
            routes.update(crawl_result.data.get("discovered", []))

        network_events: list[dict] = []
        network_urls: list[str] = []
        if browser_result and browser_result.status == "complete":
            asset_urls.extend(browser_result.data.get("scripts", []))
            asset_urls.extend(browser_result.data.get("stylesheets", []))
            network_events = browser_result.data.get("network", [])
            network_urls = [item["url"] for item in network_events if item.get("url")]
            dom = self.output / "dom" / "rendered.html"
            if dom.exists():
                texts.append(dom.read_text(encoding="utf-8", errors="ignore"))

        if rank >= 2 and asset_urls:
            downloader = AssetDownloader(timeout=self.config.timeout_seconds)
            await self._module(
                "asset-download",
                lambda: downloader.download_many(asset_urls, self.output / "assets"),
            )

        technologies = fingerprint("\n".join(texts), asset_urls + network_urls)
        endpoints = discover_endpoints(texts, network_urls)
        framework_matches = analyze_frameworks("\n".join(texts), asset_urls + network_urls)

        self.report.routes = sorted(routes)
        self.report.observed_endpoints = endpoints
        self.report.technologies = technologies

        reports_dir = self.output / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)

        route_graph = export_graph(
            build_route_graph(target, self.report.routes), reports_dir / "route-graph.json"
        )
        endpoint_graph = export_graph(
            build_endpoint_graph(target, endpoints), reports_dir / "endpoint-graph.json"
        )
        framework_path = reports_dir / "frameworks.json"
        framework_path.write_text(
            json.dumps(framework_matches, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.report.artifacts.extend([str(route_graph), str(endpoint_graph), str(framework_path)])

        if network_events:
            har_path = build_har(network_events, target, reports_dir / "capture.har")
            gql_path = write_graphql_report(
                detect_graphql(network_events), reports_dir / "graphql.json"
            )
            self.report.artifacts.extend([str(har_path), str(gql_path)])

        if rank >= 2:
            js_findings = analyze_directory(self.output / "assets", target)
            js_summary = aggregate_js(js_findings)
            js_path = reports_dir / "javascript.json"
            js_path.write_text(
                json.dumps(
                    {"summary": js_summary, "files": js_findings},
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            self.report.artifacts.append(str(js_path))

        self.report.finished_at = datetime.now(timezone.utc)
        report_path = self.output / "full-report.json"
        report_path.write_text(self.report.model_dump_json(indent=2), encoding="utf-8")
        self.report.artifacts.append(str(report_path))

        report_dict = json.loads(report_path.read_text(encoding="utf-8"))
        sqlite_path = build_index(report_dict, self.output, reports_dir / "forensic.sqlite3")
        html_path = render_html_report(report_dict, reports_dir / "report.html")
        self.report.artifacts.extend([str(sqlite_path), str(html_path)])

        # Rewrite once so generated report artifacts are themselves recorded.
        report_path.write_text(self.report.model_dump_json(indent=2), encoding="utf-8")
        return self.report

    @classmethod
    def load_report(cls, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))
