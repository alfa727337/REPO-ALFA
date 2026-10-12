from __future__ import annotations

from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Protocol, Any


class AlfaPlugin(Protocol):
    name: str

    async def run(self, context: "PluginContext") -> dict[str, Any]: ...


@dataclass(slots=True)
class PluginContext:
    target: str
    output: Path
    mode: str
    report: dict[str, Any]


def load_plugin(spec: str) -> AlfaPlugin:
    """Load `module:attribute` without executing arbitrary shell commands."""
    if ":" not in spec:
        raise ValueError("plugin spec must be module:attribute")
    module_name, attribute = spec.split(":", 1)
    module = import_module(module_name)
    plugin = getattr(module, attribute)
    if isinstance(plugin, type):
        plugin = plugin()
    if not getattr(plugin, "name", None) or not hasattr(plugin, "run"):
        raise TypeError("plugin must expose name and async run(context)")
    return plugin


async def run_plugins(specs: list[str], context: PluginContext) -> list[dict]:
    results: list[dict] = []
    for spec in specs:
        try:
            plugin = load_plugin(spec)
            data = await plugin.run(context)
            results.append({"plugin": plugin.name, "status": "complete", "data": data})
        except Exception as exc:
            results.append({"plugin": spec, "status": "failed", "error": repr(exc)})
    return results
