"""Tests for GUI state management, preset triggers, slider synchronization, and waveform peeking."""

import os
import sys
import flet as ft
import pytest
from slowverb.config import (
    COLOR_ACCENT,
    COLOR_RED,
    FA_CHECK,
    FA_COPY,
    FA_WARNING,
    PRESET_DEFAULT,
    PRESET_NIGHTCORE,
    PRESET_SLOWED_REVERB,
)
from slowverb.ui import SlowVerbApp, copy_to_clipboard


def test_gui_initial_controls_state(app):
    """Verify default states of all GUI controls upon app initialization."""
    assert app.current_filepath is None
    assert app.metadata is None
    assert app.effects.speed == 1.0
    assert app.effects.pitch == 1.0
    assert app.effects.link_pitch_to_speed is True
    assert app.effects.reverb_percent == 0.0
    assert app.effects.bass_boost_percent == 0.0

    # Controls initial values
    assert app.speed_slider.value == 1.0
    assert app.pitch_slider.value == 1.0
    assert app.pitch_slider.disabled is True  # Linked by default
    assert app.link_pitch_checkbox.value is True
    assert app.reverb_slider.value == 0.0
    assert app.bass_slider.value == 0.0
    assert app.format_radio_group.value == "opus"


def test_gui_load_file_and_waveform(app, sample_sine_audio):
    """Verify loading audio file updates track info, waveform bars, and trim fields."""
    app.load_file(sample_sine_audio)
    assert app.current_filepath == os.path.abspath(sample_sine_audio)
    assert app.metadata is not None
    assert app.metadata.duration > 0.0
    assert len(app.waveform.peaks) == app.num_wave_bars
    assert app.effects.trim_start == 0.0
    assert app.effects.trim_end == app.metadata.duration
    assert "LOADED:" in app.status_banner.value


def test_gui_preset_applications(app):
    """Verify that applying presets updates all sliders, labels, and effect parameters."""
    # 1. Apply Slowed+Reverb Preset
    app.apply_preset(PRESET_SLOWED_REVERB)
    assert app.effects.speed == 0.8
    assert app.effects.reverb_percent == 40.0
    assert app.effects.link_pitch_to_speed is True
    assert app.effects.effective_pitch == 0.8
    assert app.speed_slider.value == 0.8
    assert app.speed_label.value == "0.80x"
    assert app.reverb_slider.value == 40.0
    assert app.reverb_label.value == "40%"
    assert app.pitch_slider.value == 0.8
    assert app.pitch_slider.disabled is True

    # 2. Apply Nightcore Preset
    app.apply_preset(PRESET_NIGHTCORE)
    assert app.effects.speed == 1.2
    assert app.effects.reverb_percent == 0.0
    assert app.effects.link_pitch_to_speed is True
    assert app.effects.effective_pitch == 1.2
    assert app.speed_slider.value == 1.2
    assert app.speed_label.value == "1.20x"
    assert app.reverb_slider.value == 0.0
    assert app.pitch_slider.value == 1.2
    assert app.pitch_slider.disabled is True

    # 3. Apply Default Preset
    app.apply_preset(PRESET_DEFAULT)
    assert app.effects.speed == 1.0
    assert app.effects.reverb_percent == 0.0
    assert app.effects.effective_pitch == 1.0


def test_gui_pitch_linking_toggle(app):
    """Verify toggling link checkbox allows independent pitch slider adjustment."""
    # Change speed while linked -> pitch follows
    app.speed_slider.value = 0.85
    app._on_speed_changed(None)
    assert app.effects.speed == 0.85
    assert app.effects.pitch == 0.85
    assert app.pitch_slider.value == 0.85

    # Unlink pitch
    app.link_pitch_checkbox.value = False
    app._on_link_pitch_changed(None)
    assert app.effects.link_pitch_to_speed is False
    assert app.pitch_slider.disabled is False

    # Adjust pitch independently
    app.pitch_slider.value = 1.3
    app._on_pitch_changed(None)
    assert app.effects.speed == 0.85
    assert app.effects.pitch == 1.3
    assert app.effects.effective_pitch == 1.3

    # Relink pitch -> pitch snaps back to speed
    app.link_pitch_checkbox.value = True
    app._on_link_pitch_changed(None)
    assert app.effects.link_pitch_to_speed is True
    assert app.pitch_slider.disabled is True
    assert app.effects.effective_pitch == 0.85


