"""
Command-Line Interface
=====================

Modern CLI using Typer for color transfer operations.

Provides:
- transfer: Main color transfer command
- benchmark: Performance benchmarking
- Rich progress indicators and error handling
"""

import typer
from typing import Optional
from pathlib import Path
from enum import Enum
import sys

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich import print as rprint

from ..transfer_engine import TransferEngine, TransferConfig, TransferAlgorithm
from ..optimizer_engine import OptimizerEngine
from ..diagnostics_visualizer import DiagnosticsVisualizer
from .orchestrator import TransferOrchestrator
from .config_loader import ConfigLoader, create_example_recipes

# Initialize CLI app
app = typer.Typer(
    name="color-transfer",
    help="Color Transfer Framework - Transfer color palettes between images",
    add_completion=False
)
console = Console()


class AlgorithmChoice(str, Enum):
    """CLI choices for algorithms."""
    reinhard_lab = "reinhard_lab"
    reinhard_lch = "reinhard_lch"
    rgb_direct = "rgb_direct"
    histogram_match = "histogram_match"


@app.command()
def transfer(
    source: Path = typer.Argument(
        ...,
        help="Path to source image (color palette donor)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    target: Path = typer.Argument(
        ...,
        help="Path to target image (to be transformed)",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True
    ),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Path to save result (default: target_transferred.png)"
    ),
    algorithm: AlgorithmChoice = typer.Option(
        AlgorithmChoice.reinhard_lab,
        "--algo", "-a",
        help="Color transfer algorithm to use",
        case_sensitive=False
    ),
    blend: float = typer.Option(
        1.0,
        "--blend", "-b",
        min=0.0,
        max=1.0,
        help="Blend factor (0.0 = original, 1.0 = full transfer)"
    ),
    mask: Optional[Path] = typer.Option(
        None,
        "--mask", "-m",
        help="Path to mask image (grayscale, optional)",
        exists=True
    ),
    gpu: bool = typer.Option(
        False,
        "--gpu",
        help="Enable GPU acceleration"
    ),
    visualize: bool = typer.Option(
        False,
        "--visualize", "-v",
        help="Generate comprehensive diagnostic report"
    ),
    preserve_luminance: bool = typer.Option(
        False,
        "--preserve-luminance",
        help="Preserve original luminance (LCH algorithm only)"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Load configuration from YAML/JSON file (overrides other options)",
        exists=True
    )
):
    """
    Transfer color palette from source image to target image.

    Examples:

        # Basic transfer
        color-transfer source.jpg target.jpg -o result.jpg

        # Use LCH algorithm with blending
        color-transfer source.jpg target.jpg -a reinhard_lch -b 0.7

        # Generate diagnostic visualizations
        color-transfer source.jpg target.jpg -v

        # Use mask for selective transfer
        color-transfer source.jpg target.jpg -m mask.png
    """
    try:
        # Determine output path
        if output is None:
            output = target.parent / f"{target.stem}_transferred{target.suffix}"

        # Build configuration
        if config_file:
            # Load from file
            console.print(f"[cyan]Loading configuration from:[/cyan] {config_file}")
            config = ConfigLoader.load_config(str(config_file))
        else:
            # Use command-line options
            config = TransferConfig(
                algorithm=TransferAlgorithm(algorithm.value),
                blend_factor=blend,
                preserve_luminance=preserve_luminance
            )

        # Create orchestrator
        orchestrator = TransferOrchestrator()

        # Display operation info
        console.print("\n[bold cyan]Color Transfer Operation[/bold cyan]")
        console.print(f"Source:    {source}")
        console.print(f"Target:    {target}")
        console.print(f"Output:    {output}")
        console.print(f"Algorithm: {algorithm.value}")
        console.print(f"Blend:     {blend * 100:.0f}%")
        if mask:
            console.print(f"Mask:      {mask}")
        if gpu:
            console.print("[yellow]GPU:       Enabled[/yellow]")
        console.print()

        # Perform transfer with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Processing...", total=None)

            result = orchestrator.transfer_from_paths(
                str(source),
                str(target),
                str(output),
                config=config,
                mask_path=str(mask) if mask else None,
                enable_gpu=gpu,
                generate_diagnostics=visualize,
                interface_type="CLI"
            )

            progress.update(task, completed=True)

        # Display results
        console.print(f"[green]✓[/green] Transfer complete!")
        console.print(f"[green]✓[/green] Result saved to: {output}")

        # Display metrics
        metrics_table = Table(title="Performance Metrics", show_header=False)
        metrics_table.add_row("Execution Time", f"{result.metrics.execution_time_ms:.2f} ms")
        metrics_table.add_row("Memory Used", f"{result.metrics.memory_used_mb:.2f} MB")
        metrics_table.add_row("Throughput", f"{result.metrics.throughput_images_per_sec:.2f} img/s")
        console.print(metrics_table)

        # Display diagnostics info
        if visualize and result.visualization_paths:
            console.print("\n[bold cyan]Diagnostic Reports Generated:[/bold cyan]")
            for viz_type, viz_path in result.visualization_paths.items():
                console.print(f"  • {viz_type}: {viz_path}")

        console.print(f"\n[dim]Run ID: {result.run_id}[/dim]")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)


