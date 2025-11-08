"""
Textual TUI - Terminal User Interface
======================================

Modern text-based UI for color transfer operations using the Textual framework.

Features:
- Interactive file picker with tree view
- Configuration form for transfer settings
- Real-time status updates
- Result preview and metrics display

Usage:
    python -m color_transfer_framework.interface_layer.tui
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Button,
    Static,
    Input,
    Select,
    DirectoryTree,
    Label,
    ProgressBar,
    RichLog
)
from textual.reactive import reactive
from textual.binding import Binding
from pathlib import Path
from typing import Optional
import os

from .orchestrator import TransferOrchestrator
from ..transfer_engine import TransferConfig, TransferAlgorithm
from .. import __version__


class FilePickerPane(Container):
    """File picker pane with directory tree."""

    def __init__(self, label: str, file_var: str):
        super().__init__()
        self.label_text = label
        self.file_var = file_var
        self.selected_path: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Static(f"📁 {self.label_text}", classes="pane-title")
        yield DirectoryTree(str(Path.home()), id=f"{self.file_var}_tree")
        yield Static("No file selected", id=f"{self.file_var}_status", classes="file-status")

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Handle file selection."""
        self.selected_path = str(event.path)
        status = self.query_one(f"#{self.file_var}_status", Static)
        status.update(f"✓ {Path(self.selected_path).name}")

        # Notify parent app
        if hasattr(self.app, 'on_file_selected'):
            self.app.on_file_selected(self.file_var, self.selected_path)


class ConfigPane(Container):
    """Configuration pane with form inputs."""

    def compose(self) -> ComposeResult:
        """Create configuration widgets."""
        yield Static("⚙️ Configuration", classes="pane-title")

        yield Label("Algorithm:")
        yield Select(
            [
                ("Reinhard L*a*b* (Default)", "reinhard_lab"),
                ("Reinhard LCH", "reinhard_lch"),
                ("RGB Direct", "rgb_direct"),
                ("Histogram Match", "histogram_match"),
            ],
            value="reinhard_lab",
            id="algorithm_select"
        )

        yield Label("Blend Factor (0.0 - 1.0):")
        yield Input(value="1.0", id="blend_input", placeholder="0.0 - 1.0")

        yield Label("")
        yield Button("🎨 Run Transfer", variant="primary", id="run_button")


class StatusPane(Container):
    """Status and results pane."""

    status_text = reactive("Ready")
    progress_value = reactive(0)

    def compose(self) -> ComposeResult:
        """Create status widgets."""
        yield Static("📊 Status", classes="pane-title")
        yield Static(self.status_text, id="status_text")
        yield ProgressBar(total=100, show_eta=False, id="progress_bar")
        yield Static("", id="metrics_display")
        yield RichLog(id="log_display", wrap=True, highlight=True, markup=True)

    def update_status(self, message: str):
        """Update status message."""
        self.status_text = message
        status_widget = self.query_one("#status_text", Static)
        status_widget.update(message)

    def update_progress(self, percent: int, status: str):
        """Update progress bar."""
        self.progress_value = percent
        progress_bar = self.query_one("#progress_bar", ProgressBar)
        progress_bar.update(progress=percent)

        # Map status to user-friendly text
        status_texts = {
            'initializing': 'Initializing...',
            'loading_images': 'Loading images...',
            'calculating_statistics': 'Calculating color statistics...',
            'applying_transform': 'Applying color transformation...',
            'processing_result': 'Processing result...',
            'generating_diagnostics': 'Generating diagnostics...',
            'saving_metadata': 'Saving metadata...',
            'complete': 'Complete!'
        }
        self.update_status(status_texts.get(status, status))

    def log_message(self, message: str, style: str = ""):
        """Add message to log."""
        log = self.query_one("#log_display", RichLog)
        if style:
            log.write(f"[{style}]{message}[/{style}]")
        else:
            log.write(message)

    def display_metrics(self, metrics):
        """Display performance metrics."""
        metrics_widget = self.query_one("#metrics_display", Static)
        metrics_text = (
            f"\n[bold]Performance Metrics:[/bold]\n"
            f"  • Execution Time: {metrics.execution_time_ms:.2f} ms\n"
            f"  • Memory Used: {metrics.memory_used_mb:.2f} MB\n"
            f"  • Throughput: {metrics.throughput_images_per_sec:.2f} img/s"
        )
        metrics_widget.update(metrics_text)


