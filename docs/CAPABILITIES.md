# SloVerb Studio — Platform & Subsystem Capabilities Matrix

This document provides a comprehensive technical breakdown of all **Frontend** and **Backend** capabilities in **SloVerb Studio**, detailing support, implementation drivers, and platform-specific behaviors across **Windows**, **Linux**, **macOS**, **Android**, and **iOS**.

---

## 1. Executive Summary & Architecture Overview

SloVerb Studio employs a layered cross-platform architecture designed around a **zero-bloat core**. Rather than bundling massive Python audio frameworks (e.g. SciPy, Librosa, PyDub, TorchAudio), it delegates real-time playback, DSP transformations, and visual analytics to lightweight native libraries:

- **Desktop (Windows, Linux, macOS)**: Uses standalone FFmpeg binaries over stdio PCM pipes and `sounddevice` (PortAudio C wrapper).
- **Mobile (Android, iOS)**: Uses `flet-audio` (native Flutter audio channels) and `av` (PyAV linked with bundled `flet-libffmpeg` shared libraries).

---

## 2. Comprehensive Capabilities Matrix

### Legend
- ✅ **Fully Supported**: Production-ready, native performance, covered by test suite.
- 🟡 **Partial / Planned**: Architecture implemented, awaiting platform packaging or release verification.
- ❌ **Not Applicable**: Platform sandbox or operating system architectural constraints.

---

### 2.1. Audio Playback & Transport (Backend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Low-Latency Streaming** | ✅ | ✅ | ✅ | ❌ | ❌ | `SounddevicePlayer`: PortAudio C streaming wrapper (`sounddevice`). |
| **Native Channel Playback** | ❌ | ❌ | ❌ | ✅ | 🟡 | `FletAudioPlayer`: Flutter platform channel audio service (`flet-audio`). |
| **Seek by Seconds** | ✅ | ✅ | ✅ | ✅ | 🟡 | Thread-safe frame index seek on desktop; async audio service seek on mobile. |
| **Seek by Ratio (0.0 – 1.0)** | ✅ | ✅ | ✅ | ✅ | 🟡 | Bounded normalized scrubbing translated to duration timestamps. |
| **Pause & Resume Tracking** | ✅ | ✅ | ✅ | ✅ | 🟡 | Exact playhead preservation across pause/play transitions without resetting. |
| **Rewind to Start** | ✅ | ✅ | ✅ | ✅ | 🟡 | Instant jump to timestamp `0.0s` or active trim start `trim_start`. |
| **Playback Completion Hook** | ✅ | ✅ | ✅ | ✅ | 🟡 | Event callback `on_playback_finished` triggered on stream termination. |
| **Zero-Copy Buffer Access** | ✅ | ✅ | ✅ | ❌ | ❌ | Direct float32 NumPy array pointer access via `get_buffer()`. |

---

### 2.2. Audio DSP Engine & Effects (Backend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Standalone FFmpeg Pipes** | ✅ | ✅ | ✅ | ❌ | ❌ | `AudioEngine`: Subprocess stdio streaming (`f32le` / `s16le` PCM). |
| **In-Process PyAV Filter Graphs** | ❌ | ❌ | ❌ | ✅ | 🟡 | `PyAVAudioEngine`: In-process C filter graph via `av` / `flet-libffmpeg`. |
| **Speed Shifting (0.50x – 1.50x)** | ✅ | ✅ | ✅ | ✅ | 🟡 | Handled via FFmpeg `rubberband` / `atempo` filter graphs. |
| **Pitch Shifting (-6 to +6 st)** | ✅ | ✅ | ✅ | ✅ | 🟡 | Decoupled pitch adjustment via `rubberband=pitch=...`. |
| **Turntable Pitch Linking** | ✅ | ✅ | ✅ | ✅ | 🟡 | Automatic pitch adjustment linked proportionally to track playback speed. |
| **Diffused Reverb (0 – 100%)** | ✅ | ✅ | ✅ | ✅ | 🟡 | Multi-stage delay reflections using tuned `aecho` filter parameters. |
| **Low-Shelf Bass Boost (0 – 100%)** | ✅ | ✅ | ✅ | ✅ | 🟡 | Low-shelf EQ filter (`bass=g=GAIN:f=100`) mapping to 0–18 dB gain at 100 Hz. |
| **Soft Limiter Clipping Guard** | ✅ | ✅ | ✅ | ✅ | 🟡 | `alimiter=limit=0.98` prevents digital clipping on accumulated gain. |
| **In-Memory Peak Extraction** | ✅ | ✅ | ✅ | ✅ | 🟡 | Vectorized peak binning on float32 NumPy arrays in `<5ms`. |
| **Metadata Probing** | ✅ | ✅ | ✅ | ✅ | 🟡 | Extracts sample rate, channels, bit depth, duration, and codec metadata. |

---

