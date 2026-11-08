"""
Android FFmpeg provider for SloVerb Studio.

Locates bundled native libraries (e.g., libffmpeg.so) within the Android APK
native library path (jniLibs/<abi>/) or app-private storage.
"""

import glob
import os
import sys
from typing import List, Optional

from slowverb.ffmpeg.base import BaseFFmpegProvider
from slowverb.platform import get_android_abi


class AndroidFFmpegProvider(BaseFFmpegProvider):
    """FFmpeg provider resolving native libffmpeg.so on Android systems."""

    def __init__(self, package_name: str = "com.redu.sloverb", custom_lib_dir: Optional[str] = None):
        self.package_name = package_name
        self.custom_lib_dir = custom_lib_dir

    def _get_candidate_paths(self) -> List[str]:
        abi = get_android_abi()
        candidates: List[str] = []

        # 1. Environment variable override
        env_binary = os.environ.get("FFMPEG_BINARY")
        if env_binary:
            candidates.append(env_binary)

        # 2. Custom directory (useful for testing and custom packaging)
        if self.custom_lib_dir:
            candidates.extend([
                os.path.join(self.custom_lib_dir, "libffmpeg.so"),
                os.path.join(self.custom_lib_dir, abi, "libffmpeg.so"),
                os.path.join(self.custom_lib_dir, "ffmpeg"),
            ])

        # 3. Android app native library directory from environment
        lib_dir = os.environ.get("LIB_DIR")
        if lib_dir:
            candidates.append(os.path.join(lib_dir, "libffmpeg.so"))
            candidates.append(os.path.join(lib_dir, "ffmpeg"))

        # 4. Standard Android APK unpack locations (/data/app/<pkg>-*/lib/<abi>/libffmpeg.so)
        for pattern in [
            f"/data/app/*{self.package_name}*/lib/{abi}/libffmpeg.so",
            f"/data/app/{self.package_name}*/lib/{abi}/libffmpeg.so",
            f"/data/data/{self.package_name}/lib/libffmpeg.so",
            f"/data/data/{self.package_name}/files/bin/ffmpeg",
            f"/data/data/{self.package_name}/files/libffmpeg.so",
        ]:
            matches = glob.glob(pattern)
            candidates.extend(matches)

        return candidates

    def get_binary_path(self) -> Optional[str]:
        for candidate in self._get_candidate_paths():
            if candidate and os.path.isfile(candidate):
                # Verify executable bit or readability
                if os.access(candidate, os.X_OK) or os.access(candidate, os.R_OK):
                    return os.path.abspath(candidate)
        return None

    def is_available(self) -> bool:
        path = self.get_binary_path()
        return path is not None and os.path.isfile(path)

    def get_platform_name(self) -> str:
        return "android"
