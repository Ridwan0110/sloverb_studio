"""
Audio player package providing desktop and mobile playback backends.

Exports:
- BaseAudioPlayer: Abstract interface
- SoundDevicePlayer: Low-latency PCM streaming player for desktop
- FletAudioPlayer: Flutter audioplayers backend for mobile
- AudioPlayer: Alias to SoundDevicePlayer for full backward compatibility
- create_audio_player: Factory resolving backend based on runtime platform
"""

from typing import Callable, Optional
import flet as ft

from slowverb.player.base import BaseAudioPlayer
from slowverb.player.sounddevice_player import SoundDevicePlayer
from slowverb.player.flet_audio_player import FletAudioPlayer

# Alias for full backward compatibility with desktop test suite and modules
AudioPlayer = SoundDevicePlayer


def create_audio_player(
    page: Optional[ft.Page] = None,
    on_playback_finished: Optional[Callable[[], None]] = None,
) -> BaseAudioPlayer:
    """
    Factory creating the optimal AudioPlayer backend for the current platform:
    - On Mobile (Android/iOS): FletAudioPlayer (flet-audio)
    - On Desktop (Windows/macOS/Linux): SoundDevicePlayer (sounddevice)
    """
    import os
    from slowverb.platform import is_mobile_platform

    if is_mobile_platform(page) or os.environ.get("FORCE_FLET_AUDIO") in ("1", "true", "True"):
        try:
            return FletAudioPlayer(page=page, on_playback_finished=on_playback_finished)
        except Exception as e:
            print(f"Warning: FletAudioPlayer init failed, falling back to SoundDevicePlayer: {e}")

    return SoundDevicePlayer(on_playback_finished=on_playback_finished)


__all__ = [
    "BaseAudioPlayer",
    "SoundDevicePlayer",
    "FletAudioPlayer",
    "AudioPlayer",
    "create_audio_player",
]
