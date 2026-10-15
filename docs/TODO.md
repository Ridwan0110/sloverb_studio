# SloVerb Studio — Project Backlog & TODO

## Completed Items

### Dynamic Waveform & Status Bar Updates on Preview Playback (Resolved in v0.2.0)
- **Root Cause**:
  - In Flet 1.0 desktop on Windows, `page.update()` queues MsgPack frames into an `asyncio.Queue` (`_FletSocketServer__send_queue`).
  - When called from standard Python background threads (`threading.Thread`), the asyncio event loop waiting on socket I/O is not notified because `asyncio.Queue.put_nowait()` does not trigger the event loop's wakeup mechanism. As a result, frame updates remained pending until an external event (window resize, button click, slider drag) woke up the event loop.
- **Resolution**:
  1. **Thread-Safe Event Loop Dispatch**: Updated `SlowVerbApp.update_ui()` and `FFmpegSetupView._safe_update()` to detect thread context. When called outside the main event loop, updates are marshaled to `loop.call_soon_threadsafe(self._scheduled_page_update)`, which writes to the loop's self-pipe/IOCP and immediately wakes up the loop to flush the socket stream to the Flutter client.
  2. **Async Playback Poller Task**: Migrated `_start_playback_poller()` to use `page.run_task(self._async_playback_poller, ...)` directly on Flet's event loop with smooth 20fps (`0.05s`) ticks, with seamless fallback to `threading.Thread` for headless/test environments.
  3. **Immediate Preview Completion Flush**: Background audio render thread marshals the completed preview audio, waveform extraction, duration text, peak dB readout, and status bar update directly to the event loop, automatically launching the async poller without requiring any user interaction.

---

## Additional Backlog Items
- [ ] Add batch export feature for processing multiple tracks with selected presets.
- [ ] Implement audio recording / microphone input capture.
- [ ] Add customizable high-shelf EQ (treble boost / air).
- [ ] Provide preset saving and loading to user configuration JSON.
- [ ] Add drag-and-drop file loading support onto the waveform card.
- [ ] Add Apple macOS DMG installer packaging (.dmg via create-dmg) for release distributions.
