"""
Android APK Builder helper for SloVerb Studio.

Configures environment variables (JAVA_HOME, ANDROID_HOME, PATH),
checks dependencies, and invokes 'flet build apk'.
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional


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


def run_build():
    print("=" * 65)
    print("  SLOVERB STUDIO — ANDROID APK BUILDER")
    print("=" * 65)

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
    ]
    print(f">> Executing: {' '.join(cmd)}")
    subprocess.run(cmd)


if __name__ == "__main__":
    from typing import Optional
    run_build()
