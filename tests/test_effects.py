"""Tests for audio effects, pitch linking, presets, and audio trimming."""

import os
from slowverb.config import PRESET_NIGHTCORE, PRESET_SLOWED_REVERB
from slowverb.engine import AudioEffects, AudioEngine


def test_speed_control_effects(engine, sample_sine_audio, tmp_path):
    """Test varying speed values (0.5x, 0.8x, 1.2x, 1.5x)."""
    for spd in [0.5, 0.8, 1.2, 1.5]:
        fx = AudioEffects(speed=spd)
        out_path = str(tmp_path / f"speed_{spd}.opus")
        path, size = engine.export_audio(sample_sine_audio, out_path, fx)
        assert os.path.isfile(path)
        assert size > 0
        meta = engine.probe_file(path)
        expected_dur = 3.0 / spd
        # Allow +/- 0.5s tolerance due to codec padding
        assert abs(meta.duration - expected_dur) < 0.6


def test_pitch_control_separate(engine, sample_sine_audio, tmp_path):
    """Test controlling pitch separately from track speed."""
    # Speed 1.0 (unchanged), Pitch 0.7 (lowered)
    fx = AudioEffects(speed=1.0, pitch=0.7, link_pitch_to_speed=False)
    out_path = str(tmp_path / "pitch_lower.opus")
    path, size = engine.export_audio(sample_sine_audio, out_path, fx)
    assert os.path.isfile(path)
    meta = engine.probe_file(path)
    # Duration should remain original since speed is 1.0
    assert abs(meta.duration - 3.0) < 0.5

    # Speed 0.8, Pitch 1.3 (slowed tempo, but higher pitched vocals)
    fx2 = AudioEffects(speed=0.8, pitch=1.3, link_pitch_to_speed=False)
    out_path2 = str(tmp_path / "speed_pitch_diff.opus")
    path2, size2 = engine.export_audio(sample_sine_audio, out_path2, fx2)
    assert os.path.isfile(path2)
    meta2 = engine.probe_file(path2)
    assert abs(meta2.duration - (3.0 / 0.8)) < 0.6


def test_reverb_control_percentages(engine):
    """Test reverb from 0% to 100%."""
    # 0% Reverb
    fx0 = AudioEffects(reverb_percent=0.0)
    assert "aecho" not in engine.build_audio_filter_string(fx0)

    # 40% Reverb
    fx40 = AudioEffects(reverb_percent=40.0)
    af40 = engine.build_audio_filter_string(fx40)
    assert "aecho=" in af40

    # 100% Reverb
    fx100 = AudioEffects(reverb_percent=100.0)
    af100 = engine.build_audio_filter_string(fx100)
    assert "aecho=" in af100


def test_bass_boost_percentages(engine):
    """Test bass boost from 0% to 100%."""
    fx0 = AudioEffects(bass_boost_percent=0.0)
    assert "bass" not in engine.build_audio_filter_string(fx0)

    fx50 = AudioEffects(bass_boost_percent=50.0)
    af50 = engine.build_audio_filter_string(fx50)
    assert "bass=g=9.00:f=100" in af50

    fx100 = AudioEffects(bass_boost_percent=100.0)
    af100 = engine.build_audio_filter_string(fx100)
    assert "bass=g=18.00:f=100" in af100


def test_preset_slowed_reverb(engine, sample_sine_audio, tmp_path):
    """Verify Slowed+Reverb preset configuration and export."""
    fx = AudioEffects(
        speed=PRESET_SLOWED_REVERB.speed,
        reverb_percent=PRESET_SLOWED_REVERB.reverb,
        pitch=PRESET_SLOWED_REVERB.pitch,
        link_pitch_to_speed=PRESET_SLOWED_REVERB.link_pitch_to_speed,
        bass_boost_percent=PRESET_SLOWED_REVERB.bass_boost,
    )
    assert fx.speed == 0.8
    assert fx.reverb_percent == 40.0
    assert fx.effective_pitch == 0.8

    out_file = str(tmp_path / "preset_slowed_reverb.opus")
    path, size = engine.export_audio(sample_sine_audio, out_file, fx)
    assert os.path.isfile(path)
    assert size > 0


def test_preset_nightcore(engine, sample_sine_audio, tmp_path):
    """Verify Nightcore preset configuration and export."""
    fx = AudioEffects(
        speed=PRESET_NIGHTCORE.speed,
        reverb_percent=PRESET_NIGHTCORE.reverb,
        pitch=PRESET_NIGHTCORE.pitch,
        link_pitch_to_speed=PRESET_NIGHTCORE.link_pitch_to_speed,
        bass_boost_percent=PRESET_NIGHTCORE.bass_boost,
    )
    assert fx.speed == 1.2
    assert fx.reverb_percent == 0.0
    assert fx.effective_pitch == 1.2

    out_file = str(tmp_path / "preset_nightcore.opus")
    path, size = engine.export_audio(sample_sine_audio, out_file, fx)
    assert os.path.isfile(path)
    assert size > 0


def test_cut_and_trim_audio(engine, sample_sine_audio, tmp_path):
    """Verify trimming audio from start to end timestamps."""
    # Original is ~3.0s. Trim from 1.0s to 2.5s (duration = 1.5s)
    fx = AudioEffects(trim_start=1.0, trim_end=2.5, speed=1.0)
    out_file = str(tmp_path / "trimmed.opus")
    path, size = engine.export_audio(sample_sine_audio, out_file, fx)

    assert os.path.isfile(path)
    meta = engine.probe_file(path)
    # Result should be approximately 1.5s
    assert abs(meta.duration - 1.5) < 0.4
