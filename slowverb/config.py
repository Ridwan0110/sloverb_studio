"""Configuration, constants, theme colors, and presets for SlowVerb Studio."""

from dataclasses import dataclass
import os
import shutil
from typing import Optional

# Audio constraints and defaults
MIN_SPEED = 0.5
MAX_SPEED = 1.5
DEFAULT_SPEED = 1.0

MIN_PITCH = 0.5
MAX_PITCH = 1.5
DEFAULT_PITCH = 1.0

MIN_REVERB = 0.0
MAX_REVERB = 100.0
DEFAULT_REVERB = 0.0

MIN_BASS = 0.0
MAX_BASS = 100.0
DEFAULT_BASS = 0.0

# Supported export formats
EXPORT_FORMATS = ["opus", "mp3", "m4a", "wav"]
DEFAULT_EXPORT_FORMAT = "opus"

# Application branding
APP_NAME = "SloVerb Studio"

# Robotic / square theme colors & typography
ROBOTIC_FONT = "Consolas"
FONT_AWESOME_FONT = "FontAwesome"

COLOR_BG = "#0D0E12"
COLOR_SURFACE = "#151821"
COLOR_SURFACE_LIGHT = "#1C202C"
COLOR_BORDER = "#2C3242"
COLOR_TEXT = "#ECEFF4"
COLOR_TEXT_DIM = "#7B849B"
COLOR_ACCENT = "#00FFA3"       # Neon terminal green
COLOR_CYAN = "#00D2FF"         # Digital cyan
COLOR_AMBER = "#FFB800"        # Warning / alert amber
COLOR_RED = "#FF4B4B"          # Error / stop red
COLOR_WAVE_UNPLAYED = "#2C3446"
COLOR_WAVE_PLAYED = "#00FFA3"

# FontAwesome Free Solid Unicode codepoints (no emojis)
FA_PLAY = "\uf04b"
FA_PAUSE = "\uf04c"
FA_STOP = "\uf04d"
FA_REWIND = "\uf04a"
FA_FOLDER_OPEN = "\uf07c"
FA_BOLT = "\uf0e7"
FA_EXPORT = "\uf019"
FA_MAGIC = "\uf0d0"
FA_CHECK = "\uf00c"
FA_WARNING = "\uf071"
FA_MUSIC = "\uf001"
FA_UNDO = "\uf0e2"
FA_SLIDERS = "\uf1de"
FA_SCISSORS = "\uf0c4"
FA_COPY = "\uf0c5"
FA_BUG = "\uf188"



@dataclass
class Preset:
    name: str
    speed: float
    reverb: float
    pitch: Optional[float] = None
    link_pitch_to_speed: bool = True
    bass_boost: float = 0.0

# Official Presets
PRESET_SLOWED_REVERB = Preset(
    name="SLOWED + REVERB",
    speed=0.8,
    reverb=40.0,
    pitch=0.8,
    link_pitch_to_speed=True,
    bass_boost=15.0,  # Subtle warm low-end enhancement typical for slowed+reverb
)

PRESET_NIGHTCORE = Preset(
    name="NIGHTCORE",
    speed=1.2,
    reverb=0.0,
    pitch=1.2,
    link_pitch_to_speed=True,
    bass_boost=0.0,
)

PRESET_DEFAULT = Preset(
    name="DEFAULT",
    speed=1.0,
    reverb=0.0,
    pitch=1.0,
    link_pitch_to_speed=True,
    bass_boost=0.0,
)


def get_ffmpeg_path(ensure: bool = False, interactive: bool = True) -> str:
    """
    Locates the FFmpeg binary in the OS system PATH or project directory.
    Prioritizes OS-wide system installation, then local ./ffmpeg/ binary.
    If not found and ensure=True, prompts the user to download it automatically.
    """
    from slowverb.ffmpeg_manager import find_ffmpeg, prompt_and_ensure_ffmpeg, get_project_root

    found = find_ffmpeg()
    if found:
        return found

    if ensure:
        return prompt_and_ensure_ffmpeg(interactive=interactive)

    # Return default expected local path if not yet downloaded
    project_root = get_project_root()
    exe_name = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    return os.path.abspath(os.path.join(project_root, "ffmpeg", exe_name))


def get_subprocess_no_window_kwargs() -> dict:
    """
    Returns platform-specific subprocess creation flags and startupinfo to prevent
    console/terminal windows from flashing or popping up when running GUI applications
    on Windows (e.g. PyInstaller packaged windowed binaries or pythonw).
    """
    kwargs = {}
    if os.name == "nt":
        import subprocess
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
        if hasattr(subprocess, "STARTUPINFO"):
            si = subprocess.STARTUPINFO()
            if hasattr(subprocess, "STARTF_USESHOWWINDOW"):
                si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            if hasattr(subprocess, "SW_HIDE"):
                si.wShowWindow = subprocess.SW_HIDE
            kwargs["startupinfo"] = si
    return kwargs


def get_app_icon_path(size: str = "256x") -> Optional[str]:
    """
    Locates the application icon file (.ico / .png) across the source tree,
    assets directory, and PyInstaller frozen bundle.
    Checks sizes in order of preference (requested size, 256x, 128x, 64x, 32x, 16x).
    """
    import sys
    base_dirs = []
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        base_dirs.append(os.path.join(sys._MEIPASS, "assets"))
        base_dirs.append(sys._MEIPASS)

    from slowverb.ffmpeg_manager import get_project_root
    try:
        project_root = get_project_root()
    except Exception:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.abspath(os.path.join(current_dir, ".."))

    base_dirs.append(os.path.join(project_root, "assets"))
    base_dirs.append(project_root)

    size_order = [size] if size else []
    for s in ["256x", "128x", "64x", "32x", "16x"]:
        if s not in size_order:
            size_order.append(s)

    candidates = []
    for base in base_dirs:
        for sub in ["image", "images", ""]:
            for s in size_order:
                candidates.append(os.path.join(base, sub, f"SloVerb Studio Icon-{s}.ico"))
            candidates.append(os.path.join(base, sub, "icon.ico"))
            candidates.append(os.path.join(base, sub, "icon.png"))

    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.abspath(c)

    return None

