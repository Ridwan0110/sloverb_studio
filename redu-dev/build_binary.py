#!/usr/bin/env python3
"""
SloVerb Studio — Universal Multi-Platform Binary Builder CLI Script.
Automates PyInstaller / Flet packaging of SloVerb Studio into standalone native
binaries and distribution archives across Windows, Linux, and macOS (x86_64 and ARM64).

Usage:
    python redu-dev/build_binary.py [OPTIONS]

Examples:
    python redu-dev/build_binary.py --clean
    python redu-dev/build_binary.py --name SloVerbStudio --distpath dist
    python redu-dev/build_binary.py --dry-run
"""

import argparse
from contextlib import contextmanager
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import time
import zipfile
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


# Ensure repository root is in sys.path so modules like `slowverb` can be imported
# when this script is executed via `python redu-dev/build_binary.py` or from any working directory.
_REPO_ROOT = get_repo_root()
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def patch_flet_cli_windows_binary_open_bug():
    """
    Patches an upstream bug in flet-cli 1.1.2 (win_utils.py:130):
        with open(exe_path, "ab", encoding="utf-8") as exef:
            exef.write(overlay_before)
    In Python, opening files in binary mode ("ab") with an `encoding` argument raises:
        ValueError: binary mode doesn't take an encoding argument
    This monkeypatches builtins.open to strip `encoding`, `errors`, and `newline`
    whenever binary mode ('b') is specified, allowing Windows builds to succeed.
    """
    import builtins

    orig_open = builtins.open

    def safe_open(*args, **kwargs):
        mode = kwargs.get("mode")
        if mode is None and len(args) > 1:
            mode = args[1]
        elif mode is None:
            mode = "r"
        if isinstance(mode, str) and "b" in mode:
            kwargs.pop("encoding", None)
            kwargs.pop("errors", None)
            kwargs.pop("newline", None)
        return orig_open(*args, **kwargs)

    builtins.open = safe_open
    return orig_open


# Install patch at import time for Windows compatibility
patch_flet_cli_windows_binary_open_bug()


def get_windows_file_version(version_str: str) -> str:
    """
    Returns a standardized 4-part numeric version string (e.g. '0.3.0.0')
    compatible with Windows PE VERSIONINFO and packaging.version.parse.
    """
    nums = re.findall(r"\d+", version_str)
    parts = [int(n) for n in nums[:3]]
    while len(parts) < 3:
        parts.append(0)
    return f"{parts[0]}.{parts[1]}.{parts[2]}.0"


def get_app_version(repo_root: Path, explicit_version: str | None = None) -> str:
    """
    Resolves the application version string using robust cascading strategies:
    1. Explicit version argument (e.g. --app-version CLI flag)
    2. Dynamic import of `slowverb.__version__` if package exists in repo_root
    3. Static regex parsing of `slowverb/__init__.py` (avoids runtime audio dependency imports)
    4. Environment variables (APP_VERSION, GITHUB_REF_NAME)
    5. Git tags via `git describe`
    6. Safe fallback default: "0.0.0" (never "UNKNOWN", preventing Windows PE version failure)
    """
    if explicit_version and explicit_version.strip() and explicit_version.strip().upper() != "UNKNOWN":
        return explicit_version.strip().lstrip("v")

    init_file = repo_root / "slowverb" / "__init__.py"

    # 1. Try importing slowverb.__version__ if located in repo_root
    if init_file.is_file():
        try:
            if str(repo_root) not in sys.path:
                sys.path.insert(0, str(repo_root))
            from slowverb import __version__ as pkg_version
            if pkg_version and pkg_version.strip() and pkg_version.strip().upper() != "UNKNOWN":
                return pkg_version.strip().lstrip("v")
        except Exception:
            pass

    # 2. Try static regex parsing of slowverb/__init__.py
    if init_file.is_file():
        try:
            content = init_file.read_text(encoding="utf-8")
            match = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
            if match:
                v = match.group(1).strip()
                if v and v.upper() != "UNKNOWN":
                    return v.lstrip("v")
        except Exception:
            pass

    # 3. Check environment variables (e.g. GITHUB_REF_NAME="v0.3.0" during CI release tag builds)
    for env_var in ("APP_VERSION", "GITHUB_REF_NAME"):
        val = os.environ.get(env_var, "").strip()
        if val and val.upper() != "UNKNOWN":
            clean_val = val.lstrip("v")
            if re.match(r"^\d+(\.\d+)*", clean_val):
                return clean_val

    # 4. Check git describe
    if (repo_root / ".git").exists():
        try:
            git_res = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                cwd=str(repo_root),
                capture_output=True,
                text=True,
                timeout=5,
            )
            if git_res.returncode == 0 and git_res.stdout:
                tag = git_res.stdout.strip().lstrip("v")
                if re.match(r"^\d+(\.\d+)*", tag):
                    return tag.split("-")[0]
        except Exception:
            pass

    # 5. Safe fallback default: "0.0.0"
    return "0.0.0"


