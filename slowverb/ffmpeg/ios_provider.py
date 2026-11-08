"""
iOS FFmpeg provider interface stub for SloVerb Studio.

iOS does not permit fork/exec (subprocess.Popen). This provider defines the
architecture hook for native C framework or Flutter method channel bindings.
"""

from typing import Optional
from slowverb.ffmpeg.base import BaseFFmpegProvider


class IOSFFmpegProvider(BaseFFmpegProvider):
    """FFmpeg provider interface for iOS environments."""

    def __init__(self, bridge_name: str = "ffmpeg_kit"):
        self.bridge_name = bridge_name

    def get_binary_path(self) -> Optional[str]:
        # On iOS, FFmpeg is statically or dynamically linked inside the app bundle
        # rather than executed as a standalone POSIX binary.
        return None

    def is_available(self) -> bool:
        # Returns True once the native iOS Flutter plugin / C framework is bound
        return False

    def get_platform_name(self) -> str:
        return "ios"
