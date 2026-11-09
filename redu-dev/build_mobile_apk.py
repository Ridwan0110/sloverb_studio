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
from typing import Optional

# Ensure redu-dev directory is in sys.path to import shared build helpers
_DEV_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _DEV_DIR.parent
if str(_DEV_DIR) not in sys.path:
    sys.path.insert(0, str(_DEV_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from build_binary import bake_debug_mode


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

    flet_exe = shutil.which("flet")
    if not flet_exe:
        flet_exe = sys.executable.replace("python.exe", "flet.exe")

    print(f">> Flet CLI: {flet_exe}")
    cmd = [
        flet_exe,
        "build",
        "apk",
        "--project", "sloverb_studio",
        "--org", "com.redu.sloverb",
        "--product", "SloVerb Studio",
        "--module-name", "sloverb_studio.py",
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

    with bake_debug_mode(_REPO_ROOT, enabled=getattr(args, "debug", False)):
        res = subprocess.run(cmd)
        return res.returncode


if __name__ == "__main__":
    sys.exit(run_build())
