#!/usr/bin/env python3
"""
SloVerb Studio — Binary Builder CLI Script.
Automates PyInstaller packaging of SloVerb Studio into a standalone binary.

Usage:
    python redu-dev/build_exe.py [OPTIONS]

Example:
    python redu-dev/build_exe.py --clean
    python redu-dev/build_exe.py --name SloVerbStudio --distpath dist
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path

# Configure utf-8 console encoding on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def get_repo_root() -> Path:
    """Returns the absolute root directory of the SloVerb Studio repository."""
    current = Path(__file__).resolve().parent
    if (current / ".." / "sloverb_studio.py").resolve().is_file():
        return (current / "..").resolve()
    if (Path.cwd() / "sloverb_studio.py").is_file():
        return Path.cwd().resolve()
    return (current / "..").resolve()


def check_windows_x64() -> bool:
    """Verifies that the current execution platform is 64-bit Windows."""
    is_windows = platform.system().lower() == "windows"
    is_64bit = sys.maxsize > 2**32 or platform.machine().lower() in ("amd64", "x86_64")
    return is_windows and is_64bit


def check_prerequisites(repo_root: Path) -> dict:
    """Checks required dependencies, scripts, and fonts."""
    results = {
        "python_version": platform.python_version(),
        "is_64bit": sys.maxsize > 2**32,
        "entry_point": (repo_root / "sloverb_studio.py").is_file(),
        "font_awesome": (repo_root / "assets" / "fonts" / "fa-solid-900.ttf").is_file(),
        "local_ffmpeg": (repo_root / "ffmpeg" / "ffmpeg.exe").is_file(),
        "packages": {},
    }

    required_packages = ["flet", "flet_cli", "PyInstaller", "sounddevice", "numpy"]
    for pkg in required_packages:
        try:
            __import__(pkg)
            results["packages"][pkg] = True
        except ImportError:
            results["packages"][pkg] = False

    return results


def parse_arguments() -> argparse.Namespace:
    """Parses command-line arguments for the builder CLI script."""
    parser = argparse.ArgumentParser(
        description="SloVerb Studio Binary Builder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="SloVerbStudio",
        help="Base name for the generated executable file",
    )
    parser.add_argument(
        "-d",
        "--distpath",
        type=str,
        default="dist",
        help="Destination directory for the built application artifact",
    )
    parser.add_argument(
        "-b",
        "--buildpath",
        type=str,
        default="build",
        help="Temporary directory used by PyInstaller for build artifacts",
    )
    parser.add_argument(
        "-D",
        "--onedir",
        action="store_true",
        default=False,
        help="Build a one-folder bundle instead of a single-file executable",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        default=False,
        help="Keep a command console window visible at launch (for debugging)",
    )
    parser.add_argument(
        "--embed-ffmpeg",
        action="store_true",
        default=False,
        help="Embed ffmpeg.exe inside the onefile bundle (inflates single-file size)",
    )
    parser.add_argument(
        "--no-copy-ffmpeg",
        dest="copy_ffmpeg",
        action="store_false",
        default=True,
        help="Do NOT copy ffmpeg/ into the dist folder next to the executable",
    )
    parser.add_argument(
        "--no-clean",
        dest="clean",
        action="store_false",
        default=True,
        help="Do NOT clean build and dist directories before packaging",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        default=False,
        help="Skip post-build verification tests of the generated executable",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the planned packaging arguments and exit without building",
    )
    return parser.parse_args()


def run_build(args: argparse.Namespace) -> int:
    """Executes the PyInstaller packaging workflow for Windows x86-64."""
    start_time = time.time()
    repo_root = get_repo_root()

    print("=" * 70)
    print("  SLOVERB STUDIO — BINARY BUILDER")
    print("=" * 70)
    print(f"Repository Root : {repo_root}")
    print(f"Target OS / Arch: Windows x86-64 (AMD64)")
    print(f"Python Runtime  : {platform.python_version()} ({platform.architecture()[0]})")
    print(f"Output Target   : {args.name}.exe in '{args.distpath}'")
    print("-" * 70)

    # 1. Architecture verification
    if not check_windows_x64():
        print("ERROR: This builder script only supports Windows x86-64 bit.")
        print(f"Current System: {platform.system()} {platform.machine()}")
        return 1

    # 2. Prerequisites verification
    prereqs = check_prerequisites(repo_root)
    if not prereqs["entry_point"]:
        print("ERROR: sloverb_studio.py entry point not found in repository root.")
        return 1

    if not prereqs["font_awesome"]:
        print("ERROR: FontAwesome asset font (assets/fonts/fa-solid-900.ttf) is missing.")
        return 1

    missing_pkgs = [pkg for pkg, ok in prereqs["packages"].items() if not ok]
    if missing_pkgs:
        print(f"ERROR: Missing required Python packages: {', '.join(missing_pkgs)}")
        print("Please install development dependencies using:")
        print("    pip install -r requirements-dev.txt")
        return 1

    # Fetch version from slowverb package
    try:
        from slowverb import __version__ as app_version
    except Exception:
        app_version = "0.1.0"
    print(f"Application Ver : v{app_version}")

    dist_dir = (repo_root / args.distpath).resolve()
    build_dir = (repo_root / args.buildpath).resolve()

    # 3. Clean previous build output if requested
    if args.clean and not args.dry_run:
        print(f"\n[CLEAN] Cleaning previous build and dist directories...")
        if dist_dir.exists():
            shutil.rmtree(dist_dir, ignore_errors=True)
            print(f"  Removed: {dist_dir}")
        if build_dir.exists():
            shutil.rmtree(build_dir, ignore_errors=True)
            print(f"  Removed: {build_dir}")

    dist_dir.mkdir(parents=True, exist_ok=True)

    # 4. Construct flet pack arguments
    # PyInstaller on Windows uses ';' for path separation
    assets_src = str(repo_root / "assets")
    add_data_arg = f"{assets_src}{os.pathsep}assets"

    flet_args = [
        "flet",
        "pack",
        str(repo_root / "sloverb_studio.py"),
        "-n",
        args.name,
        "--distpath",
        str(dist_dir),
        "--add-data",
        add_data_arg,
        "--hidden-import",
        "tkinter",
        "--hidden-import",
        "sounddevice",
        "--hidden-import",
        "numpy",
        "--hidden-import",
        "slowverb",
        "--product-name",
        "SloVerb Studio",
        "--file-description",
        "SloVerb Studio - High Performance Minimalist Audio Editor",
        "--product-version",
        app_version,
        "--file-version",
        f"{app_version}.0" if app_version.count(".") == 2 else f"{app_version}.0.0",
        "--copyright",
        "Copyright (C) 2026 SloVerb Studio",
        "-y",
    ]

    if args.console:
        flet_args.append("--debug-console")

    if args.onedir:
        flet_args.append("--onedir")

    # If embedding ffmpeg inside the onefile binary
    ffmpeg_exe = repo_root / "ffmpeg" / "ffmpeg.exe"
    if args.embed_ffmpeg and ffmpeg_exe.is_file():
        add_binary_arg = f"{ffmpeg_exe}{os.pathsep}ffmpeg"
        flet_args.extend(["--add-binary", add_binary_arg])
        print(f"[CONFIG] Embedding FFmpeg binary inside executable: {ffmpeg_exe}")

    # Extra PyInstaller build args passed down via '--' separator
    flet_args.extend(["--", f"--workpath={build_dir}", "--clean"])

    print("\n[PACKAGING] Building Windows x86-64 standalone executable...")
    if args.dry_run:
        print("[DRY-RUN] Command arguments:")
        print(" ".join(flet_args))
        return 0

    # Execute build via flet_cli
    import flet.cli

    orig_argv = sys.argv
    orig_cwd = os.getcwd()
    try:
        os.chdir(str(repo_root))
        sys.argv = flet_args
        flet.cli.main()
    except SystemExit as se:
        if se.code not in (0, None):
            print(f"\nERROR: Build failed with exit code {se.code}")
            return int(se.code)
    except Exception as e:
        print(f"\nERROR: Build encountered an exception: {e}")
        return 1
    finally:
        sys.argv = orig_argv
        os.chdir(orig_cwd)

    # 5. Resolve generated executable path
    if args.onedir:
        exe_path = dist_dir / args.name / f"{args.name}.exe"
    else:
        exe_path = dist_dir / f"{args.name}.exe"

    if not exe_path.is_file():
        print(f"\nERROR: Expected executable not found at: {exe_path}")
        return 1

    exe_size_mb = exe_path.stat().st_size / (1024 * 1024)
    print(f"\n[SUCCESS] Executable created successfully!")
    print(f"  Artifact Path : {exe_path}")
    print(f"  Artifact Size : {exe_size_mb:.2f} MB")

    # 6. Copy local FFmpeg next to executable if requested
    if args.copy_ffmpeg and ffmpeg_exe.is_file():
        dest_ffmpeg_dir = (
            (dist_dir / args.name / "ffmpeg") if args.onedir else (dist_dir / "ffmpeg")
        )
        dest_ffmpeg_dir.mkdir(parents=True, exist_ok=True)
        dest_ffmpeg_exe = dest_ffmpeg_dir / "ffmpeg.exe"
        if not dest_ffmpeg_exe.exists() or (
            dest_ffmpeg_exe.stat().st_size != ffmpeg_exe.stat().st_size
        ):
            print(f"\n[FFMPEG] Copying standalone FFmpeg binary to distribution...")
            shutil.copy2(ffmpeg_exe, dest_ffmpeg_exe)
            print(f"  Copied: {dest_ffmpeg_exe}")

    # 7. Post-build verification tests
    if not args.skip_tests:
        print("\n[VERIFICATION] Running post-build tests on executable...")
        test_passed = run_verification_tests(exe_path, app_version)
        if not test_passed:
            print("\nERROR: Post-build verification tests failed.")
            return 1

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  BUILD COMPLETE in {elapsed:.1f}s — Artifact Ready: {exe_path}")
    print("=" * 70)
    return 0


def run_verification_tests(exe_path: Path, expected_version: str) -> bool:
    """Runs automated verification checks on the compiled Windows executable."""
    tests = [
        ("--version", f"v{expected_version}"),
        ("--help", "Usage:"),
        ("--check", "DIAGNOSTICS_OK"),
    ]

    all_ok = True
    for flag, expected_token in tests:
        print(f"  Testing {exe_path.name} {flag} ... ", end="", flush=True)
        try:
            res = subprocess.run(
                [str(exe_path), flag],
                capture_output=True,
                text=True,
                timeout=15,
            )
            combined_output = f"{res.stdout}\n{res.stderr}"
            if res.returncode == 0 and expected_token in combined_output:
                print("PASSED [OK]")
            else:
                print(f"FAILED (exit {res.returncode})")
                print(f"    Expected token: '{expected_token}'")
                print(f"    Output: {combined_output.strip()[:200]}")
                all_ok = False
        except subprocess.TimeoutExpired:
            print("FAILED (Timed out after 15s)")
            all_ok = False
        except Exception as e:
            print(f"FAILED ({e})")
            all_ok = False

    return all_ok


if __name__ == "__main__":
    sys.exit(run_build(parse_arguments()))