@app.command()
def algorithms():
    """List all available color transfer algorithms."""
    console.print("\n[bold cyan]Available Algorithms[/bold cyan]\n")

    algo_info = {
        "reinhard_lab": "Reinhard et al. method in L*a*b* color space (default, perceptually uniform)",
        "reinhard_lch": "Reinhard method in LCH space (preserves hue relationships)",
        "rgb_direct": "Direct RGB channel transfer (fast but less perceptually accurate)",
        "histogram_match": "Histogram matching algorithm (precise distribution matching)"
    }

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Algorithm", style="cyan")
    table.add_column("Description")

    for algo, desc in algo_info.items():
        table.add_row(algo, desc)

    console.print(table)
    console.print()


@app.command()
def info():
    """Display framework information and module status."""
    from .. import __version__

    console.print(f"\n[bold cyan]Color Transfer Framework[/bold cyan]")
    console.print(f"Version: {__version__}\n")

    # Check module availability
    modules_table = Table(title="Module Status", show_header=True)
    modules_table.add_column("Module", style="cyan")
    modules_table.add_column("Status")

    try:
        from ..transfer_engine import TransferEngine
        modules_table.add_row("TransferEngine", "[green]✓ Available[/green]")
    except ImportError:
        modules_table.add_row("TransferEngine", "[red]✗ Not available[/red]")

    try:
        from ..optimizer_engine import OptimizerEngine
        modules_table.add_row("OptimizerEngine", "[green]✓ Available[/green]")
    except ImportError:
        modules_table.add_row("OptimizerEngine", "[red]✗ Not available[/red]")

    try:
        from ..diagnostics_visualizer import DiagnosticsVisualizer
        modules_table.add_row("DiagnosticsVisualizer", "[green]✓ Available[/green]")
    except ImportError:
        modules_table.add_row("DiagnosticsVisualizer", "[red]✗ Not available[/red]")

    try:
        from ..complexity_analyzer import ComplexityAnalyzer
        modules_table.add_row("ComplexityAnalyzer", "[green]✓ Available[/green]")
    except ImportError:
        modules_table.add_row("ComplexityAnalyzer", "[red]✗ Not available[/red]")

    console.print(modules_table)
    console.print()


