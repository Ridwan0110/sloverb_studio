# SlowVerb Studio

[![CI Tests](https://github.com/Ridwan0110/sloverb_studio/actions/workflows/ci.yaml/badge.svg)](https://github.com/Ridwan0110/slowverb/actions/workflows/ci.yaml)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](https://opensource.org/license/mit/)
[![Version](https://img.shields.io/github/v/release/Ridwan0110/sloverb_studio?include_prereleases&label=version&color=blue)](https://github.com/Ridwan0110/sloverb_studio/releases)
[![GitHub](https://img.shields.io/badge/source-GitHub-blue?logo=github)](https://github.com/Ridwan0110/sloverb_studio)

**SlowVerb Studio** is a desktop Python application designed to quickly edit audio tracks for achieving iconic audio effects (i.e., Slowed + Reverb, Nightcore, Bass Boost, Custom Pitch Shifting, and Trimming).

Featuring a minimalist, desktop-optimized GUI created with **Flet** that utilizes a sharp, robotic/square aesthetic with `Consolas` monospace typography.

---

## Features

- **Speed Control (0.5x – 1.5x)**: Time stretching by FFmpeg & Rubberband.
- **Reverb (0 – 100%)**: Hear sounds 
- **Separate & Linked Pitch Control (0.5x – 1.5x)**:
  - **Linked Mode (Default)**: Automatically tracks speed to match turntable / tape pitch drops or rises.
  - **Independent Mode**: Allows detaching pitch from speed to achieve chipmunk or deep-voice vocals at any tempo.
- **Bass Boost (0 – 100%)**: Up to +18 dB warm low-end shelf at 100 Hz.
- **Presets**:
  - `[ 1. SLOWED + REVERB ]`: Speed at `0.8x`, Reverb at `40%`, Pitch at `0.8x`.
  - `[ 2. NIGHTCORE ]`: Speed at `1.2x`, Reverb at `0%`, Pitch at `1.2x`.
  - `[ RESET ]`: Restores unity settings (`1.0x` speed, `1.0x` pitch, `0%` reverb, `0%` bass).
- **Waveform Peeking & Seeking**: Click or drag on any part of the waveform to peek and seek the playhead.
- **Cut / Trim Audio**: Set start and end points via playhead locks or manual inputs.

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

---

## Building Standalone Binaries

SloVerb Studio includes a universal multi-platform builder script in `redu-dev/build_binary.py` to package standalone native executables and release archives for Windows, Linux, and macOS (x86_64 and ARM64).

### 1. Prerequisites

Install the development and packaging dependencies:

```bash
pip install -r requirements-dev.txt
```

#### System Dependencies:
- **Windows**: No additional system dependencies required.
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt-get update
  sudo apt-get install -y libportaudio2 libasound2-dev libgtk-3-0 libmpv2 ffmpeg
  ```
- **macOS**:
  ```bash
  brew install portaudio ffmpeg
  ```

### 2. Build the Application

Run the universal builder CLI script from the repository root:

```bash
python redu-dev/build_binary.py --clean
```

#### Output Artifacts:
The builder generates distribution-ready packages inside `dist/archives/`:
- **Windows (`x86_64`)**: `dist/archives/SloVerbStudio-v<version>-windows-x86_64.zip` (containing `SloVerbStudio.exe`)
- **Linux (`x86_64` / `arm64`)**: `dist/archives/SloVerbStudio-v<version>-linux-<arch>.tar.gz` (containing standalone executable)
- **macOS (`arm64` / `x86_64`)**: `dist/archives/SloVerbStudio-v<version>-darwin-<arch>.zip` (containing `SloVerbStudio.app`)

#### Useful Build Flags:
- `--dry-run`: View the resolved PyInstaller command without running the build.
- `--console`: Build with a console/terminal window attached for debugging.
- `--name <NAME>`: Custom name for the generated executable or app bundle.
- `--skip-tests`: Skip post-build self-diagnostic tests.

