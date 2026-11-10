import unittest.mock
"""
Tests for PyAV-powered audio processing backend and mobile provider resolution.
"""

import os
import pytest
import numpy as np

from slowverb.engine import AudioEffects, AudioEngine
from slowverb.ffmpeg.android_provider import AndroidFFmpegProvider


def test_android_provider_resolves_pyav(monkeypatch):
    """Verify Android provider falls back to 'pyav' when native libffmpeg.so is absent."""
    provider = AndroidFFmpegProvider(package_name="com.redu.sloverb.test.nonexistent")
    # Provider should find pyav since av is installed
    binary_path = provider.get_binary_path()
    assert binary_path == "pyav"
    assert provider.is_available() is True
    assert provider.get_platform_name() == "android"


def test_pyav_engine_initialization():
    """Verify AudioEngine can be initialized explicitly with 'pyav'."""
    engine = AudioEngine(ffmpeg_path="pyav")
    assert engine.use_pyav is True
    assert engine.ffmpeg_path == "pyav"


def test_pyav_engine_probe_file(sample_sine_audio):
    """Verify probe_file works accurately using PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    meta = engine.probe_file(sample_sine_audio)

    assert meta.duration > 2.5
    assert meta.sample_rate in (44100, 48000)
    assert meta.channels in (1, 2)
    assert meta.filename.endswith(".opus")


def test_pyav_engine_extract_waveform(sample_sine_audio):
    """Verify waveform extraction produces normalized peaks via PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    waveform = engine.extract_waveform(sample_sine_audio, num_bins=90)

    assert len(waveform.peaks) == 90
    assert all(0.0 <= p <= 1.0 for p in waveform.peaks)
    assert waveform.max_peak_db > -40.0


def test_pyav_engine_render_pcm_buffer(sample_sine_audio):
    """Verify real-time buffer rendering produces stereo float32 buffer via PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(
        speed=0.85,
        reverb_percent=40.0,
        bass_boost_percent=30.0,
    )

    buffer, sr = engine.render_pcm_buffer(sample_sine_audio, effects, target_sample_rate=44100)

    assert isinstance(buffer, np.ndarray)
    assert buffer.dtype == np.float32
    assert buffer.ndim == 2
    assert buffer.shape[1] == 2
    assert buffer.shape[0] > 0
    assert sr == 44100


def test_pyav_engine_render_pcm_buffer_trimming(sample_sine_audio):
    """Verify trimmed rendering slices audio accurately in PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(
        speed=1.0,
        trim_start=0.5,
        trim_end=2.0,
    )

    buffer, sr = engine.render_pcm_buffer(sample_sine_audio, effects, target_sample_rate=44100)

    # 1.5 seconds at 44100 Hz = ~66150 samples
    duration = buffer.shape[0] / sr
    assert abs(duration - 1.5) < 0.3


def test_pyav_engine_export_mp3(sample_sine_audio, tmp_path):
    """Verify exporting audio to MP3 using PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(speed=0.8, reverb_percent=30.0)
    out_path = str(tmp_path / "pyav_output.mp3")

    path, size = engine.export_audio(sample_sine_audio, out_path, effects, export_format="mp3")

    assert os.path.isfile(path)
    assert size > 0
    meta = engine.probe_file(path)
    assert meta.duration > 0.0


def test_pyav_engine_export_opus(sample_sine_audio, tmp_path):
    """Verify exporting audio to Opus using PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(speed=1.2, bass_boost_percent=25.0)
    out_path = str(tmp_path / "pyav_output.opus")

    path, size = engine.export_audio(sample_sine_audio, out_path, effects, export_format="opus")

    assert os.path.isfile(path)
    assert size > 0
    meta = engine.probe_file(path)
    assert meta.duration > 0.0