def test_gui_waveform_peeking_and_seeking(app, sample_sine_audio):
    """Verify waveform peeking updates time display, peak dB, and playhead."""
    app.load_file(sample_sine_audio)
    dur = app.metadata.duration

    # Seek to middle of audio
    app.seek(dur / 2.0)
    assert "00:01" in app.time_display_text.value
    assert "PEAK:" in app.peak_display_text.value

    # Seek to beginning
    app.seek(0.0)
    assert app.time_display_text.value.startswith("00:00.0")


def test_gui_visual_trim_mode_activation_and_toggles(app, sample_sine_audio):
    """Verify activating trim mode toggles TRIM button with APPLY/CANCEL and reveals waveform heads."""
    app.load_file(sample_sine_audio)

    # Initial state
    assert app.trim_mode is False
    assert app.trim_button.visible is True
    assert app.trim_mode_row.visible is False
    assert app.trim_start_head.visible is False
    assert app.trim_end_head.visible is False

    # Activate trim mode
    app.enter_trim_mode()
    assert app.trim_mode is True
    assert app.trim_button.visible is False
    assert app.trim_mode_row.visible is True
    assert app.trim_start_head.visible is True
    assert app.trim_end_head.visible is True
    assert app.trim_head_start_sec == 0.0
    assert abs(app.trim_head_end_sec - app.metadata.duration) < 0.05
    assert app.apply_trim_button.disabled is False
    assert app.trim_notice_text.visible is False


def test_gui_visual_trim_dragging_and_clamping(app, sample_sine_audio):
    """Verify dragging start and end heads across the visual waveform."""
    app.load_file(sample_sine_audio)
    app.enter_trim_mode()

    bars_w = app.total_bars_width  # 718.0
    container_w = app.waveform_container_width  # 1064.0
    start_x = (container_w - bars_w) / 2.0  # 173.0

    # Drag closer to start head (e.g. at 25% of waveform width)
    x_25 = start_x + 0.25 * bars_w
    event_start = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=x_25, y=50.0))
    app._on_waveform_gesture(event_start, is_pan=False)

    expected_start_sec = 0.25 * app.metadata.duration
    assert abs(app.trim_head_start_sec - expected_start_sec) < 0.1
    assert app.trim_head_start_sec <= app.trim_head_end_sec

    # Drag closer to end head (e.g. at 80% of waveform width)
    x_80 = start_x + 0.80 * bars_w
    event_end = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=x_80, y=50.0))
    app._on_waveform_gesture(event_end, is_pan=False)

    expected_end_sec = 0.80 * app.metadata.duration
    assert abs(app.trim_head_end_sec - expected_end_sec) < 0.1
    assert app.trim_head_end_sec >= app.trim_head_start_sec


def test_gui_visual_trim_collision_prevention_and_delete_warning(app, sample_sine_audio):
    """Verify start head cannot pass end head, and equality greys out APPLY with notice."""
    app.load_file(sample_sine_audio)
    app.enter_trim_mode()

    dur = app.metadata.duration

    # 1. Prevent start head from passing end head
    app.trim_head_end_sec = 1.5
    app._active_drag_head = "start"
    # Try dragging start head to 2.5s (beyond end head)
    container_w = app.waveform_container_width
    bars_w = app.total_bars_width
    start_x = (container_w - bars_w) / 2.0
    ratio_25 = 2.5 / dur
    x_25 = start_x + ratio_25 * bars_w
    event_drag_past = ft.DragUpdateEvent(
        "pan_update",
        app.waveform_gesture,
        local_position=ft.Offset(x=x_25, y=50.0),
        global_position=ft.Offset(x=x_25, y=50.0),
    )
    app._on_waveform_gesture(event_drag_past, is_pan=True)

    # Start head must be clamped at end head (1.5s), never beyond
    assert app.trim_head_start_sec <= app.trim_head_end_sec
    assert abs(app.trim_head_start_sec - 1.5) < 0.05

    # 2. When start == end, APPLY is disabled/greyed out with deletion notice
    app.trim_head_start_sec = 1.5
    app.trim_head_end_sec = 1.5
    app._update_trim_ui()

    assert app.apply_trim_button.disabled is True
    assert app.apply_trim_button.opacity < 1.0
    assert app.trim_notice_text.visible is True
    assert "THIS IS EQUAL TO DELETING THE FILE" in app.trim_notice_text.value
    assert "THIS IS EQUAL TO DELETING THE FILE" in app.status_banner.value

    # Applying while disabled is safely ignored
    prev_effects_trim = app.effects.trim_start
    app.apply_trim()
    assert app.effects.trim_start == prev_effects_trim


