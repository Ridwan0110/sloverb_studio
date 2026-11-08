"""
Mobile audio player implementation using flet-audio for SloVerb Studio.

Provides audio playback via Flutter audioplayers by writing in-memory buffers
to a fast temporary WAV cache and binding to flet_audio.Audio.
"""

import asyncio
import os
import tempfile
import threading
from typing import Callable, Optional
import wave
import numpy as np

try:
    import flet as ft
    import flet_audio as fta
except ImportError:
    ft = None
    fta = None

from slowverb.player.base import BaseAudioPlayer


class FletAudioPlayer(BaseAudioPlayer):
    """Audio player using flet-audio (Flutter audioplayers) for mobile playback."""

    def __init__(
        self,
        page: Optional[ft.Page] = None,
        on_playback_finished: Optional[Callable[[], None]] = None,
    ):
        self.page = page
        self._on_playback_finished = on_playback_finished
        self._data: Optional[np.ndarray] = None
        self._sample_rate: int = 44100
        self._duration: float = 0.0
        self._position: float = 0.0
        self._playing: bool = False
        self._lock = threading.Lock()
        self._temp_wav_path: Optional[str] = None
        self._audio: Optional[fta.Audio] = None

        if fta is not None:
            self._audio = fta.Audio(
                autoplay=False,
                volume=1.0,
                on_position_change=self._on_position_change,
                on_state_change=self._on_state_change,
                on_duration_change=self._on_duration_change,
            )
            if self.page is not None and hasattr(self.page, "overlay"):
                self.page.overlay.append(self._audio)
                try:
                    self.page.update()
                except Exception:
                    pass

    def _dispatch_async(self, coro_fn, *args):
        """Dispatches an async coroutine on the Flet page event loop or closes it safely."""
        if self.page is not None and hasattr(self.page, "run_task"):
            try:
                self.page.run_task(coro_fn, *args)
                return
            except Exception:
                pass
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(coro_fn(*args), loop)
                return
            else:
                loop.run_until_complete(coro_fn(*args))
                return
        except Exception:
            pass

        # If loop is not running or in test mock environment, safely close coroutine
        try:
            coro = coro_fn(*args)
            coro.close()
        except Exception:
            pass

    def attach_page(self, page: ft.Page):
        """Attaches the audio player to a Flet page overlay."""
        self.page = page
        if self._audio is not None and hasattr(self.page, "overlay"):
            if self._audio not in self.page.overlay:
                self.page.overlay.append(self._audio)
                try:
                    self.page.update()
                except Exception:
                    pass

    def _write_temp_wav(self, data: np.ndarray, sample_rate: int) -> str:
        """Writes numpy float32 buffer to a temporary 16-bit PCM WAV file."""
        if self._temp_wav_path and os.path.isfile(self._temp_wav_path):
            try:
                os.remove(self._temp_wav_path)
            except Exception:
                pass

        fd, temp_path = tempfile.mkstemp(prefix="sloverb_preview_", suffix=".wav")
        os.close(fd)

        channels = data.shape[1] if data.ndim > 1 else 1
        # Convert float32 [-1.0, 1.0] to int16
        int16_samples = np.clip(data * 32767.0, -32768, 32767).astype(np.int16)

        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(channels)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(sample_rate)
            wf.writeframes(int16_samples.tobytes())

        self._temp_wav_path = temp_path
        return temp_path

    def load_buffer(self, data: np.ndarray, sample_rate: int = 44100):
        """Loads a float32 numpy audio buffer, writes temp WAV cache, and binds to flet-audio."""
        self.stop()
        with self._lock:
            if data.dtype != np.float32:
                data = data.astype(np.float32)
            if data.ndim == 1:
                data = np.column_stack((data, data))
            self._data = data
            self._sample_rate = sample_rate
            self._duration = len(data) / sample_rate if sample_rate > 0 else 0.0
            self._position = 0.0

            wav_path = self._write_temp_wav(data, sample_rate)

            if self._audio is not None:
                self._audio.src = wav_path
                if self.page is not None:
                    try:
                        self._audio.update()
                    except Exception:
                        pass

    def load_file(self, filepath: str, duration: Optional[float] = None):
        """Directly points player to an existing audio file."""
        self.stop()
        with self._lock:
            self._data = None
            if self._audio is not None:
                self._audio.src = filepath
                if duration is not None:
                    self._duration = duration
                if self.page is not None:
                    try:
                        self._audio.update()
                    except Exception:
                        pass

    def play(self):
        """Starts or resumes playback."""
        with self._lock:
            if self._duration <= 0.0:
                return
            if self._position >= self._duration:
                self._position = 0.0
            self._playing = True

        if self._audio is not None:
            self._dispatch_async(self._audio.play)

    def pause(self):
        """Pauses playback while maintaining playhead position."""
        with self._lock:
            self._playing = False
        if self._audio is not None:
            self._dispatch_async(self._audio.pause)

    def stop(self):
        """Stops playback and rewinds to beginning."""
        with self._lock:
            self._playing = False
            self._position = 0.0
        if self._audio is not None:
            self._dispatch_async(self._audio_stop_async)

    async def _audio_stop_async(self):
        if self._audio is not None:
            try:
                await self._audio.pause()
                await self._audio.seek(0)
            except Exception:
                pass

    def seek(self, seconds: float):
        """Seeks to timestamp in seconds."""
        with self._lock:
            clamped = max(0.0, min(self._duration, seconds))
            self._position = clamped
        if self._audio is not None:
            # flet-audio seek takes milliseconds
            self._dispatch_async(self._audio.seek, int(clamped * 1000))

    def seek_ratio(self, ratio: float):
        """Seeks by normalized ratio (0.0 to 1.0)."""
        duration = self.get_duration()
        self.seek(ratio * duration)

    def get_current_time(self) -> float:
        """Returns the current playback position in seconds."""
        with self._lock:
            return self._position

    def get_duration(self) -> float:
        """Returns total duration in seconds."""
        with self._lock:
            return self._duration

    def is_playing(self) -> bool:
        """Returns True if audio is actively playing."""
        with self._lock:
            return self._playing

    def get_buffer(self) -> Optional[np.ndarray]:
        """Returns the currently loaded numpy array buffer."""
        return self._data

    def get_sample_rate(self) -> int:
        """Returns the sample rate of the loaded buffer."""
        return self._sample_rate

    def _on_position_change(self, e):
        """Callback from flet-audio position tick."""
        if hasattr(e, "position") and e.position is not None:
            with self._lock:
                self._position = e.position / 1000.0

    def _on_duration_change(self, e):
        """Callback from flet-audio duration detection."""
        if hasattr(e, "duration") and e.duration is not None and e.duration > 0:
            with self._lock:
                self._duration = e.duration / 1000.0

    def _on_state_change(self, e):
        """Callback from flet-audio state transition."""
        state_str = str(getattr(e, "state", "")).lower()
        if "completed" in state_str:
            with self._lock:
                self._playing = False
                self._position = self._duration
            if self._on_playback_finished:
                threading.Thread(target=self._on_playback_finished, daemon=True).start()

    def close(self):
        """Closes the audio player and releases temporary files."""
        self.stop()
        if self._audio is not None:
            self._dispatch_async(self._audio.release)
            if self.page is not None and hasattr(self.page, "overlay"):
                try:
                    self.page.overlay.remove(self._audio)
                except Exception:
                    pass
            self._audio = None

        if self._temp_wav_path and os.path.isfile(self._temp_wav_path):
            try:
                os.remove(self._temp_wav_path)
            except Exception:
                pass
            self._temp_wav_path = None
