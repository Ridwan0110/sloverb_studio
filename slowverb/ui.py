"""Desktop GUI for SlowVerb Studio using Flet with minimalistic square/robotic styling."""

import asyncio
import os
import platform
import threading
import time
from typing import Callable, Dict, Any, List, Optional, Tuple

import flet as ft

from slowverb.config import (
    APP_NAME,
    COLOR_ACCENT,
    COLOR_AMBER,
    COLOR_BG,
    COLOR_BORDER,
    COLOR_CYAN,
    COLOR_RED,
    COLOR_SURFACE,
    COLOR_SURFACE_LIGHT,
    COLOR_TEXT,
    COLOR_TEXT_DIM,
    COLOR_WAVE_PLAYED,
    COLOR_WAVE_UNPLAYED,
    DEFAULT_BASS,
    DEFAULT_EXPORT_FORMAT,
    DEFAULT_PITCH,
    DEFAULT_REVERB,
    DEFAULT_SPEED,
    FA_BOLT,
    FA_CHECK,
    FA_EXPORT,
    FA_FOLDER_OPEN,
    FA_MAGIC,
    FA_MUSIC,
    FA_PAUSE,
    FA_PLAY,
    FA_REWIND,
    FA_SCISSORS,
    FA_STOP,
    FA_UNDO,
    FA_WARNING,
    FONT_AWESOME_FONT,
    MAX_BASS,
    MAX_PITCH,
    MAX_REVERB,
    MAX_SPEED,
    MIN_BASS,
    MIN_PITCH,
    MIN_REVERB,
    MIN_SPEED,
    PRESET_DEFAULT,
    PRESET_NIGHTCORE,
    PRESET_SLOWED_REVERB,
    ROBOTIC_FONT,
    Preset,
)
from slowverb.engine import (
    AudioEffects,
    AudioEngine,
    AudioMetadata,
    WaveformData,
)
from slowverb.player import AudioPlayer


def pick_file_desktop(initial_dir: Optional[str] = None) -> Optional[str]:
    """Opens native OS file chooser to select an audio file without Flutter plugins."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        selected = filedialog.askopenfilename(
            parent=root,
            initialdir=initial_dir or os.getcwd(),
            title="SELECT AUDIO FILE",
            filetypes=[
                ("All Audio Files", "*.opus;*.mp3;*.wav;*.flac;*.ogg;*.m4a;*.aac"),
                ("Opus Audio (*.opus)", "*.opus"),
                ("MP3 Audio (*.mp3)", "*.mp3"),
                ("WAV Audio (*.wav)", "*.wav"),
                ("All Files (*.*)", "*.*"),
            ],
        )
        root.destroy()
        return os.path.abspath(selected) if selected else None
    except Exception as e:
        print(f"File dialog error: {e}")
        return None


def save_file_desktop(initial_filename: str, ext: str, initial_dir: Optional[str] = None) -> Optional[str]:
    """Opens native OS file save dialog without Flutter plugins."""
    try:
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.wm_attributes("-topmost", True)
        selected = filedialog.asksaveasfilename(
            parent=root,
            initialdir=initial_dir or os.getcwd(),
            initialfile=initial_filename,
            defaultextension=f".{ext}",
            filetypes=[
                (f"{ext.upper()} Audio (*.{ext})", f"*.{ext}"),
                ("All Files (*.*)", "*.*"),
            ],
        )
        root.destroy()
        return os.path.abspath(selected) if selected else None
    except Exception as e:
        print(f"Save dialog error: {e}")
        return None


from slowverb.ffmpeg_manager import (
    download_ffmpeg,
    find_ffmpeg,
    get_project_root,
    normalize_platform_arch,
)


class FFmpegSetupView(ft.Container):
    """
    Cyber/robotic Flet view displayed when FFmpeg is missing.
    Prompts the user to download FFmpeg and renders real-time download progress.
    """

    def __init__(
        self,
        page: Optional[ft.Page],
        on_success: Callable[[str], None],
        on_cancel: Optional[Callable[[], None]] = None,
        target_dir: Optional[str] = None,
    ):
        self.target_page = page
        self.on_success = on_success
        self.on_cancel = on_cancel
        self.target_dir = target_dir or os.path.join(get_project_root(), "ffmpeg")
        self._ui_lock = threading.Lock()
        self.is_downloading = False

        os_name, arch = normalize_platform_arch()
        exe_name = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
        target_file_path = os.path.join(self.target_dir, exe_name)

        # Header controls
        self.header_icon = ft.Text(
            FA_BOLT,
            font_family=FONT_AWESOME_FONT,
            size=16,
            color=COLOR_ACCENT,
        )
        self.header_title = ft.Text(
            "FFMPEG MISSING",
            font_family=ROBOTIC_FONT,
            size=12,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT,
        )
        self.arch_badge = ft.Container(
            content=ft.Text(
                f"{os_name.upper()} // {arch.upper()}",
                font_family=ROBOTIC_FONT,
                size=10,
                weight=ft.FontWeight.BOLD,
                color=COLOR_CYAN,
            ),
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(width=1, color=COLOR_CYAN),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=8, vertical=4),
        )

        header_row = ft.Row(
            [
                ft.Row([self.header_icon, self.header_title], spacing=8),
                self.arch_badge,
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Description text
        desc_text = ft.Text(
            "SloVerb Studio requires the FFmpeg to process real-time audio effects "
            "(pitch, reverberation, speed, bass boost), render audio waveforms, and export audio tracks.",
            font_family=ROBOTIC_FONT,
            size=11,
            color=COLOR_TEXT_DIM,
        )

        # Technical diagnostic info box
        self.target_path_text = ft.Text(
            f"DESTINATION: {target_file_path}",
            font_family=ROBOTIC_FONT,
            size=10,
            color=COLOR_TEXT_DIM,
        )
        info_lines = [
            ft.Text(
                "STATUS: MISSING FROM SYSTEM PATH & LOCAL APPLICATION DIRECTORY",
                font_family=ROBOTIC_FONT,
                size=11,
                weight=ft.FontWeight.BOLD,
                color=COLOR_AMBER,
            ),
            self.target_path_text,
            ft.Text(
                "SOURCE: OFFICIAL STATIC PRE-BUILT RELEASES",
                font_family=ROBOTIC_FONT,
                size=10,
                color=COLOR_TEXT_DIM,
            ),
        ]
        info_box = ft.Container(
            content=ft.Column(info_lines, spacing=4),
            bgcolor=COLOR_BG,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.all(12),
        )

        # Prompt question
        self.prompt_text = ft.Text(
            "Would you like SloVerb Studio to automatically download FFmpeg now?",
            font_family=ROBOTIC_FONT,
            size=12,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT,
        )

        # Progress elements (initially hidden)
        self.progress_bar = ft.ProgressBar(
            value=0.0,
            color=COLOR_ACCENT,
            bgcolor=COLOR_SURFACE,
            height=8,
            border_radius=ft.BorderRadius.all(2),
            visible=False,
        )
        self.status_label = ft.Text(
            "READY TO DOWNLOAD",
            font_family=ROBOTIC_FONT,
            size=11,
            color=COLOR_TEXT_DIM,
        )
        self.detail_label = ft.Text(
            "",
            font_family=ROBOTIC_FONT,
            size=10,
            color=COLOR_CYAN,
            visible=False,
        )

        # Interactive buttons
        self.btn_download_text = ft.Text(
            "DOWNLOAD FFMPEG",
            font_family=ROBOTIC_FONT,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=COLOR_BG,
        )
        self.btn_download = ft.Container(
            content=ft.Row(
                [
                    ft.Text(FA_BOLT, font_family=FONT_AWESOME_FONT, size=11, color=COLOR_BG),
                    self.btn_download_text,
                ],
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=6,
            ),
            bgcolor=COLOR_ACCENT,
            border=ft.Border.all(width=1, color=COLOR_ACCENT),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=16, vertical=10),
            alignment=ft.Alignment.CENTER,
            on_click=self._on_download_click,
            ink=True,
        )

        self.actions_row = ft.Row(
            [self.btn_download],
            spacing=12,
        )

        card_content = ft.Column(
            [
                header_row,
                ft.Divider(color=COLOR_BORDER, height=1),
                desc_text,
                info_box,
                self.prompt_text,
                self.status_label,
                self.progress_bar,
                self.detail_label,
                self.actions_row,
            ],
            spacing=14,
        )

        super().__init__(
            content=card_content,
            bgcolor=COLOR_SURFACE_LIGHT,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.all(24),
            width=700,
            alignment=ft.Alignment.CENTER,
        )

    def _safe_update(self):
        """Thread-safe update helper ensuring updates are executed on the Page's event loop."""
        if not self.target_page:
            return
        try:
            loop = getattr(self.target_page, "loop", None)
            if loop and loop.is_running() and not loop.is_closed():
                try:
                    running_loop = asyncio.get_running_loop()
                except RuntimeError:
                    running_loop = None

                if running_loop is loop:
                    with self._ui_lock:
                        self.target_page.update()
                else:
                    loop.call_soon_threadsafe(self._safe_target_page_update)
            else:
                with self._ui_lock:
                    self.target_page.update()
        except Exception:
            pass

    def _safe_target_page_update(self):
        with self._ui_lock:
            try:
                if self.target_page:
                    self.target_page.update()
            except Exception:
                pass

    def _on_download_click(self, e):
        """Triggers the FFmpeg download in a background thread."""
        if self.is_downloading:
            return

        self.is_downloading = True
        self.actions_row.visible = False
        self.progress_bar.visible = True
        self.progress_bar.value = 0.0
        self.detail_label.visible = True
        self.status_label.value = "INITIALIZING DOWNLOAD..."
        self.status_label.color = COLOR_ACCENT
        self.detail_label.value = "CONNECTING TO REPOSITORY..."
        self._safe_update()

        threading.Thread(target=self._download_thread, daemon=True).start()

    def _download_thread(self):
        """Worker thread executing download and reporting progress to the UI."""
        def _on_progress(ratio: Optional[float], message: str):
            if ratio is not None:
                self.progress_bar.value = ratio
                pct = int(ratio * 100)
                self.status_label.value = f"DOWNLOADING FFMPEG // {pct}%"
            else:
                self.progress_bar.value = None
                self.status_label.value = "DOWNLOADING FFMPEG..."
            self.detail_label.value = message.upper()
            self._safe_update()

        try:
            final_bin = download_ffmpeg(
                target_dir=self.target_dir,
                on_progress=_on_progress,
            )
            self.progress_bar.value = 1.0
            self.status_label.value = "FFMPEG CONFIGURED & VERIFIED SUCCESSFULLY"
            self.status_label.color = COLOR_ACCENT
            self.detail_label.value = "LAUNCHING APPLICATION..."
            self._safe_update()
            time.sleep(0.4)
            self.on_success(final_bin)
        except Exception as ex:
            self.is_downloading = False
            self.progress_bar.visible = False
            self.status_label.value = "DOWNLOAD FAILED"
            self.status_label.color = COLOR_RED
            self.detail_label.value = f"ERROR: {str(ex).upper()}"
            self.detail_label.color = COLOR_RED
            self.btn_download_text.value = "RETRY DOWNLOAD"
            self.actions_row.visible = True
            self._safe_update()


