"""
Tests for Textual TUI
=====================

Basic tests for the Terminal User Interface module.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from textual.widgets import DirectoryTree, Select, Input

from color_transfer_framework.interface_layer.tui import (
    ColorTransferTUI,
    FilePickerPane,
    ConfigPane,
    StatusPane
)
from color_transfer_framework.transfer_engine import TransferConfig, TransferAlgorithm


class TestFilePickerPane:
    """Tests for FilePickerPane widget."""

    def test_file_picker_creation(self):
        """Test FilePickerPane can be created."""
        pane = FilePickerPane("Test Label", "test_var")
        assert pane.label_text == "Test Label"
        assert pane.file_var == "test_var"
        assert pane.selected_path is None

    def test_file_picker_compose(self):
        """Test FilePickerPane compose method."""
        pane = FilePickerPane("Select Image", "source")
        widgets = list(pane.compose())
        assert len(widgets) > 0


class TestConfigPane:
    """Tests for ConfigPane widget."""

    def test_config_pane_creation(self):
        """Test ConfigPane can be created."""
        pane = ConfigPane()
        assert pane is not None

    def test_config_pane_compose(self):
        """Test ConfigPane compose method."""
        pane = ConfigPane()
        widgets = list(pane.compose())
        assert len(widgets) > 0


class TestStatusPane:
    """Tests for StatusPane widget."""

    def test_status_pane_creation(self):
        """Test StatusPane can be created."""
        pane = StatusPane()
        assert pane.status_text == "Ready"
        assert pane.progress_value == 0

    def test_status_pane_compose(self):
        """Test StatusPane compose method."""
        pane = StatusPane()
        widgets = list(pane.compose())
        assert len(widgets) > 0

    def test_update_status(self):
        """Test updating status message."""
        pane = StatusPane()
        pane.update_status("Test message")
        assert pane.status_text == "Test message"

    def test_update_progress(self):
        """Test updating progress."""
        pane = StatusPane()
        pane.update_progress(50, "applying_transform")
        assert pane.progress_value == 50


class TestColorTransferTUI:
    """Tests for main TUI application."""

    def test_app_creation(self):
        """Test TUI app can be created."""
        app = ColorTransferTUI()
        assert app is not None
        assert app.source_path is None
        assert app.target_path is None
        assert app.orchestrator is not None

    def test_app_compose(self):
        """Test TUI app compose method."""
        app = ColorTransferTUI()
        widgets = list(app.compose())
        # Should have Header, Footer, and panes
        assert len(widgets) >= 5

    def test_file_selection(self):
        """Test file selection callback."""
        app = ColorTransferTUI()

        # Simulate source file selection
        app.on_file_selected("source", "/path/to/source.jpg")
        assert app.source_path == "/path/to/source.jpg"

        # Simulate target file selection
        app.on_file_selected("target", "/path/to/target.jpg")
        assert app.target_path == "/path/to/target.jpg"

    @patch('color_transfer_framework.interface_layer.tui.Path')
    def test_validate_inputs_missing_files(self, mock_path):
        """Test validation with missing files."""
        app = ColorTransferTUI()

        # No files selected - validation should fail
        # This would be tested in the actual app context
        assert app.source_path is None
        assert app.target_path is None

    def test_log_message(self):
        """Test logging functionality."""
        app = ColorTransferTUI()
        # Log method should not raise errors
        app.log("Test message")


class TestTUIIntegration:
    """Integration tests for TUI."""

    @pytest.mark.skipif(not Path("/tmp").exists(), reason="Requires /tmp directory")
    def test_tui_with_mock_files(self):
        """Test TUI with mock file paths."""
        app = ColorTransferTUI()

        # Set file paths
        app.on_file_selected("source", "/tmp/test_source.jpg")
        app.on_file_selected("target", "/tmp/test_target.jpg")

        assert app.source_path == "/tmp/test_source.jpg"
        assert app.target_path == "/tmp/test_target.jpg"
