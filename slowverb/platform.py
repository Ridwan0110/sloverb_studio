"""
Cross-platform environment detection utilities for SloVerb Studio.

Detects runtime platform (Desktop, Android, iOS, Web) and viewport metrics
to dynamically switch layouts and hardware abstractions.
"""

from enum import Enum
import os
import platform
import sys
from typing import Optional

import flet as ft


class PlatformType(Enum):
    """Supported target platform categories."""
    DESKTOP = "desktop"
    ANDROID = "android"
    IOS = "ios"
    WEB = "web"


def detect_platform(page: Optional[ft.Page] = None) -> PlatformType:
    """
    Detects the active runtime platform.
    Prioritizes Flet Page.platform, falling back to OS indicators.
    """
    if page is not None and hasattr(page, "platform") and page.platform:
        if page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.ANDROID_TV):
            return PlatformType.ANDROID
        elif page.platform == ft.PagePlatform.IOS:
            return PlatformType.IOS
        elif page.platform in (ft.PagePlatform.WINDOWS, ft.PagePlatform.MACOS, ft.PagePlatform.LINUX):
            return PlatformType.DESKTOP

    if page is not None and getattr(page, "web", False):
        return PlatformType.WEB

    # Environment variable overrides (e.g., during packaging or simulation)
    env_plat = os.environ.get("FLET_PLATFORM", "").lower()
    if env_plat == "android":
        return PlatformType.ANDROID
    elif env_plat == "ios":
        return PlatformType.IOS
    elif env_plat in ("windows", "macos", "linux", "desktop"):
        return PlatformType.DESKTOP

    # Android OS runtime indicators
    if hasattr(sys, "getandroidapilevel") or os.environ.get("ANDROID_ROOT") is not None:
        return PlatformType.ANDROID

    # iOS runtime indicators
    if sys.platform == "darwin" and ("iPhone" in platform.machine() or "iPad" in platform.machine()):
        return PlatformType.IOS

    return PlatformType.DESKTOP


def is_mobile_environment(page: Optional[ft.Page] = None) -> bool:
    """
    Returns True if the application is executing on a mobile OS (Android/iOS)
    or running in a narrow mobile-like portrait viewport (width < 650).
    """
    plat = detect_platform(page)
    if plat in (PlatformType.ANDROID, PlatformType.IOS):
        return True

    if page is not None and hasattr(page, "width"):
        w = getattr(page, "width", None)
        if isinstance(w, (int, float)) and 0 < w < 650:
            return True

    return False


def get_android_abi() -> str:
    """
    Resolves the primary Android ABI architecture for native binary lookup.
    """
    machine = platform.machine().lower()
    if "aarch64" in machine or "arm64" in machine:
        return "arm64-v8a"
    elif "arm" in machine or "v7" in machine:
        return "armeabi-v7a"
    elif "x86_64" in machine or "amd64" in machine:
        return "x86_64"
    elif "i686" in machine or "x86" in machine:
        return "x86"
    return "arm64-v8a"
