from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from .analyzers import discover_endpoints, fingerprint
from .api_classification import summarize_network
from .assets import AssetDownloader
from .browser_capture import BrowserCapture
from .checkpoints import Checkpoint, CheckpointStore
from .coverage import build_coverage, write_coverage
from .crawler import Crawler
from .css_analysis import analyze_directory as analyze_css_directory
from .discovery import PublicDiscovery
from .dom_analysis import analyze_capture as analyze_dom_capture
from .frameworks import analyze_frameworks
from .graphql_capture import detect_graphql, write_report as write_graphql_report
from .graphing import build_endpoint_graph, build_route_graph, export_graph
from .har import build_har
from .html_report import render_html_report
from .javascript_analysis import aggregate as aggregate_js, analyze_directory
from .models import ModuleResult, ScanConfig, ScanReport
from .plugins import PluginContext, run_plugins
from .pwa import PWAAnalyzer
from .reconstruction import ReconstructionEngine
from .recovery import RecoveryEngine
from .security_audit import audit_cookies, audit_headers
from .sourcemaps import SourceMapAnalyzer
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
    def __init__(self, config: ScanConfig, resume: bool = False) -> None:
        self.config = config
        self.resume_existing = resume
        host = urlparse(str(config.target)).netloc.replace(":", "_")
        self.output = config.output_root / host
        self.output.mkdir(parents=True, exist_ok=True)
        self.checkpoints = CheckpointStore(self.output)
        self.recovery = RecoveryEngine(retries=config.retries)
        self.report = ScanReport(target=str(config.target), mode=config.mode)
        (self.output / "scan-config.json").write_text(
            config.model_dump_json(indent=2), encoding="utf-8"
        )

    async def _module(self, name: str, fn):
        started = datetime.now(timezone.utc)
        if self.resume_existing:
            checkpoint = self.checkpoints.load(name)
            if checkpoint and checkpoint.completed:
                data = dict(checkpoint.payload)
                data["_resumed_from_checkpoint"] = True
                result = ModuleResult(
                    name=name,
                    status="complete",
                    started_at=started,
                    finished_at=datetime.now(timezone.utc),
                    data=data,
                    recovered_failures=0,
                )
                self.report.modules.append(result)
                return result

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
            browser = BrowserCapture(
                timeout_ms=int(self.config.timeout_seconds * 1000),
                user_agent=self.config.user_agent,
                storage_state=self.config.storage_state,
            )
            browser_result = await self._module(
                "browser-capture",
                lambda: browser.capture(
                    target,
                    self.output,
                    screenshot=self.config.screenshot,
                    capture_console=self.config.capture_console,
                    explore_ui_states=self.config.explore_ui_states,
                    max_ui_states=self.config.max_ui_states,
                ),
            )

        discovery_result = None
        if rank >= 1:
            discovery = PublicDiscovery(timeout=self.config.timeout_seconds)
            discovery_result = await self._module(
                "public-discovery",
                lambda: discovery.discover(target, self.output / "discovery"),
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
        manifest_url: str | None = None
        if static_result.status == "complete":
            routes.update(static_result.data.get("links", []))
            asset_urls.extend(static_result.data.get("assets", []))
            manifest_url = static_result.data.get("manifest")
            source = self.output / "html" / "source.html"
            if source.exists():
                texts.append(source.read_text(encoding="utf-8", errors="ignore"))

        if discovery_result and discovery_result.status == "complete":
            routes.update(discovery_result.data.get("urls", []))

        if crawl_result and crawl_result.status == "complete":
            routes.update(crawl_result.data.get("discovered", []))

        network_events: list[dict] = []
        network_urls: list[str] = []
        service_workers: list[dict] = []
        if browser_result and browser_result.status == "complete":
            asset_urls.extend(browser_result.data.get("scripts", []))
            asset_urls.extend(browser_result.data.get("stylesheets", []))
            network_events = browser_result.data.get("network", [])
            network_urls = [item["url"] for item in network_events if item.get("url")]
            service_workers = browser_result.data.get("service_workers", [])
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
        self.report.framework_matches = framework_matches

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
            network_summary_path = reports_dir / "network-summary.json"
            network_summary_path.write_text(
                json.dumps(summarize_network(network_events), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.report.artifacts.extend(
                [str(har_path), str(gql_path), str(network_summary_path)]
            )

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

            css_result = analyze_css_directory(self.output / "assets")
            css_path = reports_dir / "css.json"
            css_path.write_text(
                json.dumps(css_result, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.report.artifacts.append(str(css_path))

            dom_result = analyze_dom_capture(self.output, target)
            if dom_result is not None:
                dom_path = reports_dir / "dom-diff.json"
                dom_path.write_text(
                    json.dumps(dom_result, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                self.report.artifacts.append(str(dom_path))

            pwa = PWAAnalyzer(timeout=self.config.timeout_seconds)
            await self._module(
                "pwa-analysis",
                lambda: pwa.analyze(manifest_url, service_workers, self.output / "pwa"),
            )

            cookies: list[dict] = []
            storage_path = self.output / "storage" / "browser.json"
            if storage_path.exists():
                try:
                    cookies = json.loads(storage_path.read_text(encoding="utf-8")).get("cookies", [])
                except (ValueError, OSError):
                    cookies = []
            security = {
                "headers": audit_headers(static_result.data.get("headers", {})),
                "cookies": audit_cookies(cookies),
            }
            security_path = reports_dir / "security-audit.json"
            security_path.write_text(
                json.dumps(security, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.report.artifacts.append(str(security_path))

        if rank >= 3 and browser_result and browser_result.status == "complete":
            scripts = browser_result.data.get("scripts", [])[:100]
            source_map_analyzer = SourceMapAnalyzer(timeout=self.config.timeout_seconds)
            source_map_results = []
            for script_url in scripts:
                try:
                    source_map_results.append(
                        await source_map_analyzer.inspect(
                            script_url, self.output / "sourcemaps"
                        )
                    )
                except Exception as exc:
                    source_map_results.append({"script": script_url, "error": repr(exc)})
            source_map_path = reports_dir / "sourcemaps.json"
            source_map_path.write_text(
                json.dumps(source_map_results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.report.artifacts.append(str(source_map_path))

        if self.config.mode in {"reconstruction", "exhaustive"}:
            reconstruction = ReconstructionEngine()
            reconstruction_result = await self._module(
                "reconstruction",
                lambda: _sync_to_async(
                    reconstruction.reconstruct,
                    self.output,
                    self.output / "reconstructed",
                    target,
                ),
            )
            if reconstruction_result.status == "complete":
                self.report.artifacts.append(str(self.output / "reconstructed" / "index.html"))

        if self.config.plugins:
            plugin_context = PluginContext(
                target=target,
                output=self.output,
                mode=self.config.mode,
                report=self.report.model_dump(mode="json"),
            )
            plugin_results = await run_plugins(self.config.plugins, plugin_context)
            plugin_path = reports_dir / "plugins.json"
            plugin_path.write_text(
                json.dumps(plugin_results, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.report.artifacts.append(str(plugin_path))

        self.report.finished_at = datetime.now(timezone.utc)
        report_path = self.output / "full-report.json"
        report_path.write_text(self.report.model_dump_json(indent=2), encoding="utf-8")
        self.report.artifacts.append(str(report_path))

        report_dict = json.loads(report_path.read_text(encoding="utf-8"))
        coverage_path = write_coverage(report_dict, self.output, reports_dir / "coverage.json")
        self.report.coverage = build_coverage(report_dict, self.output)
        sqlite_path = build_index(report_dict, self.output, reports_dir / "forensic.sqlite3")
        html_path = render_html_report(report_dict, reports_dir / "report.html")
        self.report.artifacts.extend([str(coverage_path), str(sqlite_path), str(html_path)])

        report_path.write_text(self.report.model_dump_json(indent=2), encoding="utf-8")
        return self.report

    @classmethod
    def load_report(cls, path: Path) -> dict:
        return json.loads(path.read_text(encoding="utf-8"))


async def _sync_to_async(fn, *args):
    """Call a fast filesystem-only function from an async pipeline."""
    return fn(*args)
