## Version: v0.1.0

Initial release of SloVerb Studio, a high-performance, minimalist desktop audio editing application designed for creating slowed and reverb, nightcore, pitch-shifted, and bass-boosted audio tracks. Features real-time audio playback with waveform peeking, in-app FFmpeg configuration, and standalone Windows binary distribution.

## Added
- Desktop graphical user interface built with Flet featuring robotic monospace styling, interactive waveform peeking, timeline display, and audio export controls (feature)
- Core DSP audio engine powered by FFmpeg supporting rubberband speed and pitch shifting, multi-tap reverb diffusion, low-shelf bass boost, and soft peak limiting (feature)
- Low-latency real-time audio playback using sounddevice with instant seeking, scrubbing, and transport controls (feature)
- One-click presets for Slowed + Reverb, Nightcore, and Default unity playback settings (feature)
- Audio export pipeline supporting high-quality Opus (VBR) and MP3 (CBR) formats (feature)
- Cross-platform automatic FFmpeg discovery across system PATH, standard directories, and local project folders (feature)
- In-app GUI setup dialog with progress bar for downloading and configuring FFmpeg binaries directly inside the desktop interface (feature)
- Application package version tracking and visual version badge in the top-right header bar (feature)
- Standalone Windows x86-64 executable packaging pipeline powered by PyInstaller (feature)
- Command-line diagnostic and inspection flags for version display, help text, and environment verification in bundled binaries (feature)
- Asset-aware startup resolution supporting bundled PyInstaller environments (improvement)
- Unit and integration test suite covering DSP filters, audio engine, player streaming, GUI states, and build processes (improvement)
- Comprehensive project documentation including architecture, installation, and user guides (misc)
- Design tokens and design system specifications for UI styling and typography (misc)
- Developer and AI agent workflow instructions (misc)
- Multi-platform continuous integration workflow covering Windows, Linux, and macOS (misc)

## Changed
- Migrated dependency management from requirements.py to split requirements.txt and requirements-dev.txt (improvement)
- Refined CI workflow dependency installation on macOS to install FFmpeg via Homebrew alongside PortAudio (improvement)

## Fixed
- Resolved macOS CI workflow failure by configuring Homebrew FFmpeg installation and restricting the setup-ffmpeg action to Windows and Linux runners (bug)

## Removed
- Obsolete main.py backward compatibility test from entry point test suite (misc)
- Legacy requirements.py dependency helper script in favor of standard pip requirements manifests (misc)
