"""Tests for sloverb_studio.py entry point and application bootstrapping."""

import os
import sys
from unittest.mock import MagicMock, patch
import pytest

import sloverb_studio


class MockWindow:
    def __init__(self):
        self.width = 1000
        self.height = 800
        self.min_width = 800
        self.min_height = 700


class MockPage:
    def __init__(self):
        self.title = ""
        self.bgcolor = ""
        self.padding = 0
        self.scroll = None
        self.window = MockWindow()
        self.controls = []
        self.overlay = []

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass


def test_import_entry_point():
    """Verify sloverb_studio exposes main and start_app callables."""
    assert hasattr(sloverb_studio, "main")
    assert callable(sloverb_studio.main)
    assert hasattr(sloverb_studio, "start_app")
    assert callable(sloverb_studio.start_app)


def test_main_page_bootstrap():
    """Verify main(page) configures page properties and builds the UI."""
    mock_page = MockPage()
    app = sloverb_studio.main(mock_page)

    assert app is not None
    assert "SloVerb Studio" in mock_page.title
    assert len(mock_page.controls) > 0
    app.close()


def test_main_cli_argument_loading(sample_sine_audio):
    """Verify main(page) loads audio track specified in sys.argv."""
    mock_page = MockPage()
    test_args = ["sloverb_studio.py", sample_sine_audio]

    with patch.object(sys, "argv", test_args):
        app = sloverb_studio.main(mock_page)
        assert app.current_filepath == os.path.abspath(sample_sine_audio)
        assert app.metadata is not None
        assert "LOADED:" in app.status_banner.value
        app.close()


def test_start_app_calls_flet_run():
    """Verify start_app invokes ft.run with the main bootstrap function."""
    with patch("flet.run") as mock_run:
        sloverb_studio.start_app()
        mock_run.assert_called_once_with(sloverb_studio.main)


def test_start_app_fallback_to_flet_app():
    """Verify start_app falls back to ft.app if ft.run is not present."""
    fake_flet = MagicMock()
    del fake_flet.run
    fake_flet.app = MagicMock()

    with patch.object(sloverb_studio, "ft", fake_flet):
        sloverb_studio.start_app()
        fake_flet.app.assert_called_once_with(target=sloverb_studio.main)
