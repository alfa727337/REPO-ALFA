from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from .doctor import run_doctor
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
    storage_state: Path | None = None,
    explore_ui_states: bool = True,
    max_ui_states: int = 30,
):
    config = ScanConfig(
        target=target,
        mode=mode,
        output_root=output,
        max_depth=depth,
        browser=browser,
        plugins=plugins or [],
        storage_state=storage_state,
        explore_ui_states=explore_ui_states,
        max_ui_states=max_ui_states,
    )
    return asyncio.run(RepoAlfaEngine(config).run())


def _print_summary(report) -> None:
    table = Table(title=f"REPO ALFA :: {report.mode.upper()}")
    table.add_column("Module")
    table.add_column("Status")
    table.add_column("Recovered")
    table.add_column("Errors")
    for module in report.modules:
        resumed = " (resume)" if module.data.get("_resumed_from_checkpoint") else ""
        table.add_row(
            module.name + resumed,
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
        names = [
            f"{item.get('name')} ({item.get('confidence')})"
            for item in report.framework_matches
        ]
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
    storage_state: Path | None = None,
    explore_ui_states: bool = True,
    max_ui_states: int = 30,
) -> None:
    report = _execute(
        target,
        mode,
        output,
        depth,
        browser,
        plugins,
        storage_state,
        explore_ui_states,
        max_ui_states,
    )
    _print_summary(report)


@app.command()
def doctor() -> None:
    """Check the local runtime before starting a scan."""
    result = run_doctor()
    console.print_json(data=result)
    if not result["ok"]:
        raise typer.Exit(code=2)


@app.command()
def scan(target: str, output: Path = Path("output"), depth: int = 1) -> None:
    _run(target, "quick", output, depth)


@app.command()
def capture(
    target: str,
    output: Path = Path("output"),
    depth: int = 2,
    storage_state: Path | None = typer.Option(
        None, "--storage-state", help="Authorized Playwright storage-state JSON"
    ),
    explore_ui: bool = typer.Option(True, "--explore-ui/--no-explore-ui"),
    max_ui_states: int = typer.Option(30, "--max-ui-states", min=0, max=250),
) -> None:
    _run(
        target,
        "standard",
        output,
        depth,
        storage_state=storage_state,
        explore_ui_states=explore_ui,
        max_ui_states=max_ui_states,
    )


@app.command("map")
def map_site(target: str, output: Path = Path("output"), depth: int = 4) -> None:
    report = _execute(target, "deep", output, depth)
    console.print_json(data={"routes": report.routes})


@app.command()
def assets(target: str, output: Path = Path("output"), depth: int = 3) -> None:
    report = _execute(target, "deep", output, depth)
    asset_modules = [
        m.model_dump(mode="json")
        for m in report.modules
        if m.name == "asset-download"
    ]
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
def deep(
    target: str,
    output: Path = Path("output"),
    depth: int = 5,
    storage_state: Path | None = typer.Option(None, "--storage-state"),
    explore_ui: bool = typer.Option(True, "--explore-ui/--no-explore-ui"),
    max_ui_states: int = typer.Option(30, "--max-ui-states", min=0, max=250),
) -> None:
    _run(
        target,
        "deep",
        output,
        depth,
        storage_state=storage_state,
        explore_ui_states=explore_ui,
        max_ui_states=max_ui_states,
    )


@app.command()
def forensic(
    target: str,
    output: Path = Path("output"),
    depth: int = 10,
    plugin: list[str] | None = typer.Option(
        None, "--plugin", help="module:attribute plugin"
    ),
    storage_state: Path | None = typer.Option(None, "--storage-state"),
    explore_ui: bool = typer.Option(True, "--explore-ui/--no-explore-ui"),
    max_ui_states: int = typer.Option(30, "--max-ui-states", min=0, max=250),
) -> None:
    _run(
        target,
        "forensic",
        output,
        depth,
        plugins=plugin,
        storage_state=storage_state,
        explore_ui_states=explore_ui,
        max_ui_states=max_ui_states,
    )


@app.command()
def exhaustive(
    target: str,
    output: Path = Path("output"),
    depth: int = 15,
    plugin: list[str] | None = typer.Option(
        None, "--plugin", help="module:attribute plugin"
    ),
    storage_state: Path | None = typer.Option(None, "--storage-state"),
    explore_ui: bool = typer.Option(True, "--explore-ui/--no-explore-ui"),
    max_ui_states: int = typer.Option(30, "--max-ui-states", min=0, max=250),
) -> None:
    _run(
        target,
        "exhaustive",
        output,
        depth,
        plugins=plugin,
        storage_state=storage_state,
        explore_ui_states=explore_ui,
        max_ui_states=max_ui_states,
    )


@app.command()
def reconstruct(
    target: str,
    output: Path = Path("output"),
    depth: int = 8,
    storage_state: Path | None = typer.Option(None, "--storage-state"),
    explore_ui: bool = typer.Option(True, "--explore-ui/--no-explore-ui"),
    max_ui_states: int = typer.Option(30, "--max-ui-states", min=0, max=250),
) -> None:
    _run(
        target,
        "reconstruction",
        output,
        depth,
        storage_state=storage_state,
        explore_ui_states=explore_ui,
        max_ui_states=max_ui_states,
    )


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
    root = path.parent if path.is_file() else path
    config_path = root / "scan-config.json"
    if not config_path.exists():
        raise typer.BadParameter("scan-config.json not found in capture directory")
    config = ScanConfig.model_validate_json(config_path.read_text(encoding="utf-8"))
    config.output_root = root.parent
    report = asyncio.run(RepoAlfaEngine(config, resume=True).run())
    _print_summary(report)


if __name__ == "__main__":
    app()