### 2.3. Audio Export & Codecs (Backend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **M4A / AAC Export** | ✅ | ✅ | ✅ | ✅ | 🟡 | AAC audio encoder (`aac`) formatted in standard MP4/M4A container. |
| **MP3 Export (`libmp3lame`)** | ✅ | ✅ | ✅ | 🟡 | 🟡 | Desktop uses standalone FFmpeg binary; mobile uses native C encoder if compiled. |
| **Opus Export (`libopus`)** | ✅ | ✅ | ✅ | 🟡 | 🟡 | Low-latency modern speech/music codec container. |
| **WAV Export (`pcm_s16le`)** | ✅ | ✅ | ✅ | 🟡 | 🟡 | Uncompressed PCM export for studio DAW workflows. |
| **Dynamic Encoder Detection** | ✅ | ✅ | ✅ | ✅ | 🟡 | Queries runtime FFmpeg/PyAV capabilities and presents available codecs. |
| **Bitrate Formatting Guard** | ✅ | ✅ | ✅ | ✅ | 🟡 | Enforces standard integer kilobits formatting (e.g. `192k` / `192000`). |

---

### 2.4. File I/O & Storage Abstraction (Backend & Frontend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Desktop File Dialogs** | ✅ | ✅ | ✅ | ❌ | ❌ | Native desktop open/save dialogs via `tkinter.filedialog` wrapper. |
| **Storage Access Framework (SAF)** | ❌ | ❌ | ❌ | ✅ | 🟡 | Android SAF content URI picking and saving via `ft.FilePicker`. |
| **CLI File Path Loading** | ✅ | ✅ | ✅ | ❌ | ❌ | Supports launching with target file argument (`sloverb_studio.py <path>`). |
| **Sandboxed Cache Management** | ❌ | ❌ | ❌ | ✅ | 🟡 | Copies picked SAF content URIs into internal app cache for fast seeking. |
| **Original Filename Preservation** | ✅ | ✅ | ✅ | ✅ | 🟡 | Retains original track names across content URIs and temp cache paths. |

---

### 2.5. Graphical User Interface & Navigation (Frontend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Cyber Monospace Theme** | ✅ | ✅ | ✅ | ✅ | ✅ | Dark high-contrast palette (`#0D0E12`, `#00FFA3`, `#00D2FF`, `#FFB800`). |
| **Robotic Geometry Rules** | ✅ | ✅ | ✅ | ✅ | ✅ | Monospace typography (`Consolas`), square borders (`border_radius=2`). |
| **Vector Icons (Zero Emojis)** | ✅ | ✅ | ✅ | ✅ | ✅ | Free FontAwesome Solid font (`fa-solid-900.ttf`). |
| **Desktop Multi-Card Layout** | ✅ | ✅ | ✅ | ❌ | ❌ | Unfolded multi-card layout optimized for wide desktop screens. |
| **Mobile Simulation Mode** | ✅ | ✅ | ✅ | ❌ | ❌ | `--mobile-ui` CLI flag enables mobile layout testing on desktop. |
| **Mobile Tabbed Interface** | ❌ | ❌ | ❌ | ✅ | 🟡 | `ft.AnimatedSwitcher` with fade transition between PEEK and EFFECTS. |
| **Mobile Safe-Area Padding** | ❌ | ❌ | ❌ | ✅ | 🟡 | `top=42` padding prevents occlusion beneath status bar or camera notches. |
| **Mobile 4-Row Control Stack** | ❌ | ❌ | ❌ | ✅ | 🟡 | Row 1: File/Status; Row 2: Transport; Row 3: Trim (100%); Row 4: Export (50-50). |
| **Thread-Safe UI Sync** | ✅ | ✅ | ✅ | ✅ | 🟡 | `_ui_lock` and asyncio loop event marshaling preventing protocol collisions. |

---

### 2.6. Visual Waveform Peeking & Trimming (Frontend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **90-Bar Fixed Desktop Waveform**| ✅ | ✅ | ✅ | ❌ | ❌ | 90 bars of 6px width + 2px spacing (`718px` total width). |
| **Screen-Adaptive Mobile Bars** | ❌ | ❌ | ❌ | ✅ | 🟡 | Dynamically calculates bar count to fit compact 360dp mobile viewports. |
| **Interactive Peeking / Scrubbing**| ✅ | ✅ | ✅ | ✅ | 🟡 | `ft.GestureDetector` tracking tap and pan gestures with sub-pixel precision. |
| **Dynamic Duration Readout** | ✅ | ✅ | ✅ | ✅ | 🟡 | Dynamic speed-scaled duration calculation (`00:00.0 / 00:00.0`). |
| **Peak Level Meter Display** | ✅ | ✅ | ✅ | ✅ | 🟡 | Displays peak dB metrics calculated directly from in-memory samples. |
| **Draggable Trim Handles** | ✅ | ✅ | ✅ | ✅ | 🟡 | Start `[S]` (cyan) and End `[E]` (amber) interactive marker heads. |
| **Trim Collision Prevention** | ✅ | ✅ | ✅ | ✅ | 🟡 | Prevents start marker from crossing end marker (`start <= end`). |
| **Zero-Duration Delete Warning** | ✅ | ✅ | ✅ | ✅ | 🟡 | Displays warning and disables `APPLY` if start and end heads collide. |
| **Trim Playback Confinement** | ✅ | ✅ | ✅ | ✅ | 🟡 | Preview playback is strictly bounded within active trim selection. |
| **Non-Destructive Trimming** | ✅ | ✅ | ✅ | ✅ | 🟡 | Full track raw and DSP buffers retained; markers can re-extend outward. |
| **Bidirectional Time Mapping** | ✅ | ✅ | ✅ | ✅ | 🟡 | Translates between original file timestamps and speed-scaled GUI space. |

