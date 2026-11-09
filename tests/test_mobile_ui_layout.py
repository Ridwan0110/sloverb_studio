"""Tests for mobile UI layout, tabbed navigation, and adaptive waveform bars."""

from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from slowverb.ui import SlowVerbApp
from slowverb.config import PRESET_SLOWED_REVERB


def test_build_ui_routing_desktop():
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    page.width = 1120
    page.overlay = []

    app = SlowVerbApp(page=page)
    ui = app.build_ui()
    assert isinstance(ui, ft.Column)
    # Desktop layout has 8 top-level children (header, loader, status, waveform, transport, effects, export, spacing)
    assert len(ui.controls) == 8


def test_build_ui_routing_mobile():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.width = 390
    page.overlay = []

    app = SlowVerbApp(page=page)
    ui = app.build_ui()
    assert isinstance(ui, ft.Column)
    # Mobile layout has 5 top-level items:
    # 0: mobile_header, 1: static_top_bar, 2: tab_header_row, 3: mobile_tab_switcher, 4: spacing
    assert len(ui.controls) == 5

    static_top_bar = ui.controls[1]
    assert isinstance(static_top_bar, ft.Container)
    # Static top bar has Column with 2 rows (Row 1: Load + Status, Row 2: Playback/Trim + Render)
    top_bar_column = static_top_bar.content
    assert isinstance(top_bar_column, ft.Column)
    assert len(top_bar_column.controls) == 2

    row_1 = top_bar_column.controls[0]
    assert isinstance(row_1, ft.Row)
    # Left is Load button, right is status container
    assert len(row_1.controls) == 2

    status_container = row_1.controls[1]
    assert isinstance(status_container, ft.Container)
    status_col = status_container.content
    assert isinstance(status_col, ft.Column)
    # 2 rows in 1 column: Row 0 is text status + copy button, Row 1 is box status
    assert len(status_col.controls) == 2
    mobile_text_row = status_col.controls[0]
    mobile_box_row = status_col.controls[1]
    assert isinstance(mobile_text_row, ft.Row)
    assert isinstance(mobile_box_row, ft.Row)
    assert app.status_banner in mobile_text_row.controls
    assert app.copy_error_button in mobile_text_row.controls
    assert app.version_indicator_container in mobile_box_row.controls

    row_2 = top_bar_column.controls[1]
    assert isinstance(row_2, ft.Row)
    assert len(row_2.controls) == 2

    # Tab switcher
    tab_switcher = ui.controls[3]
    assert isinstance(tab_switcher, ft.AnimatedSwitcher)


def test_mobile_tab_switching():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.width = 390
    page.overlay = []

    app = SlowVerbApp(page=page)
    app.build_ui()

    assert app.active_tab_index == 0
    assert app.mobile_tab_switcher.content == app.mobile_waveform_view

    # Switch to Effects tab (1)
    app._switch_mobile_tab(1)
    assert app.active_tab_index == 1
    assert app.mobile_tab_switcher.content == app.mobile_effects_view

    # Switch back to Waveform tab (0)
    app._switch_mobile_tab(0)
    assert app.active_tab_index == 0
    assert app.mobile_tab_switcher.content == app.mobile_waveform_view


def test_adaptive_waveform_bars():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.width = 360
    page.overlay = []

    app = SlowVerbApp(page=page)
    app.build_ui()

    # On a 360px mobile width, bars adapt to ~40 bars
    app._adapt_waveform_bars(360.0)
    assert app.num_wave_bars < 90
    assert 32 <= app.num_wave_bars <= 45
    assert len(app.wave_bar_containers) == app.num_wave_bars
    assert app.waveform_stack.width == app.total_bars_width

    # On desktop, bars default to 90
    page.platform = ft.PagePlatform.WINDOWS
    page.width = 1120
    app._adapt_waveform_bars(1120.0)
    assert app.num_wave_bars == 90
    assert len(app.wave_bar_containers) == 90


def test_mobile_status_banner_formatting():
    """Verify mobile status text scaling (up to 4px reduction), 3-line clamp, and ellipsis truncation."""
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.width = 390
    page.overlay = []

    app = SlowVerbApp(page=page)
    app.build_ui()

    # 1. Short message: base size 12
    app.set_status("SYSTEM READY")
    assert app.status_banner.size == 12
    assert app.status_banner.value == ">> SYSTEM READY"
    assert app.status_banner.max_lines == 3

    # 2. Medium message fitting with minor font reduction (e.g. 10 or 11)
    app.set_status("FILE PROCESSING COMPLETE WITH SPECIAL DSP FILTER APPLICATION ACTIVE IN BUFFER")
    assert 8 <= app.status_banner.size <= 12
    assert ">> FILE PROCESSING COMPLETE" in app.status_banner.value

    # 3. Very long error requiring maximum 4px reduction and ellipsis
    long_error = "A" * 300
    app.set_status(long_error, is_error=True)
    assert app.status_banner.size == 8  # 12 - 4 = 8 minimum
    assert app.status_banner.value.endswith("...")
    assert app.copy_error_button.visible is True
    # The full error is preserved for copying
    assert app._last_error == long_error


def test_desktop_status_banner_unconstrained():
    """Verify desktop status text remains at default size 12 without 3-line mobile clamp."""
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    page.width = 1120
    page.overlay = []

    app = SlowVerbApp(page=page)
    app.build_ui()

    long_msg = "VERY LONG MESSAGE ON DESKTOP " * 5
    app.set_status(long_msg)
    assert app.status_banner.size == 12
    assert app.status_banner.max_lines is None


def test_show_export_format_dialog():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []

    app = SlowVerbApp(page=page)
    app.build_ui()

    # When no file loaded, warns user
    app.show_export_format_dialog()
    assert "PLEASE LOAD AN AUDIO FILE" in app.status_banner.value

    # When file loaded, opens dialog
    app.current_filepath = "test.wav"
    app.metadata = MagicMock()
    app.show_export_format_dialog()
    page.open.assert_called_once()
