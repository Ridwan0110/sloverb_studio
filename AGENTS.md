# SloVerb Studio — AI Agent & Developer Architecture Guide (`AGENTS.md`)

This document provides a comprehensive technical overview of **SloVerb Studio** for AI coding assistants, automated agents, and human contributors. It details the project architecture, design principles, DSP audio pipeline, component interfaces, virtual environment setup, and development guidelines.

---

## 1. Project Overview & Identity

- **Application Name**: SloVerb Studio
- **Primary Purpose**: High-performance, minimalist desktop audio editing application for creating **slowed & reverb**, **nightcore**, pitch-shifted, and bass-boosted audio tracks with visual waveform peeking, visual waveform trimming, and instant MP3/Opus exporting.
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
└── tests/                     # 100% passing PyTest suite (120+ tests)
    ├── conftest.py            # Test fixtures (synthetic sine wave opus/wav generators)
    ├── test_build_binary.py   # Packaging, binary builder, platform detection
    ├── test_config.py         # Configuration & preset tests
    ├── test_dynamic_playback_ui.py # Thread-safe UI updates & async poller
    ├── test_edge_cases.py     # Extreme sliders, empty files, out-of-range trim
    ├── test_effects.py        # DSP filter string generation & math
    ├── test_engine.py         # AudioEngine, probing, buffer rendering, export
    ├── test_entry_point.py    # sloverb_studio bootstrap & legacy main.py redirect
    ├── test_ffmpeg_manager.py # OS-wide detection, priority, user prompt, auto-download
    ├── test_ffmpeg_setup_gui.py # FFmpegSetupView GUI states, mock downloads
    ├── test_gui_state.py      # GUI state transitions, peeking geometry, visual trim
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
3. **Architecture-Aware Downloader & Flet GUI Setup**:
   - Normalizes platform (`windows`, `darwin`, `linux`) and architecture (`x86_64`, `arm64`).
   - If FFmpeg is missing everywhere, prompts the user inside a cyber/robotic Flet window (`FFmpegSetupView`) with `[DOWNLOAD & CONFIGURE FFMPEG]` and real-time progress bar (`ft.ProgressBar`).
   - If confirmed, streams the official static build from GitHub releases / Gyan / Evermeet / JohnVanSickle into `<project_root>/ffmpeg/`, displays download/extraction progress, sets executable bits, and seamlessly transitions to the main editor interface.

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
- Exposes `get_buffer()` and `get_sample_rate()` for zero-copy inspection.

### 4.4. Desktop GUI & State Controller (`slowverb/ui.py`)
- **Waveform Peeking Geometry**:
  - The waveform contains 90 bars of 6px width + 2px spacing (`total_bars_width = 718px`), centered inside the container.
  - Seek ratio is calculated accurately as:
    $$\text{ratio} = \frac{\text{local\_x} - \text{start\_x}}{\text{total\_bars\_width}}$$
  - Accounts for container resizing via `_on_waveform_size_change` and `_on_page_resize`.

- **Visual Waveform Trimming & Draggable Marker Heads**:
  - Activated via the `TRIM` button, which toggles `APPLY` and `CANCEL` action controls and surfaces Start `[S]` (cyan) and End `[E]` (amber) draggable marker heads on top of the waveform canvas (`waveform_stack`).
  - **Gesture Tracking**: Handled via `ft.GestureDetector` listening to `on_tap_down`, `on_pan_start`, `on_pan_update`, and `on_pan_end`.
  - **Collision Prevention**: Start head cannot pass End head (`start <= end`). If `start == end`, the `APPLY` button is greyed out (`disabled=True`, `opacity=0.4`) and a red notice (`NOTICE: THIS IS EQUAL TO DELETING THE FILE`) is displayed beside the trim controls.
  - **Preview Enforcement**: In trim mode, playback is confined to `[trim_head_start_sec, trim_head_end_sec]`, automatically pausing and rewinding to start when the end head is reached. Waveform bars inside the selection display cyan/green; bars outside are dimmed.

- **Non-Destructive Trimming & Bidirectional Time Mapping**:
  - **Full Track Preservation (`_get_full_track_buffer`)**: Untrimmed pristine raw samples (`_full_raw_samples`) and active DSP-rendered buffers (`_rendered_full_samples`) are retained across the whole track. Trimming slices the active playback view without destroying audio from memory. Users can re-enter trim mode at any time and drag marker heads outwards to extend the audio duration.
  - **Time Domains**:
    - **Original File Space ($t_{orig}$)**: Seconds on disk (`0.0` to `metadata.duration`). Stored in `effects.trim_start` and `effects.trim_end` for FFmpeg export (`-ss` and `-to`).
    - **GUI Playback Space ($t_{gui}$)**: Scaled by active playback speed ($t_{gui} = t_{orig} / \text{speed}$).
    - Bidirectional helpers `_gui_sec_to_orig_sec()` and `_orig_sec_to_gui_sec()` translate between domains.
  - **Dynamic Duration Updates**: Moving the speed slider or applying presets immediately recalculates and updates the total duration in `time_display_text` to reflect the speed-scaled duration of the trimmed region.

- **Playhead Persistence Across Mode Transitions**:
  - Entering trim mode seamlessly maps the active playhead position into full-track space.
  - Cancelling trim mode restores the playhead to the corresponding relative timestamp in the trimmed track.
  - Applying trim mode resets the playhead to `0.0s` only when duration changed, or maintains position if unchanged.

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
.\pyvenv\Scripts\pip.exe install -r requirements-dev.txt
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
   - Avoid unbundled controls in `page.overlay` (e.g. legacy `ft.FilePicker`), use native tkinter dialog wrappers (`pick_file_desktop`, `save_file_desktop`).
4. **Maintain 100% Test Suite Pass Rate**:
   - Every modification must be verified against the test suite (`.\pyvenv\Scripts\python.exe -m pytest -v`).
   - All 120+ tests must pass before completing any task.
5. **Refer to `docs/TODO.md` & `assets/DESIGN_SYSTEM.md`**:
   - Refer to `docs/TODO.md` before making architectural changes.
   - Refer to `assets/DESIGN_SYSTEM.md` and `assets/design_tokens.json` for component blueprints, exact color tokens, geometry rules, and typographic scales when designing or refactoring UI components.
