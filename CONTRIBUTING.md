# Contributing

## Development setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium
pytest -q
ruff check repo_alfa tests
```

## Engineering rules

- Preserve raw evidence before deriving conclusions.
- A module failure must not crash the entire scan unless the target itself is unusable.
- Prefer deterministic output and explicit schemas.
- Add tests for every parser, analyzer, or recovery path.
- Keep network collection separate from evidence interpretation.
- Never silently discard errors; record them in checkpoints/reports.
- Security modules must be suitable for authorized testing and non-destructive by default.

## Pull requests

Describe what changed, which evidence path is affected, how failure handling works, and which tests cover the behavior.