---

### 2.7. Presets & Controls (Frontend & Backend)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Slowed + Reverb Preset** | ✅ | ✅ | ✅ | ✅ | 🟡 | 0.80x speed, -3.8 semitones, 40% reverb level. |
| **Nightcore Preset** | ✅ | ✅ | ✅ | ✅ | 🟡 | 1.20x speed, +3.1 semitones, 0% reverb level. |
| **Reset / Default Preset** | ✅ | ✅ | ✅ | ✅ | 🟡 | 1.00x speed, 0 pitch, 0% reverb, 0% bass boost. |
| **Buffer Status Tracking** | ✅ | ✅ | ✅ | ✅ | 🟡 | Visual badge ("CURRENT MODIFIED" vs "OLD MODIFIED"). |
| **Async Playback Poller** | ✅ | ✅ | ✅ | ✅ | 🟡 | Smooth 20fps (`0.05s`) timeline poller running on Flet's event loop. |
| **Error Copy to Clipboard** | ✅ | ✅ | ✅ | ✅ | 🟡 | One-click error message copy with temporary visual confirmation badge. |

---

### 2.8. Diagnostics, Telemetry & Setup (Application-Wide)

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Floating Debug Bug Icon** | ✅ | ✅ | ✅ | ✅ | 🟡 | Amber bug icon (`FA_BUG`) visible when application is in debug mode. |
| **Baked Debug Mode in APK** | ❌ | ❌ | ❌ | ✅ | 🟡 | `--debug` builds bake `DEBUG_MODE=True` into package for mobile. |
| **JSON Diagnostics Dump** | ✅ | ✅ | ✅ | ✅ | 🟡 | Exports complete system state, architecture, packages, and logs. |
| **Circular Ring Buffer Logger** | ✅ | ✅ | ✅ | ✅ | 🟡 | In-memory `DiagnosticLogger` retaining last 250 timestamped log events. |
| **Missing FFmpeg Setup View** | ✅ | ✅ | ✅ | ❌ | ❌ | Cyber GUI (`FFmpegSetupView`) with progress bar for automatic static download. |

---

### 2.9. Packaging & Build Automation

| Subsystem / Capability | Windows | Linux | macOS | Android | iOS | Implementation Driver / Backend Notes |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Single-File Desktop Binary** | ✅ | ✅ | ✅ | ❌ | ❌ | PyInstaller standalone packaging (`redu-dev/build_binary.py`). |
| **Universal Android APK** | ❌ | ❌ | ❌ | ✅ | ❌ | Automated packaging (`redu-dev/build_mobile_apk.py` / `flet build apk`). |
| **Multi-ABI Concurrency Control** | ❌ | ❌ | ❌ | ✅ | ❌ | Gradle flags `-Dorg.gradle.parallel=false` prevent etags race conditions. |
| **GitHub Actions CI/CD** | ✅ | ✅ | ✅ | ✅ | 🟡 | Workflows: `build-apk.yml`, `ci.yml`, `release.yml`. |

---

## 3. Platform Architectural Comparison

| Architecture Dimension | Desktop Edition (Windows / Linux / macOS) | Mobile Edition (Android / iOS) |
| :--- | :--- | :--- |
| **Primary Binary / Runtime** | Python 3.12–3.14 via PyInstaller executable | Python 3.14 via `flet build apk` (Android Zygote) |
| **Audio Processing C-Core** | Standalone FFmpeg binary (`ffmpeg.exe` / `ffmpeg`) | In-process PyAV (`av`) + `flet-libffmpeg` shared libraries |
| **Audio Playback Backend** | `sounddevice` (PortAudio C streaming callback) | `flet-audio` (Native Flutter audio player service) |
| **File Access Paradigm** | Direct OS filesystem paths (`C:\...`, `/home/...`) | Android Storage Access Framework (`content://...`) |
| **Waveform Rendering** | 90 fixed 6px bars (`718px` total width) | Dynamically computed bars scaled to mobile screen width |
| **Layout Organization** | Static multi-card dashboard | Static 4-row top bar + `PEEK`/`EFFECTS` animated tabs |
| **Export Format Standard** | MP3, Opus, WAV | M4A (Hardware/Software AAC) |
