"""
Desktop FFmpeg provider for Windows, macOS, and Linux.

Discovers system PATH, OS package managers, local project binaries,
and manages automatic downloads when missing.
"""

from typing import Optional
from slowverb.ffmpeg.base import BaseFFmpegProvider


class DesktopFFmpegProvider(BaseFFmpegProvider):
    """FFmpeg provider for desktop operating systems."""

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root

    def get_binary_path(self) -> Optional[str]:
        from slowverb.ffmpeg_manager import find_ffmpeg
        return find_ffmpeg(project_root=self.project_root)

    def is_available(self) -> bool:
        path = self.get_binary_path()
        if not path:
            return False
        from slowverb.ffmpeg_manager import is_valid_ffmpeg_binary
        return is_valid_ffmpeg_binary(path)

    def get_platform_name(self) -> str:
        return "desktop"
