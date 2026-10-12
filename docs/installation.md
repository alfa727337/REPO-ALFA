# Installation

## Requirements

- Python 3.11+
- Chromium supported by Playwright
- Git

## Linux/macOS

```bash
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
playwright install chromium
```

## Windows PowerShell

```powershell
git clone https://github.com/alfa727337/REPO-ALFA.git
cd REPO-ALFA
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
playwright install chromium
```

## Docker

```bash
docker build -t repo-alfa .
docker run --rm -v "$PWD/output:/app/output" repo-alfa scan https://example.com
```

## Verify

```bash
repo-alfa --help
pytest -q
```

If Chromium cannot launch, run `playwright install --with-deps chromium` on a supported Linux host.