def test_gui_visual_trim_preview_playback_bounds(app, sample_sine_audio):
    """Verify playback in trim mode only previews audio between trim heads."""
    app.load_file(sample_sine_audio)
    app.enter_trim_mode()

    # Set trim heads to 1.0s and 2.0s
    app.trim_head_start_sec = 1.0
    app.trim_head_end_sec = 2.0
    app._update_trim_heads_and_waveform()

    # Play starts from trim start head
    app.seek(0.0)  # seeking in trim mode clamps to start head
    assert abs(app.player.get_current_time() - 1.0) < 0.05

    app.play()
    assert "PLAYING PREVIEW" in app.status_banner.value

    # Simulate playhead reaching trim_head_end_sec (2.0s)
    app.player.seek(2.05)
    app._update_playback_tick()

    assert app.player.is_playing() is False
    assert "TRIM PREVIEW COMPLETED" in app.status_banner.value
    # Rewinds to trim start
    assert abs(app.player.get_current_time() - 1.0) < 0.05


def test_gui_visual_trim_apply_reduces_duration(app, sample_sine_audio):
    """Verify APPLY trims the waveform duration and updates active buffer."""
    app.load_file(sample_sine_audio)

    app.enter_trim_mode()
    app.trim_head_start_sec = 0.5
    app.trim_head_end_sec = 2.0
    expected_trimmed_dur = 1.5

    app.apply_trim()

    # Mode exited
    assert app.trim_mode is False
    assert app.trim_button.visible is True
    assert app.trim_mode_row.visible is False

    # Duration reduced in waveform and player
    assert abs(app.waveform.duration - expected_trimmed_dur) < 0.05
    assert abs(app.player.get_duration() - expected_trimmed_dur) < 0.05
    assert app.effects.trim_start == 0.5
    assert app.effects.trim_end == 2.0
    assert abs(app.player.get_current_time() - 0.0) < 0.01


def test_gui_visual_trim_extend_duration_non_destructive(app, sample_sine_audio):
    """Verify user can re-enter trim mode and extend audio duration outwards non-destructively."""
    app.load_file(sample_sine_audio)
    full_dur = app.metadata.duration

    # 1. Apply initial trim: 1.0s to 2.0s
    app.enter_trim_mode()
    app.trim_head_start_sec = 1.0
    app.trim_head_end_sec = 2.0
    app.apply_trim()
    assert abs(app.player.get_duration() - 1.0) < 0.05

    # 2. Re-enter trim mode: full track is restored to view and heads reflect current trim
    app.enter_trim_mode()
    assert abs(app.waveform.duration - full_dur) < 0.05
    assert abs(app.player.get_duration() - full_dur) < 0.05
    assert abs(app.trim_head_start_sec - 1.0) < 0.05
    assert abs(app.trim_head_end_sec - 2.0) < 0.05

    # 3. Extend trim outwards to 0.2s - 2.8s
    app.trim_head_start_sec = 0.2
    app.trim_head_end_sec = 2.8
    app.apply_trim()

    # 4. New extended duration applied
    extended_dur = 2.6
    assert abs(app.waveform.duration - extended_dur) < 0.05
    assert abs(app.player.get_duration() - extended_dur) < 0.05
    assert abs(app.effects.trim_start - 0.2) < 0.05
    assert abs(app.effects.trim_end - 2.8) < 0.05


def test_gui_visual_trim_cancel_restoration(app, sample_sine_audio):
    """Verify CANCEL discards unsaved head adjustments and restores previous state."""
    app.load_file(sample_sine_audio)
    full_dur = app.metadata.duration

    app.enter_trim_mode()
    app.trim_head_start_sec = 0.8
    app.trim_head_end_sec = 1.6

    app.cancel_trim()

    assert app.trim_mode is False
    assert app.trim_button.visible is True
    assert app.trim_mode_row.visible is False
    assert app.effects.trim_start == 0.0
    assert abs(app.effects.trim_end - full_dur) < 0.05
    assert abs(app.player.get_duration() - full_dur) < 0.05


