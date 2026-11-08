"""Tests for BaseFFmpegProvider and platform implementations."""

import os
import tempfile
from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from slowverb.ffmpeg import (
    AndroidFFmpegProvider,
    BaseFFmpegProvider,
    DesktopFFmpegProvider,
    IOSFFmpegProvider,
    get_ffmpeg_provider,
)


def test_get_ffmpeg_provider_desktop():
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    provider = get_ffmpeg_provider(page)
    assert isinstance(provider, DesktopFFmpegProvider)
    assert provider.get_platform_name() == "desktop"


def test_get_ffmpeg_provider_android():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    provider = get_ffmpeg_provider(page)
    assert isinstance(provider, AndroidFFmpegProvider)
    assert provider.get_platform_name() == "android"


def test_get_ffmpeg_provider_ios():
    page = MagicMock()
    page.platform = ft.PagePlatform.IOS
    provider = get_ffmpeg_provider(page)
    assert isinstance(provider, IOSFFmpegProvider)
    assert provider.get_platform_name() == "ios"
    assert provider.is_available() is False
    assert provider.get_binary_path() is None


def test_android_provider_custom_lib_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_so = os.path.join(tmp_dir, "libffmpeg.so")
        with open(fake_so, "w") as f:
            f.write("mock binary")

        provider = AndroidFFmpegProvider(custom_lib_dir=tmp_dir)
        assert provider.get_binary_path() == os.path.abspath(fake_so)
        assert provider.is_available() is True


def test_android_provider_env_override():
    with tempfile.TemporaryDirectory() as tmp_dir:
        fake_bin = os.path.join(tmp_dir, "ffmpeg")
        with open(fake_bin, "w") as f:
            f.write("mock binary")

        with patch.dict(os.environ, {"FFMPEG_BINARY": fake_bin}):
            provider = AndroidFFmpegProvider()
            assert provider.get_binary_path() == os.path.abspath(fake_bin)
            assert provider.is_available() is True
