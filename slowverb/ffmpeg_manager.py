"""
FFmpeg discovery, validation, cross-platform architecture detection, and auto-download manager.

Ensures SloVerb Studio can leverage:
1. OS-wide system installation (via system PATH and standard OS installation directories)
2. Local application installation (inside <project_root>/ffmpeg/)
3. Architecture-aware automatic download if FFmpeg is missing anywhere on the machine.
"""

import os
import platform
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from typing import Any, Callable, Dict, List, Optional, Tuple

# Official static builds from yt-dlp / gyan.dev / evermeet
FFMPEG_DOWNLOAD_URLS: Dict[Tuple[str, str], List[str]] = {
    ("windows", "x86_64"): [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip",
        "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip",
    ],
    ("windows", "arm64"): [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-winarm64-gpl.zip",
    ],
    ("linux", "x86_64"): [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz",
        "https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz",
    ],
    ("linux", "arm64"): [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz",
    ],
    ("darwin", "arm64"): [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macosarm64-gpl.zip",
        "https://evermeet.cx/ffmpeg/getrelease/zip",
    ],
    ("darwin", "x86_64"): [
        "https://github.com/yt-dlp/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-macos64-gpl.zip",
        "https://evermeet.cx/ffmpeg/getrelease/zip",
    ],
}


