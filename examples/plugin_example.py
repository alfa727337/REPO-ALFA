from __future__ import annotations

from collections import Counter
from urllib.parse import urlparse


class HostInventoryPlugin:
    name = "host-inventory"

    async def run(self, context):
        report = context.report
        urls = list(report.get("routes", [])) + list(report.get("observed_endpoints", []))
        hosts = Counter(urlparse(url).netloc for url in urls if urlparse(url).netloc)
        return {
            "target": context.target,
            "unique_hosts": len(hosts),
            "hosts": dict(hosts.most_common()),
        }


plugin = HostInventoryPlugin()
