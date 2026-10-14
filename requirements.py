#!/usr/bin/env python3
"""
SloVerb Studio — Dependency Specification & Management Script

This module defines the project's dependency manifest and provides utilities
to verify, install, and export dependencies while maintaining a de-bloated footprint.

DE-BLOATED ARCHITECTURE RATIONALE:
-----------------------------------
Traditional Python audio applications often import massive dependency trees:
- scipy (~50 MB): Avoided. Filter processing is offloaded to FFmpeg's optimized C DSP filters.
- librosa (~250 MB+, pulls numba/llvmlite): Avoided. Waveform peak binning is done in <5ms with NumPy.
- soundfile / pydub (~30 MB): Avoided. FFmpeg streams raw PCM audio directly via stdio.
- torchaudio / PyTorch (~1.5+ GB): Completely avoided.

Only 3 runtime packages are required:
1. flet (desktop GUI interface)
2. numpy (lightweight in-memory PCM audio buffers)
3. sounddevice (low-latency PortAudio stream playback)
"""

import importlib.util
import os
import subprocess
import sys
from typing import Dict, List, Optional

# Core runtime dependencies required for SloVerb Studio
CORE_REQUIREMENTS: List[str] = [
    "flet>=1.0.0",
    "numpy>=1.26.0",
    "sounddevice>=0.4.6",
]

# Development, testing, and linting dependencies
DEV_REQUIREMENTS: List[str] = [
    "pytest>=8.0.0",
    "anyio>=4.0.0",
]

# Mapping of package names to their Python import names
IMPORT_NAME_MAP: Dict[str, str] = {
    "flet": "flet",
    "numpy": "numpy",
    "sounddevice": "sounddevice",
    "pytest": "pytest",
    "anyio": "anyio",
}


def get_core_requirements() -> List[str]:
    """Returns the list of essential runtime dependencies."""
    return list(CORE_REQUIREMENTS)


def get_dev_requirements() -> List[str]:
    """Returns the list of development and testing dependencies."""
    return list(DEV_REQUIREMENTS)


def get_all_requirements() -> List[str]:
    """Returns combined runtime and development dependencies."""
    return CORE_REQUIREMENTS + DEV_REQUIREMENTS


def check_installed(include_dev: bool = True) -> Dict[str, bool]:
    """Checks whether each required dependency is installed in the current environment."""
    requirements = get_all_requirements() if include_dev else get_core_requirements()
    results: Dict[str, bool] = {}

    for req in requirements:
        pkg_name = req.split(">=")[0].split("==")[0].strip()
        import_name = IMPORT_NAME_MAP.get(pkg_name, pkg_name)
        spec = importlib.util.find_spec(import_name)
        results[req] = spec is not None

    return results


def install_requirements(
    include_dev: bool = True,
    python_exe: Optional[str] = None,
    upgrade: bool = False,
) -> int:
    """Installs dependencies using pip in the active Python environment."""
    exe = python_exe or sys.executable
    requirements = get_all_requirements() if include_dev else get_core_requirements()

    cmd = [exe, "-m", "pip", "install"]
    if upgrade:
        cmd.append("--upgrade")
    cmd.extend(requirements)

    print(f">> Installing dependencies using: {exe}")
    print(f">> Packages: {', '.join(requirements)}")
    result = subprocess.run(cmd)
    return result.returncode


def export_requirements_txt(output_path: Optional[str] = None) -> str:
    """Exports clean, categorized requirements to requirements.txt."""
    if output_path is None:
        project_root = os.path.dirname(os.path.abspath(__file__))
        output_path = os.path.join(project_root, "requirements.txt")

    content = [
        "# SloVerb Studio — Minimal De-Bloated Dependency Manifest",
        "# Generated via requirements.py",
        "",
        "# Core Runtime Dependencies",
    ]
    content.extend(CORE_REQUIREMENTS)
    content.extend([
        "",
        "# Testing & Development Dependencies",
    ])
    content.extend(DEV_REQUIREMENTS)
    content.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(content))

    print(f">> Exported requirements to: {output_path}")
    return output_path


def main():
    """Command-line interface for dependency management."""
    args = sys.argv[1:]

    if "--export" in args:
        export_requirements_txt()
        return

    if "--install" in args:
        code = install_requirements(include_dev=True)
        sys.exit(code)

    if "--install-core" in args:
        code = install_requirements(include_dev=False)
        sys.exit(code)

    # Default action: check status
    print("=" * 60)
    print("SLOVERB STUDIO — DEPENDENCY STATUS (DE-BLOATED MANIFEST)")
    print("=" * 60)
    status = check_installed(include_dev=True)
    all_ok = True

    for req, installed in status.items():
        symbol = "[OK]      " if installed else "[MISSING] "
        if not installed:
            all_ok = False
        print(f"  {symbol} {req}")

    print("=" * 60)
    if all_ok:
        print(">> All dependencies are installed and ready.")
    else:
        print(">> Some dependencies are missing.")
        print(">> Run 'python requirements.py --install' to install them.")


if __name__ == "__main__":
    main()
