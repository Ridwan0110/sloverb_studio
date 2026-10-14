"""Tests for redu-dev/build_binary.py universal binary builder and archive packager."""

import os
import platform
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

# Import helper builder module from redu-dev/build_binary.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "redu-dev"))
import build_binary


def test_detect_platform_current():
    """Verify detect_platform accurately identifies the host OS and architecture."""
    os_name, arch_name = build_binary.detect_platform()
    assert os_name in ("windows", "linux", "darwin")
    assert arch_name in ("x86_64", "arm64")


def test_detect_platform_normalization():
    """Verify platform normalization across common machine and system names."""
    cases = [
        (("Windows", "AMD64"), ("windows", "x86_64")),
        (("Windows", "x86_64"), ("windows", "x86_64")),
        (("Linux", "x86_64"), ("linux", "x86_64")),
        (("Linux", "aarch64"), ("linux", "arm64")),
        (("Darwin", "arm64"), ("darwin", "arm64")),
        (("Darwin", "x86_64"), ("darwin", "x86_64")),
    ]

    for (sys_name, mach), (expected_os, expected_arch) in cases:
        with patch("platform.system", return_value=sys_name), patch("platform.machine", return_value=mach):
            actual_os, actual_arch = build_binary.detect_platform()
            assert (actual_os, actual_arch) == (expected_os, expected_arch)


def test_get_repo_root():
    """Verify get_repo_root locates repository root containing sloverb_studio.py."""
    root = build_binary.get_repo_root()
    assert root.is_dir()
    assert (root / "sloverb_studio.py").is_file()
    assert (root / "slowverb").is_dir()
    assert (root / "assets").is_dir()


def test_check_prerequisites():
    """Verify prerequisites detector checks required entry point, assets, and dependencies."""
    repo_root = build_binary.get_repo_root()
    prereqs = build_binary.check_prerequisites(repo_root)

    assert prereqs["entry_point"] is True
    assert prereqs["font_awesome"] is True
    assert prereqs["packages"]["flet"] is True
    assert prereqs["packages"]["PyInstaller"] is True
    assert prereqs["packages"]["sounddevice"] is True
    assert prereqs["packages"]["numpy"] is True


def test_builder_argument_parsing():
    """Verify argument parser handles defaults and custom options."""
    with patch(
        "sys.argv",
        [
            "build_binary.py",
            "--name",
            "CustomBinary",
            "--distpath",
            "custom_dist",
            "--onedir",
            "--console",
            "--target-os",
            "linux",
            "--target-arch",
            "arm64",
        ],
    ):
        args = build_binary.parse_arguments()
        assert args.name == "CustomBinary"
        assert args.distpath == "custom_dist"
        assert args.onedir is True
        assert args.console is True
        assert args.clean is True
        assert args.verify is False
        assert args.target_os == "linux"
        assert args.target_arch == "arm64"


def test_builder_cross_compile_refusal():
    """Verify builder refuses to cross-compile across OS boundaries and reports error."""
    host_os, _ = build_binary.detect_platform()
    other_os = "linux" if host_os != "linux" else "windows"

    with patch(
        "sys.argv",
        ["build_binary.py", "--target-os", other_os],
    ):
        ret = build_binary.run_build(build_binary.parse_arguments())
        assert ret == 1


def test_builder_dry_run():
    """Verify builder --dry-run option generates command without executing build."""
    with patch("sys.argv", ["build_binary.py", "--dry-run", "--name", "TestDryRun"]):
        ret = build_binary.run_build(build_binary.parse_arguments())
        assert ret == 0


def test_create_distribution_archive_zip(tmp_path):
    """Verify create_distribution_archive creates a valid zip archive."""
    fake_dir = tmp_path / "SloVerbStudio.app"
    fake_dir.mkdir()
    fake_file = fake_dir / "test.txt"
    fake_file.write_text("sample content")

    output_zip = tmp_path / "test_archive.zip"
    build_binary.create_distribution_archive(fake_dir, output_zip, "darwin")

    assert output_zip.is_file()
    with zipfile.ZipFile(output_zip, "r") as zf:
        names = zf.namelist()
        assert any("test.txt" in n for n in names)


def test_create_distribution_archive_targz(tmp_path):
    """Verify create_distribution_archive creates a valid tar.gz archive for Linux."""
    fake_binary = tmp_path / "SloVerbStudio"
    fake_binary.write_text("#!/bin/sh\necho ok")

    output_tar = tmp_path / "test_archive.tar.gz"
    build_binary.create_distribution_archive(fake_binary, output_tar, "linux")

    assert output_tar.is_file()
    with tarfile.open(output_tar, "r:gz") as tf:
        names = tf.getnames()
        assert "SloVerbStudio" in names


def test_run_verification_tests_mock():
    """Verify run_verification_tests checks --version."""
    mock_bin = Path("fake_path/SloVerbStudio")

    def mock_subprocess_run(cmd, **kwargs):
        flag = cmd[1]
        if flag == "--version":
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="SloVerb Studio v0.1.0\n", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="Unknown flag")

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        success = build_binary.run_verification_tests(mock_bin, "0.1.0")
        assert success is True


def test_run_verification_tests_failure_mock():
    """Verify run_verification_tests reports failure if executable crashes or lacks expected output."""
    mock_bin = Path("fake_path/SloVerbStudio")

    with patch("subprocess.run", return_value=subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="Error")):
        success = build_binary.run_verification_tests(mock_bin, "0.1.0")
        assert success is False


@pytest.mark.skipif(platform.system().lower() != "windows", reason="Windows executable tests require Windows OS")
def test_compiled_executable_if_present():
    """Verify that if dist/SloVerbStudio.exe is present, it passes version output check."""
    repo_root = build_binary.get_repo_root()
    exe_path = repo_root / "dist" / "SloVerbStudio.exe"
    if not exe_path.is_file():
        pytest.skip("dist/SloVerbStudio.exe not yet built")

    res = subprocess.run([str(exe_path), "--version"], capture_output=True, text=True, timeout=15)
    assert res.returncode == 0
    assert "SloVerb Studio v0.1.0" in res.stdout