class ColorTransferTUI(App):
    """Color Transfer TUI Application."""

    CSS = """
    Screen {
        layout: grid;
        grid-size: 3 2;
        grid-rows: 1fr 1fr;
        grid-columns: 1fr 1fr 1fr;
    }

    .pane-title {
        text-style: bold;
        background: $primary;
        padding: 1;
        margin-bottom: 1;
    }

    .file-status {
        padding: 1;
        background: $surface;
        margin: 1 0;
    }

    FilePickerPane {
        border: solid $primary;
        height: 100%;
        padding: 1;
    }

    ConfigPane {
        border: solid $primary;
        height: 100%;
        padding: 1;
        column-span: 2;
    }

    StatusPane {
        border: solid $primary;
        height: 100%;
        padding: 1;
        column-span: 3;
    }

    DirectoryTree {
        height: 1fr;
        max-height: 20;
    }

    Select {
        margin: 0 0 2 0;
    }

    Input {
        margin: 0 0 2 0;
    }

    Button {
        width: 100%;
        margin: 1 0;
    }

    ProgressBar {
        margin: 1 0;
    }

    RichLog {
        height: 1fr;
        max-height: 10;
        background: $surface;
        border: solid $primary-background;
        margin: 1 0;
    }

    #status_text {
        padding: 1;
        background: $surface;
    }

    #metrics_display {
        padding: 1;
        background: $surface;
        margin: 1 0;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "run_transfer", "Run Transfer"),
    ]

    TITLE = f"Color Transfer Framework TUI v{__version__}"
    SUB_TITLE = "Interactive Terminal Interface"

    def __init__(self):
        super().__init__()
        self.orchestrator = TransferOrchestrator()
        self.source_path: Optional[str] = None
        self.target_path: Optional[str] = None

    def compose(self) -> ComposeResult:
        """Create child widgets."""
        yield Header()
        yield FilePickerPane("Select Source Image", "source")
        yield FilePickerPane("Select Target Image", "target")
        yield ConfigPane()
        yield StatusPane()
        yield Footer()

    def on_file_selected(self, file_var: str, path: str):
        """Handle file selection from picker panes."""
        if file_var == "source":
            self.source_path = path
            self.log(f"Source selected: {Path(path).name}")
        elif file_var == "target":
            self.target_path = path
            self.log(f"Target selected: {Path(path).name}")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button press."""
        if event.button.id == "run_button":
            self.action_run_transfer()

    def action_run_transfer(self) -> None:
        """Run the color transfer operation."""
        status_pane = self.query_one(StatusPane)

        # Validate inputs
        if not self.source_path or not self.target_path:
            status_pane.update_status("❌ Error: Please select both source and target images")
            status_pane.log_message("Please select both source and target images", "red")
            return

        # Check files exist and are images
        valid_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.tif'}
        source_ext = Path(self.source_path).suffix.lower()
        target_ext = Path(self.target_path).suffix.lower()

        if source_ext not in valid_extensions or target_ext not in valid_extensions:
            status_pane.update_status("❌ Error: Invalid file type")
            status_pane.log_message(f"Invalid file type. Supported: {', '.join(valid_extensions)}", "red")
            return

        # Get configuration
        algorithm_select = self.query_one("#algorithm_select", Select)
        blend_input = self.query_one("#blend_input", Input)

        try:
            algorithm = str(algorithm_select.value)
            blend_factor = float(blend_input.value)

            if not 0.0 <= blend_factor <= 1.0:
                raise ValueError("Blend factor must be between 0.0 and 1.0")

        except ValueError as e:
            status_pane.update_status(f"❌ Configuration error: {e}")
            status_pane.log_message(f"Configuration error: {e}", "red")
            return

        # Build config
        config = TransferConfig(
            algorithm=TransferAlgorithm(algorithm),
            blend_factor=blend_factor
        )

        # Create output path
        output_path = Path(self.target_path).parent / f"result_{Path(self.target_path).stem}.png"

        status_pane.log_message(f"\n[bold cyan]Starting transfer...[/bold cyan]")
        status_pane.log_message(f"Source: {Path(self.source_path).name}")
        status_pane.log_message(f"Target: {Path(self.target_path).name}")
        status_pane.log_message(f"Algorithm: {algorithm}")
        status_pane.log_message(f"Blend: {blend_factor}")

        # Progress callback
        def progress_callback(status: str, percent: int):
            self.call_from_thread(status_pane.update_progress, percent, status)

        # Run transfer in worker thread
        self.run_worker(
            self._perform_transfer,
            self.source_path,
            self.target_path,
            str(output_path),
            config,
            progress_callback,
            thread=True
        )

    def _perform_transfer(
        self,
        source_path: str,
        target_path: str,
        output_path: str,
        config: TransferConfig,
        progress_callback
    ):
        """Perform transfer in background thread."""
        status_pane = self.query_one(StatusPane)

        try:
            # Perform transfer
            result = self.orchestrator.transfer_from_paths(
                source_path,
                target_path,
                output_path,
                config=config,
                enable_gpu=False,
                generate_diagnostics=False,
                interface_type="TUI"
            )

            # Update UI with results
            self.call_from_thread(status_pane.update_status, "✓ Transfer complete!")
            self.call_from_thread(status_pane.log_message, f"\n[bold green]✓ Transfer complete![/bold green]", "")
            self.call_from_thread(status_pane.log_message, f"Result saved to: {output_path}", "green")
            self.call_from_thread(status_pane.display_metrics, result.metrics)
            self.call_from_thread(status_pane.update_progress, 100, "complete")

        except Exception as e:
            self.call_from_thread(status_pane.update_status, f"❌ Error: {str(e)}")
            self.call_from_thread(status_pane.log_message, f"[bold red]Error:[/bold red] {str(e)}", "")

    def log(self, message: str):
        """Log a message to the status pane."""
        status_pane = self.query_one(StatusPane)
        status_pane.log_message(message)


def main():
    """Run the TUI application."""
    app = ColorTransferTUI()
    app.run()


if __name__ == "__main__":
    main()