def test_gui_trim_buttons(app, sample_sine_audio):
    """Verify legacy trim methods for compatibility."""
    app.load_file(sample_sine_audio)

    # Move playhead to 1.0s and lock start
    app.seek(1.0)
    app.set_trim_start_from_playhead()
    assert abs(app.effects.trim_start - 1.0) < 0.05
    assert app.trim_start_field.value == "1.00"

    # Move playhead to 2.2s and lock end
    app.seek(2.2)
    app.set_trim_end_from_playhead()
    assert abs(app.effects.trim_end - 2.2) < 0.05
    assert app.trim_end_field.value == "2.20"

    # Reset trim
    app.reset_trim()
    assert app.effects.trim_start == 0.0
    assert abs(app.effects.trim_end - app.metadata.duration) < 0.01


def test_gui_export_action(app, sample_sine_audio, tmp_path):
    """Verify exporting audio through GUI controller."""
    app.load_file(sample_sine_audio)
    app.apply_preset(PRESET_SLOWED_REVERB)

    out_file = str(tmp_path / "gui_export_test.opus")
    app.export_format = "opus"
    exported_path = app.export_processed_track(custom_output_path=out_file)

    assert exported_path == out_file
    assert os.path.isfile(out_file)
    assert os.path.getsize(out_file) > 0
    assert "EXPORT COMPLETED:" in app.status_banner.value


def test_no_unsupported_controls_in_overlay():
    """Verify that no unbundled controls like FilePicker are added to page.overlay."""
    from tests.test_entry_point import MockPage
    mock_page = MockPage()
    app = SlowVerbApp(mock_page)

    # In Flet 1.0, unbundled controls like FilePicker in overlay cause Flutter crash
    assert len(mock_page.overlay) == 0
    assert not hasattr(app, "file_picker")
    app.close()


def test_gui_browse_and_save_as_dialogs(app, sample_sine_audio, tmp_path):
    """Verify browse and save as dialog triggers update file and export correctly."""
    from unittest.mock import patch

    # Mock browsing a file
    with patch("slowverb.ui.pick_file_desktop", return_value=sample_sine_audio):
        app._on_browse_clicked()
        assert app.current_filepath == os.path.abspath(sample_sine_audio)
        assert app.metadata is not None

    # Mock save as dialog
    save_dest = str(tmp_path / "custom_save_output.opus")
    with patch("slowverb.ui.save_file_desktop", return_value=save_dest):
        app._on_save_as_clicked()
        assert os.path.isfile(save_dest)
        assert os.path.getsize(save_dest) > 0


def test_status_bar_position_below_file_picker():
    """Verify that the status bar is positioned directly below the file loader bar."""
    app = SlowVerbApp()
    ui_column = app.build_ui()
    controls = ui_column.controls
    # controls[0] is header_row, controls[1] is loader_bar, controls[2] is status_bar
    status_container = controls[2]
    assert (
        app.status_banner in status_container.content.controls
        or any(app.status_banner in getattr(c, "controls", []) for c in status_container.content.controls)
    )
    app.close()


def test_section_titles_and_badges():
    """Verify section titles match user specification: SLOVERB STUDIO, PEEK, EFFECTS, Render."""
    app = SlowVerbApp()
    ui_column = app.build_ui()
    controls = ui_column.controls
    header_row = controls[0]
    waveform_card = controls[3]
    effects_card = controls[5]
    export_card = controls[6]

    # 1. Header Bar: "SLOVERB STUDIO" with codec badge on right, followed by version
    header_title_text = header_row.controls[0].value
    assert header_title_text == "SLOVERB STUDIO"
    right_header_controls = header_row.controls[1].controls
    assert app.format_badge_text in right_header_controls
    assert app.version_badge_text in right_header_controls
    codec_idx = right_header_controls.index(app.format_badge_text)
    version_idx = right_header_controls.index(app.version_badge_text)
    assert version_idx == codec_idx + 1
    import slowverb
    assert app.version == slowverb.__version__
    assert f"v{slowverb.__version__}" == app.version_badge_text.value

    # 2. Waveform Card: Left -> "PEEK", Right -> None
    wave_header_row = waveform_card.content.controls[0]
    assert wave_header_row.controls[0].value == "PEEK"
    assert len(wave_header_row.controls) == 1  # Right side removed

    # 3. DSP Effects Processor: Left -> "EFFECTS", Right -> None
    effects_header_row = effects_card.content.controls[0]
    assert effects_header_row.controls[0].value == "EFFECTS"
    assert len(effects_header_row.controls) == 1  # Right side removed

    # 4. Render & Export Card: Left -> "Render", Right -> None
    render_header_row = export_card.content.controls[0]
    assert render_header_row.controls[0].value == "Render"
    assert len(render_header_row.controls) == 1  # Right side removed

    app.close()


