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
EXPORT_FORMATS = ["opus", "mp3"]
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
