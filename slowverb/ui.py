"""Desktop GUI for SlowVerb Studio using Flet with minimalistic square/robotic styling."""

import asyncio
import json
import os
import platform
import sys
import threading
import time
from typing import Callable, Any, Optional, Tuple

import flet as ft
import numpy as np

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
    FA_BUG,
    FA_CHECK,
    FA_COPY,
    FA_EXPORT,
    FA_FOLDER_OPEN,
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
from slowverb.file_dialogs import FileService
from slowverb.platform import is_mobile_environment
from slowverb.player import AudioPlayer, create_audio_player


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
        type_desc = f"{ext.upper()} File (*.{ext})" if ext.lower() in ("json", "txt", "log") else f"{ext.upper()} Audio (*.{ext})"
        selected = filedialog.asksaveasfilename(
            parent=root,
            initialdir=initial_dir or os.getcwd(),
            initialfile=initial_filename,
            defaultextension=f".{ext}",
            filetypes=[
                (type_desc, f"*.{ext}"),
                ("All Files (*.*)", "*.*"),
            ],
        )
        root.destroy()
        return os.path.abspath(selected) if selected else None
    except Exception as e:
        print(f"Save dialog error: {e}")
        return None


_clip_lock = threading.Lock()


def copy_to_clipboard(text: str, page: Any = None) -> bool:
    """Copies text to the system clipboard without heavy dependencies like Tkinter.
    Accurately detects if clipboard access fails (e.g. locked by another application).
    Returns True on success, False on failure.
    """
    if platform.system() == "Windows":
        with _clip_lock:
            try:
                import ctypes
                from ctypes import wintypes

                user32 = ctypes.windll.user32
                kernel32 = ctypes.windll.kernel32

                CF_UNICODETEXT = 13
                GMEM_MOVEABLE = 0x0002

                user32.OpenClipboard.argtypes = [wintypes.HWND]
                user32.OpenClipboard.restype = wintypes.BOOL
                user32.CloseClipboard.argtypes = []
                user32.CloseClipboard.restype = wintypes.BOOL
                user32.EmptyClipboard.argtypes = []
                user32.EmptyClipboard.restype = wintypes.BOOL
                user32.SetClipboardData.argtypes = [wintypes.UINT, wintypes.HANDLE]
                user32.SetClipboardData.restype = wintypes.HANDLE
                user32.DestroyWindow.argtypes = [wintypes.HWND]
                user32.DestroyWindow.restype = wintypes.BOOL

                user32.CreateWindowExW.argtypes = [
                    wintypes.DWORD, wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.DWORD,
                    ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                    wintypes.HWND, wintypes.HMENU, wintypes.HINSTANCE, wintypes.LPVOID
                ]
                user32.CreateWindowExW.restype = wintypes.HWND

                kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
                kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
                kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalLock.restype = wintypes.LPVOID
                kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalUnlock.restype = wintypes.BOOL
                kernel32.GlobalFree.argtypes = [wintypes.HGLOBAL]
                kernel32.GlobalFree.restype = wintypes.HGLOBAL

                HWND_MESSAGE = wintypes.HWND(-3)
                hwnd = user32.CreateWindowExW(0, "STATIC", "SloVerbClip", 0, 0, 0, 0, 0, HWND_MESSAGE, None, None, None)
                if not hwnd:
                    hwnd = user32.CreateWindowExW(0, "STATIC", "SloVerbClip", 0, 0, 0, 0, 0, None, None, None, None)
                if not hwnd:
                    return False

                try:
                    if not user32.OpenClipboard(hwnd):
                        return False
                    try:
                        if not user32.EmptyClipboard():
                            return False
                        data = text.encode("utf-16le") + b"\x00\x00"
                        h_mem = kernel32.GlobalAlloc(GMEM_MOVEABLE, len(data))
                        if not h_mem:
                            return False
                        ptr = kernel32.GlobalLock(h_mem)
                        if not ptr:
                            kernel32.GlobalFree(h_mem)
                            return False
                        ctypes.memmove(ptr, data, len(data))
                        kernel32.GlobalUnlock(h_mem)
                        if not user32.SetClipboardData(CF_UNICODETEXT, h_mem):
                            kernel32.GlobalFree(h_mem)
                            return False
                        return True
                    finally:
                        user32.CloseClipboard()
                finally:
                    user32.DestroyWindow(hwnd)
            except Exception as e:
                print(f"Clipboard operation failed: {e}")
                return False

    # Unix / Linux / macOS command-line clipboard utilities
    import subprocess
    for cmd in [["pbcopy"], ["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            res = subprocess.run(cmd, input=text.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0:
                return True
        except Exception:
            continue

    # Mobile (Android / iOS) and Flet UI service fallback
    if page:
        try:
            clip = None
            if hasattr(page, "services") and page.services is not None:
                for s in page.services:
                    if isinstance(s, ft.Clipboard):
                        clip = s
                        break
            if not clip:
                clip = ft.Clipboard()
                if hasattr(page, "_services") and hasattr(page._services, "register_service"):
                    try:
                        page._services.register_service(clip)
                    except Exception:
                        pass
                elif hasattr(page, "services") and isinstance(page.services, list):
                    page.services.append(clip)
            if hasattr(page, "run_task"):
                page.run_task(clip.set, text)
            return True
        except Exception:
            return True

    # Detect Android / iOS mobile runtime even without page reference
    is_mobile = (
        hasattr(sys, "getandroidapilevel")
        or os.environ.get("ANDROID_ROOT") is not None
        or os.environ.get("FLET_PLATFORM") in ("android", "ios")
    )
    if is_mobile:
        return True

    return False



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

    def __init__(
        self,
        page: Optional[ft.Page] = None,
        ffmpeg_path: Optional[str] = None,
        force_mobile_ui: bool = False,
        debug_mode: Optional[bool] = None,
    ):
        self.page = page
        self.force_mobile_ui = force_mobile_ui or (os.environ.get("SLOVERB_MOBILE_UI") in ("1", "true", "True"))
        import slowverb
        if debug_mode is not None:
            self.debug_mode: bool = bool(debug_mode)
        else:
            self.debug_mode: bool = bool(getattr(slowverb, "DEBUG_MODE", False)) or (os.environ.get("SLOVERB_DEBUG") in ("1", "true", "True"))

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
        self._diagnostic_logger = None
        if self.debug_mode:
            from slowverb.debug import DiagnosticLogger
            self._diagnostic_logger = DiagnosticLogger.get_instance()
            self._diagnostic_logger.install()
            self._diagnostic_logger.log(f"SlowVerb Studio v{self.version} started in DEBUG MODE")
        self._pending_cli_file: Optional[str] = None
        self.ffmpeg_setup_view: Optional[FFmpegSetupView] = None

        # Status tracking for rendered audio buffer
        self._rendered_effects: Optional[AudioEffects] = None
        self._rendered_is_preview: bool = False
        self._last_error: Optional[str] = None
        self._copy_feedback_token: int = 0

        # Visual waveform trim mode state
        self.trim_mode: bool = False
        self.trim_head_start_sec: float = 0.0
        self.trim_head_end_sec: float = 0.0
        self._active_drag_head: Optional[str] = None
        self._full_raw_samples: Optional[np.ndarray] = None
        self._full_sample_rate: int = 44100
        self._full_waveform: Optional[WaveformData] = None
        self._rendered_full_samples: Optional[np.ndarray] = None
        self._rendered_full_sr: int = 44100
        self._rendered_full_waveform: Optional[WaveformData] = None
        self._rendered_full_effects: Optional[AudioEffects] = None
        self._current_track_samples: Optional[np.ndarray] = None
        self._current_track_sr: int = 44100
        self._current_track_waveform: Optional[WaveformData] = None
        self._trim_base_samples: Optional[np.ndarray] = None
        self._trim_base_sr: int = 44100
        self._trim_base_waveform: Optional[WaveformData] = None

        self._update_pending = False

        self.file_service = FileService(
            page=self.page,
            on_file_picked=self.load_file,
            on_save_completed=self._on_save_completed,
        )
        self.active_tab_index = 0
        self.tab_peek_btn = None
        self.tab_effects_btn = None
        self.mobile_waveform_view = None
        self.mobile_effects_view = None
        self.mobile_tab_switcher = None

        self._init_debug_button()
        if self.page:
            self._mount_debug_overlay()

        if self.ffmpeg_path:
            self.engine = AudioEngine(self.ffmpeg_path)
            self.player = create_audio_player(page=self.page, on_playback_finished=self._on_playback_end)
            self._init_controls()
            if self.page:
                self._setup_page()
        else:
            if self.page:
                self._setup_ffmpeg_page()
            else:
                self.engine = AudioEngine(auto_ensure=True)
                self.player = create_audio_player(page=self.page, on_playback_finished=self._on_playback_end)
                self._init_controls()

    def _init_debug_button(self):
        """Initializes the floating debug button for page.overlay."""
        self.debug_button = ft.Container(
            content=ft.Text(
                FA_BUG,
                font_family=FONT_AWESOME_FONT,
                size=11,
                color=COLOR_AMBER,
            ),
            bgcolor=COLOR_SURFACE_LIGHT,
            border=ft.Border.all(width=1, color=COLOR_AMBER),
            shape=ft.BoxShape.CIRCLE,
            width=26,
            height=26,
            top=12,
            right=14,
            alignment=ft.Alignment.CENTER,
            tooltip="DUMP DIAGNOSTICS JSON",
            on_click=lambda e: self._on_debug_dump_clicked(),
            ink=True,
            visible=self.debug_mode,
        )

    def _mount_debug_overlay(self):
        """Mounts the debug button in page.overlay if debug mode is active."""
        if not self.debug_mode or not self.page:
            return
        if hasattr(self.page, "overlay") and isinstance(self.page.overlay, list):
            if self.debug_button not in self.page.overlay:
                self.page.overlay.append(self.debug_button)

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

    def _adapt_waveform_bars(self, width: float):
        """Adaptively recalculates waveform bar count for mobile viewports."""
        from slowverb.platform import is_mobile_environment
        if not (getattr(self, "force_mobile_ui", False) or is_mobile_environment(self.page)):
            target_bars = 90
        else:
            usable = max(240.0, width - 40.0)
            target_bars = max(32, min(90, int(usable / 8.0)))

        if target_bars != self.num_wave_bars:
            self.num_wave_bars = target_bars
            self.total_bars_width = self.num_wave_bars * self.bar_width + (self.num_wave_bars - 1) * self.bar_spacing
            self.wave_bar_containers.clear()
            self.waveform_row.controls.clear()
            for _ in range(self.num_wave_bars):
                bar = ft.Container(
                    width=int(self.bar_width),
                    height=6,
                    bgcolor=COLOR_WAVE_UNPLAYED,
                    border_radius=ft.BorderRadius.all(1),
                )
                self.wave_bar_containers.append(bar)
                self.waveform_row.controls.append(bar)

            if hasattr(self, "waveform_stack") and self.waveform_stack:
                self.waveform_stack.width = self.total_bars_width
            if hasattr(self, "trim_end_head") and self.trim_end_head:
                self.trim_end_head.left = max(0, int(self.total_bars_width - 16))
            if self._current_track_samples is not None and self.engine is not None:
                self.waveform = self.engine.extract_waveform_from_samples(
                    self._current_track_samples,
                    sample_rate=self._current_track_sr,
                    num_bins=self.num_wave_bars,
                )
            self._update_waveform_bars(0.0)

    def _on_page_resize(self, e):
        """Updates estimated waveform container width when page is resized."""
        if self.page and hasattr(self.page, "width") and self.page.width:
            try:
                w = float(self.page.width)
                if w > 0:
                    self.waveform_container_width = max(self.total_bars_width, w - 56.0)
                    self._adapt_waveform_bars(w)
            except Exception:
                pass

    def _on_waveform_size_change(self, e: ft.LayoutSizeChangeEvent):
        """Updates exact waveform container width after layout render."""
        if hasattr(e, "width") and e.width and e.width > 0:
            self.waveform_container_width = float(e.width)
            self._adapt_waveform_bars(float(e.width))

    def _setup_page(self):
        """Configures the desktop or mobile window and page styling."""
        if not self.page:
            return

        from slowverb.platform import is_mobile_environment
        is_mobile = getattr(self, "force_mobile_ui", False) or is_mobile_environment(self.page)

        self.page.title = APP_NAME
        self.page.bgcolor = COLOR_BG

        if is_mobile:
            self.page.padding = ft.Padding.only(top=10, left=12, right=12, bottom=12)
            self.page.scroll = ft.ScrollMode.ADAPTIVE
        else:
            self.page.padding = 16
            self.page.scroll = ft.ScrollMode.AUTO

        # Register FontAwesome Free Solid font
        self.page.fonts = {
            FONT_AWESOME_FONT: "fonts/fa-solid-900.ttf",
        }

        if hasattr(self.page, "window") and self.page.window:
            if getattr(self, "force_mobile_ui", False):
                try:
                    self.page.window.width = 412
                    self.page.window.height = 840
                    self.page.window.min_width = 360
                    self.page.window.min_height = 600
                    self.waveform_container_width = 360.0
                    self._adapt_waveform_bars(360.0)
                except Exception:
                    pass
            elif not is_mobile:
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
        self._mount_debug_overlay()
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
        self._mount_debug_overlay()
        self.page.update()

    def _on_ffmpeg_installed(self, binary_path: str):
        """Called once FFmpeg has been downloaded, extracted, and verified."""
        self.ffmpeg_path = binary_path
        self.engine = AudioEngine(self.ffmpeg_path)
        self.player = create_audio_player(page=self.page, on_playback_finished=self._on_playback_end)
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

        if not hasattr(self, "debug_button") or self.debug_button is None:
            self._init_debug_button()

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

        # Waveform Trim Marker Heads (Interactive Draggable Handles)
        self.trim_start_head = ft.Container(
            width=16,
            height=94,
            left=0,
            top=0,
            visible=False,
            content=ft.Column([
                ft.Container(
                    width=16,
                    height=14,
                    bgcolor=COLOR_CYAN,
                    border_radius=ft.BorderRadius.all(1),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("S", font_family=ROBOTIC_FONT, size=9, weight=ft.FontWeight.BOLD, color=COLOR_BG),
                ),
                ft.Container(
                    width=3,
                    height=80,
                    bgcolor=COLOR_CYAN,
                    border_radius=ft.BorderRadius.all(1),
                ),
            ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        )

        self.trim_end_head = ft.Container(
            width=16,
            height=94,
            left=max(0, int(self.total_bars_width - 16)),
            top=0,
            visible=False,
            content=ft.Column([
                ft.Container(
                    width=16,
                    height=14,
                    bgcolor=COLOR_AMBER,
                    border_radius=ft.BorderRadius.all(1),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("E", font_family=ROBOTIC_FONT, size=9, weight=ft.FontWeight.BOLD, color=COLOR_BG),
                ),
                ft.Container(
                    width=3,
                    height=80,
                    bgcolor=COLOR_AMBER,
                    border_radius=ft.BorderRadius.all(1),
                ),
            ], alignment=ft.MainAxisAlignment.START, horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0),
        )

        self.waveform_stack = ft.Stack(
            controls=[
                self.waveform_row,
                self.trim_start_head,
                self.trim_end_head,
            ],
            width=self.total_bars_width,
            height=94,
            alignment=ft.Alignment.CENTER,
        )

        self.waveform_container = ft.Container(
            content=self.waveform_stack,
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
            on_tap_down=self._on_waveform_tap_down,
            on_pan_start=self._on_waveform_pan_start,
            on_pan_update=self._on_waveform_pan_update,
            on_pan_end=self._on_waveform_pan_end,
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

        # Visual Waveform Cut/Trim Controls
        self.trim_button = self._make_square_button(
            "TRIM",
            lambda e: self.enter_trim_mode(),
            accent_color=COLOR_CYAN,
            fa_icon=FA_SCISSORS,
        )
        self.apply_trim_button = self._make_square_button(
            "APPLY",
            lambda e: self.apply_trim(),
            accent_color=COLOR_ACCENT,
            fa_icon=FA_CHECK,
        )
        self.cancel_trim_button = self._make_square_button(
            "CANCEL",
            lambda e: self.cancel_trim(),
            accent_color=COLOR_TEXT_DIM,
            fa_icon=FA_UNDO,
        )
        self.trim_notice_text = ft.Text(
            "NOTICE: THIS IS EQUAL TO DELETING THE FILE",
            font_family=ROBOTIC_FONT,
            size=11,
            color=COLOR_RED,
            weight=ft.FontWeight.BOLD,
            visible=False,
        )
        self.trim_mode_row = ft.Row([
            self.apply_trim_button,
            self.cancel_trim_button,
            self.trim_notice_text,
        ], spacing=8, visible=False)

        # Legacy trim controls kept for backwards compatibility during refactoring
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
            selectable=True,
            expand=True,
        )

        self.copy_error_btn_text = ft.Text(
            "COPY",
            font_family=ROBOTIC_FONT,
            size=11,
            weight=ft.FontWeight.BOLD,
            color=COLOR_RED,
            text_align=ft.TextAlign.CENTER,
        )
        self.copy_error_btn_icon = ft.Text(
            FA_COPY,
            font_family=FONT_AWESOME_FONT,
            size=11,
            color=COLOR_RED,
        )
        self.copy_error_button = ft.Container(
            content=ft.Row([
                self.copy_error_btn_icon,
                self.copy_error_btn_text,
            ], alignment=ft.MainAxisAlignment.CENTER, vertical_alignment=ft.CrossAxisAlignment.CENTER, spacing=6),
            bgcolor=COLOR_SURFACE_LIGHT,
            border=ft.Border.all(width=1, color=COLOR_RED),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=10, vertical=4),
            alignment=ft.Alignment.CENTER,
            on_click=lambda e: self._on_copy_error_clicked(),
            ink=True,
            tooltip="COPY ERROR TO CLIPBOARD",
            visible=False,
        )

        self.status_error_row = ft.Row([
            self.copy_error_button,
        ], alignment=ft.MainAxisAlignment.START, visible=False)

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

        # Mobile tabbed navigation controls
        self.active_tab_index = 0
        self.tab_peek_btn = self._make_square_button(
            "01 // PEEK",
            lambda e: self._switch_mobile_tab(0),
            accent_color=COLOR_ACCENT,
            bg_color=COLOR_SURFACE_LIGHT,
        )
        self.tab_effects_btn = self._make_square_button(
            "02 // EFFECTS",
            lambda e: self._switch_mobile_tab(1),
            accent_color=COLOR_TEXT_DIM,
            bg_color=COLOR_SURFACE,
        )
        self.mobile_waveform_view = None
        self.mobile_effects_view = None
        self.mobile_tab_switcher = None

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

    def build_ui(self) -> ft.Control:
        """Assembles the full application UI layout based on active platform and viewport."""
        from slowverb.platform import is_mobile_environment
        if getattr(self, "force_mobile_ui", False) or is_mobile_environment(self.page):
            return self.build_mobile_ui()
        return self.build_desktop_ui()

    def build_desktop_ui(self) -> ft.Column:
        """Assembles the full application UI layout for desktop environments."""
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
                ft.Container(width=30 if self.debug_mode else 0),
            ], spacing=10, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # File Loader Bar
        loader_bar = ft.Row([
            self.file_path_field,
            self._make_square_button("BROWSE", lambda e: self._on_browse_clicked(), accent_color=COLOR_CYAN, fa_icon=FA_FOLDER_OPEN),
        ], spacing=8)

        # Status Bar (positioned right below file loader section)
        self.status_row = ft.Row([
            self.status_banner,
            self.version_indicator_container,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        status_bar = ft.Container(
            content=ft.Column([
                self.status_row,
                self.status_error_row,
            ], spacing=6),
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
            self.trim_button,
            self.trim_mode_row,
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

    def build_mobile_ui(self) -> ft.Column:
        """Assembles the mobile tabbed UI layout with static top bar (~45% height) and animated dynamic tabs."""
        # Mobile Header Bar
        mobile_header = ft.Row([
            ft.Text(
                "SLOVERB STUDIO",
                font_family=ROBOTIC_FONT,
                size=15,
                weight=ft.FontWeight.BOLD,
                color=COLOR_ACCENT,
            ),
            ft.Row([
                self.format_badge_text,
                self.version_badge_text,
                ft.Container(width=28 if self.debug_mode else 0),
            ], spacing=8, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)

        # Static Top Bar Row 1: File Picker (20%) + Status Bar (80%)
        load_button = ft.Container(
            content=ft.Row([
                ft.Text(FA_FOLDER_OPEN, font_family=FONT_AWESOME_FONT, size=11, color=COLOR_CYAN),
                ft.Text("LOAD", font_family=ROBOTIC_FONT, size=11, weight=ft.FontWeight.BOLD, color=COLOR_CYAN),
            ], alignment=ft.MainAxisAlignment.CENTER, spacing=4),
            bgcolor=COLOR_SURFACE_LIGHT,
            border=ft.Border.all(width=1, color=COLOR_CYAN),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=8, vertical=8),
            on_click=lambda e: self._on_browse_clicked(),
            ink=True,
            expand=2,
        )

        mobile_status_text_row = ft.Row([
            self.status_banner,
            self.copy_error_button,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        mobile_status_box_row = ft.Row([
            self.version_indicator_container,
        ], alignment=ft.MainAxisAlignment.START, vertical_alignment=ft.CrossAxisAlignment.CENTER)

        status_container = ft.Container(
            content=ft.Column([
                mobile_status_text_row,
                mobile_status_box_row,
            ], spacing=4),
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.symmetric(horizontal=8, vertical=6),
            expand=8,
        )

        self.status_row = mobile_status_text_row

        top_row_1 = ft.Row(
            [load_button, status_container],
            spacing=8,
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        # Static Top Bar Row 2: Playback Controls & Trim (Left) + Render (Right)
        playback_controls = ft.Row([
            self._make_square_button("PLAY", lambda e: self.play(), accent_color=COLOR_ACCENT, fa_icon=FA_PLAY),
            self._make_square_button("PAUSE", lambda e: self.pause(), accent_color=COLOR_AMBER, fa_icon=FA_PAUSE),
            self._make_square_button("STOP", lambda e: self.stop(), accent_color=COLOR_RED, fa_icon=FA_STOP),
            self._make_square_button("REWIND", lambda e: self.seek(0.0), accent_color=COLOR_TEXT_DIM, fa_icon=FA_REWIND),
            self.trim_button,
            self.trim_mode_row,
        ], spacing=6, alignment=ft.MainAxisAlignment.START, wrap=True)

        render_controls = ft.Row([
            self._make_square_button(
                "PREVIEW",
                lambda e: self.render_and_play_preview(),
                accent_color=COLOR_CYAN,
                fa_icon=FA_MUSIC,
            ),
            self._make_square_button(
                "EXPORT",
                lambda e: self.show_export_format_dialog(),
                accent_color=COLOR_ACCENT,
                bg_color=COLOR_SURFACE,
                fa_icon=FA_EXPORT,
            ),
        ], spacing=6, alignment=ft.MainAxisAlignment.END)

        top_row_2 = ft.Row([playback_controls, render_controls], spacing=8, alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)

        static_top_bar = ft.Container(
            content=ft.Column([
                top_row_1,
                top_row_2,
            ], spacing=8),
            bgcolor=COLOR_SURFACE,
            border=ft.Border.all(width=1, color=COLOR_BORDER),
            border_radius=ft.BorderRadius.all(2),
            padding=ft.Padding.all(8),
        )

        # Dynamic Tab Bar Header (PEEK / EFFECTS)
        tab_header_row = ft.Row([
            ft.Container(content=self.tab_peek_btn, expand=True),
            ft.Container(content=self.tab_effects_btn, expand=True),
        ], spacing=6)

        # Tab 1: PEEK Waveform View
        waveform_header = ft.Row([
            self.track_info_text,
            ft.Row([
                self.peak_display_text,
                self.time_display_text,
            ], spacing=8),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True)

        self.mobile_waveform_view = self._make_card(
            "PEEK",
            ft.Column([
                waveform_header,
                self.waveform_gesture,
            ], spacing=6),
            badge=None,
        )

        # Tab 2: EFFECTS View
        mobile_presets_row = ft.Row([
            ft.Text("PRESETS:", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT_DIM, weight=ft.FontWeight.BOLD),
            self._make_square_button(
                "1. SLOWED+REV",
                lambda e: self.apply_preset(PRESET_SLOWED_REVERB),
                accent_color=COLOR_ACCENT,
            ),
            self._make_square_button(
                "2. NIGHTCORE",
                lambda e: self.apply_preset(PRESET_NIGHTCORE),
                accent_color=COLOR_CYAN,
            ),
            self._make_square_button(
                "RESET",
                lambda e: self.apply_preset(PRESET_DEFAULT),
                accent_color=COLOR_TEXT_DIM,
            ),
        ], spacing=6, wrap=True)

        effects_content = ft.Column([
            mobile_presets_row,
            ft.Divider(height=1, color=COLOR_BORDER),
            # Speed Control
            ft.Column([
                ft.Row([
                    ft.Text("TRACK SPEED (SLOW / FAST):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    self.speed_label,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.speed_slider,
            ], spacing=2),
            # Pitch Control
            ft.Column([
                ft.Row([
                    ft.Text("PITCH CONTROL:", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    self.pitch_label,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.pitch_slider,
                self.link_pitch_checkbox,
            ], spacing=2),
            # Reverb Slider
            ft.Column([
                ft.Row([
                    ft.Text("REVERB LEVEL (0 - 100%):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    self.reverb_label,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.reverb_slider,
            ], spacing=2),
            # Bass Boost Slider
            ft.Column([
                ft.Row([
                    ft.Text("BASS BOOST (0 - 100%):", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT),
                    self.bass_label,
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.bass_slider,
            ], spacing=2),
        ], spacing=8)

        self.mobile_effects_view = self._make_card(
            "EFFECTS",
            effects_content,
            badge=None,
        )

        # Animated Switcher for Dynamic Tab View
        self.mobile_tab_switcher = ft.AnimatedSwitcher(
            content=self.mobile_waveform_view if self.active_tab_index == 0 else self.mobile_effects_view,
            transition=ft.AnimatedSwitcherTransition.FADE,
            duration=200,
            reverse_duration=150,
        )

        return ft.Column([
            mobile_header,
            static_top_bar,
            tab_header_row,
            self.mobile_tab_switcher,
            ft.Container(height=16),
        ], spacing=10)

    def _set_button_accent(self, btn: Optional[ft.Container], color: str, bg_color: str):
        """Helper updating button borders, background, and text colors."""
        if not btn:
            return
        btn.border = ft.Border.all(width=1, color=color)
        btn.bgcolor = bg_color
        if isinstance(btn.content, ft.Text):
            btn.content.color = color
        elif isinstance(btn.content, ft.Row):
            for c in btn.content.controls:
                c.color = color

    def _switch_mobile_tab(self, index: int):
        """Switches active mobile tab between Waveform (0) and Effects (1)."""
        self.active_tab_index = index
        if self.tab_peek_btn is None or self.tab_effects_btn is None:
            return

        if index == 0:
            self._set_button_accent(self.tab_peek_btn, COLOR_ACCENT, COLOR_SURFACE_LIGHT)
            self._set_button_accent(self.tab_effects_btn, COLOR_TEXT_DIM, COLOR_SURFACE)
            if self.mobile_tab_switcher and self.mobile_waveform_view:
                self.mobile_tab_switcher.content = self.mobile_waveform_view
        else:
            self._set_button_accent(self.tab_peek_btn, COLOR_TEXT_DIM, COLOR_SURFACE)
            self._set_button_accent(self.tab_effects_btn, COLOR_ACCENT, COLOR_SURFACE_LIGHT)
            if self.mobile_tab_switcher and self.mobile_effects_view:
                self.mobile_tab_switcher.content = self.mobile_effects_view
        self.update_ui()

    def _on_save_completed(self, target_path: str):
        """Called when an exported file is saved via FileService."""
        if target_path.lower().endswith(".json"):
            self.set_status(f"DEBUG REPORT SAVED: '{os.path.basename(target_path)}'")
        else:
            self.set_status(f"EXPORT SAVED: '{os.path.basename(target_path)}'")
        self.update_ui()

    # --- File Loading & Analysis ---

    def _on_browse_clicked(self, e=None):
        """Opens file chooser to load an audio file (desktop native or mobile FilePicker)."""
        if hasattr(self, "file_service") and self.file_service:
            self.file_service.pick_audio_file()
        else:
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
            self._full_raw_samples = raw_samples
            self._full_sample_rate = sr
            self._full_waveform = self.waveform
            self._rendered_full_samples = raw_samples
            self._rendered_full_sr = sr
            self._rendered_full_waveform = self.waveform
            self._rendered_full_effects = AudioEffects(trim_start=0.0, trim_end=self.metadata.duration)
            self._current_track_samples = raw_samples
            self._current_track_sr = sr
            self._current_track_waveform = self.waveform
            self._trim_base_samples = raw_samples
            self._trim_base_sr = sr
            self._trim_base_waveform = self.waveform
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

    def _update_waveform_bars(self, playhead_ratio: float = 0.0):
        """Draws waveform bars with heights matching amplitude peaks and color matching playhead/trim."""
        peaks = self.waveform.peaks if self.waveform else None
        if not peaks:
            for bar in self.wave_bar_containers:
                if bar.height != 6:
                    bar.height = 6
                if bar.bgcolor != COLOR_WAVE_UNPLAYED:
                    bar.bgcolor = COLOR_WAVE_UNPLAYED
            return

        active_index = int(playhead_ratio * (len(self.wave_bar_containers) - 1))

        if self.trim_mode:
            dur = self._get_active_duration()
            if dur <= 0:
                dur = 1.0
            num_bars = len(self.wave_bar_containers)
            start_idx = int(max(0.0, min(1.0, self.trim_head_start_sec / dur)) * (num_bars - 1))
            end_idx = int(max(0.0, min(1.0, self.trim_head_end_sec / dur)) * (num_bars - 1))

            for i, bar in enumerate(self.wave_bar_containers):
                peak = peaks[i] if i < len(peaks) else 0.0
                expected_h = max(6, int(peak * 88))
                if bar.height != expected_h:
                    bar.height = expected_h

                if i < start_idx or i > end_idx:
                    # Outside trim selection: dimmed dark surface
                    expected_bg = COLOR_SURFACE_LIGHT
                elif i <= active_index:
                    # Inside trim selection & played: neon green
                    expected_bg = COLOR_WAVE_PLAYED
                else:
                    # Inside trim selection & unplayed: digital cyan
                    expected_bg = COLOR_CYAN

                if bar.bgcolor != expected_bg:
                    bar.bgcolor = expected_bg
        else:
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

    def _on_waveform_gesture(self, e, is_pan: bool = False):
        """Peeks/seeks in playback mode or moves trim heads in trim mode."""
        dur = self._get_active_duration()
        if dur <= 0:
            return

        local_x = self._extract_local_x(e)
        if local_x is None:
            return

        ratio = self._calculate_waveform_ratio(local_x)
        target_sec = ratio * dur

        if not self.trim_mode:
            self.seek(target_sec)
            return

        # --- In Trim Mode: Move or drag the active head ---
        if self._active_drag_head is None:
            dist_start = abs(target_sec - self.trim_head_start_sec)
            dist_end = abs(target_sec - self.trim_head_end_sec)
            if dist_start < dist_end:
                self._active_drag_head = "start"
            elif dist_end < dist_start:
                self._active_drag_head = "end"
            else:
                if target_sec <= self.trim_head_start_sec:
                    self._active_drag_head = "start"
                else:
                    self._active_drag_head = "end"

        # Boundary checks:
        # Start head cannot pass end head (start <= end)
        # End head cannot pass start head (end >= start)
        if self._active_drag_head == "start":
            self.trim_head_start_sec = max(0.0, min(self.trim_head_end_sec, target_sec))
        elif self._active_drag_head == "end":
            self.trim_head_end_sec = min(dur, max(self.trim_head_start_sec, target_sec))

        if not is_pan:
            # Single tap releases the active drag head immediately
            self._active_drag_head = None

        self._update_trim_heads_and_waveform()
        self._update_trim_ui()
        self.update_ui()

    def _on_waveform_tap_down(self, e):
        """Handles tap down on waveform."""
        self._on_waveform_gesture(e, is_pan=False)

    def _on_waveform_pan_start(self, e):
        """Handles pan start on waveform."""
        self._active_drag_head = None
        self._on_waveform_gesture(e, is_pan=True)

    def _on_waveform_pan_update(self, e):
        """Handles continuous pan drag on waveform."""
        self._on_waveform_gesture(e, is_pan=True)

    def _on_waveform_pan_end(self, e):
        """Releases drag head on pan end."""
        self._active_drag_head = None

    def _on_waveform_tap(self, e: ft.TapEvent):
        """Tap event handler delegating to gesture processor."""
        self._on_waveform_tap_down(e)

    def _on_waveform_pan(self, e: ft.DragUpdateEvent):
        """Pan/drag event handler delegating to gesture processor."""
        self._on_waveform_pan_update(e)

    def _update_trim_heads_and_waveform(self):
        """Positions trim marker heads and updates waveform styling."""
        if not self.trim_mode:
            self.trim_start_head.visible = False
            self.trim_end_head.visible = False
            return

        dur = self._get_active_duration()
        if dur <= 0:
            dur = 1.0

        ratio_start = max(0.0, min(1.0, self.trim_head_start_sec / dur))
        ratio_end = max(0.0, min(1.0, self.trim_head_end_sec / dur))

        head_w = 16.0
        track_w = self.total_bars_width - head_w
        self.trim_start_head.left = max(0.0, min(self.total_bars_width - head_w, ratio_start * track_w))
        self.trim_end_head.left = max(0.0, min(self.total_bars_width - head_w, ratio_end * track_w))
        self.trim_start_head.visible = True
        self.trim_end_head.visible = True

        # Refresh bar colors to highlight active trimmed region
        cur_t = self.player.get_current_time() if self.player else 0.0
        cur_ratio = cur_t / dur if dur > 0 else 0.0
        self._update_waveform_bars(playhead_ratio=cur_ratio)

        self.time_display_text.value = f"{self.trim_head_start_sec:04.1f}s - {self.trim_head_end_sec:04.1f}s / {dur:04.1f}s"

    def seek(self, seconds: float):
        """Seeks playback to specified timestamp and updates UI peeking info."""
        dur = self._get_active_duration()
        if dur <= 0:
            return

        if self.trim_mode:
            # Confine seek to within the active trim heads during trim preview
            target_time = max(self.trim_head_start_sec, min(self.trim_head_end_sec, seconds))
        else:
            target_time = max(0.0, min(dur, seconds))

        self.player.seek(target_time)

        ratio = target_time / dur
        self._update_waveform_bars(playhead_ratio=ratio)

        # Update peak reading and time badge
        peak_val = self.waveform.get_peak_at_time(target_time) if self.waveform else 0.0
        peak_db = self.waveform.get_peak_db_at_time(target_time) if self.waveform else "-inf"
        self.peak_display_text.value = f"PEAK: {peak_db} dB ({int(peak_val*100)}%)"

        cur_m = int(target_time // 60)
        cur_s = target_time % 60
        tot_m = int(dur // 60)
        tot_s = dur % 60
        if self.trim_mode:
            self.time_display_text.value = f"{target_time:04.1f}s / {self.trim_head_start_sec:04.1f}s - {self.trim_head_end_sec:04.1f}s"
        else:
            self.time_display_text.value = f"{cur_m:02d}:{cur_s:04.1f} / {tot_m:02d}:{tot_s:04.1f}"

        self.update_ui()

    # --- Transport & Playback Management ---

    def play(self):
        """Starts playback and launches the UI position tracking poller."""
        if not self.current_filepath:
            self.set_status("LOAD A TRACK BEFORE PLAYING", is_error=True)
            return

        if self.trim_mode:
            # Preview only between trim heads
            cur_t = self.player.get_current_time()
            if cur_t < self.trim_head_start_sec or cur_t >= self.trim_head_end_sec:
                self.seek(self.trim_head_start_sec)

        self.player.play()
        self.set_status("PLAYING PREVIEW..." if self.trim_mode else "PLAYING...")
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
        if self.trim_mode:
            self.seek(self.trim_head_start_sec)
        else:
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

        if self.trim_mode:
            # Stop preview playback when reaching the end trim head
            if cur_t >= self.trim_head_end_sec:
                self.pause()
                self.seek(self.trim_head_start_sec)
                self.set_status("TRIM PREVIEW COMPLETED")
                return

        tot_t = self._get_active_duration()
        if tot_t > 0:
            ratio = cur_t / tot_t
            self._update_waveform_bars(ratio)
            cur_m = int(cur_t // 60)
            cur_s = cur_t % 60
            tot_m = int(tot_t // 60)
            tot_s = tot_t % 60
            if self.trim_mode:
                new_time_str = f"{cur_t:04.1f}s / {self.trim_head_start_sec:04.1f}s - {self.trim_head_end_sec:04.1f}s"
            else:
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

        # Update displayed duration immediately when speed changes
        if not self.trim_mode:
            active_dur = self._get_active_trimmed_duration()
            tot_m = int(active_dur // 60)
            tot_s = active_dur % 60
            cur_t = self.player.get_current_time() if (self.player and self.player.is_playing()) else 0.0
            cur_m = int(cur_t // 60)
            cur_s = cur_t % 60
            self.time_display_text.value = f"{cur_m:02d}:{cur_s:04.1f} / {tot_m:02d}:{tot_s:04.1f}"

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

        if not self.trim_mode:
            active_dur = self._get_active_trimmed_duration()
            tot_m = int(active_dur // 60)
            tot_s = active_dur % 60
            cur_t = self.player.get_current_time() if (self.player and self.player.is_playing()) else 0.0
            cur_m = int(cur_t // 60)
            cur_s = cur_t % 60
            self.time_display_text.value = f"{cur_m:02d}:{cur_s:04.1f} / {tot_m:02d}:{tot_s:04.1f}"

        self.set_status(f"APPLIED PRESET: {preset.name}")
        self._update_version_indicator()
        self.update_ui()

    # --- Trimming & Time Space Mapping ---

    def _gui_sec_to_orig_sec(self, gui_sec: float) -> float:
        """Converts GUI seconds (at current playback speed) to original audio file seconds."""
        eff_speed = self.effects.speed if self.effects.speed > 0 else 1.0
        return max(0.0, gui_sec * eff_speed)

    def _orig_sec_to_gui_sec(self, orig_sec: float) -> float:
        """Converts original audio file seconds to GUI seconds (at current playback speed)."""
        eff_speed = self.effects.speed if self.effects.speed > 0 else 1.0
        return max(0.0, orig_sec / eff_speed)

    def _get_active_trimmed_duration(self) -> float:
        """Returns the active trimmed duration in GUI seconds at the current speed."""
        if not self.metadata or self.metadata.duration <= 0:
            return 0.0
        orig_start = max(0.0, self.effects.trim_start)
        orig_end = (
            min(self.metadata.duration, self.effects.trim_end)
            if self.effects.trim_end is not None and self.effects.trim_end > 0.0
            else self.metadata.duration
        )
        orig_trimmed_len = max(0.0, orig_end - orig_start)
        return self._orig_sec_to_gui_sec(orig_trimmed_len)

    def _effects_dsp_match(self, eff1: Optional[AudioEffects], eff2: Optional[AudioEffects]) -> bool:
        """Checks if two AudioEffects have identical DSP parameters (speed, pitch, reverb, bass), ignoring trim."""
        if eff1 is None or eff2 is None:
            return False
        return (
            abs(eff1.speed - eff2.speed) < 1e-4
            and abs(eff1.effective_pitch - eff2.effective_pitch) < 1e-4
            and abs(eff1.reverb_percent - eff2.reverb_percent) < 1e-2
            and abs(eff1.bass_boost_percent - eff2.bass_boost_percent) < 1e-2
        )

    def _is_default_dsp_effects(self, eff: Optional[AudioEffects]) -> bool:
        """Checks if DSP parameters (speed, pitch, reverb, bass) are at default values."""
        if eff is None:
            return True
        return (
            abs(eff.speed - 1.0) < 1e-4
            and abs(eff.effective_pitch - 1.0) < 1e-4
            and abs(eff.reverb_percent) < 1e-2
            and abs(eff.bass_boost_percent) < 1e-2
        )

    def _get_full_track_buffer(self) -> Tuple[np.ndarray, int, WaveformData]:
        """
        Returns (samples, sample_rate, waveform) for the entire track with active
        DSP effects (speed, pitch, reverb, bass) applied, across the full untrimmed file duration.
        """
        if self._is_default_dsp_effects(self.effects) and self._full_raw_samples is not None:
            return self._full_raw_samples, self._full_sample_rate, self._full_waveform

        if (
            self._rendered_full_samples is not None
            and self._rendered_full_effects is not None
            and self._effects_dsp_match(self.effects, self._rendered_full_effects)
        ):
            return self._rendered_full_samples, self._rendered_full_sr, self._rendered_full_waveform

        if self._trim_base_samples is not None and self._trim_base_waveform is not None:
            base_dur = len(self._trim_base_samples) / self._trim_base_sr
            expected_full_dur = self.metadata.duration / self.effects.speed if self.metadata else base_dur
            if abs(base_dur - expected_full_dur) < 0.05:
                return self._trim_base_samples, self._trim_base_sr, self._trim_base_waveform

        eff_full = AudioEffects(
            speed=self.effects.speed,
            pitch=self.effects.pitch,
            reverb_percent=self.effects.reverb_percent,
            bass_boost_percent=self.effects.bass_boost_percent,
            link_pitch_to_speed=self.effects.link_pitch_to_speed,
            trim_start=0.0,
            trim_end=self.metadata.duration if self.metadata else None,
        )
        samples, sr = self.engine.render_pcm_buffer(self.current_filepath, eff_full)
        dur = len(samples) / sr
        wf = self.engine.extract_waveform_from_samples(
            samples, sample_rate=sr, num_bins=self.num_wave_bars, duration=dur
        )
        self._rendered_full_samples = samples
        self._rendered_full_sr = sr
        self._rendered_full_waveform = wf
        self._rendered_full_effects = eff_full
        self._trim_base_samples = samples
        self._trim_base_sr = sr
        self._trim_base_waveform = wf
        return samples, sr, wf

    def enter_trim_mode(self):
        """Activates visual waveform trim mode, displaying the full track and preserving playhead position."""
        if not self.current_filepath or not self.metadata:
            self.set_status("LOAD A TRACK BEFORE TRIMMING", is_error=True)
            return

        cur_play_time = self.player.get_current_time() if self.player else 0.0
        if self.player and self.player.is_playing():
            self.pause()

        self.trim_mode = True

        full_samples, sr, full_wf = self._get_full_track_buffer()
        full_dur = len(full_samples) / sr if sr > 0 else (self.metadata.duration / self.effects.speed)

        self.waveform = full_wf
        self.player.load_buffer(full_samples, sr)
        self._trim_base_samples = full_samples
        self._trim_base_sr = sr
        self._trim_base_waveform = full_wf

        # Position trim heads in GUI time based on current original-space trim bounds
        gui_start = self._orig_sec_to_gui_sec(self.effects.trim_start)
        orig_end = self.effects.trim_end if self.effects.trim_end is not None else self.metadata.duration
        gui_end = self._orig_sec_to_gui_sec(orig_end)

        self.trim_head_start_sec = max(0.0, min(full_dur, gui_start))
        self.trim_head_end_sec = max(self.trim_head_start_sec, min(full_dur, gui_end))

        self.trim_button.visible = False
        self.trim_mode_row.visible = True

        # Seamlessly map playhead position
        target_time = max(0.0, min(full_dur, gui_start + cur_play_time))
        self.seek(target_time)

        self._update_trim_heads_and_waveform()
        self._update_trim_ui()
        self.set_status("TRIM MODE ACTIVE // DRAG HEADS TO SELECT RANGE")
        self.update_ui()

    def cancel_trim(self):
        """Exits trim mode without applying changes, keeping playback head where it was."""
        saved_trim_time = self.player.get_current_time() if self.player else 0.0
        if self.player and self.player.is_playing():
            self.pause()

        full_samples, sr, full_wf = self._get_full_track_buffer()
        full_dur = len(full_samples) / sr if sr > 0 else (self.metadata.duration / self.effects.speed)

        gui_start = self._orig_sec_to_gui_sec(self.effects.trim_start)
        orig_end = self.effects.trim_end if self.effects.trim_end is not None else self.metadata.duration
        gui_end = self._orig_sec_to_gui_sec(orig_end)

        self.trim_mode = False
        self._active_drag_head = None
        self.trim_head_start_sec = gui_start
        self.trim_head_end_sec = gui_end

        # Restore trimmed buffer
        start_idx = max(0, int(gui_start * sr))
        end_idx = min(len(full_samples), int(gui_end * sr))
        trimmed_samples = full_samples[start_idx:end_idx]
        trimmed_dur = len(trimmed_samples) / sr

        self.player.load_buffer(trimmed_samples, sr)
        self.waveform = self.engine.extract_waveform_from_samples(
            trimmed_samples,
            sample_rate=sr,
            num_bins=self.num_wave_bars,
            duration=trimmed_dur,
        )
        self._current_track_samples = trimmed_samples
        self._current_track_sr = sr
        self._current_track_waveform = self.waveform

        # Seamlessly map playback head: saved_trim_time was in full buffer,
        # so in trimmed buffer it is saved_trim_time - gui_start
        rel_pos = max(0.0, min(trimmed_dur, saved_trim_time - gui_start))
        self.seek(rel_pos)

        self.trim_button.visible = True
        self.trim_mode_row.visible = False
        self._update_trim_heads_and_waveform()
        self._update_trim_ui()
        self.set_status("TRIM CANCELLED")
        self.update_ui()

    def apply_trim(self):
        """Applies trim bounds and exits trim mode. If duration changed, moves playhead to start of new duration."""
        if not self.metadata:
            return
        if self.apply_trim_button.disabled or abs(self.trim_head_start_sec - self.trim_head_end_sec) < 1e-3:
            return

        dur_before = self._get_active_duration()
        saved_trim_time = self.player.get_current_time() if self.player else 0.0
        if self.player and self.player.is_playing():
            self.pause()

        # Save trim bounds in ORIGINAL FILE SECONDS
        orig_start = min(self.metadata.duration, self._gui_sec_to_orig_sec(self.trim_head_start_sec))
        orig_end = min(self.metadata.duration, self._gui_sec_to_orig_sec(self.trim_head_end_sec))
        self.effects.trim_start = orig_start
        self.effects.trim_end = orig_end
        self.trim_start_field.value = f"{orig_start:.2f}"
        self.trim_end_field.value = f"{orig_end:.2f}"

        trimmed_dur = max(0.0, self.trim_head_end_sec - self.trim_head_start_sec)

        full_samples, sr, full_wf = self._get_full_track_buffer()
        if full_samples is not None and len(full_samples) > 0:
            start_idx = max(0, int(self.trim_head_start_sec * sr))
            end_idx = min(len(full_samples), int(self.trim_head_end_sec * sr))
            trimmed_samples = full_samples[start_idx:end_idx]

            self.player.load_buffer(trimmed_samples, sr)
            self.waveform = self.engine.extract_waveform_from_samples(
                trimmed_samples,
                sample_rate=sr,
                num_bins=self.num_wave_bars,
                duration=trimmed_dur,
            )
            self._current_track_samples = trimmed_samples
            self._current_track_sr = sr
            self._current_track_waveform = self.waveform

        self.trim_mode = False
        self._active_drag_head = None
        self.trim_button.visible = True
        self.trim_mode_row.visible = False

        duration_changed = abs(trimmed_dur - dur_before) > 1e-2
        if duration_changed:
            self.player.seek(0.0)
            self._update_waveform_bars(playhead_ratio=0.0)
            tot_m = int(trimmed_dur // 60)
            tot_s = trimmed_dur % 60
            self.time_display_text.value = f"00:00.0 / {tot_m:02d}:{tot_s:04.1f}"
        else:
            rel_time = max(0.0, min(trimmed_dur, saved_trim_time - self.trim_head_start_sec))
            self.seek(rel_time)

        self._update_trim_heads_and_waveform()
        self._update_trim_ui()

        if self.waveform and self.waveform.peaks:
            cur_pos = self.player.get_current_time() if self.player else 0.0
            peak_val = self.waveform.get_peak_at_time(cur_pos)
            peak_db = self.waveform.get_peak_db_at_time(cur_pos)
            self.peak_display_text.value = f"PEAK: {peak_db} dB ({int(peak_val * 100)}%)"

        self.set_status(f"TRIM APPLIED: {trimmed_dur:.2f}s (RANGE: {self.effects.trim_start:.2f}s - {self.effects.trim_end:.2f}s)")
        self._update_version_indicator()
        self.update_ui()

    def _update_trim_ui(self):
        """Updates apply button state and warning notice based on trim heads."""
        if not self.trim_mode:
            self.trim_notice_text.visible = False
            return

        is_equal = abs(self.trim_head_start_sec - self.trim_head_end_sec) < 1e-3
        if is_equal:
            self.apply_trim_button.disabled = True
            self.apply_trim_button.opacity = 0.4
            self.trim_notice_text.visible = True
        else:
            self.apply_trim_button.disabled = False
            self.apply_trim_button.opacity = 1.0
            self.trim_notice_text.visible = False

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
                # Render full track with active DSP effects (speed, pitch, reverb, bass)
                full_samples, sr, full_wf = self._get_full_track_buffer()

                # Slice to active trimmed region in GUI seconds
                gui_start = self._orig_sec_to_gui_sec(self.effects.trim_start)
                orig_end = self.effects.trim_end if self.effects.trim_end is not None else self.metadata.duration
                gui_end = self._orig_sec_to_gui_sec(orig_end)
                start_idx = max(0, int(gui_start * sr))
                end_idx = min(len(full_samples), int(gui_end * sr))
                samples = full_samples[start_idx:end_idx]
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
                self._current_track_samples = samples
                self._current_track_sr = sr
                self._current_track_waveform = self.waveform
                self._trim_base_samples = full_samples
                self._trim_base_sr = sr
                self._trim_base_waveform = full_wf
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

    def _open_dialog(self, dlg: ft.AlertDialog):
        """Displays an alert dialog safely across Flet versions (Flet 1.0+ show_dialog, Flet 0.23+ open, legacy)."""
        if not self.page:
            return
        if hasattr(self.page, "show_dialog"):
            try:
                self.page.show_dialog(dlg)
                return
            except Exception:
                pass
        if hasattr(self.page, "open"):
            try:
                self.page.open(dlg)
                return
            except Exception:
                pass
        try:
            self.page.dialog = dlg
            dlg.open = True
            self.page.update()
        except Exception:
            pass

    def _close_dialog(self, dlg: Optional[ft.AlertDialog] = None):
        """Dismisses the open dialog safely across Flet versions."""
        if not self.page:
            return
        if hasattr(self.page, "pop_dialog"):
            try:
                self.page.pop_dialog()
                return
            except Exception:
                pass
        if hasattr(self.page, "close") and dlg:
            try:
                self.page.close(dlg)
                return
            except Exception:
                pass
        try:
            if hasattr(self.page, "dialog") and self.page.dialog:
                self.page.dialog.open = False
            if dlg:
                dlg.open = False
            self.page.update()
        except Exception:
            pass

    def show_export_format_dialog(self):
        """Displays cyber modal dialog prompting user to select export format on mobile."""
        if not self.current_filepath or not self.metadata:
            self.set_status("PLEASE LOAD AN AUDIO FILE BEFORE EXPORTING", is_error=True)
            return

        def _select_and_export(fmt: str):
            self._close_dialog(dlg)
            self.export_format = fmt
            self.export_processed_track(export_format=fmt)

        def _cancel(e):
            self._close_dialog(dlg)

        dlg = ft.AlertDialog(
            title=ft.Text("EXPORT AUDIO TRACK", font_family=ROBOTIC_FONT, size=13, weight=ft.FontWeight.BOLD, color=COLOR_ACCENT),
            content=ft.Column([
                ft.Text("SELECT OUTPUT AUDIO FORMAT:", font_family=ROBOTIC_FONT, size=11, color=COLOR_TEXT_DIM),
                ft.Container(height=6),
                self._make_square_button(
                    "1. OPUS (160 KBPS HIGH EFFICIENCY)",
                    lambda e: _select_and_export("opus"),
                    accent_color=COLOR_CYAN,
                    bg_color=COLOR_SURFACE_LIGHT,
                ),
                self._make_square_button(
                    "2. MP3 (192 KBPS UNIVERSAL)",
                    lambda e: _select_and_export("mp3"),
                    accent_color=COLOR_ACCENT,
                    bg_color=COLOR_SURFACE_LIGHT,
                ),
            ], spacing=8, tight=True),
            actions=[
                self._make_square_button("CANCEL", _cancel, accent_color=COLOR_TEXT_DIM, bg_color=COLOR_SURFACE),
            ],
            bgcolor=COLOR_SURFACE,
            shape=ft.RoundedRectangleBorder(radius=2),
        )

        self._open_dialog(dlg)

    def export_processed_track(
        self,
        custom_output_path: Optional[str] = None,
        export_format: Optional[str] = None,
    ) -> Optional[str]:
        """
        Exports the track with current effects, speed, pitch, reverb, and trimming.
        Returns the output path on success.
        """
        if not self.current_filepath or not self.metadata:
            self.set_status("PLEASE LOAD AN AUDIO FILE BEFORE EXPORTING", is_error=True)
            return None

        from slowverb.platform import is_mobile_environment
        is_mobile = getattr(self, "force_mobile_ui", False) or is_mobile_environment(self.page)

        # Determine target output path
        ext = (export_format or self.export_format).lower()
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
            default_filename = f"{os.path.basename(base)}_{tag}.{ext}"

            if is_mobile:
                import tempfile
                custom_output_path = os.path.join(tempfile.gettempdir(), default_filename)
            else:
                custom_output_path = f"{base}_{tag}.{ext}"
        else:
            default_filename = os.path.basename(custom_output_path)

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

            if is_mobile and hasattr(self, "file_service") and self.file_service:
                self.file_service.save_exported_file(out_file, default_filename)

            return out_file
        except Exception as ex:
            self.set_status(f"EXPORT ERROR: {str(ex)}", is_error=True)
            self.update_ui()
            return None

    def _format_status_message(self, message: str, is_error: bool = False) -> tuple[str, int]:
        """
        Formats status text for the active viewport.
        On mobile:
          - Target maximum of 3 lines.
          - Decreases font size by up to 4px (from 12 down to 8) to fit within 3 lines.
          - If text still exceeds 3 lines at minimum size 8, truncates with '...'.
        On desktop:
          - Returns full text at default size 12.
        """
        full_text = f">> {message.upper()}"
        from slowverb.platform import is_mobile_environment
        is_mobile = getattr(self, "force_mobile_ui", False) or is_mobile_environment(self.page)

        if not is_mobile:
            return full_text, 12

        # Mobile top row text constraints
        base_size = 12
        min_size = 8  # 12 - 4px maximum reduction
        available_width = 200.0 if is_error else 275.0

        def estimate_lines(text: str, font_size: int) -> int:
            chars_per_line = max(10, int(available_width / (0.6 * font_size)))
            lines = 0
            for part in text.split("\n"):
                if not part:
                    lines += 1
                else:
                    lines += max(1, (len(part) + chars_per_line - 1) // chars_per_line)
            return lines

        # 1. Try fitting within 3 lines by reducing font size by up to 4px
        for sz in range(base_size, min_size - 1, -1):
            if estimate_lines(full_text, sz) <= 3:
                return full_text, sz

        # 2. If 4px reduction is not enough, truncate at min_size (8px) with '...'
        chars_per_line = max(10, int(available_width / (0.6 * min_size)))
        max_chars = chars_per_line * 3
        if len(full_text) > max_chars:
            truncated = full_text[: max_chars - 3].rstrip() + "..."
            return truncated, min_size

        return full_text, min_size

    def set_status(self, message: str, is_error: bool = False):
        """Updates the status footer banner and toggles copy error button."""
        if getattr(self, "_diagnostic_logger", None):
            if is_error:
                self._diagnostic_logger.log_error(message)
            else:
                self._diagnostic_logger.log(message)
        elif getattr(self, "debug_mode", False):
            from slowverb.debug import DiagnosticLogger
            logger = DiagnosticLogger.get_instance()
            if is_error:
                logger.log_error(message)
            else:
                logger.log(message)

        from slowverb.platform import is_mobile_environment
        is_mobile = getattr(self, "force_mobile_ui", False) or is_mobile_environment(self.page)
        text_val, font_sz = self._format_status_message(message, is_error=is_error)

        if hasattr(self, "status_banner") and self.status_banner:
            self.status_banner.value = text_val
            self.status_banner.size = font_sz
            self.status_banner.color = COLOR_RED if is_error else COLOR_ACCENT
            if is_mobile:
                self.status_banner.max_lines = 3
                self.status_banner.overflow = ft.TextOverflow.ELLIPSIS
            else:
                self.status_banner.max_lines = None
                self.status_banner.overflow = None

        if hasattr(self, "copy_error_button") and self.copy_error_button:
            if is_error:
                self._last_error = message
                self.copy_error_button.visible = True
                if hasattr(self, "status_error_row") and self.status_error_row:
                    self.status_error_row.visible = True
                self._set_copy_button_feedback(copied=False)
            else:
                self._last_error = None
                self.copy_error_button.visible = False
                if hasattr(self, "status_error_row") and self.status_error_row:
                    self.status_error_row.visible = False

        self.update_ui()

    def _set_copy_button_feedback(self, status: Any = "normal", copied: Optional[bool] = None):
        """Sets the copy error button visuals between standard ('normal'), confirmation ('success'), and failure ('error')."""
        if copied is not None:
            status = copied
        if status is True or status == "success":
            text = "COPIED!"
            icon = FA_CHECK
            color = COLOR_ACCENT
        elif status == "error":
            text = "ERROR COPYING"
            icon = FA_WARNING
            color = COLOR_RED
        else:
            text = "COPY"
            icon = FA_COPY
            color = COLOR_RED

        if hasattr(self, "copy_error_btn_text") and self.copy_error_btn_text:
            self.copy_error_btn_text.value = text
            self.copy_error_btn_text.color = color
        if hasattr(self, "copy_error_btn_icon") and self.copy_error_btn_icon:
            self.copy_error_btn_icon.value = icon
            self.copy_error_btn_icon.color = color
        if hasattr(self, "copy_error_button") and self.copy_error_button:
            self.copy_error_button.border = ft.Border.all(width=1, color=color)

    def _on_copy_error_clicked(self):
        """Copies the active error message to the system clipboard and displays confirmation or error feedback."""
        text = self._last_error
        if not text and hasattr(self, "status_banner") and self.status_banner:
            val = self.status_banner.value or ""
            text = val[3:] if val.startswith(">> ") else val
        if not text:
            return

        success = copy_to_clipboard(text, page=getattr(self, "page", None))
        self._copy_feedback_token += 1
        current_token = self._copy_feedback_token

        if success:
            self._set_copy_button_feedback("success")
        else:
            self._set_copy_button_feedback("error")
        self.update_ui()

        def revert():
            time.sleep(2.0)
            if self._copy_feedback_token == current_token and self._last_error:
                self._set_copy_button_feedback("normal")
                self.update_ui()

        threading.Thread(target=revert, daemon=True).start()

    def _on_debug_dump_clicked(self):
        """Generates a comprehensive diagnostics JSON report and prompts user to save it."""
        try:
            from slowverb.debug import generate_debug_dump
            dump_data = generate_debug_dump(self)
            json_str = json.dumps(dump_data, indent=2, default=str)
            default_filename = "sloverb_debug_dump.json"

            from slowverb.platform import is_mobile_platform
            if not is_mobile_platform(self.page):
                save_path = save_file_desktop(initial_filename=default_filename, ext="json")
                if save_path:
                    with open(save_path, "w", encoding="utf-8") as f:
                        f.write(json_str)
                    self.set_status(f"DEBUG REPORT SAVED: '{os.path.basename(save_path)}'")
                    if hasattr(self, "ffmpeg_setup_view") and self.ffmpeg_setup_view and hasattr(self.ffmpeg_setup_view, "detail_label"):
                        self.ffmpeg_setup_view.detail_label.value = f">> DEBUG REPORT SAVED: '{os.path.basename(save_path)}'"
                        self.ffmpeg_setup_view.detail_label.color = COLOR_ACCENT
                        self.ffmpeg_setup_view._safe_update()
                    if getattr(self, "_diagnostic_logger", None):
                        self._diagnostic_logger.log(f"Debug report saved to {save_path}")
            else:
                import tempfile
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, default_filename)
                with open(temp_path, "w", encoding="utf-8") as f:
                    f.write(json_str)

                if hasattr(self, "file_service") and self.file_service:
                    self.file_service.save_exported_file(
                        temp_exported_path=temp_path,
                        default_filename=default_filename,
                        allowed_extensions=["json"],
                        dialog_title="SAVE DEBUG REPORT",
                    )
                else:
                    self.set_status(f"DEBUG REPORT SAVED: '{temp_path}'")
        except Exception as ex:
            self.set_status(f"DEBUG DUMP FAILED: {str(ex).upper()}", is_error=True)
            if hasattr(self, "ffmpeg_setup_view") and self.ffmpeg_setup_view and hasattr(self.ffmpeg_setup_view, "detail_label"):
                self.ffmpeg_setup_view.detail_label.value = f">> DEBUG DUMP FAILED: {str(ex).upper()}"
                self.ffmpeg_setup_view.detail_label.color = COLOR_RED
                self.ffmpeg_setup_view._safe_update()
            if getattr(self, "_diagnostic_logger", None):
                self._diagnostic_logger.log_error(f"Debug dump failed: {ex}", exc=ex)

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
        self._copy_feedback_token += 1
        if self.player:
            self.player.close()
