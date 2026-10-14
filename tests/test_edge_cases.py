"""Tests for common edge cases, invalid inputs, boundary conditions, and error recovery."""

import os
import pytest
from slowverb.engine import AudioEffects, AudioEngine


def test_missing_input_file(engine):
    """Probing, extracting waveform, or exporting a non-existent file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        engine.probe_file("non_existent_file.opus")

    with pytest.raises(FileNotFoundError):
        engine.extract_waveform("non_existent_file.opus")

    with pytest.raises(FileNotFoundError):
        engine.export_audio("non_existent_file.opus", "out.opus", AudioEffects())


def test_invalid_unsupported_export_format(engine, sample_sine_audio, tmp_path):
    """Requesting an unsupported export format raises ValueError."""
    out_file = str(tmp_path / "out.avi")
    with pytest.raises(ValueError, match="Unsupported export format"):
        engine.export_audio(sample_sine_audio, out_file, AudioEffects(), export_format="avi")


def test_effect_parameter_clamping():
    """Verify that values outside legal boundaries are safely clamped."""
    # Speed below 0.5 clamped to 0.5, above 1.5 clamped to 1.5
    fx_low = AudioEffects(speed=0.1, pitch=0.2, reverb_percent=-50, bass_boost_percent=-20)
    assert fx_low.speed == 0.5
    assert fx_low.pitch == 0.5
    assert fx_low.reverb_percent == 0.0
    assert fx_low.bass_boost_percent == 0.0

    fx_high = AudioEffects(speed=9.9, pitch=8.8, reverb_percent=250, bass_boost_percent=300)
    assert fx_high.speed == 1.5
    assert fx_high.pitch == 1.5
    assert fx_high.reverb_percent == 100.0
    assert fx_high.bass_boost_percent == 100.0


def test_trimming_edge_cases(engine, sample_sine_audio, tmp_path):
    """Test boundary trimming cases: micro-trim, inverted trim range, negative trim."""
    # 1. Negative trim_start is clamped to 0.0
    fx_neg = AudioEffects(trim_start=-10.0)
    assert fx_neg.trim_start == 0.0

    # 2. Inverted trim_end < trim_start is adjusted
    fx_inv = AudioEffects(trim_start=2.0, trim_end=1.0)
    assert fx_inv.trim_end >= fx_inv.trim_start

    # 3. Micro-trim (0.2s duration) exports without crashing
    fx_micro = AudioEffects(trim_start=0.5, trim_end=0.7)
    out_micro = str(tmp_path / "micro.opus")
    path, size = engine.export_audio(sample_sine_audio, out_micro, fx_micro)
    assert os.path.isfile(path)
    assert size > 0


def test_paths_with_spaces_and_special_characters(engine, sample_sine_audio, tmp_path):
    """Test handling filenames with spaces, parentheses, brackets, and symbols."""
    tricky_filename = "cool track (slowed + reverb) [2026] #1.opus"
    out_file = str(tmp_path / tricky_filename)

    fx = AudioEffects(speed=0.8, reverb_percent=40.0)
    path, size = engine.export_audio(sample_sine_audio, out_file, fx)

    assert os.path.isfile(path)
    assert size > 0
    # Probe file with tricky path
    meta = engine.probe_file(path)
    assert meta.filename == tricky_filename


def test_corrupt_file_handling(engine, tmp_path):
    """Corrupt or non-audio file raises an informative error during probing or extraction."""
    corrupt_file = str(tmp_path / "corrupt.opus")
    with open(corrupt_file, "wb") as f:
        f.write(b"NOT_A_VALID_AUDIO_FILE_JUST_RANDOM_GARBAGE_BYTES")

    # Waveform extraction on corrupt file should fail gracefully with RuntimeError
    with pytest.raises(RuntimeError):
        engine.extract_waveform(corrupt_file)
