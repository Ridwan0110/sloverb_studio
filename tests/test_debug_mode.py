"""
Unit tests for SloVerb Studio Debug Mode, DiagnosticLogger, and environment dump.
"""

import json
import os
import sys
import tempfile
from unittest.mock import MagicMock, patch
import pytest

import slowverb
from slowverb.config import FA_BUG
from slowverb.debug import (
    DiagnosticLogger,
    generate_debug_dump,
    get_backend_capabilities,
    get_ffmpeg_diagnostics,
    get_python_site_packages,
)
from slowverb.ui import SlowVerbApp
from sloverb_studio import parse_cli_args


def test_debug_mode_defaults_and_cli_toggle(monkeypatch):
    """Verifies DEBUG_MODE default state and CLI argument override."""
    monkeypatch.setattr(slowverb, "DEBUG_MODE", False)
    monkeypatch.delenv("SLOVERB_DEBUG", raising=False)

    args = parse_cli_args([])
    assert args.debug is False
    assert slowverb.DEBUG_MODE is False

    args_debug = parse_cli_args(["--debug"])
    assert args_debug.debug is True
    assert slowverb.DEBUG_MODE is True
    assert os.environ.get("SLOVERB_DEBUG") == "1"


def test_diagnostic_logger_ring_buffer():
    """Verifies DiagnosticLogger logs timestamped entries and formats 1-based indexed dict."""
    logger = DiagnosticLogger.get_instance()
    logger.clear()

    # Empty entries
    empty_dict = logger.get_entries_dict()
    assert "1" in empty_dict
    assert "NO TERMINAL ERRORS" in empty_dict["1"]

    # Log events
    logger.log("System initializing", level="INFO")
    logger.log("Audio buffer loaded", level="DEBUG")
    logger.log_error("Sample rate mismatch", exc=ValueError("Invalid rate 12345"))

    entries = logger.get_entries_dict()
    assert len(entries) == 3
    assert "1" in entries and "System initializing" in entries["1"]
    assert "2" in entries and "Audio buffer loaded" in entries["2"]
    assert "3" in entries and "Sample rate mismatch" in entries["3"]
    assert "ValueError" in entries["3"]


def test_generate_debug_dump_structure():
    """Verifies the complete structure and keys of generate_debug_dump."""
    dump = generate_debug_dump()
    assert isinstance(dump, dict)

    # Core sections
    assert "timestamp" in dump
    assert "app" in dump
    assert "platform" in dump
    assert "screen_size" in dump
    assert "ffmpeg" in dump
    assert "backend_capabilities" in dump
    assert "python_site_packages" in dump
    assert "audio_file" in dump
    assert "terminal" in dump

    # App section
    assert dump["app"]["name"] == "SloVerb Studio"
    assert dump["app"]["version"] == slowverb.__version__
    assert "is_frozen" in dump["app"]
    assert "python_executable" in dump["app"]

    # Platform section
    plat = dump["platform"]
    assert "os_name" in plat
    assert "python_version" in plat
    assert "platform_type" in plat
    assert "is_mobile_platform" in plat
    assert "is_mobile_environment" in plat

    # FFmpeg section
    assert "location" in dump["ffmpeg"]
    assert "exists" in dump["ffmpeg"]
    assert "version" in dump["ffmpeg"]

    # Capabilities & Packages
    assert "sounddevice" in dump["backend_capabilities"]
    assert isinstance(dump["python_site_packages"], dict)
    assert len(dump["python_site_packages"]) > 0

    # No audio file loaded
    assert dump["audio_file"] is None


def test_debug_button_initialization_and_visibility():
    """Verifies the debug button appearance and visibility controlled by debug_mode."""
    app_off = SlowVerbApp(page=None, debug_mode=False)
    assert app_off.debug_mode is False
    assert app_off.debug_button is not None
    assert app_off.debug_button.visible is False

    app_on = SlowVerbApp(page=None, debug_mode=True)
    assert app_on.debug_mode is True
    assert app_on.debug_button is not None
    assert app_on.debug_button.visible is True
    assert app_on.debug_button.content.value == FA_BUG


def test_debug_button_in_ui_layouts():
    """Verifies that debug_button is included in both desktop and mobile header rows."""
    app = SlowVerbApp(page=None, debug_mode=True)

    # Desktop header
    desktop_layout = app.build_desktop_ui()
    header_row = desktop_layout.controls[0]
    right_header_row = header_row.controls[1]
    assert app.debug_button in right_header_row.controls

    # Mobile header
    mobile_layout = app.build_mobile_ui()
    mobile_header = mobile_layout.controls[0]
    mobile_right_header = mobile_header.controls[1]
    assert app.debug_button in mobile_right_header.controls


def test_debug_dump_desktop_save_flow(tmp_path):
    """Verifies that clicking the debug button on desktop prompts and writes JSON."""
    app = SlowVerbApp(page=None, debug_mode=True)
    target_json = str(tmp_path / "test_debug_dump.json")

    with patch("slowverb.ui.save_file_desktop", return_value=target_json):
        app._on_debug_dump_clicked()

    assert os.path.isfile(target_json)
    with open(target_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert data["app"]["name"] == "SloVerb Studio"
    assert "DEBUG REPORT SAVED" in app.status_banner.value


def test_debug_dump_with_loaded_track(tmp_path):
    """Verifies that debug dump accurately captures loaded audio file metadata and modifications."""
    app = SlowVerbApp(page=None, debug_mode=True)
    fake_audio = str(tmp_path / "ambient_track.opus")
    with open(fake_audio, "wb") as f:
        f.write(b"OggS" + b"\x00" * 256)

    app.current_filepath = fake_audio
    app.effects.speed = 0.85
    app.effects.reverb_percent = 40.0
    app.effects.bass_boost_percent = 25.0
    app.effects.trim_start = 5.0
    app.effects.trim_end = 65.0

    target_json = str(tmp_path / "test_audio_debug_dump.json")
    with patch("slowverb.ui.save_file_desktop", return_value=target_json):
        app._on_debug_dump_clicked()

    with open(target_json, "r", encoding="utf-8") as f:
        data = json.load(f)

    audio_info = data["audio_file"]
    assert audio_info is not None
    assert audio_info["name"] == "ambient_track.opus"
    assert audio_info["location"] == fake_audio
    assert audio_info["access_type"]["exists"] is True
    assert audio_info["modifications"]["speed"] == 0.85
    assert audio_info["modifications"]["reverb_percent"] == 40.0
    assert audio_info["modifications"]["bass_boost_percent"] == 25.0
    assert audio_info["modifications"]["trim_start"] == 5.0
    assert audio_info["modifications"]["trim_end"] == 65.0


def test_debug_dump_mobile_save_flow(tmp_path):
    """Verifies that debug dump on mobile delegates to file_service.save_exported_file with allowed_extensions=['json']."""
    app = SlowVerbApp(page=None, debug_mode=True)

    with patch("slowverb.platform.is_mobile_platform", return_value=True):
        mock_save = MagicMock()
        app.file_service.save_exported_file = mock_save

        app._on_debug_dump_clicked()

        assert mock_save.called
        call_kwargs = mock_save.call_args[1] if mock_save.call_args[1] else {}
        args = mock_save.call_args[0]
        # Check that json extension was passed
        assert call_kwargs.get("allowed_extensions") == ["json"] or (len(args) > 2 and args[2] == ["json"])
