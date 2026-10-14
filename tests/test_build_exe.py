"""Tests for redu-dev/build_exe.py Windows x86-64 executable builder and artifact verification."""

import os
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Import helper builder functions from redu-dev/build_exe.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "redu-dev"))
import build_exe


def test_check_windows_x64():
    """Verify check_windows_x64 accurately detects platform and 64-bit architecture."""
    is_win = platform.system().lower() == "windows"
    is_64 = sys.maxsize > 2**32 or platform.machine().lower() in ("amd64", "x86_64")

    expected = is_win and is_64
    assert build_exe.check_windows_x64() == expected


def test_get_repo_root():
    """Verify get_repo_root locates the repository directory containing sloverb_studio.py."""
    root = build_exe.get_repo_root()
    assert root.is_dir()
    assert (root / "sloverb_studio.py").is_file()
    assert (root / "slowverb").is_dir()
    assert (root / "assets").is_dir()


def test_check_prerequisites():
    """Verify prerequisites detector checks required entry point, assets, and dependencies."""
    repo_root = build_exe.get_repo_root()
    prereqs = build_exe.check_prerequisites(repo_root)

    assert prereqs["entry_point"] is True
    assert prereqs["font_awesome"] is True
    assert prereqs["packages"]["flet"] is True
    assert prereqs["packages"]["PyInstaller"] is True
    assert prereqs["packages"]["sounddevice"] is True
    assert prereqs["packages"]["numpy"] is True


def test_builder_argument_parsing():
    """Verify argument parser handles defaults and custom options."""
    with patch("sys.argv", ["build_exe.py", "--name", "CustomApp", "--distpath", "custom_dist", "--onedir", "--console"]):
        args = build_exe.parse_arguments()
        assert args.name == "CustomApp"
        assert args.distpath == "custom_dist"
        assert args.onedir is True
        assert args.console is True
        assert args.clean is True
        assert args.embed_ffmpeg is False
        assert args.copy_ffmpeg is True


def test_builder_dry_run():
    """Verify builder --dry-run option generates command without executing build."""
    with patch("sys.argv", ["build_exe.py", "--dry-run", "--name", "TestDryRun"]):
        ret = build_exe.run_build(build_exe.parse_arguments())
        assert ret == 0


def test_run_verification_tests_mock():
    """Verify run_verification_tests checks --version, --help, and --check."""
    mock_exe = Path("fake_path/SloVerbStudio.exe")

    def mock_subprocess_run(cmd, **kwargs):
        flag = cmd[1]
        if flag == "--version":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="SloVerb Studio v0.1.0\n", stderr="")
        elif flag == "--help":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="Usage: SloVerbStudio\n", stderr="")
        elif flag == "--check":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="DIAGNOSTICS_OK\n", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="Unknown flag")

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        success = build_exe.run_verification_tests(mock_exe, "0.1.0")
        assert success is True


def test_run_verification_tests_failure_mock():
    """Verify run_verification_tests reports failure if executable crashes or lacks expected output."""
    mock_exe = Path("fake_path/SloVerbStudio.exe")

    with patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Error")):
        success = build_exe.run_verification_tests(mock_exe, "0.1.0")
        assert success is False


@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows executable tests require Windows OS")
def test_compiled_executable_exists_and_valid_pe():
    """Verify generated SloVerbStudio.exe exists in dist/ and has valid Windows x86-64 PE header."""
    repo_root = build_exe.get_repo_root()
    exe_path = repo_root / "dist" / "SloVerbStudio.exe"
    if not exe_path.is_file():
        pytest.skip("dist/SloVerbStudio.exe has not been built yet")

    assert exe_path.stat().st_size > 10 * 1024 * 1024  # > 10 MB

    # Verify DOS and PE headers
    with open(exe_path, "rb") as f:
        dos_header = f.read(64)
        assert dos_header[:2] == b"MZ", "Missing DOS 'MZ' magic bytes"

        # e_lfanew offset to PE header is at offset 0x3C (60)
        pe_offset = int.from_bytes(dos_header[60:64], byteorder="little")
        f.seek(pe_offset)
        pe_sig = f.read(4)
        assert pe_sig == b"PE\x00\x00", "Missing 'PE\\0\\0' signature"

        # Machine type is at pe_offset + 4 (2 bytes). 0x8664 is IMAGE_FILE_MACHINE_AMD64
        machine = int.from_bytes(f.read(2), byteorder="little")
        assert machine == 0x8664, f"Expected x86-64 machine (0x8664), got: {hex(machine)}"


@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows executable tests require Windows OS")
def test_compiled_executable_cli_version():
    """Verify compiled executable runs --version and outputs current version."""
    repo_root = build_exe.get_repo_root()
    exe_path = repo_root / "dist" / "SloVerbStudio.exe"
    if not exe_path.is_file():
        pytest.skip("dist/SloVerbStudio.exe has not been built yet")

    res = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    assert "SloVerb Studio v0.1.0" in res.stdout


@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows executable tests require Windows OS")
def test_compiled_executable_cli_help():
    """Verify compiled executable runs --help and prints CLI usage."""
    repo_root = build_exe.get_repo_root()
    exe_path = repo_root / "dist" / "SloVerbStudio.exe"
    if not exe_path.is_file():
        pytest.skip("dist/SloVerbStudio.exe has not been built yet")

    res = subprocess.run([str(exe_path), "--help"], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    assert "Usage: SloVerbStudio" in res.stdout


@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows executable tests require Windows OS")
def test_compiled_executable_cli_check():
    """Verify compiled executable runs --check diagnostics and verifies numpy, sounddevice, ffmpeg."""
    repo_root = build_exe.get_repo_root()
    exe_path = repo_root / "dist" / "SloVerbStudio.exe"
    if not exe_path.is_file():
        pytest.skip("dist/SloVerbStudio.exe has not been built yet")

    res = subprocess.run([str(exe_path), "--check"], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    assert "DIAGNOSTICS_OK" in res.stdout
    assert "NumPy version:" in res.stdout
    assert "SoundDevice default hostapi:" in res.stdout