@app.command()
def recipes():
    """List available configuration recipes."""
    console.print("\n[bold cyan]Available Recipes[/bold cyan]\n")

    recipe_list = ConfigLoader.list_recipes()

    if not recipe_list:
        console.print("[yellow]No recipes found.[/yellow]")
        console.print(f"Run [cyan]color-transfer create-examples[/cyan] to create example recipes.")
        console.print(f"Recipe directory: {ConfigLoader.get_default_recipes_dir()}\n")
        return

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Name", style="cyan")
    table.add_column("Description")
    table.add_column("Tags", style="dim")

    for recipe in recipe_list:
        tags = ', '.join(recipe['tags']) if recipe['tags'] else '-'
        table.add_row(recipe['name'], recipe['description'], tags)

    console.print(table)
    console.print(f"\n[dim]Recipe directory: {ConfigLoader.get_default_recipes_dir()}[/dim]")
    console.print(f"[dim]Use with: --config <recipe.yaml>[/dim]\n")


@app.command()
def create_examples():
    """Create example recipe files."""
    console.print("\n[bold cyan]Creating Example Recipes[/bold cyan]\n")

    try:
        create_example_recipes()
        console.print(f"[green]✓[/green] Example recipes created in:")
        console.print(f"  {ConfigLoader.get_default_recipes_dir()}\n")

        console.print("Available examples:")
        console.print("  • warm_sunset.yaml - Warm, golden sunset tones")
        console.print("  • cool_blue.yaml - Cool, blue cinematic tones")
        console.print("  • high_contrast.yaml - Dramatic histogram matching")
        console.print("  • subtle_enhancement.yaml - Gentle color correction\n")

        console.print("Use with:")
        console.print("  [cyan]color-transfer source.jpg target.jpg --config warm_sunset.yaml[/cyan]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)


@app.command()
def save_config(
    name: str = typer.Argument(..., help="Name for the configuration"),
    output: Path = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (default: ~/.color_transfer/recipes/<name>.yaml)"
    ),
    algorithm: AlgorithmChoice = typer.Option(
        AlgorithmChoice.reinhard_lab,
        "--algo", "-a",
        help="Algorithm to use"
    ),
    blend: float = typer.Option(
        1.0,
        "--blend", "-b",
        min=0.0,
        max=1.0,
        help="Blend factor"
    ),
    preserve_luminance: bool = typer.Option(
        False,
        "--preserve-luminance",
        help="Preserve luminance"
    ),
    description: str = typer.Option(
        "",
        "--desc", "-d",
        help="Description of the configuration"
    ),
    tags: str = typer.Option(
        "",
        "--tags", "-t",
        help="Comma-separated tags"
    )
):
    """
    Save a configuration as a reusable recipe.

    Examples:

        # Save a warm sunset configuration
        color-transfer save-config "Warm Sunset" \\
            --algo reinhard_lch --blend 0.7 \\
            --desc "Golden hour warm tones" \\
            --tags warm,sunset,golden
    """
    try:
        # Build config
        config = TransferConfig(
            algorithm=TransferAlgorithm(algorithm.value),
            blend_factor=blend,
            preserve_luminance=preserve_luminance
        )

        # Determine output path
        if output is None:
            recipes_dir = ConfigLoader.get_default_recipes_dir()
            output = recipes_dir / f"{name.lower().replace(' ', '_')}.yaml"

        # Parse tags
        tag_list = [t.strip() for t in tags.split(',') if t.strip()] if tags else None

        # Create recipe
        from .config_loader import TransferRecipe
        from datetime import datetime

        recipe = TransferRecipe(
            name=name,
            description=description or f"Configuration: {name}",
            config=config.to_dict(),
            created_at=datetime.utcnow().isoformat(),
            tags=tag_list
        )

        # Save
        ConfigLoader.save_config(config, str(output), recipe=recipe)

        console.print(f"[green]✓[/green] Configuration saved to: {output}")
        console.print(f"\nUse with:")
        console.print(f"  [cyan]color-transfer source.jpg target.jpg --config {output}[/cyan]\n")

    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}", style="red")
        raise typer.Exit(code=1)


@app.callback()
def main():
    """Color Transfer Framework CLI."""
    pass


def cli_main():
    """Entry point for CLI."""
    app()


if __name__ == "__main__":
    cli_main()
