"""
Diagnostic and environment inspection module for SloVerb Studio.

Collects platform, FFmpeg, audio subsystem, installed packages, and loaded
audio file metadata into a structured JSON report for troubleshooting.
"""

from collections import deque
from datetime import datetime, timezone
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import threading
from typing import Any, Dict, List, Optional

from slowverb.config import APP_NAME, get_subprocess_no_window_kwargs
from slowverb.platform import (
    PlatformType,
    detect_platform,
    get_android_abi,
    is_mobile_environment,
    is_mobile_platform,
)


class DiagnosticLogger:
    """Thread-safe in-memory ring buffer capturing terminal and error events."""

    _instance: Optional["DiagnosticLogger"] = None
    _lock = threading.Lock()

    def __init__(self, maxlen: int = 500):
        self._entries: deque = deque(maxlen=maxlen)
        self._entry_lock = threading.Lock()
        self._installed = False
        self._orig_stderr = None

    @classmethod
    def get_instance(cls) -> "DiagnosticLogger":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def log(self, message: str, level: str = "INFO"):
        """Appends a timestamped log entry."""
        if not message:
            return
        now = datetime.now(timezone.utc).isoformat()
        line = f"[{now}] [{level.upper()}] {message.strip()}"
        with self._entry_lock:
            self._entries.append(line)

    def log_error(self, message: str, exc: Optional[Exception] = None):
        """Appends an error entry with optional exception information."""
        if exc:
            message = f"{message} | Exception: {type(exc).__name__}: {str(exc)}"
        self.log(message, level="ERROR")

    def get_entries_dict(self) -> Dict[str, str]:
        """Returns the logged events as an indexed 1-based string dictionary."""
        with self._entry_lock:
            if not self._entries:
                return {"1": "NO TERMINAL ERRORS OR DIAGNOSTICS RECORDED"}
            return {str(idx + 1): entry for idx, entry in enumerate(self._entries)}

    def clear(self):
        """Clears all recorded entries."""
        with self._entry_lock:
            self._entries.clear()

    def install(self):
        """Hooks stderr to capture diagnostics into the ring buffer."""
        with self._entry_lock:
            if self._installed:
                return
            self._installed = True

        logger_ref = self

        class StderrInterceptor:
            def __init__(self, original):
                self._original = original

            def write(self, s):
                if s and s.strip():
                    logger_ref.log(s.strip(), level="STDERR")
                if self._original and hasattr(self._original, "write"):
                    try:
                        self._original.write(s)
                    except Exception:
                        pass

            def flush(self):
                if self._original and hasattr(self._original, "flush"):
                    try:
                        self._original.flush()
                    except Exception:
                        pass

            def __getattr__(self, item):
                return getattr(self._original, item)

        try:
            self._orig_stderr = sys.stderr
            sys.stderr = StderrInterceptor(self._orig_stderr)
        except Exception:
            pass

    def uninstall(self):
        """Restores original stderr stream if installed."""
        with self._entry_lock:
            if not self._installed:
                return
            if self._orig_stderr is not None:
                sys.stderr = self._orig_stderr
                self._orig_stderr = None
            self._installed = False


def get_ffmpeg_diagnostics(ffmpeg_path: Optional[str] = None) -> Dict[str, Any]:
    """Inspects FFmpeg location, version output, and active provider."""
    info: Dict[str, Any] = {
        "location": ffmpeg_path,
        "exists": bool(ffmpeg_path and os.path.isfile(ffmpeg_path)),
        "version": None,
        "provider": None,
    }
    if not ffmpeg_path or not os.path.isfile(ffmpeg_path):
        return info

    try:
        cmd = [ffmpeg_path, "-version"]
        res = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3,
            **get_subprocess_no_window_kwargs(),
        )
        if res.stdout:
            lines = res.stdout.strip().splitlines()
            info["version"] = "\n".join(lines[:5])
    except Exception as e:
        info["version"] = f"Error querying FFmpeg version: {e}"

    return info


def get_backend_capabilities(app: Any = None) -> Dict[str, Any]:
    """Inspects available audio subsystems, sound devices, and GUI modules."""
    caps: Dict[str, Any] = {
        "active_player": app.player.__class__.__name__ if app and getattr(app, "player", None) else None,
        "sounddevice": {
            "available": False,
            "version": None,
            "default_device": None,
            "devices": [],
            "host_apis": [],
        },
        "flet_audio": {
            "available": False,
            "version": None,
        },
        "tkinter": {
            "available": False,
        },
    }

    # SoundDevice query
    try:
        import sounddevice as sd
        caps["sounddevice"]["available"] = True
        caps["sounddevice"]["version"] = getattr(sd, "__version__", "unknown")
        try:
            default_dev = getattr(sd.default, "device", None)
            if default_dev is not None:
                caps["sounddevice"]["default_device"] = list(default_dev) if isinstance(default_dev, (list, tuple)) else str(default_dev)
            
            raw_devices = sd.query_devices()
            if isinstance(raw_devices, list):
                caps["sounddevice"]["devices"] = [
                    {
                        "index": idx,
                        "name": d.get("name"),
                        "max_input_channels": d.get("max_input_channels"),
                        "max_output_channels": d.get("max_output_channels"),
                        "default_samplerate": d.get("default_samplerate"),
                    }
                    for idx, d in enumerate(raw_devices)
                    if isinstance(d, dict)
                ]
            raw_apis = sd.query_hostapis()
            if isinstance(raw_apis, (list, tuple)):
                caps["sounddevice"]["host_apis"] = [
                    api.get("name") for api in raw_apis if isinstance(api, dict) and "name" in api
                ]
        except Exception as ex:
            caps["sounddevice"]["query_warning"] = str(ex)
    except Exception:
        caps["sounddevice"]["available"] = False

    # Flet-Audio query
    try:
        import flet_audio as fta
        caps["flet_audio"]["available"] = True
        caps["flet_audio"]["version"] = getattr(fta, "__version__", "installed")
    except Exception:
        caps["flet_audio"]["available"] = False

    # Tkinter query
    try:
        import tkinter
        caps["tkinter"]["available"] = True
    except Exception:
        caps["tkinter"]["available"] = False

    return caps


