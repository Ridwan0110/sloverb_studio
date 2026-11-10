"""
Android APK Builder helper for SloVerb Studio.

Configures environment variables (JAVA_HOME, ANDROID_HOME, PATH),
checks dependencies, and invokes 'flet build apk'.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
from typing import Optional

# Ensure redu-dev directory is in sys.path to import shared build helpers
_DEV_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DEV_DIR.parent
if str(_DEV_DIR) not in sys.path:
    sys.path.insert(0, str(_DEV_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from build_binary import bake_debug_mode


class BuildTimer:
    """
    Background build timer that tracks elapsed duration and logs periodic heartbeats.
    Runs in a daemon thread alongside the build and formats total time in minutes and seconds.
    """

    def __init__(self, heartbeat_interval: float = 30.0):
        self.heartbeat_interval = heartbeat_interval
        self.start_time: float = 0.0
        self.end_time: float = 0.0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Starts the timer and background heartbeat thread."""
        self.start_time = time.time()
        self.end_time = 0.0
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_heartbeat, daemon=True)
        self._thread.start()
        return self

    def _run_heartbeat(self):
        """Periodically prints elapsed time while the build is running."""
        while not self._stop_event.wait(self.heartbeat_interval):
            elapsed = time.time() - self.start_time
            mins, secs = divmod(int(elapsed), 60)
            print(f">> [BUILD IN PROGRESS] Elapsed: {mins}m {secs:02d}s...")

    def stop(self) -> str:
        """Stops the timer and background thread, returning formatted elapsed duration."""
        self.end_time = time.time()
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        return self.format_elapsed()

    @property
    def elapsed_seconds(self) -> float:
        """Returns elapsed seconds, or total duration once stopped."""
        end = self.end_time if self.end_time > 0.0 else time.time()
        return max(0.0, end - self.start_time)

    def format_elapsed(self) -> str:
        """Formats elapsed duration into minutes and seconds (e.g. '10m 24s')."""
        mins, secs = divmod(int(self.elapsed_seconds), 60)
        return f"{mins}m {secs:02d}s"


def find_java_17() -> Optional[str]:
    """Locates Java 17 installation."""
    candidates = [
        os.environ.get("JAVA_HOME"),
        r"C:\Program Files\Eclipse Adoptium\jdk-17.0.21.9-hotspot",
        r"C:\Program Files\Java\jdk-17",
        r"C:\Program Files\Android\Android Studio\jbr",
    ]
    for c in candidates:
        if c and os.path.isdir(c) and os.path.isfile(os.path.join(c, "bin", "java.exe" if sys.platform == "win32" else "java")):
            return os.path.abspath(c)
    return None


def find_android_sdk() -> Optional[str]:
    """Locates Android SDK installation."""
    candidates = [
        os.environ.get("ANDROID_HOME"),
        os.environ.get("ANDROID_SDK_ROOT"),
        os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk"),
        r"C:\Android\sdk",
    ]
    for c in candidates:
        if c and os.path.isdir(c):
            return os.path.abspath(c)
    return None


def parse_arguments(argv: Optional[list[str]] = None) -> argparse.Namespace:
    """Parses command-line arguments for the Android APK builder."""
    parser = argparse.ArgumentParser(
        description="SloVerb Studio Android APK Builder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--debug",
        "--debug-mode",
        action="store_true",
        default=False,
        dest="debug",
        help="Bake DEBUG_MODE=True into the APK package for diagnostics export",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the planned packaging arguments and exit without building",
    )
    return parser.parse_args(argv)


def run_build(args: Optional[argparse.Namespace] = None) -> int:
    if args is None:
        args = parse_arguments()

    print("=" * 65)
    print("  SLOVERB STUDIO — ANDROID APK BUILDER")
    print("=" * 65)
    print(f">> Debug Mode Bake : {'ENABLED (DEBUG_MODE=True)' if getattr(args, 'debug', False) else 'DISABLED'}")

    java_home = find_java_17()
    if java_home:
        print(f">> JAVA_HOME: {java_home}")
        os.environ["JAVA_HOME"] = java_home
        java_bin = os.path.join(java_home, "bin")
        if java_bin not in os.environ["PATH"]:
            os.environ["PATH"] = java_bin + os.pathsep + os.environ["PATH"]
    else:
        print(">> Warning: Java 17 not found automatically. Ensure JAVA_HOME is configured.")

    android_home = find_android_sdk()
    if android_home:
        print(f">> ANDROID_HOME: {android_home}")
        os.environ["ANDROID_HOME"] = android_home
        os.environ["ANDROID_SDK_ROOT"] = android_home
    else:
        print(">> Warning: Android SDK not found automatically.")

    # Prevent Gradle download task race conditions on etags.json in multi-ABI builds
    gradle_opts = os.environ.get("GRADLE_OPTS", "")
    flags = ["-Dorg.gradle.parallel=false", "-Dorg.gradle.workers.max=1"]
    for flag in flags:
        if flag not in gradle_opts:
            gradle_opts = f"{gradle_opts} {flag}".strip()
    os.environ["GRADLE_OPTS"] = gradle_opts
    print(f">> GRADLE_OPTS: {os.environ['GRADLE_OPTS']}")

    flet_exe = shutil.which("flet")
    if not flet_exe:
        bin_dir = Path(sys.executable).parent
        candidate = bin_dir / ("flet.exe" if sys.platform == "win32" else "flet")
        if candidate.is_file():
            flet_exe = str(candidate)
        else:
            flet_exe = "flet"

    print(f">> Flet CLI: {flet_exe}")
    cmd = [
        flet_exe,
        "build",
        "apk",
        "--project", "sloverb_studio",
        "--org", "com.redu.sloverb",
        "--product", "SloVerb Studio",
        "--module-name", "sloverb_studio.py",
        "--android-legacy-packaging",
        "--android-adaptive-icon-background", "#0D0E12",
        "--splash-color", "#0D0E12",
        "--splash-dark-color", "#0D0E12",
        "--exclude", "ffmpeg",
        "--exclude", "dist",
        "--exclude", "tests",
        "--exclude", "redu-dev",
        "--exclude", "SloVerbStudio.spec",
        "--exclude", "SloVerbStudioTest.spec",
        "--exclude", "docs",
    ]
    print(f">> Executing: {' '.join(cmd)}")

    if getattr(args, "dry_run", False):
        print("[DRY-RUN] Command arguments:")
        print(" ".join(cmd))
        if getattr(args, "debug", False):
            print("[DRY-RUN] Would bake DEBUG_MODE = True into slowverb/__init__.py")
        return 0

    repo_root = _REPO_ROOT
    orig_cwd = os.getcwd()
    timer = BuildTimer().start()
    try:
        os.chdir(str(repo_root))
        with bake_debug_mode(repo_root, enabled=getattr(args, "debug", False)):
            res = subprocess.run(cmd)
            return res.returncode
    finally:
        total_time = timer.stop()
        print(f"\n>> Total Build Time: {total_time}")
        os.chdir(orig_cwd)


if __name__ == "__main__":
    sys.exit(run_build())
