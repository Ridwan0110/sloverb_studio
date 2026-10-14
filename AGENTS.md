# SloVerb Studio — AI Agent & Developer Architecture Guide (`AGENTS.md`)

This document provides a comprehensive technical overview of **SloVerb Studio** for AI coding assistants, automated agents, and human contributors. It details the project architecture, design principles, DSP audio pipeline, component interfaces, virtual environment setup, and development guidelines.

---

## 1. Project Overview & Identity

- **Application Name**: SloVerb Studio
- **Primary Purpose**: High-performance, minimalist desktop audio editing application for creating **slowed & reverb**, **nightcore**, pitch-shifted, and bass-boosted audio tracks with visual waveform peeking and instant MP3/Opus exporting.
- **UI Framework**: [Flet](https://flet.dev/) (Flutter-powered desktop GUI in Python).
- **Design Philosophy**: Minimalist cyber/robotic terminal aesthetic:
  - Square borders (`border_radius=2`)
  - Robotic monospace typography (`Consolas`)
  - Dark high-contrast palette (`#0D0E12` background, `#00FFA3` neon green accent, `#00D2FF` cyan, `#FFB800` amber)
  - Free FontAwesome Solid icons (`fa-solid-900.ttf`, zero emojis anywhere in the interface)
- **Zero-Bloat Core**: The Python library footprint is strictly de-bloated. Heavy audio packages like SciPy, Librosa, SoundFile, PyDub, and TorchAudio are intentionally avoided in favor of streaming stdio PCM pipes to FFmpeg.

---

## 2. Directory Structure

```
sloverb_studio/
├── sloverb_studio.py          # Primary application bootstrap & entry point
├── requirements.py            # De-bloated dependency specification & CLI installer
├── requirements.txt           # Minimal pinned/ranged requirements manifest
├── LICENSE                    # MIT License
├── assets/
│   └── fonts/
│       └── fa-solid-900.ttf   # FontAwesome Free Solid icon font
├── docs/
│   └── TODO.md                # Project backlog & technical issue tracking
├── ffmpeg/
│   └── ffmpeg.exe             # Local standalone FFmpeg binary (Windows x64)
├── pyvenv/                    # Clean, isolated Python virtual environment
├── slowverb/                  # Core package
│   ├── __init__.py            # Package initialization & public exports
│   ├── config.py              # Constants, theme colors, presets, FFmpeg lookup
│   ├── engine.py              # AudioEngine, DSP filter graph builder, PCM streamer
│   ├── ffmpeg_manager.py      # OS-wide FFmpeg discovery, architecture detection, downloader
│   ├── player.py              # Low-latency real-time AudioPlayer (sounddevice / PortAudio)
│   └── ui.py                  # SlowVerbApp GUI, state controller, waveform geometry
└── tests/                     # 100% passing PyTest suite (66+ tests)
    ├── conftest.py            # Test fixtures (synthetic sine wave opus/wav generators)
    ├── test_config.py         # Configuration & preset tests
    ├── test_edge_cases.py     # Extreme sliders, empty files, out-of-range trim
    ├── test_effects.py        # DSP filter string generation & math
    ├── test_engine.py         # AudioEngine, probing, buffer rendering, export
    ├── test_entry_point.py    # sloverb_studio bootstrap & legacy main.py redirect
    ├── test_ffmpeg_manager.py # OS-wide detection, priority, user prompt, auto-download
    ├── test_gui_state.py      # GUI state transitions, peeking geometry, presets
    └── test_player.py         # AudioPlayer loading, playback, seeking, callbacks
```

---

## 3. Technology Stack & De-Bloated Architecture

| Role | Library / Tool | Rationale & Bloat Elimination |
| :--- | :--- | :--- |
| **GUI Framework** | `flet>=1.0.0` | Desktop GUI using Flutter engine without HTML/CSS bloat. |
| **Audio Playback** | `sounddevice>=0.4.6` | Minimal C PortAudio wrapper for low-latency non-blocking streaming. |
| **In-Memory Buffers** | `numpy>=1.26.0` | 2D float32 arrays for playback buffers and vector peak analysis. |
| **Audio Processing** | `FFmpeg` (C binary) | Replaces 300MB+ of Python audio packages (SciPy, Librosa, PyDub). |
| **Testing** | `pytest>=8.0.0` | Test runner and assertions. |

### Eliminated Dependencies
- **SciPy (~50 MB)**: DSP filters are handled by FFmpeg's optimized C filters (`bass`, `aecho`, `rubberband`).
- **Librosa / Numba / LLVM (~250 MB)**: Waveform peak binning is executed directly on float32 NumPy arrays in `<5ms`.
- **SoundFile / PyDub (~30 MB)**: Raw PCM is streamed over stdout pipes (`f32le` and `s16le`).
- **TorchAudio (~1.5+ GB)**: Completely avoided.

---

## 4. Core Subsystems

### 4.1. FFmpeg Discovery & Auto-Downloader (`slowverb/ffmpeg_manager.py`)
1. **OS-Wide Discovery**:
   - Checks `FFMPEG_BINARY` environment variable.
   - Searches system `PATH` via `shutil.which("ffmpeg")`.
   - Inspects standard OS directories (Windows WinGet/Chocolatey/Scoop/Program Files, macOS Homebrew, Linux `/usr/bin`).
2. **Local Application Discovery**:
   - Checks `<project_root>/ffmpeg/ffmpeg.exe` (or `ffmpeg`).
3. **Architecture-Aware Downloader**:
   - Normalizes platform (`windows`, `darwin`, `linux`) and architecture (`x86_64`, `arm64`).
   - If FFmpeg is missing everywhere, prompts the user (`prompt_and_ensure_ffmpeg`).
   - If confirmed, streams the official static build from GitHub releases / Gyan / Evermeet / JohnVanSickle into `<project_root>/ffmpeg/` and sets executable bits.

### 4.2. Audio DSP Engine (`slowverb/engine.py`)
- **Speed & Pitch**: Implemented via FFmpeg's `rubberband` filter (`rubberband=tempo=...:pitch=...`). Allows decoupled or turntable-linked pitch adjustments.
- **Bass Boost**: Low-shelf filter (`bass=g=GAIN:f=100`), mapping `0-100%` boost to `0-18 dB` gain at 100 Hz.
- **Reverb**: Multi-stage diffused reflections using tuned `aecho` taps:
  - Early reflections: 50ms, 100ms, 200ms, 350ms delays.
  - Late diffusion reflections: 70ms, 150ms, 300ms, 600ms delays.
- **Soft Limiter**: `alimiter=limit=0.98` prevents digital clipping when bass boost or reverb gain accumulates.
- **Waveform Extraction**:
  - `extract_waveform()`: Probes file with FFmpeg into 8kHz mono int16 stream, divides into 90 bins, computes max and RMS amplitude.
  - `extract_waveform_from_samples()`: Computes waveform peaks and dB metrics directly from in-memory float32 NumPy buffers in `<5ms`.

### 4.3. Real-Time Audio Player (`slowverb/player.py`)
- Uses `sounddevice.OutputStream` with a custom streaming callback (`_audio_callback`).
- Maintains a thread-safe lock around frame indices, buffer references, and playback states.
- Supports instant non-blocking `seek(seconds)`, `seek_ratio(0.0-1.0)`, `pause()`, and `stop()`.

### 4.4. Desktop GUI & State Controller (`slowverb/ui.py`)
- **Waveform Peeking Geometry**:
  - The waveform contains 90 bars of 6px width + 2px spacing (`total_bars_width = 718px`), centered inside the container.
  - Seek ratio is calculated accurately as:
    $$\text{ratio} = \frac{\text{local\_x} - \text{start\_x}}{\text{total\_bars\_width}}$$
  - Accounts for container resizing via `_on_waveform_size_change` and `_on_page_resize`.
- **Status Indicator**:
  - Tracks whether the loaded audio buffer matches active slider parameters (`CURRENT MODIFIED VERSION` with green check) or whether sliders have drifted (`OLD MODIFIED VERSION` with amber warning).
- **Thread-Safe UI Sync**:
  - Encapsulated in `update_ui()` with a dedicated `_ui_lock` to prevent WebSocket/Flutter protocol collisions.

---

## 5. Development & Testing Workflow

### 5.1. Virtual Environment Setup
The project uses an isolated virtual environment named `pyvenv`:
```powershell
# Create virtual environment
python -m venv pyvenv

# Install de-bloated dependencies
.\pyvenv\Scripts\python.exe requirements.py --install
```

### 5.2. Running the Application
```powershell
# Using the project virtual environment
.\pyvenv\Scripts\python.exe sloverb_studio.py

# Or load a specific audio file directly
.\pyvenv\Scripts\python.exe sloverb_studio.py "eien - melancholy.opus"
```

### 5.3. Running the Test Suite
The complete test suite runs via PyTest and must maintain 100% pass rate:
```powershell
.\pyvenv\Scripts\python.exe -m pytest -v
```

---

## 6. Guidelines for AI Agents

1. **Maintain De-Bloated Principles**:
   - Do NOT introduce dependencies on SciPy, PyDub, Librosa, SoundFile, or PyTorch.
   - Utilize FFmpeg filter graphs and NumPy vector operations.
2. **Preserve UI Aesthetics**:
   - Maintain the square terminal aesthetic (`border_radius=2`, `Consolas` font).
   - Never add emojis to UI buttons or labels. Use FontAwesome Unicode glyphs defined in `slowverb/config.py`.
   - Keep preset buttons text-only without icons.
3. **Respect Python 3.14 & Flet 1.0**:
   - In Flet 1.0, do not use legacy `flet.app(target=main)`. Use `flet.run(main)`.
   - Avoid unbundled controls in `page.overlay` (e.g. legacy `ft.FilePicker`), use native tkinter dialog wrappers (`pick_file_desktop`, `save_file_desktop`).
4. **Refer to `docs/TODO.md`**:
   - Always check `docs/TODO.md` before making changes to ongoing background poller or waveform synchronization features.
