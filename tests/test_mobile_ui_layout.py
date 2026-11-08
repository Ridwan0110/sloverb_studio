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