class SlowVerbApp:
    """Core GUI and state controller for SlowVerb Studio."""

    def __init__(self, page: Optional[ft.Page] = None, ffmpeg_path: Optional[str] = None):
        self.page = page
        self.ffmpeg_path: Optional[str] = ffmpeg_path or find_ffmpeg()
        self.engine: Optional[AudioEngine] = None
        self.player: Optional[AudioPlayer] = None

        # State
        self.current_filepath: Optional[str] = None
        self.metadata: Optional[AudioMetadata] = None
        self.waveform: WaveformData = WaveformData()
        self.effects = AudioEffects()
        self.export_format = DEFAULT_EXPORT_FORMAT

        self.num_wave_bars = 90
        self.bar_width = 6.0
        self.bar_spacing = 2.0
        self.total_bars_width = self.num_wave_bars * self.bar_width + (self.num_wave_bars - 1) * self.bar_spacing
        self.waveform_container_width = 1064.0
        self.wave_bar_containers = []
        self._playback_poll_active = False
        self._playback_poller_id = 0
        self._ui_lock = threading.Lock()
        from slowverb import __version__

        self.version: str = __version__
        self._pending_cli_file: Optional[str] = None
        self.ffmpeg_setup_view: Optional[FFmpegSetupView] = None

        # Status tracking for rendered audio buffer
        self._rendered_effects: Optional[AudioEffects] = None
        self._rendered_is_preview: bool = False

        self._update_pending = False

        if self.ffmpeg_path:
            self.engine = AudioEngine(self.ffmpeg_path)
            self.player = AudioPlayer(on_playback_finished=self._on_playback_end)
            self._init_controls()
            if self.page:
                self._setup_page()
        else:
            if self.page:
                self._setup_ffmpeg_page()
            else:
                self.engine = AudioEngine(auto_ensure=True)
                self.player = AudioPlayer(on_playback_finished=self._on_playback_end)
                self._init_controls()

    def update_ui(self):
        """Thread-safe UI update wrapper ensuring updates are executed on the Page's event loop."""
        if not self.page:
            return
        try:
            loop = getattr(self.page, "loop", None)
            if loop and loop.is_running() and not loop.is_closed():
                try:
                    running_loop = asyncio.get_running_loop()
                except RuntimeError:
                    running_loop = None

                if running_loop is loop:
                    self._update_pending = False
                    with self._ui_lock:
                        self.page.update()
                else:
                    if not self._update_pending:
                        self._update_pending = True
                        loop.call_soon_threadsafe(self._scheduled_page_update)
            else:
                with self._ui_lock:
                    self.page.update()
        except Exception:
            pass

    def _scheduled_page_update(self):
        """Dispatches page.update() inside the UI lock on the event loop."""
        self._update_pending = False
        with self._ui_lock:
            try:
                if self.page:
                    self.page.update()
            except Exception:
                pass

    def _on_page_resize(self, e):
        """Updates estimated waveform container width when page is resized."""
        if self.page and hasattr(self.page, "width") and self.page.width:
            try:
                w = float(self.page.width)
                if w > 0:
                    self.waveform_container_width = max(self.total_bars_width, w - 56.0)
            except Exception:
                pass

    def _on_waveform_size_change(self, e: ft.LayoutSizeChangeEvent):
        """Updates exact waveform container width after layout render."""
        if hasattr(e, "width") and e.width and e.width > 0:
            self.waveform_container_width = float(e.width)

    def _setup_page(self):
        """Configures the desktop window and page styling."""
        self.page.title = APP_NAME
        self.page.bgcolor = COLOR_BG
        self.page.padding = 16
        self.page.scroll = ft.ScrollMode.AUTO

        # Register FontAwesome Free Solid font
        self.page.fonts = {
            FONT_AWESOME_FONT: "fonts/fa-solid-900.ttf",
        }

        if hasattr(self.page, "window") and self.page.window:
            try:
                self.page.window.width = 1120
                self.page.window.height = 900
                self.page.window.min_width = 880
                self.page.window.min_height = 750
                w = float(self.page.window.width)
                if w > 0:
                    self.waveform_container_width = max(self.total_bars_width, w - 56.0)
            except Exception:
                pass

        if hasattr(self.page, "on_resize"):
            self.page.on_resize = self._on_page_resize

        self.page.add(self.build_ui())
        self.page.update()


    def _setup_ffmpeg_page(self):
        """Configures window and mounts the FFmpeg setup view when FFmpeg is missing."""
        self.page.title = f"{APP_NAME} // FFMPEG SETUP"
        self.page.bgcolor = COLOR_BG
        self.page.padding = 24
        self.page.scroll = ft.ScrollMode.AUTO

        self.page.fonts = {
            FONT_AWESOME_FONT: "fonts/fa-solid-900.ttf",
        }

        if hasattr(self.page, "window") and self.page.window:
            try:
                self.page.window.width = 850
                self.page.window.height = 620
                self.page.window.min_width = 750
                self.page.window.min_height = 550
            except Exception:
                pass

        self.ffmpeg_setup_view = FFmpegSetupView(
            page=self.page,
            on_success=self._on_ffmpeg_installed,
            on_cancel=self._on_ffmpeg_cancelled,
        )

        center_wrapper = ft.Container(
            content=self.ffmpeg_setup_view,
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=ft.Padding.only(top=30),
        )
        self.page.add(center_wrapper)
        self.page.update()

    def _on_ffmpeg_installed(self, binary_path: str):
        """Called once FFmpeg has been downloaded, extracted, and verified."""
        self.ffmpeg_path = binary_path
        self.engine = AudioEngine(self.ffmpeg_path)
        self.player = AudioPlayer(on_playback_finished=self._on_playback_end)
        self._init_controls()

        if self.page:
            if hasattr(self.page, "clean"):
                self.page.clean()
            else:
                self.page.controls.clear()

            self._setup_page()

            if self._pending_cli_file:
                cli_path = self._pending_cli_file
                self._pending_cli_file = None
                self.load_file(cli_path)

    def _on_ffmpeg_cancelled(self):
        """Called when user declines FFmpeg setup."""
        if self.page:
            if hasattr(self.page, "window") and self.page.window and hasattr(self.page.window, "close"):
                try:
                    self.page.window.close()
                except Exception:
                    pass
            elif hasattr(self.page, "window_destroy"):
                try:
                    self.page.window_destroy()
                except Exception:
                    pass

    def _init_controls(self):
        """Initializes all interactive UI controls."""
        # Top bar file loading
        self.file_path_field = ft.TextField(
            hint_text="ENTER AUDIO FILE PATH OR BROWSE...",
            text_size=12,
            text_style=ft.TextStyle(font_family=ROBOTIC_FONT, color=COLOR_TEXT),
            bgcolor=COLOR_SURFACE,
            border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT,
            border_radius=ft.BorderRadius.all(2),
            expand=True,
            dense=True,
            on_submit=lambda e: self.load_file(self.file_path_field.value),
        )

        # Metadata banner
        self.track_info_text = ft.Text(
            "NO TRACK LOADED // SELECT AN AUDIO FILE TO BEGIN",
            font_family=ROBOTIC_FONT,
            size=12,
            color=COLOR_TEXT_DIM,
            weight=ft.FontWeight.BOLD,
        )

        self.format_badge_text = ft.Text(
            "FORMAT: --",
            font_family=ROBOTIC_FONT,
            size=11,
            color=COLOR_CYAN,
        )

        self.version_badge_text = ft.Text(
            f"v{self.version}",
            font_family=ROBOTIC_FONT,
            size=11,
            color=COLOR_TEXT_DIM,
            weight=ft.FontWeight.BOLD,
        )

        # Waveform peeking and timeline info
        self.time_display_text = ft.Text(
            "00:00.0 / 00:00.0",
            font_family=ROBOTIC_FONT,
            size=13,
            color=COLOR_ACCENT,
            weight=ft.FontWeight.BOLD,
        )

        self.peak_display_text = ft.Text(
            "PEAK: -- dB",
            font_family=ROBOTIC_FONT,
            size=11,
            color=COLOR_TEXT_DIM,
        )

        # Interactive Waveform Bars
        self.waveform_row = ft.Row(
            spacing=2,
            alignment=ft.MainAxisAlignment.CENTER,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            expand=True,
        )
        for _ in range(self.num_wave_bars):
            bar = ft.Container(
                width=6,
                height=6,
                bgcolor=COLOR_WAVE_UNPLAYED,
                border_radius=ft.BorderRadius.all(1),
            )
            self.wave_bar_containers.append(bar)
            self.waveform_row.controls.append(bar)

        self.waveform_container = ft.Container(
            content=self.waveform_row,
            height=110,
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            alignment=ft.Alignment.CENTER,
            on_size_change=self._on_waveform_size_change,
        )

        self.waveform_gesture = ft.GestureDetector(
            content=self.waveform_container,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap_down=self._on_waveform_gesture,
            on_pan_start=self._on_waveform_gesture,
            on_pan_update=self._on_waveform_gesture,
        )

        # Speed Slider
        self.speed_label = ft.Text(f"{DEFAULT_SPEED:.2f}x", font_family=ROBOTIC_FONT, size=12, color=COLOR_ACCENT)
        self.speed_slider = ft.Slider(
            min=MIN_SPEED,
            max=MAX_SPEED,
            value=DEFAULT_SPEED,
            divisions=20,
            active_color=COLOR_ACCENT,
            inactive_color=COLOR_BORDER,
            on_change=self._on_speed_changed,
        )

        # Pitch Slider & Link Checkbox
        self.pitch_label = ft.Text(f"{DEFAULT_PITCH:.2f}x", font_family=ROBOTIC_FONT, size=12, color=COLOR_CYAN)
        self.pitch_slider = ft.Slider(
            min=MIN_PITCH,
            max=MAX_PITCH,
            value=DEFAULT_PITCH,
            divisions=20,
            active_color=COLOR_CYAN,
            inactive_color=COLOR_BORDER,
            on_change=self._on_pitch_changed,
            disabled=True,  # Initially disabled because pitch links to speed by default
        )
        self.link_pitch_checkbox = ft.Checkbox(
            label="LINK PITCH TO SPEED (MATCH TURNTABLE / TAPE RATE)",
            value=True,
            label_style=ft.TextStyle(font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
            active_color=COLOR_ACCENT,
            check_color=COLOR_BG,
            on_change=self._on_link_pitch_changed,
        )

        # Reverb Slider
        self.reverb_label = ft.Text(f"{int(DEFAULT_REVERB)}%", font_family=ROBOTIC_FONT, size=12, color=COLOR_AMBER)
        self.reverb_slider = ft.Slider(
            min=MIN_REVERB,
            max=MAX_REVERB,
            value=DEFAULT_REVERB,
            divisions=100,
            active_color=COLOR_AMBER,
            inactive_color=COLOR_BORDER,
            on_change=self._on_reverb_changed,
        )

        # Bass Boost Slider
        self.bass_label = ft.Text(f"{int(DEFAULT_BASS)}%", font_family=ROBOTIC_FONT, size=12, color=COLOR_CYAN)
        self.bass_slider = ft.Slider(
            min=MIN_BASS,
            max=MAX_BASS,
            value=DEFAULT_BASS,
            divisions=100,
            active_color=COLOR_CYAN,
            inactive_color=COLOR_BORDER,
            on_change=self._on_bass_changed,
        )

        # Cut/Trim Controls
        self.trim_start_field = ft.TextField(
            value="0.0",
            label="START (SEC)",
            label_style=ft.TextStyle(font_family=ROBOTIC_FONT, size=10, color=COLOR_TEXT_DIM),
            text_size=12,
            text_style=ft.TextStyle(font_family=ROBOTIC_FONT, color=COLOR_TEXT),
            bgcolor=COLOR_SURFACE,
            border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT,
            border_radius=ft.BorderRadius.all(2),
            width=110,
            dense=True,
            on_change=self._on_trim_fields_changed,
        )
        self.trim_end_field = ft.TextField(
            value="0.0",
            label="END (SEC)",
            label_style=ft.TextStyle(font_family=ROBOTIC_FONT, size=10, color=COLOR_TEXT_DIM),
            text_size=12,
            text_style=ft.TextStyle(font_family=ROBOTIC_FONT, color=COLOR_TEXT),
            bgcolor=COLOR_SURFACE,
            border_color=COLOR_BORDER,
            focused_border_color=COLOR_ACCENT,
            border_radius=ft.BorderRadius.all(2),
            width=110,
            dense=True,
            on_change=self._on_trim_fields_changed,
        )

        # Export controls
        self.format_radio_group = ft.RadioGroup(
            content=ft.Row([
                ft.Radio(
                    value="opus",
                    label="OPUS (160k VBR)",
                    label_style=ft.TextStyle(font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    active_color=COLOR_ACCENT,
                ),
                ft.Radio(
                    value="mp3",
                    label="MP3 (192k CBR)",
                    label_style=ft.TextStyle(font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    active_color=COLOR_ACCENT,
                ),
            ], spacing=20),
            value=DEFAULT_EXPORT_FORMAT,
            on_change=self._on_format_changed,
        )

        self.status_banner = ft.Text(
            ">> SYSTEM READY",
            font_family=ROBOTIC_FONT,
            size=12,
            color=COLOR_TEXT_DIM,
            weight=ft.FontWeight.BOLD,
        )

        # Status indicator: shows whether playing current modified or old modified version
        self.version_indicator_icon = ft.Text(
            FA_MUSIC,
            font_family=FONT_AWESOME_FONT,
            size=11,
            color=COLOR_TEXT_DIM,
        )
        self.version_indicator_text = ft.Text(
            "NO TRACK LOADED",
            font_family=ROBOTIC_FONT,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=COLOR_TEXT_DIM,
        )
        self.version_indicator_container = ft.Container(
            content=ft.Row([
                self.version_indicator_icon,
                self.version_indicator_text,
            ], spacing=6, alignment=ft.MainAxisAlignment.CENTER),
            bgcolor=COLOR_SURFACE_LIGHT,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
        )

    # --- UI Layout Builders ---

    def _make_square_button(
        self,
        text: str,
        on_click,
        accent_color: str = COLOR_TEXT,
        bg_color: str = COLOR_SURFACE_LIGHT,
        width: Optional[int] = None,
        fa_icon: Optional[str] = None,
    ) -> ft.Container:
        """Constructs a minimalistic square robotic button container with optional FontAwesome icon."""
        controls = []
        if fa_icon:
            controls.append(
                ft.Text(
                    fa_icon,
                    font_family=FONT_AWESOME_FONT,
                    size=12,
                    color=accent_color,
                )
            )
        controls.append(
            ft.Text(
                text,
                font_family=ROBOTIC_FONT,
                size=11,
                weight=ft.FontWeight.BOLD,
                color=accent_color,
                text_align=ft.TextAlign.CENTER,
            )
        )
        if len(controls) == 1:
            button_content = controls[0]
        else:
            button_content = ft.Row(
                controls,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                spacing=6,
            )

        return ft.Container(
            content=button_content,
            bgcolor=bg_color,
            border=ft.Border.all(width=1, color=accent_color),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=8),
            alignment=ft.Alignment.CENTER,
            width=width,
            on_click=on_click,
            ink=True,
        )

    def _make_card(self, title: str, content: ft.Control, badge: Optional[str] = None) -> ft.Container:
        """Constructs a cyber/robotic styled panel card with square borders."""
        header_controls = [
            ft.Text(
                title,
                font_family=ROBOTIC_FONT,
                size=11,
                weight=ft.FontWeight.BOLD,
                color=COLOR_TEXT_DIM,
            )
        ]
        if badge:
            header_controls.append(
                ft.Text(
                    badge,
                    font_family=ROBOTIC_FONT,
                    size=10,
                    color=COLOR_CYAN,
                )
            )

        return ft.Container(
            content=ft.Column([
                ft.Row(header_controls, alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                ft.Divider(height=1, color=COLOR_BORDER),
                content,
            ], spacing=8),
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.all(12),
        )

    def build_ui(self) -> ft.Column:
        """Assembles the full application UI layout."""
        # Header bar
        header_row = ft.Row([
            ft.Text(
                "SLOVERB STUDIO",
                font_family=ROBOTIC_FONT,
                size=16,
                weight=ft.FontWeight.BOLD,
                color=COLOR_ACCENT,
            ),
            ft.Row([
                self.format_badge_text,
                self.version_badge_text,
            ], spacing=10),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # File Loader Bar
        loader_bar = ft.Row([
            self.file_path_field,
            self._make_square_button("BROWSE", lambda e: self._on_browse_clicked(), accent_color=COLOR_CYAN, fa_icon=FA_FOLDER_OPEN),
        ], spacing=8)

        # Status Bar (positioned right below file loader section)
        status_bar = ft.Container(
            content=ft.Row([
                self.status_banner,
                self.version_indicator_container,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER),
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=12, vertical=6),
        )

        # Waveform Section
        waveform_header = ft.Row([
            self.track_info_text,
            ft.Row([
                self.peak_display_text,
                self.time_display_text,
            ], spacing=15),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        waveform_card = self._make_card(
            "PEEK",
            ft.Column([
                waveform_header,
                self.waveform_gesture,
            ], spacing=6),
            badge=None,
        )

        # Transport & Trim Bar
        transport_row = ft.Row([
            self._make_square_button("PLAY", lambda e: self.play(), accent_color=COLOR_ACCENT, fa_icon=FA_PLAY),
            self._make_square_button("PAUSE", lambda e: self.pause(), accent_color=COLOR_AMBER, fa_icon=FA_PAUSE),
            self._make_square_button("STOP", lambda e: self.stop(), accent_color=COLOR_RED, fa_icon=FA_STOP),
            self._make_square_button("REWIND", lambda e: self.seek(0.0), accent_color=COLOR_TEXT_DIM, fa_icon=FA_REWIND),
            ft.VerticalDivider(width=20, color=COLOR_BORDER),
            ft.Text("TRIM:", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT_DIM, weight=ft.FontWeight.BOLD),
            self.trim_start_field,
            self._make_square_button("SET START", lambda e: self.set_trim_start_from_playhead(), accent_color=COLOR_CYAN, fa_icon=FA_SCISSORS),
            self.trim_end_field,
            self._make_square_button("SET END", lambda e: self.set_trim_end_from_playhead(), accent_color=COLOR_CYAN, fa_icon=FA_SCISSORS),
            self._make_square_button("RESET TRIM", lambda e: self.reset_trim(), accent_color=COLOR_TEXT_DIM, fa_icon=FA_UNDO),
        ], spacing=8, alignment=ft.MainAxisAlignment.START)

        # Presets Bar
        presets_row = ft.Row([
            ft.Text("PRESETS:", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT_DIM, weight=ft.FontWeight.BOLD),
            self._make_square_button(
                "1. SLOWED + REVERB (0.8x / 40%)",
                lambda e: self.apply_preset(PRESET_SLOWED_REVERB),
                accent_color=COLOR_ACCENT,
            ),
            self._make_square_button(
                "2. NIGHTCORE (1.2x / 0%)",
                lambda e: self.apply_preset(PRESET_NIGHTCORE),
                accent_color=COLOR_CYAN,
            ),
            self._make_square_button(
                "RESET ALL EFFECTS",
                lambda e: self.apply_preset(PRESET_DEFAULT),
                accent_color=COLOR_TEXT_DIM,
            ),
        ], spacing=10)

        # Effect Sliders Card
        effects_content = ft.Column([
            presets_row,
            ft.Divider(height=1, color=COLOR_BORDER),
            # Speed Control
            ft.Column([
                ft.Row([
                    ft.Text("TRACK SPEED (SLOWED / SPED UP):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    self.speed_label,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.speed_slider,
            ], spacing=2),
            # Pitch Control
            ft.Column([
                ft.Row([
                    ft.Text("PITCH CONTROL (INDEPENDENT OR TIED):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    self.pitch_label,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.pitch_slider,
                self.link_pitch_checkbox,
            ], spacing=2),
            # Reverb & Bass Boost
            ft.Row([
                ft.Column([
                    ft.Row([
                        ft.Text("REVERB LEVEL (0 - 100%):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                        self.reverb_label,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.reverb_slider,
                ], spacing=2, expand=True),
                ft.Column([
                    ft.Row([
                        ft.Text("BASS BOOST (0 - 100%):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                        self.bass_label,
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    self.bass_slider,
                ], spacing=2, expand=True),
            ], spacing=20),
        ], spacing=10)

        effects_card = self._make_card(
            "EFFECTS",
            effects_content,
            badge=None,
        )

        # Export Card
        export_content = ft.Row([
            ft.Column([
                ft.Text("SELECT EXPORT FORMAT:", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT_DIM),
                self.format_radio_group,
            ], spacing=4),
            ft.Row([
                self._make_square_button(
                    "PREVIEW EFFECTS",
                    lambda e: self.render_and_play_preview(),
                    accent_color=COLOR_CYAN,
                    fa_icon=FA_MUSIC,
                ),
                self._make_square_button(
                    "EXPORT AUDIO TRACK",
                    lambda e: self.export_processed_track(),
                    accent_color=COLOR_ACCENT,
                    bg_color=COLOR_SURFACE,
                    fa_icon=FA_EXPORT,
                ),
            ], spacing=10),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        export_card = self._make_card(
            "Render",
            export_content,
            badge=None,
        )

        return ft.Column([
            header_row,
            loader_bar,
            status_bar,
            waveform_card,
            transport_row,
            effects_card,
            export_card,
            ft.Container(height=16),
        ], spacing=12)

    # --- File Loading & Analysis ---

    def _on_browse_clicked(self, e=None):
        """Opens native OS file chooser to load an audio file without Flutter plugins."""
        picked = pick_file_desktop()
        if picked:
            self.load_file(picked)

    def _on_save_as_clicked(self, e=None):
        """Prompts user for destination path using native OS dialog and exports track."""
        if not self.current_filepath or not self.metadata:
            self.set_status("PLEASE LOAD AN AUDIO FILE BEFORE EXPORTING", is_error=True)
            return

        ext = self.export_format.lower()
        base = os.path.splitext(self.metadata.filename)[0]
        desc = []
        if abs(self.effects.speed - 1.0) > 0.01:
            desc.append(f"{self.effects.speed:.1f}x")
        if self.effects.reverb_percent > 1.0:
            desc.append(f"rev{int(self.effects.reverb_percent)}")
        if self.effects.bass_boost_percent > 1.0:
            desc.append(f"bass{int(self.effects.bass_boost_percent)}")
        tag = "_".join(desc) if desc else "edited"
        initial_name = f"{base}_{tag}.{ext}"

        save_path = save_file_desktop(initial_filename=initial_name, ext=ext)
        if save_path:
            self.export_processed_track(custom_output_path=save_path)

    def load_file(self, filepath: str):
        """Loads an audio file, probes metadata, extracts waveform, and prepares player."""
        if not self.engine:
            self._pending_cli_file = filepath
            return

        if not filepath or not os.path.isfile(filepath):
            self.set_status(f"ERROR: FILE NOT FOUND '{filepath}'", is_error=True)
            return

        try:
            self.player.stop()
            self.current_filepath = os.path.abspath(filepath)
            self.file_path_field.value = self.current_filepath

            # Probe technical details
            self.metadata = self.engine.probe_file(self.current_filepath)
            self.track_info_text.value = (
                f"TRACK: {self.metadata.title.upper()} // "
                f"LENGTH: {self.metadata.formatted_duration} // "
                f"SR: {self.metadata.sample_rate}Hz // "
                f"CH: {self.metadata.channels}"
            )
            self.format_badge_text.value = f"CODEC: {self.metadata.format_name.upper()} @ {self.metadata.bitrate}kbps"

            # Set trim fields to full duration initially
            self.effects.trim_start = 0.0
            self.effects.trim_end = self.metadata.duration
            self.trim_start_field.value = "0.0"
            self.trim_end_field.value = f"{self.metadata.duration:.1f}"

            # Extract waveform for visualization and peeking
            self.set_status("ANALYZING WAVEFORM PEAKS...")
            self.waveform = self.engine.extract_waveform(self.current_filepath, num_bins=self.num_wave_bars)
            self._update_waveform_bars(playhead_ratio=0.0)

            # Pre-load raw original audio into player
            raw_samples, sr = self.engine.render_pcm_buffer(self.current_filepath, AudioEffects())
            self.player.load_buffer(raw_samples, sr)
            self._rendered_effects = AudioEffects(trim_start=0.0, trim_end=self.metadata.duration)
            self._rendered_is_preview = False
            self._update_version_indicator()

            self.time_display_text.value = f"00:00.0 / {self.metadata.formatted_duration}"
            self.peak_display_text.value = f"PEAK: {self.waveform.max_peak_db} dB"
            self.set_status(f"LOADED: {self.metadata.filename}")

            self.update_ui()

        except Exception as ex:
            self.set_status(f"LOAD ERROR: {str(ex)}", is_error=True)
            self.update_ui()

    # --- Waveform Peeking & Seeking ---

    def _update_waveform_bars(self, playhead_ratio: float):
        """Draws waveform bars with heights matching amplitude peaks and color matching playhead."""
        peaks = self.waveform.peaks
        if not peaks:
            for bar in self.wave_bar_containers:
                if bar.height != 6:
                    bar.height = 6
                if bar.bgcolor != COLOR_WAVE_UNPLAYED:
                    bar.bgcolor = COLOR_WAVE_UNPLAYED
            return

        active_index = int(playhead_ratio * (len(self.wave_bar_containers) - 1))
        for i, bar in enumerate(self.wave_bar_containers):
            peak = peaks[i] if i < len(peaks) else 0.0
            # Scale height from min 6px to max 88px
            expected_h = max(6, int(peak * 88))
            if bar.height != expected_h:
                bar.height = expected_h
            expected_bg = COLOR_WAVE_PLAYED if i <= active_index else COLOR_WAVE_UNPLAYED
            if bar.bgcolor != expected_bg:
                bar.bgcolor = expected_bg

    def _extract_local_x(self, e) -> Optional[float]:
        """Extracts local horizontal position from Flet tap or drag event."""
        if hasattr(e, "local_position") and e.local_position is not None:
            return float(e.local_position.x)
        if hasattr(e, "data") and e.data:
            try:
                parts = str(e.data).split()
                return float(parts[0])
            except Exception:
                pass
        return None

    def _calculate_waveform_ratio(self, local_x: float) -> float:
        """
        Calculates exact seek ratio (0.0 to 1.0) based on the mouse local X coordinate,
        accounting for the centered alignment of waveform bars within the container.
        """
        bars_width = getattr(self, "total_bars_width", 718.0)
        container_width = getattr(self, "waveform_container_width", 1064.0)

        # Waveform row is centered inside the container.
        # The bars start at start_x and end at start_x + bars_width.
        if container_width > bars_width:
            start_x = (container_width - bars_width) / 2.0
        else:
            start_x = 0.0

        end_x = start_x + bars_width

        if local_x <= start_x:
            return 0.0
        if local_x >= end_x:
            return 1.0

        return (local_x - start_x) / bars_width

    def _get_active_duration(self) -> float:
        """Returns the duration of the actively loaded audio buffer or file."""
        if self.player and self.player.get_duration() > 0:
            return self.player.get_duration()
        if self.waveform and self.waveform.duration > 0:
            return self.waveform.duration
        if self.metadata and self.metadata.duration > 0:
            return self.metadata.duration
        return 0.0

    def _on_waveform_gesture(self, e):
        """Peeks/seeks to the exact position clicked or dragged on the waveform."""
        dur = self._get_active_duration()
        if dur <= 0:
            return

        local_x = self._extract_local_x(e)
        if local_x is None:
            return

        ratio = self._calculate_waveform_ratio(local_x)
        target_sec = ratio * dur
        self.seek(target_sec)

    def _on_waveform_tap(self, e: ft.TapEvent):
        """Tap event handler delegating to gesture processor."""
        self._on_waveform_gesture(e)

    def _on_waveform_pan(self, e: ft.DragUpdateEvent):
        """Pan/drag event handler delegating to gesture processor."""
        self._on_waveform_gesture(e)

    def seek(self, seconds: float):
        """Seeks playback to specified timestamp and updates UI peeking info."""
        dur = self._get_active_duration()
        if dur <= 0:
            return

        target_time = max(0.0, min(dur, seconds))
        self.player.seek(target_time)

        ratio = target_time / dur
        self._update_waveform_bars(playhead_ratio=ratio)

        # Update peak reading and time badge
        peak_val = self.waveform.get_peak_at_time(target_time)
        peak_db = self.waveform.get_peak_db_at_time(target_time)
        self.peak_display_text.value = f"PEAK: {peak_db} dB ({int(peak_val*100)}%)"

        cur_m = int(target_time // 60)
        cur_s = target_time % 60
        tot_m = int(dur // 60)
        tot_s = dur % 60
        self.time_display_text.value = f"{cur_m:02d}:{cur_s:04.1f} / {tot_m:02d}:{tot_s:04.1f}"

        self.update_ui()

    # --- Transport & Playback Management ---

    def play(self):
        """Starts playback and launches the UI position tracking poller."""
        if not self.current_filepath:
            self.set_status("LOAD A TRACK BEFORE PLAYING", is_error=True)
            return

        self.player.play()
        self.set_status("PLAYING...")
        self._update_version_indicator()
        self._start_playback_poller()
        self.update_ui()

    def pause(self):
        """Pauses playback."""
        self.player.pause()
        self._playback_poller_id += 1
        self._playback_poll_active = False
        self.set_status("PAUSED")
        self._update_version_indicator()
        self.update_ui()

    def stop(self):
        """Stops playback and rewinds to beginning."""
        self.player.stop()
        self._playback_poller_id += 1
        self._playback_poll_active = False
        self.seek(0.0)
        self.set_status("STOPPED")
        self._update_version_indicator()
        self.update_ui()

    def _on_playback_end(self):
        """Callback when audio completes playback."""
        self.stop()

    def _update_playback_tick(self):
        """Updates waveform playhead, time display, and peak display for current playback position."""
        if not self.player:
            return
        cur_t = self.player.get_current_time()
        tot_t = self._get_active_duration()
        if tot_t > 0:
            ratio = cur_t / tot_t
            self._update_waveform_bars(ratio)
            cur_m = int(cur_t // 60)
            cur_s = cur_t % 60
            tot_m = int(tot_t // 60)
            tot_s = tot_t % 60
            new_time_str = f"{cur_m:02d}:{cur_s:04.1f} / {tot_m:02d}:{tot_s:04.1f}"
            if self.time_display_text.value != new_time_str:
                self.time_display_text.value = new_time_str

            # Keep Peak Display updated dynamically during playback
            if self.waveform and self.waveform.peaks:
                peak_val = self.waveform.get_peak_at_time(cur_t)
                peak_db = self.waveform.get_peak_db_at_time(cur_t)
                new_peak_str = f"PEAK: {peak_db} dB ({int(peak_val * 100)}%)"
                if self.peak_display_text.value != new_peak_str:
                    self.peak_display_text.value = new_peak_str

            self.update_ui()

    def _start_playback_poller(self):
        """Launches playback poller to dynamically update playhead, peak readout, and time display."""
        self._playback_poller_id += 1
        current_id = self._playback_poller_id
        self._playback_poll_active = True

        loop = getattr(self.page, "loop", None) if self.page else None
        if self.page and hasattr(self.page, "run_task") and loop and loop.is_running() and not loop.is_closed():
            self.page.run_task(self._async_playback_poller, current_id)
        else:
            threading.Thread(target=self._thread_playback_poller, args=(current_id,), daemon=True).start()

    async def _async_playback_poller(self, poller_id: int):
        """Asynchronous playback poller executing directly on the Page event loop."""
        while self._playback_poller_id == poller_id and self.player and self.player.is_playing():
            try:
                self._update_playback_tick()
            except Exception:
                pass
            await asyncio.sleep(0.05)
        if self._playback_poller_id == poller_id:
            self._playback_poll_active = False

    def _thread_playback_poller(self, poller_id: int):
        """Fallback thread poller for headless/mock environments."""
        while self._playback_poller_id == poller_id and self.player and self.player.is_playing():
            try:
                self._update_playback_tick()
            except Exception:
                pass
            time.sleep(0.05)
        if self._playback_poller_id == poller_id:
            self._playback_poll_active = False

    # --- Effect Parameter Handlers ---

    def _on_speed_changed(self, e):
        """Handles track speed slider changes."""
        val = round(float(self.speed_slider.value), 2)
        self.effects.speed = val
        self.speed_label.value = f"{val:.2f}x"

        # If pitch is linked to speed, sync pitch automatically
        if self.effects.link_pitch_to_speed:
            self.effects.pitch = val
            self.pitch_slider.value = val
            self.pitch_label.value = f"{val:.2f}x"

        self._update_version_indicator()
        self.update_ui()

    def _on_pitch_changed(self, e):
        """Handles independent pitch slider changes."""
        val = round(float(self.pitch_slider.value), 2)
        self.effects.pitch = val
        self.pitch_label.value = f"{val:.2f}x"
        self._update_version_indicator()
        self.update_ui()

    def _on_link_pitch_changed(self, e):
        """Toggles linking pitch to speed."""
        linked = bool(self.link_pitch_checkbox.value)
        self.effects.link_pitch_to_speed = linked
        self.pitch_slider.disabled = linked
        if linked:
            # Sync pitch to current speed
            self.effects.pitch = self.effects.speed
            self.pitch_slider.value = self.effects.speed
            self.pitch_label.value = f"{self.effects.speed:.2f}x"
        self._update_version_indicator()
        self.update_ui()

    def _on_reverb_changed(self, e):
        """Handles reverb percentage slider changes."""
        val = round(float(self.reverb_slider.value), 1)
        self.effects.reverb_percent = val
        self.reverb_label.value = f"{int(val)}%"
        self._update_version_indicator()
        self.update_ui()

    def _on_bass_changed(self, e):
        """Handles bass boost percentage slider changes."""
        val = round(float(self.bass_slider.value), 1)
        self.effects.bass_boost_percent = val
        self.bass_label.value = f"{int(val)}%"
        self._update_version_indicator()
        self.update_ui()

    def apply_preset(self, preset: Preset):
        """Applies a named preset (e.g. Slowed+Reverb or Nightcore) to all controls."""
        self.effects.speed = preset.speed
        self.effects.reverb_percent = preset.reverb
        self.effects.bass_boost_percent = preset.bass_boost
        self.effects.link_pitch_to_speed = preset.link_pitch_to_speed
        self.effects.pitch = preset.pitch if preset.pitch is not None else preset.speed

        # Update controls
        self.speed_slider.value = self.effects.speed
        self.speed_label.value = f"{self.effects.speed:.2f}x"

        self.reverb_slider.value = self.effects.reverb_percent
        self.reverb_label.value = f"{int(self.effects.reverb_percent)}%"

        self.bass_slider.value = self.effects.bass_boost_percent
        self.bass_label.value = f"{int(self.effects.bass_boost_percent)}%"

        self.link_pitch_checkbox.value = self.effects.link_pitch_to_speed
        self.pitch_slider.disabled = self.effects.link_pitch_to_speed
        self.pitch_slider.value = self.effects.pitch
        self.pitch_label.value = f"{self.effects.pitch:.2f}x"

        self.set_status(f"APPLIED PRESET: {preset.name}")
        self._update_version_indicator()
        self.update_ui()

    # --- Trimming ---

    def _on_trim_fields_changed(self, e):
        """Validates and updates trim start and end values from text fields."""
        try:
            st = float(self.trim_start_field.value)
            self.effects.trim_start = max(0.0, st)
        except ValueError:
            pass

        try:
            en = float(self.trim_end_field.value)
            if self.metadata and en > self.metadata.duration:
                en = self.metadata.duration
            self.effects.trim_end = en
        except ValueError:
            pass

        self._update_version_indicator()
        self.update_ui()

    def set_trim_start_from_playhead(self):
        """Locks current playhead timestamp as trim start."""
        cur_t = round(self.player.get_current_time(), 2)
        self.effects.trim_start = cur_t
        self.trim_start_field.value = f"{cur_t:.2f}"
        self.set_status(f"TRIM START SET: {cur_t:.2f}s")
        self._update_version_indicator()
        self.update_ui()

    def set_trim_end_from_playhead(self):
        """Locks current playhead timestamp as trim end."""
        cur_t = round(self.player.get_current_time(), 2)
        if cur_t > self.effects.trim_start:
            self.effects.trim_end = cur_t
            self.trim_end_field.value = f"{cur_t:.2f}"
            self.set_status(f"TRIM END SET: {cur_t:.2f}s")
            self._update_version_indicator()
            self.update_ui()

    def reset_trim(self):
        """Resets trim points to start and end of track."""
        if not self.metadata:
            return
        self.effects.trim_start = 0.0
        self.effects.trim_end = self.metadata.duration
        self.trim_start_field.value = "0.0"
        self.trim_end_field.value = f"{self.metadata.duration:.1f}"
        self.set_status("TRIM RESET TO FULL TRACK")
        self._update_version_indicator()
        self.update_ui()

    # --- Preview & Export ---

    def _on_format_changed(self, e):
        """Updates export format selection (opus / mp3)."""
        self.export_format = self.format_radio_group.value

    def render_and_play_preview(self):
        """Renders the audio with active effects and loads it into the player."""
        if not self.current_filepath:
            self.set_status("PLEASE LOAD AN AUDIO FILE FIRST", is_error=True)
            return

        self.set_status("RENDERING PREVIEW WITH ACTIVE EFFECTS...")
        self.update_ui()

        def background_render():
            try:
                samples, sr = self.engine.render_pcm_buffer(self.current_filepath, self.effects)
                eff_dur = len(samples) / sr

                # 1. Extract new waveform from rendered samples so PEEK card displays actual preview peaks
                self.waveform = self.engine.extract_waveform_from_samples(
                    samples, sample_rate=sr, num_bins=self.num_wave_bars, duration=eff_dur
                )
                self._update_waveform_bars(0.0)

                # 2. Update Peak and Time text readouts immediately
                peak_val = self.waveform.get_peak_at_time(0.0)
                peak_db = self.waveform.get_peak_db_at_time(0.0)
                self.peak_display_text.value = f"PEAK: {peak_db} dB ({int(peak_val * 100)}%)"

                tot_m = int(eff_dur // 60)
                tot_s = eff_dur % 60
                self.time_display_text.value = f"00:00.0 / {tot_m:02d}:{tot_s:04.1f}"

                # 3. Load audio buffer into player and start playback
                self.player.load_buffer(samples, sr)
                self._rendered_effects = AudioEffects(
                    speed=self.effects.speed,
                    pitch=self.effects.pitch,
                    reverb_percent=self.effects.reverb_percent,
                    bass_boost_percent=self.effects.bass_boost_percent,
                    link_pitch_to_speed=self.effects.link_pitch_to_speed,
                    trim_start=self.effects.trim_start,
                    trim_end=self.effects.trim_end,
                )
                self._rendered_is_preview = True
                self.player.play()

                # 4. Update Status Bar and version indicator
                self._update_version_indicator()
                self.set_status(f"PLAYING PREVIEW // DURATION: {tot_m:02d}:{tot_s:04.1f}")

                # 5. Launch playback poller to continuously update playhead, peak, and time
                self._start_playback_poller()

            except Exception as ex:
                self.set_status(f"PREVIEW ERROR: {str(ex)}", is_error=True)
                self._update_version_indicator()

            self.update_ui()

        threading.Thread(target=background_render, daemon=True).start()

    def export_processed_track(self, custom_output_path: Optional[str] = None) -> Optional[str]:
        """
        Exports the track with current effects, speed, pitch, reverb, and trimming.
        Returns the output path on success.
        """
        if not self.current_filepath or not self.metadata:
            self.set_status("PLEASE LOAD AN AUDIO FILE BEFORE EXPORTING", is_error=True)
            return None

        # Determine target output path
        ext = self.export_format.lower()
        if not custom_output_path:
            base, _ = os.path.splitext(self.current_filepath)
            # Descriptor tag based on active effects
            desc = []
            if abs(self.effects.speed - 1.0) > 0.01:
                desc.append(f"{self.effects.speed:.1f}x")
            if self.effects.reverb_percent > 1.0:
                desc.append(f"rev{int(self.effects.reverb_percent)}")
            if self.effects.bass_boost_percent > 1.0:
                desc.append(f"bass{int(self.effects.bass_boost_percent)}")
            tag = "_".join(desc) if desc else "edited"
            custom_output_path = f"{base}_{tag}.{ext}"

        self.set_status("EXPORTING AUDIO TRACK... PLEASE WAIT...")
        self.update_ui()

        try:
            out_file, file_size = self.engine.export_audio(
                input_path=self.current_filepath,
                output_path=custom_output_path,
                effects=self.effects,
                export_format=ext,
            )
            mb = file_size / (1024 * 1024)
            self.set_status(f"EXPORT COMPLETED: '{os.path.basename(out_file)}' ({mb:.2f} MB)")
            self.update_ui()
            return out_file
        except Exception as ex:
            self.set_status(f"EXPORT ERROR: {str(ex)}", is_error=True)
            self.update_ui()
            return None

    def set_status(self, message: str, is_error: bool = False):
        """Updates the status footer banner."""
        if hasattr(self, "status_banner") and self.status_banner:
            self.status_banner.value = f">> {message.upper()}"
            self.status_banner.color = COLOR_RED if is_error else COLOR_ACCENT
            self.update_ui()

    def _effects_match(self, eff1: Optional[AudioEffects], eff2: Optional[AudioEffects]) -> bool:
        """Checks if two AudioEffects parameter sets have identical values."""
        if eff1 is None or eff2 is None:
            return False

        trim_end_match = (
            (eff1.trim_end is None and eff2.trim_end is None)
            or (
                eff1.trim_end is not None
                and eff2.trim_end is not None
                and abs(eff1.trim_end - eff2.trim_end) < 1e-2
            )
        )

        return (
            abs(eff1.speed - eff2.speed) < 1e-4 and
            abs(eff1.effective_pitch - eff2.effective_pitch) < 1e-4 and
            abs(eff1.reverb_percent - eff2.reverb_percent) < 1e-2 and
            abs(eff1.bass_boost_percent - eff2.bass_boost_percent) < 1e-2 and
            abs(eff1.trim_start - eff2.trim_start) < 1e-2 and
            trim_end_match
        )

    def _is_default_effects(self, eff: Optional[AudioEffects]) -> bool:
        """Checks if effect settings match initial untouched defaults."""
        if eff is None:
            return True
        dur = self.metadata.duration if self.metadata else 0.0
        trim_end_default = (
            eff.trim_end is None
            or dur <= 0.0
            or abs(eff.trim_end - dur) < 1e-2
        )
        return (
            abs(eff.speed - 1.0) < 1e-4 and
            abs(eff.effective_pitch - 1.0) < 1e-4 and
            abs(eff.reverb_percent) < 1e-2 and
            abs(eff.bass_boost_percent) < 1e-2 and
            abs(eff.trim_start) < 1e-2 and
            trim_end_default
        )

    def is_playing_current_modified_version(self) -> bool:
        """Returns True if the loaded buffer matches the active slider effects."""
        if not self.current_filepath:
            return False
        if self._rendered_is_preview and self._rendered_effects is not None:
            return self._effects_match(self.effects, self._rendered_effects)
        return self._is_default_effects(self.effects)

    def _update_version_indicator(self):
        """Updates the status indicator showing whether playing current or old modified version."""
        if not self.current_filepath:
            self.version_indicator_icon.value = FA_MUSIC
            self.version_indicator_icon.color = COLOR_TEXT_DIM
            self.version_indicator_text.value = "NO TRACK LOADED"
            self.version_indicator_text.color = COLOR_TEXT_DIM
            self.version_indicator_container.border = ft.Border.all(width=1, color=COLOR_BORDER)
            self.update_ui()
            return

        is_playing = self.player.is_playing() if self.player else False
        is_current = self.is_playing_current_modified_version()

        if is_current:
            version_label = "CURRENT MODIFIED VERSION"
            display_text = f"PLAYING: {version_label}" if is_playing else version_label
            self.version_indicator_icon.value = FA_CHECK
            self.version_indicator_icon.color = COLOR_ACCENT
            self.version_indicator_text.value = display_text
            self.version_indicator_text.color = COLOR_ACCENT
            self.version_indicator_container.border = ft.Border.all(width=1, color=COLOR_ACCENT)
        else:
            version_label = "OLD MODIFIED VERSION"
            display_text = f"PLAYING: {version_label}" if is_playing else version_label
            self.version_indicator_icon.value = FA_WARNING
            self.version_indicator_icon.color = COLOR_AMBER
            self.version_indicator_text.value = display_text
            self.version_indicator_text.color = COLOR_AMBER
            self.version_indicator_container.border = ft.Border.all(width=1, color=COLOR_AMBER)

        self.update_ui()

    def close(self):
        """Cleanly releases audio player streams and background pollers."""
        self._playback_poll_active = False
        self._playback_poller_id += 1
        if self.player:
            self.player.close()
