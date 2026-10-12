# Plugin development

REPO ALFA supports Python plugins loaded as `module:attribute`.

A plugin exposes a `name` and an async `run(context)` method.

```python
class ExamplePlugin:
    name = "example"

    async def run(self, context):
        return {
            "target": context.target,
            "mode": context.mode,
            "output": str(context.output),
        }

plugin = ExamplePlugin()
```

Run it with:

```bash
repo-alfa forensic https://example.com --plugin my_plugin:plugin
```

The `PluginContext` contains:

- `target`
- `output`
- `mode`
- a serialized snapshot of the current report

Plugin failures are isolated and written to `reports/plugins.json`; one plugin failure does not terminate the main scan.

Plugins should consume captured evidence rather than bypass authentication or attempt to access server-side data that was not exposed to the authorized browser session.
