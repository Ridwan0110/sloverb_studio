"""Tests for AudioPlayer, buffer loading, seeking, and playback state."""

import numpy as np
import pytest
from slowverb.player import AudioPlayer


def test_player_initial_state():
    """Verify player starts stopped with zero position and duration."""
    player = AudioPlayer()
    assert player.is_playing() is False
    assert player.get_current_time() == 0.0
    assert player.get_duration() == 0.0
    player.close()


def test_player_load_buffer_and_duration():
    """Verify loading audio buffer calculates correct duration."""
    player = AudioPlayer()
    sr = 44100
    # 2 seconds of silence / dummy audio
    data = np.zeros((sr * 2, 2), dtype=np.float32)
    player.load_buffer(data, sample_rate=sr)

    assert player.get_duration() == 2.0
    assert player.get_current_time() == 0.0
    player.close()


def test_player_seek():
    """Verify seeking adjusts current playback timestamp."""
    player = AudioPlayer()
    sr = 44100
    data = np.zeros((sr * 5, 2), dtype=np.float32)
    player.load_buffer(data, sample_rate=sr)

    player.seek(2.5)
    assert abs(player.get_current_time() - 2.5) < 0.01

    # Seek beyond duration clamps to end
    player.seek(10.0)
    assert abs(player.get_current_time() - 5.0) < 0.01

    # Seek negative clamps to 0
    player.seek(-2.0)
    assert player.get_current_time() == 0.0

    # Seek ratio
    player.seek_ratio(0.5)
    assert abs(player.get_current_time() - 2.5) < 0.01

    player.close()


def test_player_play_pause_stop():
    """Verify state transitions between play, pause, and stop."""
    player = AudioPlayer()
    sr = 44100
    data = np.zeros((sr * 2, 2), dtype=np.float32)
    player.load_buffer(data, sample_rate=sr)

    player.play()
    assert player.is_playing() is True

    player.pause()
    assert player.is_playing() is False

    player.seek(1.0)
    assert abs(player.get_current_time() - 1.0) < 0.01

    player.stop()
    assert player.is_playing() is False
    assert player.get_current_time() == 0.0

    player.close()