def test_file_picker_bar_controls():
    """Verify File Picker Bar contains BROWSE and does NOT contain LOAD button."""
    app = SlowVerbApp()
    ui_column = app.build_ui()
    loader_bar = ui_column.controls[1]

    # Should only have file_path_field and BROWSE button
    assert len(loader_bar.controls) == 2
    assert loader_bar.controls[0] == app.file_path_field

    # Check that button text is BROWSE and no LOAD button exists
    browse_btn = loader_bar.controls[1]
    labels = [c.value for c in browse_btn.content.controls if hasattr(c, "value")]
    assert "BROWSE" in labels
    assert not any("LOAD" in (c.value if hasattr(c, "value") else "") for c in browse_btn.content.controls)
    app.close()


def test_render_export_buttons():
    """Verify Render card has EXPORT AUDIO TRACK and no duplicate SAVE AS... button."""
    app = SlowVerbApp()
    ui_column = app.build_ui()
    export_card = ui_column.controls[6]
    export_content_row = export_card.content.controls[2]  # content after header and divider
    button_row = export_content_row.controls[1]

    # Buttons should be PREVIEW EFFECTS and EXPORT AUDIO TRACK only
    assert len(button_row.controls) == 2
    btn_labels = []
    for btn in button_row.controls:
        for c in btn.content.controls:
            if hasattr(c, "value") and c.font_family != "FontAwesome":
                btn_labels.append(c.value)

    assert "PREVIEW EFFECTS" in btn_labels
    assert "EXPORT AUDIO TRACK" in btn_labels
    assert "SAVE AS..." not in btn_labels
    assert not any("SAVE" in l for l in btn_labels)
    app.close()


def test_zero_emojis_in_buttons_and_fa_icons():
    """Verify all buttons use FontAwesome icons and contain zero emojis."""
    import unicodedata
    app = SlowVerbApp()
    ui_column = app.build_ui()

    def check_container_for_emojis(container):
        if hasattr(container, "content"):
            content = container.content
            if hasattr(content, "controls"):
                for ctrl in content.controls:
                    if hasattr(ctrl, "value"):
                        text = ctrl.value
                        for char in text:
                            cat = unicodedata.category(char)
                            # Emojis are typically 'So' (Symbol, other), ensure no emoji characters in label texts
                            if cat == "So" and ctrl.font_family != "FontAwesome":
                                assert False, f"Found non-FA symbol/emoji: {char} in {text}"
                    if hasattr(ctrl, "controls"):
                        check_container_for_emojis(ctrl)

    for ctrl in ui_column.controls:
        check_container_for_emojis(ctrl)
    app.close()


def test_version_status_indicator_transitions(sample_sine_audio):
    """Verify status indicator accurately tracks current modified vs old modified version."""
    import copy
    from unittest.mock import patch
    app = SlowVerbApp()

    # 1. Initial state (no track loaded)
    assert "NO TRACK LOADED" in app.version_indicator_text.value

    # 2. Load file -> defaults active -> current version
    app.load_file(sample_sine_audio)
    assert "CURRENT MODIFIED VERSION" in app.version_indicator_text.value
    assert app.is_playing_current_modified_version() is True

    # 3. Tweak speed slider -> buffer has old audio, not current slider values
    app.speed_slider.value = 0.8
    app._on_speed_changed(None)
    assert "OLD MODIFIED VERSION" in app.version_indicator_text.value
    assert app.is_playing_current_modified_version() is False

    # 4. If playing -> indicator shows "PLAYING: OLD MODIFIED VERSION"
    with patch.object(app.player, "is_playing", return_value=True):
        app._update_version_indicator()
        assert app.version_indicator_text.value == "PLAYING: OLD MODIFIED VERSION"

    # 5. Move slider back to default (1.0) -> matches loaded buffer again!
    app.speed_slider.value = 1.0
    app._on_speed_changed(None)
    assert app.is_playing_current_modified_version() is True

    # 6. Apply preset -> buffer outdated
    app.apply_preset(PRESET_SLOWED_REVERB)
    assert "OLD MODIFIED VERSION" in app.version_indicator_text.value

    # 7. Render preview with preset
    app._rendered_effects = copy.deepcopy(app.effects)
    app._rendered_is_preview = True
    app._update_version_indicator()

    assert "CURRENT MODIFIED VERSION" in app.version_indicator_text.value
    assert app.is_playing_current_modified_version() is True

    # 8. While preview is active, change reverb -> becomes old modified version
    app.reverb_slider.value = 80.0
    app._on_reverb_changed(None)
    assert "OLD MODIFIED VERSION" in app.version_indicator_text.value
    assert app.is_playing_current_modified_version() is False

    # 9. Change reverb back to 40% -> becomes current modified version again!
    app.reverb_slider.value = 40.0
    app._on_reverb_changed(None)
    assert "CURRENT MODIFIED VERSION" in app.version_indicator_text.value
    assert app.is_playing_current_modified_version() is True

    app.close()