def get_project_root() -> str:
    """Returns the absolute path to the application root directory."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(current_dir, ".."))



def is_valid_ffmpeg_binary(binary_path: str) -> bool:
    """Verifies that an executable exists at the given path and responds to ffmpeg -version."""
    if not binary_path or not os.path.isfile(binary_path):
        return False

    try:
        proc = subprocess.run(
            [binary_path, "-version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
        )
        return proc.returncode == 0
    except Exception:
        return False


def find_system_ffmpeg() -> Optional[str]:
    """
    Searches for an OS-wide FFmpeg installation via system PATH and standard OS locations.
    Returns the absolute path to the binary if found and executable.
    """
    # 1. Environment variable override
    env_ffmpeg = os.environ.get("FFMPEG_BINARY")
    if env_ffmpeg and is_valid_ffmpeg_binary(env_ffmpeg):
        return os.path.abspath(env_ffmpeg)

    # 2. Check system PATH
    which_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if which_path and is_valid_ffmpeg_binary(which_path):
        return os.path.abspath(which_path)

    # 3. Standard OS-specific installation directories
    os_name = platform.system().lower()
    system_candidates: List[str] = []

    if os_name == "windows":
        system_candidates.extend([
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
            r"C:\scoop\apps\ffmpeg\current\bin\ffmpeg.exe",
            r"C:\tools\ffmpeg\bin\ffmpeg.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WinGet\Links\ffmpeg.exe"),
        ])
    elif os_name == "darwin":
        system_candidates.extend([
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/usr/bin/ffmpeg",
        ])
    else:  # Linux and other UNIX
        system_candidates.extend([
            "/usr/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/snap/bin/ffmpeg",
            "/usr/bin/ffmpeg.static",
        ])

    for candidate in system_candidates:
        if candidate and is_valid_ffmpeg_binary(candidate):
            return os.path.abspath(candidate)

    return None


def find_local_ffmpeg(project_root: Optional[str] = None) -> Optional[str]:
    """
    Searches for an FFmpeg binary in the local application folder or current working directory.
    """
    root = project_root or get_project_root()
    cwd = os.getcwd()
    exe_name = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"

    candidates = [
        os.path.join(root, "ffmpeg", exe_name),
        os.path.join(cwd, "ffmpeg", exe_name),
        os.path.join(root, "bin", exe_name),
        os.path.join(cwd, "bin", exe_name),
        os.path.join(root, exe_name),
        os.path.join(cwd, exe_name),
    ]
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        candidates.extend([
            os.path.join(sys._MEIPASS, "ffmpeg", exe_name),
            os.path.join(sys._MEIPASS, exe_name),
        ])

    for candidate in candidates:
        if candidate and is_valid_ffmpeg_binary(candidate):
            return os.path.abspath(candidate)

    return None


def find_ffmpeg(project_root: Optional[str] = None) -> Optional[str]:
    """
    Locates FFmpeg with the following priority:
    1. OS-wide system installation (PATH / system directories)
    2. Local application folder (<project_root>/ffmpeg/ or cwd)
    Returns absolute path if found, or None if not found anywhere.
    """
    # 1. Prioritize OS-wide system installation
    system_path = find_system_ffmpeg()
    if system_path:
        return system_path

    # 2. Check local application installation
    local_path = find_local_ffmpeg(project_root)
    if local_path:
        return local_path

    return None


def normalize_platform_arch() -> Tuple[str, str]:
    """
    Normalizes the current OS and CPU architecture for URL resolution.
    Returns (os_name, arch_name), e.g. ('windows', 'x86_64') or ('darwin', 'arm64').
    """
    os_name = platform.system().lower()
    machine = platform.machine().lower()

    if machine in ("x86_64", "amd64"):
        arch_name = "x86_64"
    elif machine in ("arm64", "aarch64"):
        arch_name = "arm64"
    else:
        arch_name = "x86_64"

    return os_name, arch_name


def get_download_urls() -> List[str]:
    """Returns candidate download URLs for the current OS and CPU architecture."""
    os_name, arch = normalize_platform_arch()
    urls = FFMPEG_DOWNLOAD_URLS.get((os_name, arch))
    if not urls:
        # Fallback to x86_64 for the current OS
        urls = FFMPEG_DOWNLOAD_URLS.get((os_name, "x86_64"), [])
    return urls


def download_ffmpeg(
    target_dir: Optional[str] = None,
    on_progress: Optional[Callable[[float, str], None]] = None,
) -> str:
    """
    Downloads and extracts FFmpeg into target_dir (defaults to <project_root>/ffmpeg/).
    Returns the absolute path to the extracted, verified executable.
    """
    dest_dir = target_dir or os.path.join(get_project_root(), "ffmpeg")
    os.makedirs(dest_dir, exist_ok=True)

    exe_name = "ffmpeg.exe" if platform.system().lower() == "windows" else "ffmpeg"
    final_binary_path = os.path.join(dest_dir, exe_name)

    urls = get_download_urls()
    if not urls:
        raise RuntimeError(f"No download URL available for {platform.system()} ({platform.machine()})")

    download_error = None
    with tempfile.TemporaryDirectory() as tmp_dir:
        for url in urls:
            try:
                archive_name = "ffmpeg_archive" + (".zip" if ".zip" in url else ".tar.xz")
                archive_path = os.path.join(tmp_dir, archive_name)

                if on_progress:
                    on_progress(0.05, f"Connecting to {url}...")

                # Stream download with progress tracking
                req = urllib.request.Request(
                    url,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) SloVerbStudio/1.0"},
                )
                with urllib.request.urlopen(req) as response, open(archive_path, "wb") as out_file:
                    total_size = response.getheader("Content-Length")
                    total_bytes = int(total_size) if total_size else None
                    downloaded = 0
                    chunk_size = 1024 * 256  # 256 KB

                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        out_file.write(chunk)
                        downloaded += len(chunk)
                        if total_bytes and on_progress:
                            percent = min(0.85, 0.05 + 0.80 * (downloaded / total_bytes))
                            mb = downloaded / (1024 * 1024)
                            total_mb = total_bytes / (1024 * 1024)
                            on_progress(percent, f"Downloading FFmpeg: {mb:.1f}MB / {total_mb:.1f}MB")

                if on_progress:
                    on_progress(0.90, "Extracting FFmpeg binary...")

                # Extract only the ffmpeg executable from the archive
                extracted = False
                if zipfile.is_zipfile(archive_path):
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        for member in zf.namelist():
                            if member.endswith(exe_name):
                                with zf.open(member) as src, open(final_binary_path, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                extracted = True
                                break
                else:
                    # Tar archive (e.g. tar.xz)
                    try:
                        with tarfile.open(archive_path, "r:*") as tf:
                            for member in tf.getmembers():
                                if member.name.endswith(exe_name) and member.isfile():
                                    with tf.extractfile(member) as src, open(final_binary_path, "wb") as dst:
                                        shutil.copyfileobj(src, dst)
                                    extracted = True
                                    break
                    except Exception as tar_err:
                        print(f"Tar extraction failed: {tar_err}")

                if extracted and os.path.isfile(final_binary_path):
                    # Set executable permissions on UNIX
                    if platform.system().lower() != "windows":
                        st = os.stat(final_binary_path)
                        os.chmod(final_binary_path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

                    if is_valid_ffmpeg_binary(final_binary_path):
                        if on_progress:
                            on_progress(1.0, "FFmpeg ready.")
                        return os.path.abspath(final_binary_path)

            except Exception as e:
                download_error = e
                print(f"Failed download from {url}: {e}")
                continue

    raise RuntimeError(
        f"Failed to download and install FFmpeg automatically. "
        f"Please install FFmpeg on your system PATH or place ffmpeg in {dest_dir}. Last error: {download_error}"
    )


def run_ffmpeg_setup_flet(project_root: Optional[str] = None) -> str:
    """
    Launches a dedicated Flet window to prompt the user and show download progress.
    Returns the absolute path to the verified FFmpeg binary.
    """
    import flet as ft
    from slowverb.ui import FFmpegSetupView

    download_result: Dict[str, Any] = {"path": None, "cancelled": False, "error": None}

    def main_setup(page: ft.Page):
        page.title = "SloVerb Studio // FFmpeg Setup"
        page.bgcolor = "#0D0E12"
        page.padding = 24
        page.scroll = ft.ScrollMode.AUTO

        page.fonts = {
            "FontAwesome": "fonts/fa-solid-900.ttf",
        }

        if hasattr(page, "window") and page.window:
            try:
                page.window.width = 850
                page.window.height = 620
                page.window.min_width = 750
                page.window.min_height = 550
            except Exception:
                pass

        def on_success(binary_path: str):
            download_result["path"] = binary_path
            if hasattr(page, "window") and page.window and hasattr(page.window, "close"):
                try:
                    page.window.close()
                except Exception:
                    pass
            elif hasattr(page, "window_destroy"):
                try:
                    page.window_destroy()
                except Exception:
                    pass

        def on_cancel():
            download_result["cancelled"] = True
            if hasattr(page, "window") and page.window and hasattr(page.window, "close"):
                try:
                    page.window.close()
                except Exception:
                    pass
            elif hasattr(page, "window_destroy"):
                try:
                    page.window_destroy()
                except Exception:
                    pass

        target_dir = os.path.join(project_root or get_project_root(), "ffmpeg")
        setup_view = FFmpegSetupView(
            page=page,
            on_success=on_success,
            on_cancel=on_cancel,
            target_dir=target_dir,
        )
        center_wrapper = ft.Container(
            content=setup_view,
            alignment=ft.Alignment.CENTER,
            expand=True,
            padding=ft.Padding.only(top=30),
        )
        page.add(center_wrapper)
        page.update()

    if hasattr(ft, "run"):
        ft.run(main_setup)
    elif hasattr(ft, "app"):
        ft.app(target=main_setup)

    if download_result["path"]:
        return download_result["path"]

    raise FileNotFoundError(
        "FFmpeg is required for SloVerb Studio audio processing, but was not found or setup was cancelled."
    )


def prompt_and_ensure_ffmpeg(
    interactive: bool = True,
    prompt_callback: Optional[Callable[[], bool]] = None,
    on_progress: Optional[Callable[[float, str], None]] = None,
    project_root: Optional[str] = None,
) -> str:
    """
    Locates FFmpeg or prompts the user to download it if missing.
    In GUI / interactive mode, prompts via a Flet window and displays download progress there.
    Raises FileNotFoundError if FFmpeg cannot be found and user declines download.
    """
    existing_path = find_ffmpeg(project_root)
    if existing_path:
        return existing_path

    # User callback override (e.g. for unit testing)
    if prompt_callback is not None:
        user_agreed = prompt_callback()
        if user_agreed:
            target_dir = os.path.join(project_root or get_project_root(), "ffmpeg")
            return download_ffmpeg(target_dir=target_dir, on_progress=on_progress)
        raise FileNotFoundError(
            "FFmpeg is required for SloVerb Studio audio processing, but was not found. "
            "Please install FFmpeg OS-wide or place the ffmpeg binary inside the ./ffmpeg/ folder."
        )

    if interactive:
        try:
            return run_ffmpeg_setup_flet(project_root=project_root)
        except Exception as e:
            # Fall back to terminal prompt only if Flet GUI cannot run (e.g. headless environment)
            print(f">> Note: Flet GUI setup unavailable ({e}), falling back to terminal...")
            print("\n" + "=" * 65)
            print(">> FFmpeg was not detected on your system PATH or local folder.")
            print(">> SloVerb Studio requires FFmpeg to process and export audio.")
            print("=" * 65)
            try:
                choice = input(">> Would you like to download FFmpeg automatically now? [Y/n]: ").strip().lower()
                user_agreed = choice in ("", "y", "yes")
            except (EOFError, KeyboardInterrupt):
                user_agreed = False

            if user_agreed:
                target_dir = os.path.join(project_root or get_project_root(), "ffmpeg")
                return download_ffmpeg(target_dir=target_dir, on_progress=on_progress)

    raise FileNotFoundError(
        "FFmpeg is required for SloVerb Studio audio processing, but was not found. "
        "Please install FFmpeg OS-wide or place the ffmpeg binary inside the ./ffmpeg/ folder."
    )
