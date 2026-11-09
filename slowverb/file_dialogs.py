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
        """Attaches to a Flet page and registers the FilePicker in the overlay."""
        self.page = page
        self._init_picker()

    def _init_picker(self):
        if is_mobile_platform(self.page):
            if self.page is not None and hasattr(self.page, "overlay"):
                self._file_picker = ft.FilePicker(
                    on_result=self._on_picker_result,
                )
                if self._file_picker not in self.page.overlay:
                    self.page.overlay.append(self._file_picker)
                    try:
                        self.page.update()
                    except Exception:
                        pass

    def _dispatch_async(self, fn, *args, **kwargs):
        """Dispatches an async or synchronous function safely on page event loop."""
        res = fn(*args, **kwargs)
        import inspect
        if inspect.iscoroutine(res):
            if self.page is not None and hasattr(self.page, "run_task"):
                try:
                    self.page.run_task(lambda: res)
                    return
                except Exception:
                    pass
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.run_coroutine_threadsafe(res, loop)
                    return
                else:
                    loop.run_until_complete(res)
                    return
            except Exception:
                try:
                    res.close()
                except Exception:
                    pass

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
            self._dispatch_async(
                self._file_picker.save_file,
                dialog_title=dialog_title,
                file_name=default_filename,
                allowed_extensions=allowed_extensions or AUDIO_EXTENSIONS,
            )
        else:
            # Fallback if no picker attached
            if self.on_save_completed:
                self.on_save_completed(temp_exported_path)

    def _on_picker_result(self, e: ft.FilePickerResultEvent):
        """Callback from Flet FilePicker."""
        # Handle file open result
        if e.files and len(e.files) > 0:
            selected_path = e.files[0].path
            if selected_path and self.on_file_picked:
                self.on_file_picked(selected_path)
            return

        # Handle save file result
        if e.path:
            target_path = e.path
            if self._pending_export_path and os.path.isfile(self._pending_export_path):
                try:
                    shutil.copy2(self._pending_export_path, target_path)
                    os.remove(self._pending_export_path)
                except Exception as ex:
                    print(f"Error saving exported file to {target_path}: {ex}")
                self._pending_export_path = None

            if self.on_save_completed:
                self.on_save_completed(target_path)
