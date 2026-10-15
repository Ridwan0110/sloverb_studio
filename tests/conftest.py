"""Pytest test fixtures and test audio generation helpers."""

import os
import subprocess
import tempfile
import pytest
import numpy as np

from slowverb.config import get_ffmpeg_path
from slowverb.engine import AudioEngine
from slowverb.ui import SlowVerbApp


@pytest.fixture(scope="session")
def ffmpeg_bin():
    """Path to valid FFmpeg binary."""
    path = get_ffmpeg_path()
    assert os.path.isfile(path), f"FFmpeg not found at {path}"
    return path


@pytest.fixture(scope="session")
def sample_sine_audio(tmp_path_factory, ffmpeg_bin):
    """
    Creates a temporary 3-second stereo 44.1kHz sine wave audio file (sine.opus)
    for fast and deterministic audio testing.
    """
    tmp_dir = tmp_path_factory.mktemp("audio_test")
    file_path = os.path.join(tmp_dir, "test_sine.opus")

    cmd = [
        ffmpeg_bin, "-y",
        "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
        "-c:a", "libopus", "-b:a", "128k",
        file_path
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert res.returncode == 0, f"Failed to create test audio: {res.stderr.decode()}"
    assert os.path.isfile(file_path)
    return file_path


@pytest.fixture
def engine(ffmpeg_bin):
    """Initialized AudioEngine instance."""
    return AudioEngine(ffmpeg_bin)


@pytest.fixture
def app():
    """Initialized SlowVerbApp instance in headless mode."""
    application = SlowVerbApp()
    yield application
    application.close()
