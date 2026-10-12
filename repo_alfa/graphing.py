from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse

import networkx as nx


def build_route_graph(seed: str, routes: list[str]) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(seed, kind="seed")
    for route in sorted(set(routes)):
        graph.add_node(route, kind="route")
        graph.add_edge(seed, route, relation="discovered")
    return graph


def build_endpoint_graph(page_url: str, endpoints: list[str]) -> nx.DiGraph:
    graph = nx.DiGraph()
    graph.add_node(page_url, kind="page")
    page_host = urlparse(page_url).netloc
    for endpoint in sorted(set(endpoints)):
        kind = "same-origin-endpoint" if urlparse(endpoint).netloc in {"", page_host} else "external-endpoint"
        graph.add_node(endpoint, kind=kind)
        graph.add_edge(page_url, endpoint, relation="observed")
    return graph


def export_graph(graph: nx.DiGraph, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "nodes": [{"id": node, **data} for node, data in graph.nodes(data=True)],
        "edges": [
            {"source": source, "target": target, **data}
            for source, target, data in graph.edges(data=True)
        ],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
