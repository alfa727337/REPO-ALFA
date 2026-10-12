from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .engine import RepoAlfaEngine
from .models import ScanConfig
from .validator import validate_capture
from .visual_diff import compare_images

app = typer.Typer(help="REPO ALFA - Advanced Web Reverse Engineering Framework")
console = Console()


def _execute(
    target: str,
    mode: str,
    output: Path,
    depth: int,
    browser: bool = True,
    plugins: list[str] | None = None,
):
    config = ScanConfig(
        target=target,
        mode=mode,
        output_root=output,
        max_depth=depth,
        browser=browser,
        plugins=plugins or [],
    )
    return asyncio.run(RepoAlfaEngine(config).run())


def _print_summary(report) -> None:
    table = Table(title=f"REPO ALFA :: {report.mode.upper()}")
    table.add_column("Module")
    table.add_column("Status")
    table.add_column("Recovered")
    table.add_column("Errors")
    for module in report.modules:
        table.add_row(
            module.name,
            module.status,
            str(module.recovered_failures),
            str(len(module.errors)),
        )
    console.print(table)
    console.print(
        f"[bold]Technologies:[/bold] {', '.join(report.technologies) or 'none detected'}"
    )
    console.print(f"[bold]Routes:[/bold] {len(report.routes)}")
    console.print(f"[bold]Observed endpoints:[/bold] {len(report.observed_endpoints)}")
    if report.framework_matches:
        names = [f"{item.get('name')} ({item.get('confidence')})" for item in report.framework_matches]
        console.print(f"[bold]Frameworks:[/bold] {', '.join(names)}")
    if report.coverage:
        console.print(f"[bold]Coverage:[/bold] {report.coverage.get('score', 0)}%")


def _run(
    target: str,
    mode: str,
    output: Path,
    depth: int,
    browser: bool = True,
    plugins: list[str] | None = None,
) -> None:
    report = _execute(target, mode, output, depth, browser, plugins)
    _print_summary(report)


@app.command()
def scan(target: str, output: Path = Path("output"), depth: int = 1) -> None:
    _run(target, "quick", output, depth)


@app.command()
def capture(target: str, output: Path = Path("output"), depth: int = 2) -> None:
    _run(target, "standard", output, depth)


@app.command("map")
def map_site(target: str, output: Path = Path("output"), depth: int = 4) -> None:
    report = _execute(target, "deep", output, depth)
    console.print_json(data={"routes": report.routes})


@app.command()
def assets(target: str, output: Path = Path("output"), depth: int = 3) -> None:
    report = _execute(target, "deep", output, depth)
    asset_modules = [m.model_dump(mode="json") for m in report.modules if m.name == "asset-download"]
    console.print_json(data={"asset_modules": asset_modules})


@app.command()
def scripts(target: str, output: Path = Path("output"), depth: int = 2) -> None:
    report = _execute(target, "standard", output, depth)
    browser = next((m for m in report.modules if m.name == "browser-capture"), None)
    console.print_json(data={"scripts": browser.data.get("scripts", []) if browser else []})


@app.command()
def endpoints(target: str, output: Path = Path("output"), depth: int = 3) -> None:
    report = _execute(target, "deep", output, depth)
    console.print_json(data={"endpoints": report.observed_endpoints})


@app.command()
def technologies(target: str, output: Path = Path("output"), depth: int = 1) -> None:
    report = _execute(target, "standard", output, depth)
    console.print_json(
        data={
            "technologies": report.technologies,
            "frameworks": report.framework_matches,
        }
    )


@app.command()
def deep(target: str, output: Path = Path("output"), depth: int = 5) -> None:
    _run(target, "deep", output, depth)


@app.command()
def forensic(
    target: str,
    output: Path = Path("output"),
    depth: int = 10,
    plugin: list[str] | None = typer.Option(None, "--plugin", help="module:attribute plugin"),
) -> None:
    _run(target, "forensic", output, depth, plugins=plugin)


@app.command()
def exhaustive(
    target: str,
    output: Path = Path("output"),
    depth: int = 15,
    plugin: list[str] | None = typer.Option(None, "--plugin", help="module:attribute plugin"),
) -> None:
    _run(target, "exhaustive", output, depth, plugins=plugin)


@app.command()
def reconstruct(target: str, output: Path = Path("output"), depth: int = 8) -> None:
    _run(target, "reconstruction", output, depth)


@app.command()
def validate(path: Path) -> None:
    root = path.parent if path.is_file() else path
    result = validate_capture(root)
    console.print_json(data=result.to_dict())
    if not result.ok:
        raise typer.Exit(code=2)


@app.command("visual-diff")
def visual_diff(
    left: Path,
    right: Path,
    output: Path = Path("visual-diff.png"),
) -> None:
    result = compare_images(left, right, output)
    console.print_json(data=result.to_dict())


@app.command()
def resume(path: Path) -> None:
    checkpoint_dir = path / "checkpoints"
    if not checkpoint_dir.exists():
        raise typer.BadParameter("checkpoint directory not found")
    checkpoints = sorted(checkpoint_dir.glob("*.json"))
    console.print(f"Found {len(checkpoints)} checkpoint(s).")
    for item in checkpoints:
        data = json.loads(item.read_text(encoding="utf-8"))
        status = "complete" if data.get("completed") else "incomplete"
        console.print(f" - {item.name}: {status}")


if __name__ == "__main__":
    app()
