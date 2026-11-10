"""Tests for cross-platform FileService in slowverb.file_dialogs."""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from slowverb.file_dialogs import AUDIO_EXTENSIONS, FileService


def test_audio_extensions_list():
    assert "opus" in AUDIO_EXTENSIONS
    assert "mp3" in AUDIO_EXTENSIONS
    assert "wav" in AUDIO_EXTENSIONS


def test_file_service_init_desktop():
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    page.overlay = []
    page.services = []

    service = FileService(page=page)
    assert service.page == page
    assert len(page.overlay) == 0
    assert len(page.services) == 0


def test_file_service_init_mobile():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    service = FileService(page=page)
    assert service.page == page
    assert len(page.overlay) == 0
    assert len(page.services) == 1
    assert service._file_picker in page.services


def test_file_service_pick_mobile():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    picked_files = []
    service = FileService(page=page, on_file_picked=lambda p: picked_files.append(p))

    # Trigger pick
    with patch.object(service._file_picker, "pick_files", new_callable=MagicMock) as mock_pick:
        service.pick_audio_file()
        mock_pick.assert_called_once()

    # Simulate callback
    event = MagicMock()
    fake_file = MagicMock()
    fake_file.path = "/data/user/0/com.redu.sloverb/cache/track.mp3"
    event.files = [fake_file]
    event.path = None

    service._on_picker_result(event)
    assert len(picked_files) == 1
    assert picked_files[0] == "/data/user/0/com.redu.sloverb/cache/track.mp3"


def test_file_service_save_mobile():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    saved_files = []
    service = FileService(page=page, on_save_completed=lambda p: saved_files.append(p))

    with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as tf:
        tf.write(b"mock opus data")
        temp_export = tf.name

    target_export = temp_export + ".saved.opus"

    # Save file
    with patch.object(service._file_picker, "save_file", new_callable=MagicMock) as mock_save:
        service.save_exported_file(temp_export, "my_track_edited.opus")
        mock_save.assert_called_once()
        _, kwargs = mock_save.call_args
        assert kwargs.get("src_bytes") == b"mock opus data"

    # Simulate picker result with destination path
    event = MagicMock()
    event.files = None
    event.path = target_export

    service._on_picker_result(event)

    assert os.path.isfile(target_export)
    with open(target_export, "rb") as f:
        assert f.read() == b"mock opus data"

    assert len(saved_files) == 1
    assert saved_files[0] == target_export

    # Clean up
    if os.path.isfile(target_export):
        os.remove(target_export)

def test_file_service_pick_async_resolution():
    """Verify that awaiting pick_files returns FilePickerFile list and calls on_file_picked directly."""
    import asyncio
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    # Mock run_task so it actually executes the coroutine
    def fake_run_task(coro_fn, *args):
        coro = coro_fn(*args)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    page.run_task.side_effect = fake_run_task

    picked_files = []
    service = FileService(page=page, on_file_picked=lambda p: picked_files.append(p))

    fake_file = MagicMock()
    fake_file.path = "/data/user/0/com.redu.sloverb/cache/picked_track.opus"
    fake_file.bytes = None

    async def fake_pick_files(**kwargs):
        return [fake_file]

    with patch.object(service._file_picker, "pick_files", side_effect=fake_pick_files):
        service.pick_audio_file()

    assert len(picked_files) == 1
    assert picked_files[0] == "/data/user/0/com.redu.sloverb/cache/picked_track.opus"


def test_file_service_save_async_resolution():
    """Verify that awaiting save_file returns target path string and completes save directly."""
    import asyncio
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    def fake_run_task(coro_fn, *args):
        coro = coro_fn(*args)
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    page.run_task.side_effect = fake_run_task

    saved_files = []
    service = FileService(page=page, on_save_completed=lambda p: saved_files.append(p))

    with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as tf:
        tf.write(b"async export test bytes")
        temp_export = tf.name

    target_export = temp_export + ".saved.opus"

    async def fake_save_file(**kwargs):
        return target_export

    with patch.object(service._file_picker, "save_file", side_effect=fake_save_file):
        service.save_exported_file(temp_export, "my_track.opus")

    assert len(saved_files) == 1
    assert saved_files[0] == target_export
    assert os.path.isfile(target_export)
    with open(target_export, "rb") as f:
        assert f.read() == b"async export test bytes"

    if os.path.isfile(target_export):
        os.remove(target_export)

def test_file_service_preserves_original_filename(tmp_path):
    """Verify that picking an audio file preserves original filename in cache on mobile."""
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []
    page.services = []

    test_src = tmp_path / "original_track_name.opus"
    test_src.write_bytes(b"mock audio bytes")

    picked = []
    service = FileService(page=page, on_file_picked=lambda p: picked.append(p))

    service._handle_file_picked(str(test_src), original_filename="original_track_name.opus")
    assert len(picked) == 1
    assert os.path.basename(picked[0]) == "original_track_name.opus"

