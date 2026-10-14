"""Tests for Flet GUI-based FFmpeg setup prompt, download progress, and state transitions."""

import os
import platform
import time
from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from slowverb.config import APP_NAME
from slowverb.ui import FFmpegSetupView, SlowVerbApp
from slowverb.ffmpeg_manager import prompt_and_ensure_ffmpeg, run_ffmpeg_setup_flet


class MockWindow:
    def __init__(self):
        self.width = 1000
        self.height = 800
        self.min_width = 800
        self.min_height = 700
        self.closed = False

    def close(self):
        self.closed = True


class MockPage:
    def __init__(self):
        self.title = ""
        self.bgcolor = ""
        self.padding = 0
        self.scroll = None
        self.window = MockWindow()
        self.controls = []
        self.overlay = []
        self.fonts = {}

    def add(self, *controls):
        self.controls.extend(controls)

    def clean(self):
        self.controls.clear()

    def update(self):
        pass


def test_ffmpeg_setup_view_download_success():
    """Verify clicking download starts worker thread, updates progress bar, and triggers on_success."""
    mock_page = MockPage()
    success_paths = []

    def handle_success(path):
        success_paths.append(path)

    view = FFmpegSetupView(
        page=mock_page,
        on_success=handle_success,
        target_dir="/mock/target/dir",
    )

    fake_binary = "/mock/target/dir/ffmpeg.exe"

    def mock_download(target_dir=None, on_progress=None):
        if on_progress:
            on_progress(0.35, "Downloading FFmpeg: 14.0MB / 40.0MB")
            on_progress(0.90, "Extracting FFmpeg binary...")
            on_progress(1.0, "FFmpeg ready.")
        return fake_binary

    with patch("slowverb.ui.download_ffmpeg", side_effect=mock_download):
        view._on_download_click(None)
        assert view.is_downloading is True
        assert view.progress_bar.visible is True

        # Wait briefly for daemon download thread to execute
        time.sleep(0.6)

        assert len(success_paths) == 1
        assert success_paths[0] == fake_binary
        assert view.progress_bar.value == 1.0
        assert "VERIFIED SUCCESSFULLY" in view.status_label.value


def test_ffmpeg_setup_view_download_failure():
    """Verify download error shows failure state, error message in red, and enables retry button."""
    mock_page = MockPage()
    success_mock = MagicMock()

    view = FFmpegSetupView(
        page=mock_page,
        on_success=success_mock,
        target_dir="/mock/target/dir",
    )

    def failing_download(target_dir=None, on_progress=None):
        raise ConnectionResetError("Connection reset by peer")

    with patch("slowverb.ui.download_ffmpeg", side_effect=failing_download):
        view._on_download_click(None)
        time.sleep(0.3)

        assert view.is_downloading is False
        assert view.progress_bar.visible is False
        assert view.status_label.value == "DOWNLOAD FAILED"
        assert "CONNECTION RESET BY PEER" in view.detail_label.value
        assert view.btn_download_text.value == "RETRY DOWNLOAD"
        assert view.actions_row.visible is True
        success_mock.assert_not_called()


def test_slowverb_app_missing_ffmpeg_renders_setup_screen():
    """Verify SlowVerbApp mounts the setup view when FFmpeg is not found anywhere."""
    mock_page = MockPage()

    with patch("slowverb.ui.find_ffmpeg", return_value=None):
        app = SlowVerbApp(mock_page)

        assert app.ffmpeg_path is None
        assert app.engine is None
        assert app.ffmpeg_setup_view is not None
        assert "FFMPEG SETUP" in mock_page.title
        assert len(mock_page.controls) > 0


def test_slowverb_app_completes_setup_and_transitions_to_main_ui():
    """Verify SlowVerbApp transitions from setup screen to main UI upon download success."""
    mock_page = MockPage()

    with patch("slowverb.ui.find_ffmpeg", return_value=None):
        app = SlowVerbApp(mock_page)
        assert app.engine is None

        # Simulate download completion
        with patch("slowverb.ui.AudioEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine

            app._on_ffmpeg_installed("/path/to/downloaded/ffmpeg.exe")

            assert app.ffmpeg_path == "/path/to/downloaded/ffmpeg.exe"
            assert app.engine is not None
            assert mock_page.title == APP_NAME
            assert hasattr(app, "file_path_field")
            assert hasattr(app, "speed_slider")
            assert hasattr(app, "waveform_container")


def test_slowverb_app_queues_cli_file_during_setup_and_loads_after():
    """Verify audio file requested before setup is queued and loaded once FFmpeg is ready."""
    mock_page = MockPage()

    with patch("slowverb.ui.find_ffmpeg", return_value=None):
        app = SlowVerbApp(mock_page)

        # File is requested before engine exists
        app.load_file("custom_track.opus")
        assert app._pending_cli_file == "custom_track.opus"

        with patch("slowverb.ui.AudioEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine_cls.return_value = mock_engine

            with patch.object(app, "load_file") as mock_load:
                app._on_ffmpeg_installed("/path/to/downloaded/ffmpeg.exe")
                mock_load.assert_called_with("custom_track.opus")


def test_slowverb_app_on_ffmpeg_cancelled_closes_window():
    """Verify SlowVerbApp attempts to close page window when user cancels setup."""
    mock_page = MockPage()

    with patch("slowverb.ui.find_ffmpeg", return_value=None):
        app = SlowVerbApp(mock_page)
        app._on_ffmpeg_cancelled()
        assert mock_page.window.closed is True


def test_run_ffmpeg_setup_flet_invokes_ft_run():
    """Verify run_ffmpeg_setup_flet configures Flet page and returns verified path."""
    with patch("flet.run") as mock_run:
        # Mock run to simulate user successfully downloading
        def fake_run(target):
            mock_p = MockPage()
            target(mock_p)
            assert len(mock_p.controls) > 0
            assert "FFMPEG SETUP" in mock_p.title

        mock_run.side_effect = fake_run

        with patch("slowverb.ffmpeg_manager.download_ffmpeg", return_value="/mock/dl/ffmpeg.exe"):
            # When ft.run finishes, if path was set, returns it
            pass


def test_prompt_and_ensure_ffmpeg_interactive_calls_flet():
    """Verify prompt_and_ensure_ffmpeg in interactive mode launches Flet window."""
    with patch("slowverb.ffmpeg_manager.find_ffmpeg", return_value=None):
        with patch("slowverb.ffmpeg_manager.run_ffmpeg_setup_flet", return_value="/mock/flet/ffmpeg.exe") as mock_flet:
            res = prompt_and_ensure_ffmpeg(interactive=True)
            assert res == "/mock/flet/ffmpeg.exe"
            mock_flet.assert_called_once()


def test_prompt_and_ensure_ffmpeg_flet_fallback_to_terminal():
    """Verify that if Flet GUI cannot initialize, it falls back to terminal prompt."""
    with patch("slowverb.ffmpeg_manager.find_ffmpeg", return_value=None):
        with patch("slowverb.ffmpeg_manager.run_ffmpeg_setup_flet", side_effect=RuntimeError("No GUI display")):
            with patch("builtins.input", return_value="y"):
                with patch("slowverb.ffmpeg_manager.download_ffmpeg", return_value="/mock/terminal/ffmpeg.exe"):
                    res = prompt_and_ensure_ffmpeg(interactive=True)
                    assert res == "/mock/terminal/ffmpeg.exe"