def test_pyav_engine_export_wav(sample_sine_audio, tmp_path):
    """Verify exporting audio to WAV using PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(speed=1.0)
    out_path = str(tmp_path / "pyav_output.wav")

    path, size = engine.export_audio(sample_sine_audio, out_path, effects, export_format="wav")

    assert os.path.isfile(path)
    assert size > 0
    meta = engine.probe_file(path)
    assert meta.duration > 0.0


def test_pyav_engine_export_m4a(sample_sine_audio, tmp_path):
    """Verify exporting audio to M4A (AAC) using PyAV."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(speed=1.0)
    out_path = str(tmp_path / "pyav_output.m4a")

    path, size = engine.export_audio(sample_sine_audio, out_path, effects, export_format="m4a")

    assert os.path.isfile(path)
    assert size > 0
    meta = engine.probe_file(path)
    assert meta.duration > 0.0


def test_pyav_has_filter():
    """Verify has_filter queries PyAV available filters correctly."""
    engine = AudioEngine(ffmpeg_path="pyav")
    assert engine.has_filter("bass") is True
    assert engine.has_filter("aecho") is True
    assert engine.has_filter("alimiter") is True
    assert engine.has_filter("rubberband") is False
    assert engine.has_filter("nonexistent_fake_filter_xyz") is False

def test_pyav_resolve_audio_encoder():
    """Verify fallback from external encoders to native encoders and detection of missing codecs."""
    import av
    engine = AudioEngine(ffmpeg_path="pyav")

    # Native resolution on desktop returns available encoder
    assert engine._resolve_audio_encoder("opus") in ("libopus", "opus")
    assert engine._resolve_audio_encoder("mp3") in ("libmp3lame", "mp3")
    assert engine._resolve_audio_encoder("wav") == "pcm_s16le"
    assert engine._resolve_audio_encoder("m4a") in ("aac", "libfdk_aac")

    # Simulate mobile environment where libmp3lame and libopus are absent
    real_codec = av.Codec
    def mock_codec(name, mode='r'):
        if name in ("libopus", "libmp3lame"):
            raise av.error.CodecNotFoundError(f"Codec {name} not found")
        return real_codec(name, mode)

    import unittest.mock as mock
    with mock.patch("av.Codec", side_effect=mock_codec):
        assert engine._resolve_audio_encoder("opus") == "opus"
        assert engine.is_encoder_available("mp3") is False
        with pytest.raises(RuntimeError, match="MP3 encoding"):
            engine._resolve_audio_encoder("mp3")


def test_pyav_engine_export_native_codecs(sample_sine_audio, tmp_path):
    """Verify exporting audio works with native 'opus' and 'aac' encoders directly."""
    engine = AudioEngine(ffmpeg_path="pyav")
    effects = AudioEffects(speed=1.0)

    # Force native 'opus' encoder with strict options
    with unittest.mock.patch.object(engine, "_resolve_audio_encoder", return_value="opus"):
        out_opus = str(tmp_path / "native_output.opus")
        path, size = engine.export_audio(sample_sine_audio, out_opus, effects, export_format="opus")
        assert os.path.isfile(path)
        assert size > 0

    # Force native 'aac' encoder
    with unittest.mock.patch.object(engine, "_resolve_audio_encoder", return_value="aac"):
        out_m4a = str(tmp_path / "native_output.m4a")
        path, size = engine.export_audio(sample_sine_audio, out_m4a, effects, export_format="m4a")
        assert os.path.isfile(path)
        assert size > 0

    # Verify descriptive error when MP3 encoder is absent
    import av
    def mock_codec(name, mode='r'):
        if name in ("libmp3lame", "mp3"):
            raise av.error.CodecNotFoundError(f"Codec {name} not found")
        return av.Codec(name, mode)

    with unittest.mock.patch("av.Codec", side_effect=mock_codec):
        out_mp3 = str(tmp_path / "fail_output.mp3")
        with pytest.raises(RuntimeError, match="MP3 encoding"):
            engine.export_audio(sample_sine_audio, out_mp3, effects, export_format="mp3")