def get_python_site_packages() -> Dict[str, str]:
    """Returns sorted dictionary of installed Python distribution packages and versions."""
    packages: Dict[str, str] = {}
    try:
        for dist in importlib.metadata.distributions():
            name = dist.metadata.get("Name") if dist.metadata else None
            if name:
                packages[name] = dist.version
    except Exception as e:
        packages["_error"] = str(e)
    return dict(sorted(packages.items()))


def get_audio_file_diagnostics(app: Any) -> Optional[Dict[str, Any]]:
    """Returns metadata and modification parameters of the currently loaded audio file."""
    if not app or not getattr(app, "current_filepath", None):
        return None

    path = app.current_filepath
    exists = os.path.isfile(path)

    # Determine modification status
    mod_status = "UNKNOWN"
    if hasattr(app, "_is_buffer_current"):
        if app._is_buffer_current():
            mod_status = "CURRENT MODIFIED VERSION"
        elif getattr(app, "_rendered_effects", None) is not None:
            mod_status = "OLD MODIFIED VERSION"
        else:
            mod_status = "PRISTINE LOADED FILE"

    file_info: Dict[str, Any] = {
        "name": os.path.basename(path),
        "location": path,
        "access_type": {
            "exists": exists,
            "readable": os.access(path, os.R_OK) if exists else False,
            "writable": os.access(path, os.W_OK) if exists else False,
            "size_bytes": os.path.getsize(path) if exists else 0,
        },
        "modification_status": mod_status,
        "modifications": {
            "speed": getattr(app.effects, "speed", 1.0) if hasattr(app, "effects") else 1.0,
            "pitch": getattr(app.effects, "pitch", 1.0) if hasattr(app, "effects") else 1.0,
            "link_pitch_to_speed": getattr(app.effects, "link_pitch_to_speed", True) if hasattr(app, "effects") else True,
            "effective_pitch": getattr(app.effects, "effective_pitch", 1.0) if hasattr(app, "effects") else 1.0,
            "reverb_percent": getattr(app.effects, "reverb_percent", 0.0) if hasattr(app, "effects") else 0.0,
            "bass_boost_percent": getattr(app.effects, "bass_boost_percent", 0.0) if hasattr(app, "effects") else 0.0,
            "trim_start": getattr(app.effects, "trim_start", 0.0) if hasattr(app, "effects") else 0.0,
            "trim_end": getattr(app.effects, "trim_end", None) if hasattr(app, "effects") else None,
            "is_trimmed": getattr(app.effects, "is_trimmed", False) if hasattr(app, "effects") else False,
            "export_format": getattr(app, "export_format", "opus"),
        },
        "metadata": None,
    }

    if getattr(app, "metadata", None):
        m = app.metadata
        file_info["metadata"] = {
            "title": getattr(m, "title", ""),
            "artist": getattr(m, "artist", ""),
            "duration_sec": getattr(m, "duration", 0.0),
            "formatted_duration": getattr(m, "formatted_duration", "00:00.0"),
            "sample_rate": getattr(m, "sample_rate", 44100),
            "channels": getattr(m, "channels", 2),
            "bitrate_kbps": getattr(m, "bitrate", 0),
            "format_name": getattr(m, "format_name", ""),
        }

    return file_info


def generate_debug_dump(app: Any = None) -> Dict[str, Any]:
    """
    Assembles a comprehensive diagnostics dictionary for SloVerb Studio.
    """
    page = getattr(app, "page", None) if app else None
    plat_type = detect_platform(page)
    logger = DiagnosticLogger.get_instance()

    dump: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "app": {
            "name": APP_NAME,
            "version": getattr(app, "version", "0.4.0"),
            "debug_mode": getattr(app, "debug_mode", True) if app else True,
            "is_frozen": getattr(sys, "frozen", False),
            "python_executable": sys.executable,
            "app_directory": os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "argv": sys.argv,
        },
        "platform": {
            "os_name": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "architecture": list(platform.architecture()),
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "platform_type": plat_type.value,
            "is_mobile_platform": is_mobile_platform(page),
            "is_mobile_environment": is_mobile_environment(page),
            "android_abi": get_android_abi() if plat_type == PlatformType.ANDROID else None,
            "android_api_level": getattr(sys, "getandroidapilevel", lambda: None)(),
        },
        "screen_size": {
            "page_width": getattr(page, "width", None) if page else None,
            "page_height": getattr(page, "height", None) if page else None,
            "window_width": getattr(page.window, "width", None) if page and hasattr(page, "window") else None,
            "window_height": getattr(page.window, "height", None) if page and hasattr(page, "window") else None,
            "page_platform": str(getattr(page, "platform", None)) if page else None,
        },
        "ffmpeg": get_ffmpeg_diagnostics(getattr(app, "ffmpeg_path", None) if app else None),
        "backend_capabilities": get_backend_capabilities(app),
        "python_site_packages": get_python_site_packages(),
        "audio_file": get_audio_file_diagnostics(app),
        "terminal": logger.get_entries_dict(),
    }
    return dump
