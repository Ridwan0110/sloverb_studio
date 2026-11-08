"""
Abstract Base Audio Player interface for SloVerb Studio.

Defines the contract for real-time audio playback backends
(e.g., sounddevice for desktop, flet-audio for mobile).
"""

from abc import ABC, abstractmethod
from typing import Optional
import numpy as np


class BaseAudioPlayer(ABC):
    """Abstract interface for audio playback."""

    @abstractmethod
    def load_buffer(self, data: np.ndarray, sample_rate: int = 44100):
        """Loads a stereo or mono float32 numpy array into the player buffer."""
        pass

    @abstractmethod
    def play(self):
        """Starts or resumes audio playback."""
        pass

    @abstractmethod
    def pause(self):
        """Pauses audio playback while maintaining the playhead position."""
        pass

    @abstractmethod
    def stop(self):
        """Stops audio playback and resets the playhead to the beginning."""
        pass

    @abstractmethod
    def seek(self, seconds: float):
        """Seeks to a specific timestamp in seconds."""
        pass

    @abstractmethod
    def seek_ratio(self, ratio: float):
        """Seeks by normalized ratio (0.0 to 1.0)."""
        pass

    @abstractmethod
    def get_current_time(self) -> float:
        """Returns the current playback position in seconds."""
        pass

    @abstractmethod
    def get_duration(self) -> float:
        """Returns the total duration of the loaded audio in seconds."""
        pass

    @abstractmethod
    def is_playing(self) -> bool:
        """Returns True if audio is actively playing."""
        pass

    @abstractmethod
    def close(self):
        """Releases all audio resources, streams, and temporary caches."""
        pass

    def get_buffer(self) -> Optional[np.ndarray]:
        """Optional inspection of currently loaded raw sample buffer."""
        return None

    def get_sample_rate(self) -> int:
        """Returns the sample rate of the loaded audio."""
        return 44100
