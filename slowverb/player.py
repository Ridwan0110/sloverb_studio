"""Audio player providing real-time playback, pausing, and seeking via sounddevice."""

import threading
from typing import Callable, Optional
import numpy as np
import sounddevice as sd


class AudioPlayer:
    """Real-time audio player using sounddevice OutputStream."""

    def __init__(self, on_playback_finished: Optional[Callable[[], None]] = None):
        self._data: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._position: int = 0
        self._playing: bool = False
        self._lock = threading.Lock()
        self._stream: Optional[sd.OutputStream] = None
        self._on_playback_finished = on_playback_finished
        self._finished_notified = False

    def load_buffer(self, data: np.ndarray, sample_rate: int = 44100):
        """Loads a stereo or mono float32 numpy array into the player buffer."""
        self.stop()
        with self._lock:
            # Ensure float32 and 2D
            if data.dtype != np.float32:
                data = data.astype(np.float32)
            if data.ndim == 1:
                data = np.column_stack((data, data))
            self._data = data
            self._sample_rate = sample_rate
            self._position = 0
            self._finished_notified = False

    def _ensure_stream(self):
        """Initializes or reconfigures the sounddevice OutputStream."""
        if self._stream is not None and self._stream.active:
            return

        if self._data is None or len(self._data) == 0:
            return

        channels = self._data.shape[1] if self._data.ndim > 1 else 1
        try:
            if self._stream is not None:
                try:
                    self._stream.close()
                except Exception:
                    pass
            self._stream = sd.OutputStream(
                samplerate=self._sample_rate,
                channels=channels,
                dtype="float32",
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            # Fallback if specific sample rate / channels fails
            print(f"Warning: Failed to open audio stream: {e}")

    def _audio_callback(self, outdata, frames, time_info, status):
        """Low-latency audio streaming callback."""
        with self._lock:
            if not self._playing or self._data is None or len(self._data) == 0:
                outdata.fill(0)
                return

            total_len = len(self._data)
            if self._position >= total_len:
                outdata.fill(0)
                self._playing = False
                if not self._finished_notified:
                    self._finished_notified = True
                    if self._on_playback_finished:
                        threading.Thread(target=self._on_playback_finished, daemon=True).start()
                return

            remaining = total_len - self._position
            chunk_size = min(frames, remaining)
            chunk = self._data[self._position : self._position + chunk_size]

            outdata[:chunk_size] = chunk
            if chunk_size < frames:
                outdata[chunk_size:].fill(0)
                self._playing = False
                if not self._finished_notified:
                    self._finished_notified = True
                    if self._on_playback_finished:
                        threading.Thread(target=self._on_playback_finished, daemon=True).start()

            self._position += chunk_size

    def play(self):
        """Starts or resumes playback."""
        with self._lock:
            if self._data is None or len(self._data) == 0:
                return
            if self._position >= len(self._data):
                self._position = 0
            self._playing = True
            self._finished_notified = False

        if self._stream is None or not self._stream.active:
            self._ensure_stream()

    def pause(self):
        """Pauses playback while keeping playhead position."""
        with self._lock:
            self._playing = False

    def stop(self):
        """Stops playback and resets playhead to start."""
        with self._lock:
            self._playing = False
            self._position = 0
            self._finished_notified = False
        if self._stream is not None and self._stream.active:
            try:
                self._stream.stop()
            except Exception:
                pass

    def seek(self, seconds: float):
        """Seeks to a specific timestamp in seconds."""
        with self._lock:
            if self._data is None or self._sample_rate <= 0:
                return
            target_frame = int(seconds * self._sample_rate)
            self._position = max(0, min(len(self._data), target_frame))
            self._finished_notified = False

    def seek_ratio(self, ratio: float):
        """Seeks by normalized ratio (0.0 - 1.0)."""
        duration = self.get_duration()
        self.seek(ratio * duration)

    def get_current_time(self) -> float:
        """Returns the current playback timestamp in seconds."""
        with self._lock:
            if self._sample_rate <= 0:
                return 0.0
            return self._position / self._sample_rate

    def get_duration(self) -> float:
        """Returns total duration of loaded buffer in seconds."""
        with self._lock:
            if self._data is None or self._sample_rate <= 0:
                return 0.0
            return len(self._data) / self._sample_rate

    def is_playing(self) -> bool:
        """Returns True if audio is actively playing."""
        with self._lock:
            return self._playing

    def close(self):
        """Closes the audio stream and releases resources."""
        self.stop()
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None
