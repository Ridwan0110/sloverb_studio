"""SlowVerb Studio audio package."""

__version__ = "0.1.0"

from slowverb.config import (
    APP_NAME,
    PRESET_DEFAULT,
    PRESET_NIGHTCORE,
    PRESET_SLOWED_REVERB,
    Preset,
    get_ffmpeg_path,
)
from slowverb.engine import (
    AudioEffects,
    AudioEngine,
    AudioMetadata,
    WaveformData,
)
from slowverb.player import AudioPlayer
from slowverb.ui import FFmpegSetupView, SlowVerbApp

__all__ = [
    "__version__",
    "APP_NAME",
    "AudioEngine",
    "AudioPlayer",
    "AudioEffects",
    "AudioMetadata",
    "WaveformData",
    "Preset",
    "PRESET_SLOWED_REVERB",
    "PRESET_NIGHTCORE",
    "PRESET_DEFAULT",
    "get_ffmpeg_path",
    "FFmpegSetupView",
    "SlowVerbApp",
]
