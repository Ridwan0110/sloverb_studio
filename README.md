# SlowVerb Studio

[![CI Tests](https://github.com/Ridwan0110/sloverb_studio/actions/workflows/ci.yaml/badge.svg)](https://github.com/Ridwan0110/slowverb/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/license/mit/)
[![Version](https://img.shields.io/github/v/release/Ridwan0110/sloverb_studio?include_prereleases&label=version&color=blue)](https://github.com/Ridwan0110/sloverb_studio/releases)
[![GitHub](https://img.shields.io/badge/source-GitHub-blue?logo=github)](https://github.com/Ridwan0110/sloverb_studio)

**SlowVerb Studio** is a desktop Python application designed to quickly edit audio tracks for achieving iconic audio effects (i.e., Slowed + Reverb, Nightcore, Bass Boost, Custom Pitch Shifting, and Trimming).

Featuring a minimalist, desktop-optimized GUI created with **Flet** that utilizes a sharp, robotic/square aesthetic with `Consolas` monospace typography.

---

## Features

- **Track Speed Control (0.5x – 1.5x)**: High-quality time stretching powered by FFmpeg & Rubberband.
- **Reverb (0 – 100%)**: Multi-tap spatial reflection engine delivering lush, warm atmosphere with soft peak limiting.
- **Separate & Linked Pitch Control (0.5x – 1.5x)**:
  - **Linked Mode (Default)**: Automatically tracks speed to match turntable / tape pitch drops or rises.
  - **Independent Mode**: Allows detaching pitch from speed to achieve chipmunk or deep-voice vocals at any tempo.
- **Bass Boost (0 – 100%)**: Up to +18 dB warm low-end shelf at 100 Hz.
- **One-Click Presets**:
  - `[ 1. SLOWED + REVERB ]`: Speed at `0.8x`, Reverb at `40%`, Pitch at `0.8x`.
  - `[ 2. NIGHTCORE ]`: Speed at `1.2x`, Reverb at `0%`, Pitch at `1.2x`.
  - `[ RESET ]`: Restores unity settings (`1.0x` speed, `1.0x` pitch, `0%` reverb, `0%` bass).
- **Interactive Waveform Peeking & Seeking**:
  - Visual envelope computed directly from audio peaks.
  - Click or drag on any part of the waveform to peek and seek the playhead.
  - Real-time peak level monitoring (`dBFS`) and timestamp counters.
- **Cut / Trim Audio**: Set start and end points via playhead locks or manual inputs.
- **High-Quality Export**:
  - **Opus** (160 kbps VBR)
  - **MP3** (192 kbps CBR)

---

## Project Structure

```
sloverb_studio/
├── ffmpeg/
│   └── ffmpeg.exe         # Local FFmpeg binary
├── slowverb/
│   ├── __init__.py        # Package exports
│   ├── config.py          # Color scheme, constants, presets & path resolver
│   ├── engine.py          # AudioEngine: probe, waveform extraction, filter graph & export
│   ├── player.py          # AudioPlayer: real-time playback, scrubbing & sounddevice engine
│   └── ui.py              # SlowVerbApp: Flet GUI with square robotic styling
├── tests/
│   ├── conftest.py        # Pytest fixtures & synthetic audio generator
│   ├── test_config.py     # Configuration & preset tests
│   ├── test_effects.py    # Speed, pitch, reverb, bass & trimming tests
│   ├── test_engine.py     # FFmpeg filter building, metadata & export tests
│   ├── test_player.py     # Real-time player buffer & state transitions tests
│   ├── test_edge_cases.py # Boundary conditions, corrupt files & path character tests
│   ├── test_entry_point.py# Tests for sloverb_studio.py entry point & CLI args
│   └── test_gui_state.py  # GUI controls, slider sync & waveform peeking tests
├── sloverb_studio.py      # Main desktop application launcher
├── main.py                # Backward compatibility launcher
└── export_melancholy.py   # Script to process 'eien - melancholy.opus'
```

---

## Running the Application

Launch the desktop GUI:

```bash
python sloverb_studio.py
```

Or pass a file directly from the command line:

```bash
python sloverb_studio.py "eien - melancholy.opus"
```

---

## Running the Test Suite

Run the full pytest suite:

```bash
python -m pytest -v
```

All 38 tests cover:
- Parameter boundary clamping (`0.5x - 1.5x`, `0% - 100%`)
- Pitch linking / unlinking synchronization
- Presets (Slowed+Reverb and Nightcore)
- Waveform peak analysis and peeking math
- Trimming edge cases (micro-trims, negative ranges)
- Corrupt and non-audio file handling
- Special characters and unicode in paths
- Player stream lifecycles
- Exporting to both `.opus` and `.mp3`