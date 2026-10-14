# SloVerb Studio — Project Backlog & TODO

## High Priority: Dynamic Waveform & Status Bar Updates on Preview Playback

### Problem Description
When clicking `PREVIEW EFFECTS` in the application:
1. The background thread renders audio with FFmpeg and loads it into the `AudioPlayer`.
2. Audio playback begins and is audible.
3. However, on screen:
   - The **Peak Bar** (waveform bars and `PEAK: -- dB` text readout) does not dynamically update as playback progresses.
   - The **Status Bar** (playback duration banner and `CURRENT MODIFIED VERSION` indicator) does not visually update to reflect active preview playback.
4. The visual elements only refresh on-screen when:
   - The user manually clicks or scrubs anywhere on the waveform ("peeks").
   - The user presses STOP and then PLAY.

### Root Cause Analysis & Technical Context
- **Flet Desktop Event Loop vs Background Threads**:
  - In Flet 1.0 desktop on Windows, the UI is driven by an underlying event loop communicating via WebSockets / IPC to the Flutter desktop runner.
  - `page.update()` calls made from background `threading.Thread` instances (e.g. `_start_playback_poller` or `background_render`) can experience message batching or synchronization stalls with the Flutter frontend if not dispatched through Flet's main event loop or thread marshal.
  - When the user triggers a UI event (like tapping the waveform gesture detector or clicking transport buttons), an event is processed on the main UI loop, immediately flushing all pending control patches and updating the visual canvas.

### Proposed Solutions for Future Resolution
1. **Async Flet Loop / Main Thread Dispatch**:
   - Migrate the poller thread to use Flet's async event scheduling (`page.run_task` or `asyncio.create_task`) to dispatch UI updates directly onto the Flutter message bus.
2. **Periodic UI Flush Timer**:
   - Introduce a timer or UI subscription on the main page loop that queries player state at 20Hz and flushes state changes synchronously on the main thread.
3. **Canvas-Based Waveform**:
   - Instead of 90 individual `Container` widgets inside a `Row`, render waveform bars using `flet.canvas.Canvas` with custom shapes, reducing control tree diffing overhead.

---

## Additional Backlog Items
- [ ] Add batch export feature for processing multiple tracks with selected presets.
- [ ] Implement audio recording / microphone input capture.
- [ ] Add customizable high-shelf EQ (treble boost / air).
- [ ] Provide preset saving and loading to user configuration JSON.
- [ ] Add drag-and-drop file loading support onto the waveform card.
- [ ] Add Apple macOS DMG installer packaging (.dmg via create-dmg) for release distributions.

