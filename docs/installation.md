# Installation

## Requirements

- Python 3.11+
- Chromium supported by Playwright
- Git
- Node.js 20+ is optional but recommended for the modern Babel AST analyzer

## Linux/macOS

```bash
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium
```

Install the optional JavaScript/TypeScript AST layer:

```bash
npm install
```

When Node and the Babel packages are available, REPO ALFA automatically enriches JavaScript reports with AST-derived imports, exports, dynamic imports, `fetch` calls, Axios calls, WebSocket constructors, functions, classes, URL-like literals and node counts. If Node is unavailable, the Python analyzer remains operational and reports the AST layer as unavailable rather than failing the scan.

## Windows PowerShell

```powershell
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
playwright install chromium
npm install
```

## Docker

```bash
docker build -t repo-alfa .
docker run --rm -v "$PWD/output:/app/output" repo-alfa scan https://example.com
```

The current Python Docker image runs the core analyzer. Install Node/Babel in a custom image when AST enrichment is required inside Docker.

## Verify

```bash
repo-alfa doctor
repo-alfa --help
pytest -q
```

If Chromium cannot launch, run `playwright install --with-deps chromium` on a supported Linux host.
