"""Tests for AudioPlayer abstraction and FletAudioPlayer backend."""

import os
from unittest.mock import MagicMock, patch
import numpy as np
import pytest
import flet as ft

from slowverb.player import (
    AudioPlayer,
    BaseAudioPlayer,
    FletAudioPlayer,
    SoundDevicePlayer,
    create_audio_player,
)


def test_audio_player_alias():
    assert AudioPlayer is SoundDevicePlayer
    player = AudioPlayer()
    assert isinstance(player, BaseAudioPlayer)
    player.close()


def test_create_audio_player_desktop():
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    page.width = 1120
    player = create_audio_player(page)
    assert isinstance(player, SoundDevicePlayer)
    player.close()


def test_create_audio_player_mobile():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []
    player = create_audio_player(page)
    assert isinstance(player, FletAudioPlayer)
    assert len(page.overlay) == 0
    assert len(page.services) == 1
    assert player._audio in page.services
    player.close()


def test_flet_audio_player_load_buffer_and_seek():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    player = FletAudioPlayer(page=page)
    sr = 44100
    # 3 seconds of stereo audio
    data = np.zeros((sr * 3, 2), dtype=np.float32)
    player.load_buffer(data, sample_rate=sr)

    assert player.get_duration() == 3.0
    assert player.get_current_time() == 0.0
    assert player.is_playing() is False

    # Check temp WAV file was created
    assert player._temp_wav_path is not None
    assert os.path.isfile(player._temp_wav_path)

    # Seek
    player.seek(1.5)
    assert abs(player.get_current_time() - 1.5) < 0.01

    # Seek ratio
    player.seek_ratio(0.5)
    assert abs(player.get_current_time() - 1.5) < 0.01

    # Play & Pause
    player.play()
    assert player.is_playing() is True

    player.pause()
    assert player.is_playing() is False

    # Stop resets position
    player.stop()
    assert player.is_playing() is False
    assert player.get_current_time() == 0.0

    # Cleanup
    temp_path = player._temp_wav_path
    player.close()
    assert not os.path.isfile(temp_path)


def test_flet_audio_player_callbacks():
    finished_called = []
    def on_finished():
        finished_called.append(True)

    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    player = FletAudioPlayer(page=page, on_playback_finished=on_finished)
    sr = 44100
    data = np.zeros((sr * 2, 2), dtype=np.float32)
    player.load_buffer(data, sample_rate=sr)
    player.play()

    # Simulate position change event (1200ms -> 1.2s)
    pos_event = MagicMock()
    pos_event.position = 1200
    player._on_position_change(pos_event)
    assert abs(player.get_current_time() - 1.2) < 0.01

    # Simulate state completed event
    state_event = MagicMock()
    state_event.state = "completed"
    player._on_state_change(state_event)

    import time
    time.sleep(0.1)
    assert len(finished_called) == 1
    assert player.is_playing() is False
    assert player.get_current_time() == 2.0

    player.close()