def test_waveform_exact_peeking_under_mouse(sample_sine_audio):
    """
    Verify that clicking at mouse position on the waveform peeks exactly at that bar,
    eliminating the previous +20% offset bug.
    """
    import flet as ft
    app = SlowVerbApp()
    app.load_file(sample_sine_audio)

    # Assume typical container width of 1064px
    app.waveform_container_width = 1064.0
    bars_w = app.total_bars_width  # 718.0
    start_x = (1064.0 - bars_w) / 2.0  # 173.0

    # 1. Click at bar 0 start
    event_bar0 = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=start_x, y=50.0))
    app._on_waveform_tap(event_bar0)
    assert app.player.get_current_time() == 0.0

    # 2. Click at bar 22 (the red square scenario from user's report)
    # Target bar 22 is located at start_x + 22 * (bar_width + bar_spacing) = start_x + 22 * 8.0 = start_x + 176.0
    mouse_x_bar22 = start_x + 22 * 8.0
    event_bar22 = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=mouse_x_bar22, y=50.0))
    app._on_waveform_tap(event_bar22)

    expected_ratio = 176.0 / bars_w  # approx 0.2451
    expected_sec = expected_ratio * app.metadata.duration
    assert abs(app.player.get_current_time() - expected_sec) < 0.1
    # Check that active bar is bar 21/22 and definitely not bar 40+ (the previous +20% bug)
    active_bars = sum(1 for b in app.wave_bar_containers if b.bgcolor == "#00FFA3")
    assert 21 <= active_bars <= 23

    # 3. Click at center of waveform (bar 45)
    mouse_x_center = start_x + bars_w / 2.0
    event_center = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=mouse_x_center, y=50.0))
    app._on_waveform_tap(event_center)
    assert abs(app.player.get_current_time() - (app.metadata.duration / 2.0)) < 0.1

    # 4. Drag scrub update across waveform
    drag_event = ft.DragUpdateEvent("pan_update", app.waveform_gesture, local_position=ft.Offset(x=mouse_x_bar22, y=50.0), global_position=ft.Offset(x=mouse_x_bar22, y=50.0))
    app._on_waveform_pan(drag_event)
    assert abs(app.player.get_current_time() - expected_sec) < 0.1

    # 5. Click in dead space to the left of the waveform
    event_left_dead = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=10.0, y=50.0))
    app._on_waveform_tap(event_left_dead)
    assert app.player.get_current_time() == 0.0

    # 6. Click in dead space to the right of the waveform
    event_right_dead = ft.TapEvent("tap_down", app.waveform_gesture, local_position=ft.Offset(x=1000.0, y=50.0))
    app._on_waveform_tap(event_right_dead)
    assert abs(app.player.get_current_time() - app.metadata.duration) < 0.01

    app.close()


def test_presets_buttons_have_no_icons():
    """Verify that preset buttons in the UI have no FontAwesome or other icons (pure text buttons)."""
    app = SlowVerbApp()
    ui_column = app.build_ui()
    effects_card = ui_column.controls[5]
    presets_row = effects_card.content.controls[2].controls[0]  # first control in effects card content

    assert presets_row.controls[0].value == "PRESETS:"
    preset_buttons = presets_row.controls[1:]
    assert len(preset_buttons) == 3

    for btn in preset_buttons:
        # Each button container content should be a single Text control, with NO icon
        if isinstance(btn.content, ft.Row):
            # If it's a row, make sure none of the controls have FontAwesome font
            for c in btn.content.controls:
                assert getattr(c, "font_family", None) != "FontAwesome", f"Found icon in preset button: {c}"
        else:
            # Single control: should be the label text, not FontAwesome
            assert getattr(btn.content, "font_family", None) != "FontAwesome"
            assert isinstance(btn.content, ft.Text)

    labels = [
        btn.content.value if isinstance(btn.content, ft.Text) else btn.content.controls[0].value
        for btn in preset_buttons
    ]
    assert "1. SLOWED + REVERB (0.8x / 40%)" in labels[0]
    assert "2. NIGHTCORE (1.2x / 0%)" in labels[1]
    assert "RESET ALL EFFECTS" in labels[2]
    app.close()


