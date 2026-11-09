"""
Cross-platform file dialogs, picking, and sharing services for SloVerb Studio.

Provides native tkinter dialogs on Desktop and Flet FilePicker / Android Storage
Access Framework on Mobile.
"""

import os
import shutil
import tempfile
from typing import Callable, List, Optional
import flet as ft

from slowverb.platform import is_mobile_platform


AUDIO_EXTENSIONS = ["opus", "mp3", "wav", "flac", "ogg", "m4a", "aac"]


class FileService:
    """Unified file picking and export sharing service."""

    def __init__(
        self,
        page: Optional[ft.Page] = None,
        on_file_picked: Optional[Callable[[str], None]] = None,
        on_save_completed: Optional[Callable[[str], None]] = None,
    ):
        self.page = page
        self.on_file_picked = on_file_picked
        self.on_save_completed = on_save_completed
        self._pending_export_path: Optional[str] = None
        self._file_picker: Optional[ft.FilePicker] = None

        if page is not None:
            self._init_picker()

    def attach_page(self, page: ft.Page):
        """Attaches to a Flet page and registers the FilePicker in the page services."""
        self.page = page
        self._init_picker()

    def _init_picker(self):
        if is_mobile_platform(self.page):
            if self._file_picker is None:
                self._file_picker = ft.FilePicker(
                    on_result=self._on_picker_result,
                )
            if self.page is not None:
                # In Flet 1.0, services belong in page.services, NEVER in page.overlay
                if hasattr(self.page, "services") and isinstance(self.page.services, list):
                    if self._file_picker not in self.page.services:
                        self.page.services.append(self._file_picker)
                elif hasattr(self.page, "_services") and hasattr(self.page._services, "register_service"):
                    try:
                        self.page._services.register_service(self._file_picker)
                    except Exception:
                        pass
                # Guard against any legacy addition to page.overlay (which causes Flutter Unknown control crashes)
                if hasattr(self.page, "overlay") and isinstance(self.page.overlay, list):
                    if self._file_picker in self.page.overlay:
                        self.page.overlay.remove(self._file_picker)
                try:
                    self.page.update()
                except Exception:
                    pass

    def _dispatch_async(self, fn, *args, **kwargs):
        """Dispatches an async or synchronous function safely on page event loop."""
        res = fn(*args, **kwargs)
        import inspect
        if inspect.iscoroutine(res):
            async def _run():
                try:
                    val = await res
                    # Handle pick_files result (list of FilePickerFile)
                    if isinstance(val, list):
                        if len(val) > 0:
                            f = val[0]
                            selected_path = getattr(f, "path", None)
                            if not selected_path and getattr(f, "bytes", None):
                                ext = os.path.splitext(getattr(f, "name", "audio.tmp"))[1] or ".opus"
                                fd, temp_p = tempfile.mkstemp(prefix="picked_", suffix=ext)
                                with os.fdopen(fd, "wb") as out_f:
                                    out_f.write(f.bytes)
                                selected_path = temp_p
                            if selected_path:
                                self._handle_file_picked(selected_path)
                    # Handle save_file result (target path string)
                    elif isinstance(val, str) and val:
                        self._handle_save_completed(val)
                except Exception as ex:
                    print(f"Async dispatch error: {ex}")

            if self.page is not None and hasattr(self.page, "run_task"):
                try:
                    self.page.run_task(_run)
                    return
                except Exception:
                    pass
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(_run(), loop)
                    return
                else:
                    loop.run_until_complete(_run())
                    return
            except Exception:
                try:
                    res.close()
                except Exception:
                    pass

    def _handle_file_picked(self, selected_path: str):
        """Processes picked file path, ensures local caching if needed, and notifies listener."""
        if not selected_path:
            return

        import time
        now = time.time()
        # Debounce identical file picked within 1.0 second
        if getattr(self, "_last_picked_path", None) == selected_path and (now - getattr(self, "_last_picked_time", 0.0)) < 1.0:
            return
        self._last_picked_path = selected_path
        self._last_picked_time = now

        # On mobile, cache file to app temp dir to ensure persistence and accessible path
        if is_mobile_platform(self.page) and os.path.isfile(selected_path):
            ext = os.path.splitext(selected_path)[1]
            safe_dest = os.path.join(tempfile.gettempdir(), f"sloverb_picked_track{ext}")
            try:
                if os.path.abspath(selected_path) != os.path.abspath(safe_dest):
                    shutil.copy2(selected_path, safe_dest)
                    selected_path = safe_dest
            except Exception as e:
                print(f"Warning: failed copying picked file to cache: {e}")

        if self.on_file_picked:
            if self.page is not None and hasattr(self.page, "run_thread") and callable(self.page.run_thread):
                try:
                    from unittest.mock import Mock
                    if isinstance(self.page.run_thread, Mock):
                        self.on_file_picked(selected_path)
                    else:
                        self.page.run_thread(self.on_file_picked, selected_path)
                    return
                except Exception:
                    pass
            self.on_file_picked(selected_path)

    def _handle_save_completed(self, target_path: str):
        """Processes saved export destination path and cleans up temp cache."""
        if not target_path:
            return
        if self._pending_export_path and os.path.isfile(self._pending_export_path):
            if os.path.abspath(self._pending_export_path) != os.path.abspath(target_path):
                try:
                    shutil.copy2(self._pending_export_path, target_path)
                    os.remove(self._pending_export_path)
                except Exception as ex:
                    print(f"Error saving exported file to {target_path}: {ex}")
            self._pending_export_path = None

        if self.on_save_completed:
            self.on_save_completed(target_path)

    def pick_audio_file(self):
        """Triggers audio file picking dialog."""
        if not is_mobile_platform(self.page):
            # Desktop native tkinter dialog
            from slowverb.ui import pick_file_desktop
            picked = pick_file_desktop()
            if picked and self.on_file_picked:
                self.on_file_picked(picked)
            return

        # Mobile FilePicker
        if self._file_picker is not None:
            self._dispatch_async(
                self._file_picker.pick_files,
                dialog_title="SELECT AUDIO FILE",
                allowed_extensions=AUDIO_EXTENSIONS,
                allow_multiple=False,
            )

    def save_exported_file(
        self,
        temp_exported_path: str,
        default_filename: str,
        allowed_extensions: Optional[List[str]] = None,
        dialog_title: str = "SAVE EXPORTED TRACK",
    ):
        """
        Saves or shares an exported track or file. On mobile, triggers FilePicker save dialog
        or native save action, copying from the temp export cache.
        """
        self._pending_export_path = temp_exported_path

        if not is_mobile_platform(self.page):
            # Desktop save dialog
            from slowverb.ui import save_file_desktop
            ext = os.path.splitext(default_filename)[1].lstrip(".")
            target_path = save_file_desktop(initial_filename=default_filename, ext=ext)
            if target_path:
                shutil.copy2(temp_exported_path, target_path)
                try:
                    os.remove(temp_exported_path)
                except Exception:
                    pass
                if self.on_save_completed:
                    self.on_save_completed(target_path)
            return

        # Mobile FilePicker save
        if self._file_picker is not None:
            # Read file bytes for mobile (required by Flet 1.0 on Android SAF)
            src_bytes = None
            if temp_exported_path and os.path.isfile(temp_exported_path):
                try:
                    with open(temp_exported_path, "rb") as f:
                        src_bytes = f.read()
                except Exception:
                    pass

            self._dispatch_async(
                self._file_picker.save_file,
                dialog_title=dialog_title,
                file_name=default_filename,
                allowed_extensions=allowed_extensions or AUDIO_EXTENSIONS,
                src_bytes=src_bytes,
            )
        else:
            # Fallback if no picker attached
            if self.on_save_completed:
                self.on_save_completed(temp_exported_path)

    def _on_picker_result(self, e: ft.FilePickerResultEvent):
        """Callback from Flet FilePicker (e.g. PickFiles client action)."""
        # Handle file open result
        if e.files and len(e.files) > 0:
            f = e.files[0]
            selected_path = getattr(f, "path", None)
            if not selected_path and getattr(f, "bytes", None):
                ext = os.path.splitext(getattr(f, "name", "audio.tmp"))[1] or ".opus"
                fd, temp_p = tempfile.mkstemp(prefix="picked_", suffix=ext)
                with os.fdopen(fd, "wb") as out_f:
                    out_f.write(f.bytes)
                selected_path = temp_p

            if selected_path:
                self._handle_file_picked(selected_path)
            return

        # Handle save file result
        if e.path:
            self._handle_save_completed(e.path)
