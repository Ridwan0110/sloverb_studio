"""Tests for AudioEngine, metadata extraction, filter generation, and audio exporting."""

import os
import pytest
from slowverb.engine import AudioEffects, AudioEngine


def test_probe_metadata(engine, sample_sine_audio):
    """Test extracting metadata from an audio file."""
    meta = engine.probe_file(sample_sine_audio)
    assert meta.filepath == os.path.abspath(sample_sine_audio)
    assert meta.filename == os.path.basename(sample_sine_audio)
    assert meta.duration > 2.8  # ~3 seconds
    assert meta.sample_rate > 0
    assert meta.format_name in ["opus", "ogg"]
    assert meta.formatted_duration.startswith("00:03") or meta.formatted_duration.startswith("00:02")


def test_extract_waveform(engine, sample_sine_audio):
    """Test waveform downsampling and normalized peak extraction."""
    waveform = engine.extract_waveform(sample_sine_audio, num_bins=50)
    assert len(waveform.peaks) == 50
    assert all(0.0 <= p <= 1.0 for p in waveform.peaks)
    assert waveform.duration > 0.0
    assert waveform.max_peak_db > -40.0

    # Test peak lookup at time
    p1 = waveform.get_peak_at_time(1.0)
    assert 0.0 <= p1 <= 1.0
    db = waveform.get_peak_db_at_time(1.0)
    assert isinstance(db, float)


def test_build_filter_default_bypass(engine):
    """Unity settings (speed 1.0, pitch 1.0, reverb 0, bass 0) produce empty or bypass filter."""
    fx = AudioEffects(speed=1.0, pitch=1.0, link_pitch_to_speed=True, reverb_percent=0.0, bass_boost_percent=0.0)
    af = engine.build_audio_filter_string(fx)
    assert af == ""


def test_build_filter_speed_and_linked_pitch(engine):
    """Speed change with linked pitch generates matching tempo and pitch in rubberband."""
    fx = AudioEffects(speed=0.8, pitch=0.8, link_pitch_to_speed=True)
    af = engine.build_audio_filter_string(fx)
    assert "rubberband=tempo=0.8000:pitch=0.8000" in af


def test_build_filter_independent_pitch(engine):
    """Independent pitch (speed 0.8, pitch 1.2) uses separate tempo and pitch values."""
    fx = AudioEffects(speed=0.8, pitch=1.2, link_pitch_to_speed=False)
    af = engine.build_audio_filter_string(fx)
    assert "rubberband=tempo=0.8000:pitch=1.2000" in af


def test_build_filter_reverb_and_bass(engine):
    """Reverb and bass boost generate aecho, bass filter, and alimiter."""
    fx = AudioEffects(speed=1.0, reverb_percent=40.0, bass_boost_percent=25.0)
    af = engine.build_audio_filter_string(fx)
    assert "aecho=" in af
    assert "bass=" in af
    assert "alimiter=limit=0.98" in af


def test_export_opus(engine, sample_sine_audio, tmp_path):
    """Test exporting audio to Opus format."""
    out_file = str(tmp_path / "output_test.opus")
    fx = AudioEffects(speed=0.8, reverb_percent=40.0)
    path, size = engine.export_audio(sample_sine_audio, out_file, fx, export_format="opus")

    assert os.path.isfile(path)
    assert size > 0
    # Probe exported file
    meta = engine.probe_file(path)
    # At 0.8x speed, 3s file should become ~3 / 0.8 = ~3.75s
    assert meta.duration > 3.2


def test_export_mp3(engine, sample_sine_audio, tmp_path):
    """Test exporting audio to MP3 format."""
    out_file = str(tmp_path / "output_test.mp3")
    fx = AudioEffects(speed=1.2, reverb_percent=0.0)
    path, size = engine.export_audio(sample_sine_audio, out_file, fx, export_format="mp3")

    assert os.path.isfile(path)
    assert size > 0
    meta = engine.probe_file(path)
    # At 1.2x speed, 3s file should become ~3 / 1.2 = ~2.5s
    assert 2.0 < meta.duration < 3.0


def test_render_pcm_buffer(engine, sample_sine_audio):
    """Test rendering processed audio into memory as float32 stereo array."""
    fx = AudioEffects(speed=1.0)
    samples, sr = engine.render_pcm_buffer(sample_sine_audio, fx, target_sample_rate=44100, max_duration_seconds=1.0)
    assert samples.ndim == 2
    assert samples.shape[1] == 2
    assert samples.dtype == "float32"
    assert sr == 44100
    assert len(samples) > 0