def test_preview_effects_updates_peak_bar_and_status_bar(sample_sine_audio):
    """
    Verify that clicking PREVIEW EFFECTS automatically updates both the Peak Bar (waveform, peak dB,
    time display) and the Status Bar (playback status, version indicator) without requiring manual peeking.
    """
    import numpy as np
    from unittest.mock import patch
    import time

    app = SlowVerbApp()
    app.load_file(sample_sine_audio)

    # Initial state
    assert "CURRENT MODIFIED VERSION" in app.version_indicator_text.value
    orig_peak_db = app.waveform.max_peak_db

    # User adjusts sliders / applies preset
    app.apply_preset(PRESET_SLOWED_REVERB)
    assert "OLD MODIFIED VERSION" in app.version_indicator_text.value

    # Simulate render_pcm_buffer returning processed buffer (e.g. longer duration and boosted peak)
    mock_samples = np.sin(2 * np.pi * 220 * np.linspace(0, 3.0, 3 * 44100)).astype(np.float32)
    mock_stereo = np.column_stack((mock_samples, mock_samples))

    with patch.object(app.engine, "render_pcm_buffer", return_value=(mock_stereo, 44100)):
        app.render_and_play_preview()
        # Wait briefly for background_render thread to execute
        time.sleep(0.3)

        # 1. Status Bar updates
        assert "PLAYING PREVIEW" in app.status_banner.value
        assert "CURRENT MODIFIED VERSION" in app.version_indicator_text.value
        assert app.is_playing_current_modified_version() is True

        # 2. Peak Bar updates
        assert "PEAK:" in app.peak_display_text.value
        assert app.peak_display_text.value != "PEAK: -- dB"
        assert "/ 00:03.0" in app.time_display_text.value

        # 3. Waveform bars updated and poller active
        assert app.player.is_playing() is True
        assert app._playback_poll_active is True

    app.close()


def test_poller_race_condition_resolution(app, sample_sine_audio):
    """Verify that _playback_poller_id ensures new poller runs even when old poller is terminating."""
    app.load_file(sample_sine_audio)

    # Start initial playback
    app.play()
    assert app._playback_poll_active is True
    initial_poller_id = app._playback_poller_id

    # Trigger second poller start (simulating preview loading while playback was running)
    app._start_playback_poller()
    new_poller_id = app._playback_poller_id
    assert new_poller_id > initial_poller_id
    assert app._playback_poll_active is True

    app.close()




def test_copy_button_initial_state_and_geometry():
    """Verify Copy button initial hidden state, square geometry, and typography."""
    app = SlowVerbApp()
    app.build_ui()

    assert app.copy_error_button.visible is False
    assert app.status_error_row.visible is False
    assert app._last_error is None
    assert app.copy_error_btn_text.value == "COPY"
    assert app.copy_error_btn_icon.value == FA_COPY
    assert app.copy_error_button.border_radius.top_left == 2
    assert app.copy_error_button.border_radius.bottom_right == 2
    assert app.copy_error_btn_text.font_family == "Consolas"
    assert app.copy_error_btn_icon.font_family == "FontAwesome"
    app.close()


def test_copy_button_visibility_on_error_and_reset():
    """Verify Copy button appears when error is thrown and hides when non-error status is set."""
    app = SlowVerbApp()
    app.build_ui()

    # Trigger error
    error_msg = "FFmpeg export failed with error:\nInvalid sample rate\nExit code 1"
    app.set_status(error_msg, is_error=True)

    assert app.copy_error_button.visible is True
    assert app.status_error_row.visible is True
    assert app._last_error == error_msg
    assert "FFMPEG EXPORT FAILED" in app.status_banner.value
    assert app.status_banner.color == COLOR_RED

    # Clear error by setting normal status
    app.set_status("STOPPED", is_error=False)
    assert app.copy_error_button.visible is False
    assert app.status_error_row.visible is False
    assert app._last_error is None
    assert "STOPPED" in app.status_banner.value
    assert app.status_banner.color == COLOR_ACCENT

    app.close()


