"""
Abstract Base FFmpeg Provider interface for SloVerb Studio.

Defines the contract for platform-specific binary resolution and execution.
"""

from abc import ABC, abstractmethod
from typing import Optional


class BaseFFmpegProvider(ABC):
    """Abstract interface for locating and verifying FFmpeg on any platform."""

    @abstractmethod
    def get_binary_path(self) -> Optional[str]:
        """Returns the absolute path to the FFmpeg executable or shared library."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Returns True if a valid, executable FFmpeg binary is available."""
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """Returns the human-readable platform identifier (e.g. 'desktop', 'android', 'ios')."""
        pass
