"""Tests for FFmpeg discovery, validation, architecture detection, and auto-downloading."""

import os
import platform
import subprocess
from unittest.mock import MagicMock, patch
import pytest

from slowverb.ffmpeg_manager import (
    download_ffmpeg,
    find_ffmpeg,
    find_local_ffmpeg,
    find_system_ffmpeg,
    get_download_urls,
    is_valid_ffmpeg_binary,
    normalize_platform_arch,
    prompt_and_ensure_ffmpeg,
)


def test_is_valid_ffmpeg_binary_nonexistent():
    """Verify non-existent file returns False."""
    assert is_valid_ffmpeg_binary("non_existent_ffmpeg_path_12345.exe") is False
    assert is_valid_ffmpeg_binary("") is False


def test_is_valid_ffmpeg_binary_real_or_mocked():
    """Verify is_valid_ffmpeg_binary executes ffmpeg -version and checks returncode."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = subprocess.CompletedProcess(args=["ffmpeg", "-version"], returncode=0)
        with patch("os.path.isfile", return_value=True):
            assert is_valid_ffmpeg_binary("mock_ffmpeg.exe") is True

        mock_run.return_value = subprocess.CompletedProcess(args=["ffmpeg", "-version"], returncode=1)
        with patch("os.path.isfile", return_value=True):
            assert is_valid_ffmpeg_binary("mock_ffmpeg.exe") is False


def test_find_system_ffmpeg_env_var(tmp_path):
    """Verify FFMPEG_BINARY environment variable override is prioritized."""
    fake_ffmpeg = tmp_path / "custom_ffmpeg.exe"
    fake_ffmpeg.write_text("fake binary")

    with patch.dict(os.environ, {"FFMPEG_BINARY": str(fake_ffmpeg)}):
        with patch("slowverb.ffmpeg_manager.is_valid_ffmpeg_binary", return_value=True):
            found = find_system_ffmpeg()
            assert found == os.path.abspath(str(fake_ffmpeg))


def test_find_system_ffmpeg_path(tmp_path):
    """Verify shutil.which resolves system PATH ffmpeg."""
    fake_path = str(tmp_path / "system_ffmpeg.exe")
    with patch.dict(os.environ, {}, clear=True):
        with patch("shutil.which", return_value=fake_path):
            with patch("slowverb.ffmpeg_manager.is_valid_ffmpeg_binary", return_value=True):
                found = find_system_ffmpeg()
                assert found == os.path.abspath(fake_path)


def test_find_local_ffmpeg_in_project_dir(tmp_path):
    """Verify local project root ./ffmpeg/ffmpeg.exe is located."""
    local_dir = tmp_path / "ffmpeg"
    local_dir.mkdir()
    exe_name = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
    fake_bin = local_dir / exe_name
    fake_bin.write_text("fake local")

    with patch("slowverb.ffmpeg_manager.is_valid_ffmpeg_binary", return_value=True):
        found = find_local_ffmpeg(project_root=str(tmp_path))
        assert found == os.path.abspath(str(fake_bin))


def test_find_ffmpeg_precedence(tmp_path):
    """Verify system PATH is prioritized over local folder."""
    sys_path = str(tmp_path / "sys_ffmpeg.exe")
    local_path = str(tmp_path / "ffmpeg" / "ffmpeg.exe")

    with patch("slowverb.ffmpeg_manager.find_system_ffmpeg", return_value=sys_path):
        with patch("slowverb.ffmpeg_manager.find_local_ffmpeg", return_value=local_path):
            assert find_ffmpeg() == sys_path

    # Fallback to local when system is None
    with patch("slowverb.ffmpeg_manager.find_system_ffmpeg", return_value=None):
        with patch("slowverb.ffmpeg_manager.find_local_ffmpeg", return_value=local_path):
            assert find_ffmpeg() == local_path


def test_normalize_platform_arch():
    """Verify platform and architecture string normalization."""
    os_name, arch = normalize_platform_arch()
    assert os_name in ("windows", "darwin", "linux")
    assert arch in ("x86_64", "arm64")


def test_get_download_urls():
    """Verify candidate download URLs are returned for current platform."""
    urls = get_download_urls()
    assert len(urls) > 0
    assert any("http" in u for u in urls)


def test_prompt_and_ensure_ffmpeg_user_declines():
    """Verify FileNotFoundError is raised if FFmpeg is missing and user declines."""
    with patch("slowverb.ffmpeg_manager.find_ffmpeg", return_value=None):
        with pytest.raises(FileNotFoundError) as exc_info:
            prompt_and_ensure_ffmpeg(interactive=False, prompt_callback=lambda: False)

        assert "FFmpeg is required" in str(exc_info.value)


def test_prompt_and_ensure_ffmpeg_user_accepts(tmp_path):
    """Verify download_ffmpeg is triggered if user accepts prompt."""
    target_bin = str(tmp_path / "ffmpeg" / "ffmpeg.exe")
    with patch("slowverb.ffmpeg_manager.find_ffmpeg", return_value=None):
        with patch("slowverb.ffmpeg_manager.download_ffmpeg", return_value=target_bin) as mock_dl:
            res = prompt_and_ensure_ffmpeg(
                interactive=False,
                prompt_callback=lambda: True,
                project_root=str(tmp_path),
            )
            assert res == target_bin
            mock_dl.assert_called_once()
