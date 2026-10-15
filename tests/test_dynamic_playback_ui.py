"""Tests for dynamic UI updates, async playback poller, and event-loop thread marshaling."""

import asyncio
import threading
from unittest.mock import MagicMock, patch
import pytest
import numpy as np

from slowverb.config import PRESET_SLOWED_REVERB
from slowverb.ui import SlowVerbApp


class DummyEventLoopPage:
    """Mock Flet page with simulated event loop and task runner."""

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self.loop = loop
        self.update_count = 0
        self.run_task_calls = []
        self.window = MagicMock()
        self.controls = []

    def update(self):
        self.update_count += 1

    def run_task(self, handler, *args, **kwargs):
        self.run_task_calls.append((handler, args, kwargs))
        return asyncio.run_coroutine_threadsafe(handler(*args, **kwargs), self.loop)


@pytest.mark.anyio
async def test_update_ui_threadsafe_marshaling():
    """Verify that update_ui marshals to loop.call_soon_threadsafe when called from an external thread."""
    loop = asyncio.get_running_loop()
    page = DummyEventLoopPage(loop)
    app = SlowVerbApp()
    app.page = page

    # 1. Calling update_ui from within the running loop thread should call update immediately
    initial_updates = page.update_count
    app.update_ui()
    assert page.update_count == initial_updates + 1

    # 2. Calling update_ui from a background worker thread
    def worker():
        app.update_ui()

    t = threading.Thread(target=worker)
    t.start()
    t.join()

    # Yield control to the event loop to let call_soon_threadsafe callback execute
    await asyncio.sleep(0.05)
    assert page.update_count == initial_updates + 2

    app.close()


@pytest.mark.anyio
async def test_async_playback_poller_dynamic_updates(sample_sine_audio):
    """Verify that async playback poller runs on the page loop and dynamically updates time, waveform, and peak text."""
    loop = asyncio.get_running_loop()
    page = DummyEventLoopPage(loop)
    app = SlowVerbApp()
    app.page = page
    app.load_file(sample_sine_audio)

    # Start playback
    app.play()
    assert len(page.run_task_calls) == 1
    assert app._playback_poll_active is True

    # Advance time to allow poller ticks
    await asyncio.sleep(0.15)

    # Verify that playback poller updated time and waveform
    assert app.time_display_text.value != "00:00.0 / 00:00.0"
    assert "PEAK:" in app.peak_display_text.value
    assert page.update_count > 0

    # Pause playback and verify poller stops
    app.pause()
    assert app._playback_poll_active is False
    assert "PAUSED" in app.status_banner.value

    app.close()


@pytest.mark.anyio
async def test_preview_effects_dynamic_ui_flush(sample_sine_audio):
    """Verify that background render thread dynamically flushes status, version indicator, and waveform without manual interaction."""
    loop = asyncio.get_running_loop()
    page = DummyEventLoopPage(loop)
    app = SlowVerbApp()
    app.page = page
    app.load_file(sample_sine_audio)

    app.apply_preset(PRESET_SLOWED_REVERB)
    assert "OLD MODIFIED VERSION" in app.version_indicator_text.value

    mock_samples = np.sin(2 * np.pi * 220 * np.linspace(0, 2.0, 2 * 44100)).astype(np.float32)
    mock_stereo = np.column_stack((mock_samples, mock_samples))

    with patch.object(app.engine, "render_pcm_buffer", return_value=(mock_stereo, 44100)):
        app.render_and_play_preview()

        # Allow background_render thread to finish and marshal update to event loop
        for _ in range(20):
            await asyncio.sleep(0.05)
            if "PLAYING PREVIEW" in app.status_banner.value:
                break

        assert "PLAYING PREVIEW" in app.status_banner.value
        assert "CURRENT MODIFIED VERSION" in app.version_indicator_text.value
        assert app.is_playing_current_modified_version() is True
        assert "/ 00:02.0" in app.time_display_text.value
        assert app._playback_poll_active is True

    app.stop()
    assert "STOPPED" in app.status_banner.value
    app.close()
