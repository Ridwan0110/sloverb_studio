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
        self.services = []

    def add(self, *controls):
        self.controls.extend(controls)

    def update(self):
        pass


def test_import_entry_point():
    """Verify sloverb_studio exposes main, start_app callables, and __version__ matching package."""
    import slowverb
    assert hasattr(sloverb_studio, "main")
    assert callable(sloverb_studio.main)
    assert hasattr(sloverb_studio, "start_app")
    assert callable(sloverb_studio.start_app)
    assert hasattr(sloverb_studio, "__version__")
    assert sloverb_studio.__version__ == slowverb.__version__


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


def test_create_argument_parser():
    """Verify create_argument_parser configures file, --mobile-ui, and --version options."""
    parser = sloverb_studio.create_argument_parser()
    args = parser.parse_args(["song.mp3", "--mobile-ui"])
    assert args.file == "song.mp3"
    assert args.mobile_ui is True


def test_parse_cli_args_mobile_ui():
    """Verify parse_cli_args handles --mobile-ui and sets SLOVERB_MOBILE_UI env var."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SLOVERB_MOBILE_UI", None)
        args = sloverb_studio.parse_cli_args(["sloverb_studio.py", "--mobile-ui"])
        assert args.mobile_ui is True
        assert os.environ.get("SLOVERB_MOBILE_UI") == "1"


def test_parse_cli_args_file_and_mobile_ui(sample_sine_audio):
    """Verify parse_cli_args handles positional file along with --mobile-ui."""
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SLOVERB_MOBILE_UI", None)
        args = sloverb_studio.parse_cli_args(["sloverb_studio.py", sample_sine_audio, "--mobile-ui"])
        assert args.file == sample_sine_audio
        assert args.mobile_ui is True


def test_parse_cli_args_version(capsys):
    """Verify parse_cli_args displays version and exits cleanly on --version."""
    with pytest.raises(SystemExit) as exc_info:
        sloverb_studio.parse_cli_args(["sloverb_studio.py", "--version"])
    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert f"SloVerb Studio v{sloverb_studio.__version__}" in captured.out


def test_main_mobile_ui_flag():
    """Verify main(page) with --mobile-ui configures mobile viewport dimensions and mobile UI."""
    mock_page = MockPage()
    test_args = ["sloverb_studio.py", "--mobile-ui"]

    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("SLOVERB_MOBILE_UI", None)
        with patch.object(sys, "argv", test_args):
            with patch("slowverb.ui.find_ffmpeg", return_value="mock_ffmpeg.exe"):
                app = sloverb_studio.main(mock_page)
                assert app.force_mobile_ui is True
                assert mock_page.window.width == 412
                assert mock_page.window.height == 840
                assert mock_page.window.min_width == 360
                assert mock_page.window.min_height == 600
                app.close()
