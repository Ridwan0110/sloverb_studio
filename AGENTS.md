# SloVerb Studio — AI Agent & Developer Architecture Guide (`AGENTS.md`)

This document provides a comprehensive technical overview of **SloVerb Studio** for AI coding assistants, automated agents, and human contributors. It details the project architecture, design principles, DSP audio pipeline, component interfaces, virtual environment setup, and development guidelines.

---

## 1. Project Overview & Identity

- **Application Name**: SloVerb Studio
- **Primary Purpose**: High-performance, minimalist desktop and mobile audio editing application for creating **slowed & reverb**, **nightcore**, pitch-shifted, and bass-boosted audio tracks with visual waveform peeking, visual waveform trimming, and instant MP3/Opus/M4A exporting.
- **UI Framework**: [Flet](https://flet.dev/) (Flutter-powered desktop and mobile GUI in Python).
- **Supported Platforms**: Windows, Linux, macOS, and Android (with iOS architecture ready).
- **Design Philosophy**: Minimalist cyber/robotic terminal aesthetic:
  - Square borders (`border_radius=2`)
  - Robotic monospace typography (`Consolas`)
  - Dark high-contrast palette (`#0D0E12` background, `#00FFA3` neon green accent, `#00D2FF` cyan, `#FFB800` amber)
  - Free FontAwesome Solid icons (`fa-solid-900.ttf`, zero emojis anywhere in the interface)
- **Zero-Bloat Core**: The Python library footprint is strictly de-bloated. Heavy audio packages like SciPy, Librosa, SoundFile, PyDub, and TorchAudio are intentionally avoided in favor of streaming stdio PCM pipes to FFmpeg on desktop, and PyAV (`av`) linked with bundled `flet-libffmpeg` on mobile.

---

## 2. Directory Structure

```
sloverb_studio/
├── sloverb_studio.py          # Primary application bootstrap & entry point
├── requirements.txt           # Core runtime dependency manifest
├── requirements-dev.txt       # Development & testing dependency manifest
├── SloVerbStudio.spec         # PyInstaller packaging specification
├── CHANGELOG.md               # Version history and release notes
├── LICENSE                    # MIT License
├── assets/
│   ├── fonts/
│   │   └── fa-solid-900.ttf   # FontAwesome Free Solid icon font
│   ├── design_tokens.json     # Cyber/robotic design tokens & colors
│   └── DESIGN_SYSTEM.md       # UI component blueprints & spacing rules
├── docs/
│   ├── CAPABILITIES.md        # Complete platform & subsystem capability matrix
│   ├── PR_DESCRIPTION.md     # Pull request template and changelog summary
│   └── TODO.md                # Project backlog & technical issue tracking
├── ffmpeg/
│   └── ffmpeg.exe             # Local standalone FFmpeg binary (Windows x64)
├── pyvenv/                    # Clean, isolated Python virtual environment
├── redu-dev/                  # Build scripts & development tools
│   ├── build_binary.py        # Desktop PyInstaller builder & version extractor
│   └── build_mobile_apk.py    # Android APK builder & Gradle runner
├── slowverb/                  # Core package
│   ├── __init__.py            # Package initialization, version, DEBUG_MODE export
│   ├── config.py              # Constants, theme colors, presets, FA icons
│   ├── debug.py               # DiagnosticLogger ring buffer & telemetry dump generator
│   ├── engine.py              # AudioEngine, PyAVAudioEngine, DSP filter builder
│   ├── ffmpeg/                # Modular FFmpeg backend providers
│   │   ├── __init__.py        # Provider factory (get_ffmpeg_provider)
│   │   ├── base.py            # BaseFFmpegProvider interface
│   │   ├── android_provider.py # Android PyAV / NDK provider
│   │   ├── desktop_provider.py # Desktop standalone executable provider
│   │   └── ios_provider.py    # iOS PyAV provider stub
│   ├── ffmpeg_manager.py      # OS-wide FFmpeg discovery, architecture detection, downloader
│   ├── file_dialogs.py        # Cross-platform FileService (Desktop tkinter & Android SAF)
│   ├── platform.py            # Environment detection, ABI lookup, mobile checks
│   ├── player/                # Low-latency audio playback drivers
│   │   ├── __init__.py        # Player factory (create_audio_player)
│   │   ├── base.py            # BaseAudioPlayer interface
│   │   ├── flet_audio_player.py # Mobile Flutter platform channel player (flet-audio)
│   │   └── sounddevice_player.py # Desktop PortAudio low-latency player (sounddevice)
│   └── ui.py                  # SlowVerbApp GUI, state controller, responsive layouts
└── tests/                     # 100% passing PyTest suite (187+ tests)
    ├── conftest.py            # Test fixtures (synthetic sine wave opus/wav generators)
    ├── test_build_binary.py   # Packaging, binary builder, platform detection
    ├── test_config.py         # Configuration & preset tests
    ├── test_debug_mode.py     # Diagnostics dump, logger ring buffer, baked debug mode
    ├── test_dynamic_playback_ui.py # Thread-safe UI updates & async poller
    ├── test_edge_cases.py     # Extreme sliders, empty files, out-of-range trim
    ├── test_effects.py        # DSP filter string generation & math
    ├── test_engine.py         # AudioEngine, probing, buffer rendering, export
    ├── test_entry_point.py    # sloverb_studio bootstrap & CLI argument handling
    ├── test_ffmpeg_manager.py # OS-wide detection, priority, user prompt, auto-download
    ├── test_ffmpeg_provider.py # FFmpeg provider routing & NDK library resolution
    ├── test_ffmpeg_setup_gui.py # FFmpegSetupView GUI states, mock downloads
    ├── test_file_dialogs.py   # Cross-platform FileService pick/save flows
    ├── test_gui_state.py      # GUI state transitions, peeking geometry, visual trim
    ├── test_mobile_ui_layout.py # Mobile tabbed UI, static top bar, responsive bars
    ├── test_platform_detection.py # OS, mobile environment, and ABI detection
    ├── test_player.py         # Desktop AudioPlayer loading, playback, seeking
    ├── test_player_abstraction.py # Player factory, FletAudioPlayer state & seeking
    └── test_pyav_engine.py    # PyAV C filter graphs, PCM rendering, M4A export
```

---

## 3. Technology Stack & De-Bloated Architecture

| Role | Library / Tool | Rationale & Bloat Elimination |
| :--- | :--- | :--- |
| **GUI Framework** | `flet>=1.0.0` | Desktop & mobile GUI using Flutter engine without HTML/CSS bloat. |
| **Desktop Playback** | `sounddevice>=0.4.6` | Minimal C PortAudio wrapper for low-latency non-blocking streaming. |
| **Mobile Playback** | `flet-audio>=1.1.0` | Native Flutter platform audio channel for mobile background audio. |
| **In-Memory Buffers** | `numpy>=1.26.0` | 2D float32 arrays for playback buffers and vector peak analysis. |
| **Desktop Processing** | `FFmpeg` (C binary) | Replaces 300MB+ of Python audio packages (SciPy, Librosa, PyDub). |
| **Mobile Processing** | `av>=14.0.0` (PyAV) | Direct in-process C FFmpeg filter graphs via bundled `flet-libffmpeg`. |
| **Testing** | `pytest>=8.0.0` | Test runner, fixtures, and assertions (187+ tests). |

### Eliminated Dependencies
- **SciPy (~50 MB)**: DSP filters are handled by native C filters (`bass`, `aecho`, `rubberband`).
- **Librosa / Numba / LLVM (~250 MB)**: Waveform peak binning is executed directly on float32 NumPy arrays in `<5ms`.
- **SoundFile / PyDub (~30 MB)**: Raw PCM is streamed over stdout pipes (`f32le` and `s16le`) or decoded via PyAV.
- **TorchAudio (~1.5+ GB)**: Completely avoided.

---

## 4. Core Subsystems

### 4.1. Audio Player Abstraction (`slowverb/player/`)
- **Factory Pattern (`create_audio_player`)**: Instantiates `SounddevicePlayer` on desktop and `FletAudioPlayer` on mobile environments.
- **Desktop (`SounddevicePlayer`)**: Low-latency PortAudio C streaming callback (`_audio_callback`) supporting non-blocking `seek()`, `pause()`, and zero-copy `get_buffer()` access.
- **Mobile (`FletAudioPlayer`)**: Uses `flet-audio` to interface directly with Android/iOS native audio services. Accurately maintains playhead position on pause/resume cycles, and registers completion callbacks (`on_playback_finished`).

### 4.2. FFmpeg Provider & Mobile DSP Engine (`slowverb/ffmpeg/` & `slowverb/engine.py`)
- **Desktop DSP (`AudioEngine`)**: Streams raw PCM over stdio pipes to standalone FFmpeg executables (`rubberband`, `aecho`, `bass`, `alimiter`).
- **Mobile DSP (`PyAVAudioEngine`)**: Executes C filter graphs in-process using PyAV (`av`) linked against `flet-libffmpeg` shared libraries:
  - **Speed & Pitch**: Rubberband or atempo filter graphs (0.50x – 1.50x tempo, -6 to +6 st pitch).
  - **Reverb**: Multi-stage diffused reflections using tuned `aecho` taps.
  - **Bass Boost**: Low-shelf filter (`bass=g=GAIN:f=100`) mapping to 0–18 dB gain.
  - **Exporting**: Encodes directly to standard **M4A / AAC** (`aac` encoder) with sample rate guards and proper kilobit bitrate formatting (`192k`).
  - **Waveform Extraction**: Vectorized peak and RMS binning on float32 NumPy buffers in `<5ms`.

### 4.3. Cross-Platform File I/O (`slowverb/file_dialogs.py`)
- **Unified `FileService`**:
  - **Desktop**: Native OS file pickers via `tkinter.filedialog` (`pick_file_desktop`, `save_file_desktop`).
  - **Mobile**: Android Storage Access Framework (SAF) via `ft.FilePicker` registered on `page.services`.
  - **Cache Management**: Copies picked content URIs to internal app cache for instant non-blocking seeking while preserving original filenames across the interface.

### 4.4. Desktop & Mobile User Interface (`slowverb/ui.py`)

- **Waveform Peeking Geometry**:
  - Desktop: 90 bars of 6px width + 2px spacing (`718px` total width).
  - Mobile: Dynamically computes bar counts to fit compact 360dp+ viewports without overflow.
  - Sub-pixel tap and pan scrubbing via `ft.GestureDetector`.

- **Visual Waveform Trimming & Draggable Marker Heads**:
  - Activated via `TRIM` button; displays Start `[S]` (cyan) and End `[E]` (amber) draggable marker heads.
  - Collision prevention: `start <= end`. When `start == end`, `APPLY` is disabled with a red warning notice (`NOTICE: THIS IS EQUAL TO DELETING THE FILE`).
  - Playback confinement: Preview playback is strictly bounded within `[trim_head_start_sec, trim_head_end_sec]`.

- **Non-Destructive Trimming & Bidirectional Time Mapping**:
  - **Full Track Retention**: Pristine raw samples (`_full_raw_samples`) and active DSP buffers (`_rendered_full_samples`) are retained in memory. Users can re-enter trim mode and drag marker heads outwards at any time.
  - **Time Spaces**: Original file space ($t_{orig}$) and speed-scaled GUI playback space ($t_{gui} = t_{orig} / \text{speed}$).
  - Playhead persistence across trim mode entry, exit, and apply transitions.

- **Mobile Responsive Layout**:
  - **Safe-Area Insets**: `top=42` padding protects the header from Android notification bars and camera notches.
  - **Dynamic Tab View**: `ft.AnimatedSwitcher` toggles between **`PEEK`** (waveform visualizer, duration, peak dB) and **`EFFECTS`** (presets, speed, pitch, reverb, bass boost).
  - **Static 4-Row Top Bar**:
    - Row 1: File Loader (`LOAD`, 20%) + Status & Version Box (80%).
    - Row 2: Transport Controls (`PLAY`, `PAUSE`, `STOP`, `REWIND`).
    - Row 3: Dedicated full-width Trim Row (`TRIM` takes 100% width; `APPLY` / `CANCEL` when active).
    - Row 4: Action Controls (`PREVIEW` and `EXPORT` taking 50/50 full width).

- **Diagnostics & Telemetry Suite (`slowverb/debug.py`)**:
  - Floating amber bug button (`FA_BUG`) visible when `DEBUG_MODE=True`.
  - Generates comprehensive `sloverb_debug_dump.json` capturing hardware architecture, ABI, Python runtime, screen dimensions, native packages, and in-memory terminal logs.
  - Circular ring-buffer logger (`DiagnosticLogger`) retaining last 250 timestamped events.
  - One-click status banner error copying to clipboard with visual confirmation.

---

## 5. Development & Testing Workflow

### 5.1. Virtual Environment Setup
The project uses an isolated virtual environment named `pyvenv`:
```powershell
# Create virtual environment
python -m venv pyvenv

# Install de-bloated dependencies
.\pyvenv\Scripts\pip.exe install -r requirements-dev.txt
```

### 5.2. Running the Application
```powershell
# Using the project virtual environment on desktop
.\pyvenv\Scripts\python.exe sloverb_studio.py

# Simulate mobile UI layout on desktop
.\pyvenv\Scripts\python.exe sloverb_studio.py --mobile-ui

# Run with diagnostics debug mode enabled
.\pyvenv\Scripts\python.exe sloverb_studio.py --debug

# Load an audio file directly on startup
.\pyvenv\Scripts\python.exe sloverb_studio.py "audio_track.opus"
```

### 5.3. Building the Android APK
```powershell
# Standard production APK build
python redu-dev/build_mobile_apk.py

# Build APK with baked DEBUG_MODE=True for telemetry export
python redu-dev/build_mobile_apk.py --debug
```

### 5.4. Running the Test Suite
The complete test suite runs via PyTest and must maintain 100% pass rate:
```powershell
.\pyvenv\Scripts\python.exe -m pytest -v
```

---

## 6. Guidelines for AI Agents

### 6.1. Git & Version Control Protocol (CRITICAL RULES)

1. **NO Autonomous Commits — Explicit User Request Only**:
   - AI agents must **NEVER** create git commits on their own initiative.
   - Do NOT commit after making a change unless the user explicitly tells you to do so (e.g., *"commit your changes"*, *"use a commit for each logical change"*).
   - If unprompted, leave changes in the working tree or staged and report back to the user for review.
2. **Atomic Commits — One Commit per Logical Change**:
   - When the user instructs you to commit, strictly follow: **one commit for one logical change**.
   - Never combine unrelated features, bug fixes, or test additions into a single monolithic commit.
   - Keep commit messages short, concise, and structured with Conventional Commits syntax:
     - `feat(ui): ...`
     - `fix(dsp): ...`
     - `test: ...`
     - `docs: ...`
3. **STRICT PROHIBITION: NEVER Push to Remote / Origin**:
   - Under **NO circumstances** should an AI agent ever execute `git push` or push commits/branches to GitHub or any remote repository.
   - Remote pushes, branch management, pull requests, and merges are strictly the user's prerogative.

### 6.2. Engineering & Architecture Rules

1. **Maintain De-Bloated Principles**:
   - Do NOT introduce dependencies on SciPy, PyDub, Librosa, SoundFile, or PyTorch.
   - Utilize FFmpeg filter graphs and NumPy vector operations.
2. **Preserve UI Aesthetics**:
   - Maintain the square terminal aesthetic (`border_radius=2`, `Consolas` font).
   - Never add emojis to UI buttons or labels. Use FontAwesome Unicode glyphs defined in `slowverb/config.py`.
   - Keep preset buttons text-only without icons.
3. **Respect Python 3.14 & Flet 1.0**:
   - In Flet 1.0, do not use legacy `flet.app(target=main)`. Use `flet.run(main)`.
   - Avoid unbundled controls in `page.overlay` (e.g. legacy `ft.FilePicker`), use native tkinter dialog wrappers (`pick_file_desktop`, `save_file_desktop`) or `FileService`.
4. **Maintain 100% Test Suite Pass Rate**:
   - Every modification must be verified against the test suite (`.\pyvenv\Scripts\python.exe -m pytest -v`).
   - All 187+ tests must pass before completing any task.
5. **Refer to Documentation**:
   - Refer to `docs/CAPABILITIES.md` for cross-platform feature support and implementation drivers.
   - Refer to `docs/TODO.md` before making architectural changes.
   - Refer to `assets/DESIGN_SYSTEM.md` and `assets/design_tokens.json` for component blueprints, exact color tokens, geometry rules, and typographic scales when designing or refactoring UI components.