def detect_platform() -> tuple[str, str]:
    """
    Detects and normalizes the current host operating system and CPU architecture.

    Returns:
        tuple[str, str]: Normalized (os_name, arch_name)
            os_name: 'windows', 'linux', or 'darwin'
            arch_name: 'x86_64' or 'arm64'
    """
    raw_os = platform.system().lower()
    if "darwin" in raw_os or "mac" in raw_os:
        os_name = "darwin"
    elif "windows" in raw_os or "nt" in raw_os:
        os_name = "windows"
    else:
        os_name = "linux"

    raw_machine = platform.machine().lower()
    if raw_machine in ("amd64", "x86_64", "x64", "i686", "i386"):
        arch_name = "x86_64"
    elif raw_machine in ("arm64", "aarch64", "armv8b", "armv8l"):
        arch_name = "arm64"
    else:
        arch_name = raw_machine

    return os_name, arch_name


def check_prerequisites(repo_root: Path) -> dict:
    """Checks required dependencies, scripts, and font assets."""
    results = {
        "python_version": platform.python_version(),
        "entry_point": (repo_root / "sloverb_studio.py").is_file(),
        "font_awesome": (repo_root / "assets" / "fonts" / "fa-solid-900.ttf").is_file(),
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
    """Parses command-line arguments for the universal builder CLI script."""
    current_os, current_arch = detect_platform()

    parser = argparse.ArgumentParser(
        description="SloVerb Studio Universal Multi-Platform Binary Builder",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="SloVerbStudio",
        help="Base name for the generated executable file or app bundle",
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
        help="Build a one-folder bundle instead of a single-file executable (Windows/Linux only)",
    )
    parser.add_argument(
        "--console",
        action="store_true",
        default=False,
        help="Keep a command console window visible at launch (for debugging)",
    )
    parser.add_argument(
        "--clean",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Clean build and dist directories before packaging (default: True, use --no-clean to disable)",
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        default=False,
        help="Run post-build verification tests of the generated binary",
    )
    parser.add_argument(
        "--skip-archive",
        action="store_true",
        default=False,
        help="Skip creating compressed release archives (.zip / .tar.gz)",
    )
    parser.add_argument(
        "--target-os",
        type=str,
        choices=["windows", "linux", "darwin"],
        default=current_os,
        help="Target operating system override (must match host runner environment)",
    )
    parser.add_argument(
        "--target-arch",
        type=str,
        choices=["x86_64", "arm64"],
        default=current_arch,
        help="Target CPU architecture override (must match host runner environment)",
    )
    parser.add_argument(
        "--app-version",
        type=str,
        default=None,
        help="Explicit version override (defaults to slowverb.__version__ or package metadata)",
    )
    parser.add_argument(
        "-i",
        "--icon",
        type=str,
        default=None,
        help="Path to an icon file for the executable (.ico on Windows, .png on Linux, .icns on macOS)",
    )
    parser.add_argument(
        "--debug",
        "--debug-mode",
        action="store_true",
        default=False,
        dest="debug",
        help="Bake DEBUG_MODE=True into the packaged application for diagnostics export",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Print the planned packaging arguments and exit without building",
    )
    return parser.parse_args()


def create_distribution_archive(
    target_path: Path,
    output_archive: Path,
    target_os: str,
) -> Path:
    """
    Creates a compressed release archive from the built application artifact.
    Windows & macOS -> .zip (preserves .app bundle structure and file permissions).
    Linux -> .tar.gz.
    """
    output_archive.parent.mkdir(parents=True, exist_ok=True)
    if output_archive.exists():
        output_archive.unlink()

    if target_os == "linux" or output_archive.name.endswith(".tar.gz"):
        with tarfile.open(output_archive, "w:gz") as tar:
            if target_path.is_dir():
                tar.add(target_path, arcname=target_path.name)
            else:
                tar.add(target_path, arcname=target_path.name)
    else:  # Windows & macOS (.zip)
        with zipfile.ZipFile(output_archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
            if target_path.is_dir():
                for root, dirs, files in os.walk(target_path):
                    for file in files:
                        full_path = Path(root) / file
                        arcname = full_path.relative_to(target_path.parent)
                        zip_info = zipfile.ZipInfo.from_file(full_path, arcname=str(arcname))
                        # Preserve POSIX executable permissions for macOS bundles
                        if target_os == "darwin" and os.access(full_path, os.X_OK):
                            zip_info.external_attr = (0o755 << 16) | 0o100000
                        zip_file.writestr(zip_info, full_path.read_bytes())
            else:
                zip_file.write(target_path, arcname=target_path.name)

    return output_archive


@contextmanager
def bake_debug_mode(repo_root: Path, enabled: bool = False):
    """
    Context manager that temporarily sets DEBUG_MODE = True in slowverb/__init__.py
    during the build process, and restores the original file content upon exit.
    """
    if not enabled:
        yield
        return

    init_file = repo_root / "slowverb" / "__init__.py"
    if not init_file.is_file():
        yield
        return

    original_content = init_file.read_text(encoding="utf-8")
    patched_content = re.sub(
        r"DEBUG_MODE\s*:\s*bool\s*=\s*(?:False|True)",
        "DEBUG_MODE: bool = True",
        original_content,
    )
    if patched_content == original_content:
        patched_content = re.sub(
            r"DEBUG_MODE\s*=\s*(?:False|True)",
            "DEBUG_MODE = True",
            original_content,
        )

    print(f"\n>> [DEBUG MODE] Baking DEBUG_MODE = True into {init_file.name}")
    init_file.write_text(patched_content, encoding="utf-8")
    try:
        yield
    finally:
        print(f"\n>> [DEBUG MODE] Restoring original {init_file.name}")
        init_file.write_text(original_content, encoding="utf-8")


def run_build(args: argparse.Namespace) -> int:
    """Executes the universal packaging workflow for the active platform."""
    start_time = time.time()
    repo_root = get_repo_root()
    host_os, host_arch = detect_platform()
    target_os = args.target_os or host_os
    target_arch = args.target_arch or host_arch

    print("=" * 70)
    print("  SLOVERB STUDIO — UNIVERSAL BINARY BUILDER")
    print("=" * 70)
    print(f"Repository Root : {repo_root}")
    print(f"Host Platform   : {host_os} ({host_arch})")
    print(f"Target Platform : {target_os} ({target_arch})")
    print(f"Python Runtime  : {platform.python_version()} ({platform.architecture()[0]})")
    print(f"Output Target   : {args.name} in '{args.distpath}'")
    print(f"Debug Mode Bake : {'ENABLED (DEBUG_MODE=True)' if getattr(args, 'debug', False) else 'DISABLED'}")
    print("-" * 70)

    # 1. Host vs Target compatibility verification
    if host_os != target_os:
        print(f"ERROR: Cannot cross-compile from host OS '{host_os}' to target OS '{target_os}'.")
        print("PyInstaller requires running natively on the target operating system.")
        print("Use GitHub Actions matrix runners to build on other operating systems.")
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

    # Fetch version using robust resolution (imports slowverb, parses __init__.py, checks env vars/git, or defaults to 0.0.0)
    app_version = get_app_version(repo_root, explicit_version=getattr(args, "app_version", None))
    print(f"Application Ver : v{app_version}")

    dist_dir = (repo_root / args.distpath).resolve()
    build_dir = (repo_root / args.buildpath).resolve()
    archives_dir = dist_dir / "archives"

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
    archives_dir.mkdir(parents=True, exist_ok=True)

    # 4. Construct flet pack arguments
    # PyInstaller uses os.pathsep (';' on Windows, ':' on Linux/macOS)
    assets_src = str(repo_root / "assets")
    add_data_arg = f"{assets_src}{os.pathsep}assets"

    windows_file_version = get_windows_file_version(app_version)

    # Resolve executable icon
    icon_path = None
    if getattr(args, "icon", None) and os.path.isfile(args.icon):
        icon_path = os.path.abspath(args.icon)
    else:
        for c in [
            repo_root / "assets" / "image" / "SloVerb Studio Icon-256x.ico",
            repo_root / "assets" / "image" / "SloVerb Studio Icon-128x.ico",
            repo_root / "assets" / "image" / "SloVerb Studio Icon-64x.ico",
            repo_root / "assets" / "image" / "SloVerb Studio Icon-32x.ico",
            repo_root / "assets" / "icon.png",
        ]:
            if c.is_file():
                icon_path = str(c.resolve())
                break

    flet_args = [
        "flet",
        "pack",
        str(repo_root / "sloverb_studio.py"),
        "-n",
        args.name,
    ]
    if icon_path:
        flet_args.extend(["-i", icon_path])
    flet_args.extend([
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
        windows_file_version,
        "--copyright",
        "Copyright (C) 2026 SloVerb Studio",
        "-y",
    ])

    # Platform-specific packaging adjustments
    if target_os == "darwin":
        # macOS: flet pack creates a .app bundle
        flet_args.extend(["--bundle-id", "com.sloverb.studio"])
    elif target_os == "linux":
        flet_args.extend(["--bundle-id", "sloverb-studio"])
        if args.onedir:
            flet_args.append("--onedir")
    elif target_os == "windows":
        if args.onedir:
            flet_args.append("--onedir")

    if args.console:
        flet_args.append("--debug-console")

    # Extra PyInstaller build args passed down via '--' separator
    flet_args.extend(["--", f"--workpath={build_dir}", "--clean"])

    print(f"\n[PACKAGING] Building standalone application for {target_os}-{target_arch}...")
    if args.dry_run:
        print("[DRY-RUN] Command arguments:")
        print(" ".join(flet_args))
        if getattr(args, "debug", False):
            print("[DRY-RUN] Would bake DEBUG_MODE = True into slowverb/__init__.py")
        return 0

    # Execute build via flet_cli
    import flet.cli

    # Ensure Windows flet-cli 1.1.2 binary open bug patch is active
    patch_flet_cli_windows_binary_open_bug()

    orig_argv = sys.argv
    orig_cwd = os.getcwd()
    with bake_debug_mode(repo_root, enabled=getattr(args, "debug", False)):
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

    # 5. Locate generated artifact
    if target_os == "darwin":
        artifact_path = dist_dir / f"{args.name}.app"
        binary_executable = artifact_path / "Contents" / "MacOS" / args.name
    elif target_os == "windows":
        artifact_path = (dist_dir / args.name / f"{args.name}.exe") if args.onedir else (dist_dir / f"{args.name}.exe")
        binary_executable = artifact_path
    else:  # Linux
        artifact_path = (dist_dir / args.name / args.name) if args.onedir else (dist_dir / args.name)
        binary_executable = artifact_path

    if not artifact_path.exists():
        print(f"\nERROR: Expected built artifact not found at: {artifact_path}")
        return 1

    if artifact_path.is_file():
        size_mb = artifact_path.stat().st_size / (1024 * 1024)
    else:
        size_mb = sum(f.stat().st_size for f in artifact_path.rglob("*") if f.is_file()) / (1024 * 1024)

    print(f"\n[SUCCESS] Artifact built successfully!")
    print(f"  Artifact Path : {artifact_path}")
    print(f"  Artifact Size : {size_mb:.2f} MB")

    # 6. Post-build verification tests (optional via --verify)
    if args.verify and binary_executable.is_file():
        print("\n[VERIFICATION] Running post-build tests on binary...")
        test_passed = run_verification_tests(binary_executable, app_version)
        if not test_passed:
            print("\nERROR: Post-build verification tests failed.")
            return 1

    # 7. Create distribution archive
    if not args.skip_archive:
        archive_ext = "tar.gz" if target_os == "linux" else "zip"
        archive_name = f"SloVerbStudio-v{app_version}-{target_os}-{target_arch}.{archive_ext}"
        archive_file = archives_dir / archive_name
        print(f"\n[ARCHIVE] Creating release package: {archive_name} ...")
        create_distribution_archive(artifact_path, archive_file, target_os)
        archive_size_mb = archive_file.stat().st_size / (1024 * 1024)
        print(f"  Archive Path : {archive_file}")
        print(f"  Archive Size : {archive_size_mb:.2f} MB")

    elapsed = time.time() - start_time
    print("\n" + "=" * 70)
    print(f"  BUILD COMPLETE in {elapsed:.1f}s — Ready for Distribution!")
    print("=" * 70)
    return 0


def run_verification_tests(binary_path: Path, expected_version: str) -> bool:
    """Runs automated verification checks on the compiled native executable."""
    tests = [
        ("--version", f"v{expected_version}"),
    ]

    all_ok = True
    for flag, expected_token in tests:
        print(f"  Testing {binary_path.name} {flag} ... ", end="", flush=True)
        try:
            res = subprocess.run(
                [str(binary_path), flag],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
            )
            stdout = res.stdout or ""
            stderr = res.stderr or ""
            combined_output = f"{stdout}\n{stderr}"
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
