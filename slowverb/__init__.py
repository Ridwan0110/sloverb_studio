"""SlowVerb Studio audio package."""

from slowverb.config import (
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

__all__ = [
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
]
