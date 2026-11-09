"""Tests for cross-platform detection in slowverb.platform."""

import os
from unittest.mock import MagicMock, patch
import pytest
import flet as ft

from slowverb.platform import (
    PlatformType,
    detect_platform,
    get_android_abi,
    is_mobile_environment,
    is_mobile_platform,
)


def test_detect_platform_from_page_android():
    page = MagicMock()
    page.platform = ft.PagePlatform.ANDROID
    assert detect_platform(page) == PlatformType.ANDROID
    assert is_mobile_environment(page) is True


def test_detect_platform_from_page_ios():
    page = MagicMock()
    page.platform = ft.PagePlatform.IOS
    assert detect_platform(page) == PlatformType.IOS
    assert is_mobile_environment(page) is True


def test_detect_platform_from_page_desktop():
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    page.width = 1120
    assert detect_platform(page) == PlatformType.DESKTOP
    assert is_mobile_environment(page) is False


def test_detect_platform_from_page_narrow_desktop():
    page = MagicMock()
    page.platform = ft.PagePlatform.WINDOWS
    page.width = 400
    assert detect_platform(page) == PlatformType.DESKTOP
    assert is_mobile_environment(page) is True


def test_detect_platform_env_override():
    with patch.dict(os.environ, {"FLET_PLATFORM": "android"}):
        assert detect_platform(None) == PlatformType.ANDROID
        assert is_mobile_environment(None) is True

    with patch.dict(os.environ, {"FLET_PLATFORM": "ios"}):
        assert detect_platform(None) == PlatformType.IOS
        assert is_mobile_environment(None) is True


def test_get_android_abi():
    with patch("platform.machine", return_value="aarch64"):
        assert get_android_abi() == "arm64-v8a"
    with patch("platform.machine", return_value="x86_64"):
        assert get_android_abi() == "x86_64"
    with patch("platform.machine", return_value="armv7l"):
        assert get_android_abi() == "armeabi-v7a"


def test_is_mobile_platform():
    android_page = MagicMock(platform=ft.PagePlatform.ANDROID)
    ios_page = MagicMock(platform=ft.PagePlatform.IOS)
    desktop_page = MagicMock(platform=ft.PagePlatform.WINDOWS, width=400)

    assert is_mobile_platform(android_page) is True
    assert is_mobile_platform(ios_page) is True
    assert is_mobile_platform(desktop_page) is False

    with patch.dict(os.environ, {"SLOVERB_MOBILE_UI": "1"}):
        assert is_mobile_platform(desktop_page) is False
        assert is_mobile_environment(desktop_page) is True
