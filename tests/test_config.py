"""Tests for configuration, presets, and path resolution."""

import os
from slowverb.config import (
    DEFAULT_BASS,
    DEFAULT_PITCH,
    DEFAULT_REVERB,
    DEFAULT_SPEED,
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
    get_ffmpeg_path,
)


def test_ffmpeg_path_resolution():
    """Verify that FFmpeg binary is located and is an executable file."""
    path = get_ffmpeg_path()
    assert os.path.isabs(path)
    assert os.path.isfile(path)
    assert path.lower().endswith("ffmpeg.exe") or path.lower().endswith("ffmpeg")


def test_parameter_bounds():
    """Verify standard bounds for speed, pitch, reverb, and bass."""
    assert MIN_SPEED == 0.5
    assert MAX_SPEED == 1.5
    assert DEFAULT_SPEED == 1.0

    assert MIN_PITCH == 0.5
    assert MAX_PITCH == 1.5
    assert DEFAULT_PITCH == 1.0

    assert MIN_REVERB == 0.0
    assert MAX_REVERB == 100.0
    assert DEFAULT_REVERB == 0.0

    assert MIN_BASS == 0.0
    assert MAX_BASS == 100.0
    assert DEFAULT_BASS == 0.0


def test_preset_slowed_reverb_values():
    """Verify required values for Slowed+Reverb preset (speed 0.8x, reverb 40%)."""
    assert PRESET_SLOWED_REVERB.speed == 0.8
    assert PRESET_SLOWED_REVERB.reverb == 40.0
    assert PRESET_SLOWED_REVERB.link_pitch_to_speed is True
    assert PRESET_SLOWED_REVERB.pitch == 0.8


def test_preset_nightcore_values():
    """Verify required values for Nightcore preset (speed 1.2x, reverb 0%)."""
    assert PRESET_NIGHTCORE.speed == 1.2
    assert PRESET_NIGHTCORE.reverb == 0.0
    assert PRESET_NIGHTCORE.link_pitch_to_speed is True
    assert PRESET_NIGHTCORE.pitch == 1.2


def test_preset_default_values():
    """Verify default reset preset."""
    assert PRESET_DEFAULT.speed == 1.0
    assert PRESET_DEFAULT.reverb == 0.0
    assert PRESET_DEFAULT.pitch == 1.0
    assert PRESET_DEFAULT.bass_boost == 0.0


def test_package_version():
    """Verify package version is defined as single source of truth and follows semver."""
    import re
    import slowverb

    assert hasattr(slowverb, "__version__")
    assert isinstance(slowverb.__version__, str)
    assert re.match(r"^\d+\.\d+\.\d+", slowverb.__version__)