def test_copy_button_click_and_clipboard_flow():
    """Verify clicking Copy copies error to clipboard and provides visual feedback."""
    from unittest.mock import patch

    app = SlowVerbApp()
    app.build_ui()

    error_text = "FAILED TO RENDER BUFFER: Invalid audio format\n[libopus] Internal error"
    app.set_status(error_text, is_error=True)

    with patch("slowverb.ui.copy_to_clipboard") as mock_copy:
        app._on_copy_error_clicked()
        mock_copy.assert_called_once_with(error_text, page=app.page)

        # Check visual feedback
        assert app.copy_error_btn_text.value == "COPIED!"
        assert app.copy_error_btn_icon.value == FA_CHECK
        assert app.copy_error_btn_text.color == COLOR_ACCENT
        assert app.copy_error_btn_icon.color == COLOR_ACCENT

        # Reset feedback
        app._set_copy_button_feedback(copied=False)
        assert app.copy_error_btn_text.value == "COPY"
        assert app.copy_error_btn_icon.value == FA_COPY
        assert app.copy_error_btn_text.color == COLOR_RED
        assert app.copy_error_btn_icon.color == COLOR_RED

    app.close()


def test_copy_to_clipboard_helper():
    """Verify copy_to_clipboard executes without error."""
    result = copy_to_clipboard("Test error clipboard message", page=None)
    assert isinstance(result, bool)


def test_copy_button_failure_feedback():
    """Verify clicking Copy when clipboard operation fails reports ERROR COPYING."""
    from unittest.mock import patch

    app = SlowVerbApp()
    app.build_ui()

    error_text = "FAILED TO RENDER BUFFER"
    app.set_status(error_text, is_error=True)

    with patch("slowverb.ui.copy_to_clipboard", return_value=False):
        app._on_copy_error_clicked()

        # Check failure visual feedback
        assert app.copy_error_btn_text.value == "ERROR COPYING"
        assert app.copy_error_btn_icon.value == FA_WARNING
        assert app.copy_error_btn_text.color == COLOR_RED
        assert app.copy_error_btn_icon.color == COLOR_RED

    app.close()


def test_copy_to_clipboard_when_locked():
    """Verify copy_to_clipboard returns False when another process locks the Windows clipboard."""
    import platform
    if platform.system() != "Windows":
        return

    import subprocess
    from slowverb.ui import copy_to_clipboard

    lock_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "redu-dev", "keep_clipboard_locked.py")
    if not os.path.isfile(lock_script):
        return

    proc = subprocess.Popen([sys.executable, lock_script], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        proc.stdout.readline()
        proc.stdout.readline()

        # While locked, copy_to_clipboard must fail and return False
        assert copy_to_clipboard("Should fail to copy") is False
    finally:
        try:
            proc.stdin.write("\n")
            proc.stdin.flush()
        except Exception:
            pass
        proc.wait(timeout=3)

    # After unlock, copying should succeed
    assert copy_to_clipboard("Should succeed after unlock") is True


def test_copy_to_clipboard_mobile_fallback():
    """Verify copy_to_clipboard on mobile environments uses page/service fallback and returns True."""
    from unittest.mock import patch, MagicMock
    from slowverb.ui import copy_to_clipboard

    class MockMobilePage:
        def __init__(self):
            self.services = []
            self.tasks = []

        def run_task(self, handler, *args, **kwargs):
            self.tasks.append((handler, args, kwargs))

    mock_page = MockMobilePage()

    # Simulate non-Windows environment (e.g. Android or iOS) with no CLI tools
    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.run", side_effect=FileNotFoundError("Tool not found")):
            result = copy_to_clipboard("Mobile error text", page=mock_page)
            assert result is True
            assert len(mock_page.tasks) == 1
            assert mock_page.tasks[0][1] == ("Mobile error text",)

    # Simulate mobile environment without page reference
    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.run", side_effect=FileNotFoundError("Tool not found")):
            with patch.dict(os.environ, {"FLET_PLATFORM": "android"}):
                result_no_page = copy_to_clipboard("Mobile error text without page", page=None)
                assert result_no_page is True
