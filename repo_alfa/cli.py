from __future__ import annotations

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .engine import RepoAlfaEngine
from .models import ScanConfig

app = typer.Typer(help="REPO ALFA - Advanced Web Reverse Engineering Framework")
console = Console()


def _run(target: str, mode: str, output: Path, depth: int, browser: bool = True) -> None:
    config = ScanConfig(
        target=target,
        mode=mode,
        output_root=output,
        max_depth=depth,
        browser=browser,
    )
    report = asyncio.run(RepoAlfaEngine(config).run())
    table = Table(title=f"REPO ALFA :: {mode.upper()}")
    table.add_column("Module")
    table.add_column("Status")
    table.add_column("Errors")
    for module in report.modules:
        table.add_row(module.name, module.status, str(len(module.errors)))
    console.print(table)
    console.print(f"[bold]Technologies:[/bold] {', '.join(report.technologies) or 'none detected'}")
    console.print(f"[bold]Routes:[/bold] {len(report.routes)}")
    console.print(f"[bold]Observed endpoints:[/bold] {len(report.observed_endpoints)}")


@app.command()
def scan(target: str, output: Path = Path("output"), depth: int = 1) -> None:
    _run(target, "quick", output, depth)


@app.command()
def capture(target: str, output: Path = Path("output"), depth: int = 2) -> None:
    _run(target, "standard", output, depth)


@app.command()
def deep(target: str, output: Path = Path("output"), depth: int = 5) -> None:
    _run(target, "deep", output, depth)


@app.command()
def forensic(target: str, output: Path = Path("output"), depth: int = 10) -> None:
    _run(target, "forensic", output, depth)


@app.command()
def exhaustive(target: str, output: Path = Path("output"), depth: int = 15) -> None:
    _run(target, "exhaustive", output, depth)


@app.command()
def reconstruct(target: str, output: Path = Path("output"), depth: int = 8) -> None:
    _run(target, "reconstruction", output, depth)


@app.command()
def validate(path: Path) -> None:
    report = path / "full-report.json" if path.is_dir() else path
    if not report.exists():
        raise typer.BadParameter(f"report not found: {report}")
    data = json.loads(report.read_text(encoding="utf-8"))
    console.print("[green]Report is readable.[/green]")
    console.print(f"Target: {data.get('target')}")
    console.print(f"Modules: {len(data.get('modules', []))}")


@app.command()
def resume(path: Path) -> None:
    checkpoint_dir = path / "checkpoints"
    if not checkpoint_dir.exists():
        raise typer.BadParameter("checkpoint directory not found")
    checkpoints = sorted(checkpoint_dir.glob("*.json"))
    console.print(f"Found {len(checkpoints)} checkpoint(s).")
    for item in checkpoints:
        console.print(f" - {item.name}")


if __name__ == "__main__":
    app()
