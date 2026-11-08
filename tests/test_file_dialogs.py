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

    service = FileService(page=page)
    assert service.page == page
    assert len(page.overlay) == 1


def test_file_service_pick_mobile():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    page.overlay = []

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
