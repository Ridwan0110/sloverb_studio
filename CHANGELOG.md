## Version: v0.4.0

Release v0.4.0 introduces an interactive visual waveform trimming system with draggable marker heads and preview playback bounds, non-destructive audio editing with bidirectional time mapping across speed changes, playhead persistence across mode transitions, and Windows binary packaging fixes.

## Added
- Interactive visual waveform trim mode with draggable start and end marker heads and real-time gesture tracking (feature) #7 
- Packaging version resolution pipeline with fallback strategies and Windows PE version formatting (improvement)
- Architecture documentation and developer guidelines for visual trim geometry and time domains (misc)

## Changed
- Replaced legacy numeric trim input fields with interactive trim toggle buttons (improvement)

## Fixed
- Fixed upstream flet-cli crash on Windows caused by binary file open with encoding argument during packaging (bug)
- Fixed packaging failure when resolving application version by falling back to safe numeric defaults instead of UNKNOWN (bug)

## Version: v0.3.0

Release v0.3.0 brings major memory optimizations for large audio processing, a status bar button to copy error details to the clipboard with visual feedback, silent background FFmpeg processing on Windows without terminal popups, and reverb filter stability fixes.

## Added
- Memory-mapped buffer streaming and chunked peak analysis for handling audio files exceeding 50MB without memory exhaustion (feature)
- Status bar error copy button with real-time visual feedback confirming clipboard actions (feature) #4
- Native Win32 and Unix command-line clipboard integration with error detection and reporting (feature)
- Mobile platform clipboard support with Flet service fallback for Android and iOS environments (feature)
- Console suppression helper for executing background subprocesses without terminal window popups (improvement)

## Changed
- Replaced Tkinter clipboard management with zero-dependency native OS and CLI implementations (improvement)
- Standardized UTF-8 encoding across audio probing, buffer rendering, and export subprocesses (improvement)
- Fall back to `UNKNOWN` instead of a static version when version resolution fails during binary builds (improvement)
- Optimized and pruned unused imports across application modules (improvement)
- Dynamically asserted package version metadata across test suites (improvement)

## Fixed
- Fixed out-of-memory crashes and subprocess pipe deadlocks when processing large audio files (bug) #1 
- Fixed unwanted terminal window flashing on Windows by applying no-window flags to all subprocess calls (bug)
- Fixed audio filter errors at low reverb settings by enforcing a 0.01 minimum reflection decay floor (bug) #5 
- Fixed Unicode decoding errors when processing audio files with international titles and multi-byte characters (bug) #2 

## Removed
- Removed Tkinter dependency from desktop clipboard handling pipeline (improvement)

## Version: v0.2.0

Release v0.2.0 introduces universal cross-platform release packaging for Windows, Linux, and macOS, real-time dynamic playback UI updates via an asynchronous event-loop poller, clean application startup without default demo track loading, and configuration variable documentation.

## Added
- Cross-platform standalone binary packaging pipeline supporting Windows, Linux, and macOS with compressed distribution archives (feature)
- Automated GitHub Actions release build workflow for compiling multi-platform release assets (feature)
- Asynchronous playback poller utilizing the Flet page event loop for dynamic waveform, peak meter, and duration updates (feature)
- Formal application configuration and environment variable documentation (misc)
- Test suites covering universal binary packaging, archive creation, and thread-safe UI event-loop dispatching (improvement)

## Changed
- Replaced Windows-only packaging script with cross-platform build packager (improvement)
- Configured macOS CI and release workflows to install ffmpeg-full with Rubberband support (improvement)
- Updated development dependencies manifest to support cross-platform builds and testing (improvement)

## Fixed
- Resolved UI update stalls and race conditions during preview playback through thread-safe event loop dispatching (bug)
- Corrected CI workflow status badge link in project documentation (bug)

## Removed
- Automatic startup loading of hardcoded default audio track (improvement)
- Legacy Windows-only executable packaging script (misc)

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
