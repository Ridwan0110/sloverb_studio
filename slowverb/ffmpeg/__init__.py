"""
FFmpeg provider package for SloVerb Studio.

Exports:
- BaseFFmpegProvider: Abstract interface
- DesktopFFmpegProvider: Desktop (Windows/macOS/Linux) provider
- AndroidFFmpegProvider: Android native library provider
- IOSFFmpegProvider: iOS modular provider stub
- get_ffmpeg_provider: Factory resolving the provider for the active platform
"""

from typing import Optional
import flet as ft

from slowverb.ffmpeg.base import BaseFFmpegProvider
from slowverb.ffmpeg.desktop_provider import DesktopFFmpegProvider
from slowverb.ffmpeg.android_provider import AndroidFFmpegProvider
from slowverb.ffmpeg.ios_provider import IOSFFmpegProvider


def get_ffmpeg_provider(
    page: Optional[ft.Page] = None,
    project_root: Optional[str] = None,
) -> BaseFFmpegProvider:
    """
    Returns the appropriate FFmpeg provider instance based on runtime platform.
    """
    from slowverb.platform import PlatformType, detect_platform

    plat = detect_platform(page)
    if plat == PlatformType.ANDROID:
        return AndroidFFmpegProvider()
    elif plat == PlatformType.IOS:
        return IOSFFmpegProvider()
    return DesktopFFmpegProvider(project_root=project_root)


__all__ = [
    "BaseFFmpegProvider",
    "DesktopFFmpegProvider",
    "AndroidFFmpegProvider",
    "IOSFFmpegProvider",
    "get_ffmpeg_provider",
]
