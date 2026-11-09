"""Audio processing engine using FFmpeg and NumPy for SlowVerb Studio."""

from dataclasses import dataclass, field
import math
import os
import re
import subprocess
import tempfile
import threading
from typing import List, Optional, Tuple
import numpy as np

from slowverb.config import (
    DEFAULT_BASS,
    DEFAULT_PITCH,
    DEFAULT_REVERB,
    DEFAULT_SPEED,
    MAX_BASS,
    MAX_PITCH,
    MAX_REVERB,
    MAX_SPEED,
    MIN_BASS,
    MIN_PITCH,
    MIN_REVERB,
    MIN_SPEED,
    get_ffmpeg_path,
    get_subprocess_no_window_kwargs,
)


@dataclass
class AudioMetadata:
    """Metadata container for loaded audio files."""
    filepath: str
    filename: str
    duration: float  # seconds
    sample_rate: int = 44100
    channels: int = 2
    bitrate: int = 0
    format_name: str = ""
    title: str = ""
    artist: str = ""

    @property
    def formatted_duration(self) -> str:
        """Returns duration in MM:SS.S format."""
        m = int(self.duration // 60)
        s = self.duration % 60
        return f"{m:02d}:{s:04.1f}"


@dataclass
class AudioEffects:
    """Audio effect parameters with validation and clamping."""
    speed: float = DEFAULT_SPEED
    pitch: float = DEFAULT_PITCH
    link_pitch_to_speed: bool = True
    reverb_percent: float = DEFAULT_REVERB
    bass_boost_percent: float = DEFAULT_BASS
    trim_start: float = 0.0
    trim_end: Optional[float] = None

    def __post_init__(self):
        self.clamp_values()

    def clamp_values(self):
        """Ensures all values stay within safe defined ranges."""
        self.speed = round(max(MIN_SPEED, min(MAX_SPEED, float(self.speed))), 3)
        self.pitch = round(max(MIN_PITCH, min(MAX_PITCH, float(self.pitch))), 3)
        self.reverb_percent = round(max(MIN_REVERB, min(MAX_REVERB, float(self.reverb_percent))), 2)
        self.bass_boost_percent = round(max(MIN_BASS, min(MAX_BASS, float(self.bass_boost_percent))), 2)
        if self.trim_start < 0.0:
            self.trim_start = 0.0
        if self.trim_end is not None and self.trim_end < self.trim_start:
            self.trim_end = self.trim_start

    @property
    def effective_pitch(self) -> float:
        """If linked to speed, pitch tracks speed ratio; otherwise uses independent pitch."""
        return self.speed if self.link_pitch_to_speed else self.pitch

    def calculate_output_duration(self, original_duration: float) -> float:
        """Estimates the resulting duration after trimming and speed scaling."""
        t_start = max(0.0, self.trim_start)
        t_end = min(original_duration, self.trim_end) if self.trim_end is not None else original_duration
        trimmed_len = max(0.0, t_end - t_start)
        eff_speed = max(0.01, self.speed)
        return round(trimmed_len / eff_speed, 2)


@dataclass
class WaveformData:
    """Waveform visualization cache and peak lookup."""
    peaks: List[float] = field(default_factory=list)  # Normalized 0.0 to 1.0
    duration: float = 0.0
    max_peak_db: float = -100.0
    rms_db: float = -100.0

    def get_peak_at_time(self, time_sec: float) -> float:
        """Returns normalized peak amplitude (0.0 - 1.0) at specific timestamp."""
        if not self.peaks or self.duration <= 0:
            return 0.0
        ratio = max(0.0, min(1.0, time_sec / self.duration))
        idx = int(ratio * (len(self.peaks) - 1))
        return self.peaks[idx]

    def get_peak_db_at_time(self, time_sec: float) -> float:
        """Returns peak in dBFS at specific timestamp."""
        peak = self.get_peak_at_time(time_sec)
        if peak <= 1e-4:
            return -80.0
        return round(20.0 * math.log10(peak), 1)


class AudioEngine:
    """Core audio processing engine powered by FFmpeg."""

    def __init__(self, ffmpeg_path: Optional[str] = None, auto_ensure: bool = True, page=None):
        self._temp_files: List[str] = []
        if not ffmpeg_path:
            from slowverb.ffmpeg import get_ffmpeg_provider
            provider = get_ffmpeg_provider(page=page)
            resolved = provider.get_binary_path()
            if resolved:
                ffmpeg_path = resolved
            else:
                ffmpeg_path = get_ffmpeg_path(ensure=auto_ensure)
        self.use_pyav: bool = False
        if ffmpeg_path == "pyav":
            try:
                import av  # noqa: F401
                self.use_pyav = True
                self.ffmpeg_path = "pyav"
            except ImportError:
                raise FileNotFoundError("PyAV (av) is not installed.")
        elif ffmpeg_path and os.path.isfile(ffmpeg_path):
            self.ffmpeg_path = ffmpeg_path
            self.use_pyav = False
        else:
            try:
                import av  # noqa: F401
                self.use_pyav = True
                self.ffmpeg_path = "pyav"
            except ImportError:
                target_str = str(ffmpeg_path) if ffmpeg_path else "None"
                raise FileNotFoundError(
                    f"FFmpeg binary not found at '{target_str}'. "
                    f"Please ensure FFmpeg is installed system-wide, inside the 'ffmpeg' directory, or PyAV is installed."
                )

    def __del__(self):
        self.cleanup()

    def cleanup(self):
        """Cleans up all temporary files generated by the engine."""
        temp_files = getattr(self, "_temp_files", [])
        for temp_file in temp_files:
            try:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
            except OSError:
                pass
        temp_files.clear()

    def _probe_file_pyav(self, filepath: str) -> AudioMetadata:
        import av
        try:
            container = av.open(filepath)
        except Exception as e:
            raise RuntimeError(f"Failed to read audio file '{filepath}': {e}")

        with container:
            if not container.streams.audio:
                raise RuntimeError(f"No audio streams found in '{filepath}'.")
            stream = container.streams.audio[0]
            duration = 0.0
            if stream.duration is not None and stream.time_base is not None:
                duration = float(stream.duration * stream.time_base)
            if duration <= 0.0 and container.duration is not None:
                duration = float(container.duration / av.time_base)

            sr = stream.rate or 44100
            channels = getattr(stream, "channels", 2) or 2
            bitrate = stream.bit_rate or getattr(container, "bit_rate", 0) or 0
            if bitrate > 1000:
                bitrate = int(bitrate // 1000)
            fmt_name = os.path.splitext(filepath)[1].lstrip(".").lower()
            metadata = container.metadata or {}
            title = metadata.get("title") or os.path.splitext(os.path.basename(filepath))[0]
            artist = metadata.get("artist") or ""

        return AudioMetadata(
            filepath=os.path.abspath(filepath),
            filename=os.path.basename(filepath),
            duration=round(duration, 2),
            sample_rate=sr,
            channels=channels,
            bitrate=bitrate,
            format_name=fmt_name,
            title=title,
            artist=artist,
        )

    def probe_file(self, filepath: str) -> AudioMetadata:
        """Extracts technical metadata from an audio file."""
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Input file not found: {filepath}")

        if getattr(self, "use_pyav", False):
            return self._probe_file_pyav(filepath)

        cmd = [self.ffmpeg_path, "-hide_banner", "-i", filepath, "-f", "null", "-"]
        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            **get_subprocess_no_window_kwargs(),
        )
        info = proc.stderr or ""

        if proc.returncode != 0 or "Invalid data found" in info:
            err_detail = info.strip() if info else f"Exit code {proc.returncode}"
            raise RuntimeError(f"Failed to read audio file '{filepath}': {err_detail}")

        # Duration
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", info)
        if dur_match:
            hours = int(dur_match.group(1))
            minutes = int(dur_match.group(2))
            seconds = float(dur_match.group(3))
            duration = hours * 3600 + minutes * 60 + seconds
        else:
            raise RuntimeError(f"Could not determine audio duration from '{filepath}'")

        # Sample Rate
        sr_match = re.search(r"(\d+)\s*Hz", info)
        sample_rate = int(sr_match.group(1)) if sr_match else 44100

        # Channels
        channels = 2
        if "stereo" in info:
            channels = 2
        elif "mono" in info:
            channels = 1
        else:
            ch_match = re.search(r"(\d+)\s*channels", info)
            if ch_match:
                channels = int(ch_match.group(1))

        # Bitrate
        br_match = re.search(r"bitrate:\s*(\d+)\s*kb/s", info)
        bitrate = int(br_match.group(1)) if br_match else 0

        # Title & Artist
        title_match = re.search(r"title\s*:\s*(.+)", info, re.IGNORECASE)
        artist_match = re.search(r"artist\s*:\s*(.+)", info, re.IGNORECASE)
        title = title_match.group(1).strip() if title_match else os.path.splitext(os.path.basename(filepath))[0]
        artist = artist_match.group(1).strip() if artist_match else ""

        # Format
        ext = os.path.splitext(filepath)[1].lstrip(".").lower()

        return AudioMetadata(
            filepath=os.path.abspath(filepath),
            filename=os.path.basename(filepath),
            duration=duration,
            sample_rate=sample_rate,
            channels=channels,
            bitrate=bitrate,
            format_name=ext,
            title=title,
            artist=artist,
        )

    def _extract_waveform_pyav(self, filepath: str, num_bins: int = 100) -> WaveformData:
        import av
        try:
            container = av.open(filepath)
        except Exception as e:
            raise RuntimeError(f"Failed to read audio file '{filepath}': {e}")

        with container:
            if not container.streams.audio:
                raise RuntimeError(f"No audio stream found in '{filepath}'.")
            stream = container.streams.audio[0]
            duration = 0.0
            if stream.duration is not None and stream.time_base is not None:
                duration = float(stream.duration * stream.time_base)
            if duration <= 0.0 and container.duration is not None:
                duration = float(container.duration / av.time_base)

            resampler = av.AudioResampler(format="s16", layout="mono", rate=8000)
            chunks = []
            for frame in container.decode(stream):
                resampled = resampler.resample(frame)
                for r in resampled:
                    chunks.append(r.to_ndarray().flatten())
            try:
                flushed = resampler.resample(None)
                for r in flushed:
                    chunks.append(r.to_ndarray().flatten())
            except Exception:
                pass

            if not chunks:
                return WaveformData(peaks=[0.0] * num_bins, duration=duration)

            samples = np.concatenate(chunks).astype(np.float32) / 32768.0
            return self.extract_waveform_from_samples(samples, sample_rate=8000, num_bins=num_bins)

    def extract_waveform(self, filepath: str, num_bins: int = 100) -> WaveformData:
        """
        Downsamples the audio track to 8kHz mono and extracts peak amplitudes
        binned across the duration for responsive GUI waveform rendering.
        """
        if not os.path.isfile(filepath):
            raise FileNotFoundError(f"Input file not found: {filepath}")

        if getattr(self, "use_pyav", False):
            return self._extract_waveform_pyav(filepath, num_bins=num_bins)

        meta = self.probe_file(filepath)
        if meta.duration <= 0.0:
            return WaveformData(peaks=[0.0] * num_bins, duration=0.0)

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-i", filepath,
            "-ac", "1",
            "-ar", "8000",
            "-f", "s16le",
            "-"
        ]

        file_size = os.path.getsize(filepath)
        safe_limit = 50 * 1024 * 1024

        if file_size > safe_limit:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **get_subprocess_no_window_kwargs(),
            )
            err_output = []
            def read_stderr():
                for line in proc.stderr:
                    err_output.append(line)

            stderr_thread = threading.Thread(target=read_stderr)
            stderr_thread.start()

            # Streaming computation
            # We don't know exact total samples, but duration * 8000 is a good guess.
            total_expected_samples = int(math.ceil(meta.duration * 8000))
            if total_expected_samples <= 0:
                total_expected_samples = 1

            bin_size = max(1, total_expected_samples // num_bins)
            current_bin = 0
            current_bin_samples = 0
            current_bin_max = 0.0

            peaks = []

            overall_max = 0.0
            sum_squares = 0.0
            total_samples = 0

            remainder = b""
            chunk_size = 1024 * 1024  # 1MB chunks

            while True:
                chunk = proc.stdout.read(chunk_size)
                if not chunk:
                    break
                data = remainder + chunk
                align = len(data) - (len(data) % 2)
                if align > 0:
                    arr = np.frombuffer(data[:align], dtype=np.int16)
                    float_arr = np.abs(arr.astype(np.float32) / 32768.0)

                    if len(float_arr) > 0:
                        chunk_max = float(np.max(float_arr))
                        if chunk_max > overall_max:
                            overall_max = chunk_max

                        sum_squares += float(np.sum(float_arr ** 2))
                        total_samples += len(float_arr)

                        # binning
                        for val in float_arr:
                            if val > current_bin_max:
                                current_bin_max = float(val)
                            current_bin_samples += 1
                            if current_bin_samples >= bin_size:
                                peaks.append(current_bin_max)
                                current_bin_max = 0.0
                                current_bin_samples = 0

                remainder = data[align:]

            if current_bin_samples > 0:
                peaks.append(current_bin_max)

            proc.stdout.close()
            proc.wait()
            stderr_thread.join()

            if proc.returncode != 0:
                err_msg = b"".join(err_output).decode('utf-8', errors='replace') if err_output else f"Exit code {proc.returncode}"
                raise RuntimeError(f"FFmpeg waveform extraction failed: {err_msg}")

            # pad to num_bins if needed
            while len(peaks) < num_bins:
                peaks.append(0.0)

            # truncate to num_bins
            if len(peaks) > num_bins:
                # downsample the peaks array simply
                step = len(peaks) / float(num_bins)
                new_peaks = []
                for i in range(num_bins):
                    idx = int(i * step)
                    new_peaks.append(peaks[idx])
                peaks = new_peaks

            overall_rms = math.sqrt(sum_squares / total_samples) if total_samples > 0 else 0.0

        else:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **get_subprocess_no_window_kwargs(),
            )
            if proc.returncode != 0:
                err_msg = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else f"Exit code {proc.returncode}"
                raise RuntimeError(f"FFmpeg waveform extraction failed: {err_msg}")
            raw_data = np.frombuffer(proc.stdout, dtype=np.int16)
            if len(raw_data) == 0:
                return WaveformData(peaks=[0.0] * num_bins, duration=meta.duration)

            float_samples = np.abs(raw_data.astype(np.float32) / 32768.0)
            overall_max = float(np.max(float_samples)) if len(float_samples) > 0 else 0.0
            overall_rms = float(np.sqrt(np.mean(float_samples ** 2))) if len(float_samples) > 0 else 0.0

            bin_size = max(1, len(float_samples) // num_bins)
            peaks: List[float] = []

            for i in range(num_bins):
                start = i * bin_size
                end = min(len(float_samples), (i + 1) * bin_size)
                if start < len(float_samples):
                    chunk_peak = float(np.max(float_samples[start:end]))
                else:
                    chunk_peak = 0.0
                peaks.append(chunk_peak)

        max_db = round(20.0 * math.log10(max(1e-5, overall_max)), 1)
        rms_db = round(20.0 * math.log10(max(1e-5, overall_rms)), 1)

        # Normalize peaks so maximum bar reaches near 1.0 while preserving relative dynamics
        norm_factor = max(peaks) if peaks and max(peaks) > 0 else 1.0
        normalized_peaks = [min(1.0, round(p / norm_factor, 3)) for p in peaks]

        return WaveformData(
            peaks=normalized_peaks,
            duration=meta.duration,
            max_peak_db=max_db,
            rms_db=rms_db,
        )

    def extract_waveform_from_samples(
        self, samples: np.ndarray, sample_rate: int = 44100, num_bins: int = 90, duration: Optional[float] = None
    ) -> WaveformData:
        """
        Extracts peak amplitudes and dB readings directly from an in-memory numpy audio buffer.
        """
        dur = duration if duration is not None else (len(samples) / sample_rate if sample_rate > 0 else 0.0)
        if len(samples) == 0:
            return WaveformData(peaks=[0.0] * num_bins, duration=dur)

        float_samples = np.abs(samples.astype(np.float32))
        overall_max = float(np.max(float_samples)) if len(float_samples) > 0 else 0.0
        overall_rms = float(np.sqrt(np.mean(float_samples ** 2))) if len(float_samples) > 0 else 0.0

        max_db = round(20.0 * math.log10(max(1e-5, overall_max)), 1)
        rms_db = round(20.0 * math.log10(max(1e-5, overall_rms)), 1)

        bin_size = max(1, len(float_samples) // num_bins)
        peaks: List[float] = []

        for i in range(num_bins):
            start = i * bin_size
            end = min(len(float_samples), (i + 1) * bin_size)
            if start < len(float_samples):
                chunk_peak = float(np.max(float_samples[start:end]))
            else:
                chunk_peak = 0.0
            peaks.append(chunk_peak)

        norm_factor = max(peaks) if peaks and max(peaks) > 0 else 1.0
        normalized_peaks = [min(1.0, round(p / norm_factor, 3)) for p in peaks]

        return WaveformData(
            peaks=normalized_peaks,
            duration=dur,
            max_peak_db=max_db,
            rms_db=rms_db,
        )

    def has_filter(self, filter_name: str) -> Optional[bool]:
        """
        Checks if a specific filter is supported by the current FFmpeg installation.
        Returns True/False if determinable, or None if FFmpeg could not be queried.
        """
        if getattr(self, "use_pyav", False):
            try:
                import av.filter
                if hasattr(av.filter, "filters_available"):
                    return filter_name in av.filter.filters_available
            except Exception:
                pass
            return False

        if not hasattr(self, "_supported_filters"):
            try:
                cmd = [self.ffmpeg_path, "-hide_banner", "-filters"]
                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    encoding="utf-8",
                    errors="replace",
                    **get_subprocess_no_window_kwargs(),
                )
                if proc.returncode == 0 and proc.stdout:
                    self._supported_filters = {
                        parts[1]
                        for line in proc.stdout.splitlines()
                        for parts in [line.split()]
                        if len(parts) >= 2
                    }
                else:
                    self._supported_filters = None
            except Exception:
                self._supported_filters = None

        if self._supported_filters is None:
            return None
        return filter_name in self._supported_filters

    def build_audio_filter_string(self, effects: AudioEffects) -> str:
        """
        Builds the FFmpeg audio filter string (-af) implementing:
        1. Speed & Pitch via rubberband
        2. Bass boost via lowshelf / bass filter
        3. Reverb via tuned multi-stage aecho
        4. Soft peak limiter to prevent digital clipping
        """
        filters: List[str] = []

        # 1. Speed and Pitch
        speed = effects.speed
        pitch = effects.effective_pitch
        # Apply rubberband if speed or pitch differs from unity (1.0)
        if abs(speed - 1.0) > 1e-4 or abs(pitch - 1.0) > 1e-4:
            if self.has_filter("rubberband") is True or (self.has_filter("rubberband") is None and not getattr(self, "use_pyav", False)):
                filters.append(f"rubberband=tempo={speed:.4f}:pitch={pitch:.4f}")
            elif self.has_filter("rubberband") is False and not getattr(self, "use_pyav", False):
                raise RuntimeError(
                    f"FFmpeg binary at '{self.ffmpeg_path}' does not support the 'rubberband' audio filter "
                    f"required for speed and pitch adjustments. Please install a full FFmpeg build "
                    f"(e.g., 'brew install ffmpeg-full' on macOS or Gyan full build on Windows)."
                )
            else:
                if effects.link_pitch_to_speed:
                    filters.append(f"asetrate=44100*{speed:.4f},aresample=44100")
                else:
                    filters.append(f"asetrate=44100*{pitch:.4f},aresample=44100")
                    ratio = speed / pitch
                    if abs(ratio - 1.0) > 1e-4:
                        filters.append(f"atempo={ratio:.4f}")

        # 2. Bass Boost (0% - 100% maps to 0dB - 18dB gain at 100Hz)
        if effects.bass_boost_percent > 0.01:
            gain_db = (effects.bass_boost_percent / 100.0) * 18.0
            filters.append(f"bass=g={gain_db:.2f}:f=100")

        # 3. Reverb (0% - 100%)
        if effects.reverb_percent > 0.01:
            w = max(0.01, min(1.0, effects.reverb_percent / 100.0))

            in_gain = max(0.68, 1.0 - (0.25 * w))
            out_gain1 = min(0.85, 0.28 + (0.50 * w))
            out_gain2 = out_gain1 * 0.70

            # Early reflections with a 0.01 minimum floor
            d1 = "50|100|200|350"
            decay1 = f"{max(0.01, 0.50 * w):.2f}|{max(0.01, 0.38 * w):.2f}|{max(0.01, 0.28 * w):.2f}|{max(0.01, 0.18 * w):.2f}"
            filters.append(f"aecho={in_gain:.2f}:{out_gain1:.2f}:{d1}:{decay1}")

            # Late diffusion reflections with a 0.01 minimum floor
            d2 = "70|150|300|600"
            decay2 = f"{max(0.01, 0.35 * w):.2f}|{max(0.01, 0.25 * w):.2f}|{max(0.01, 0.18 * w):.2f}|{max(0.01, 0.10 * w):.2f}"
            filters.append(f"aecho={in_gain:.2f}:{out_gain2:.2f}:{d2}:{decay2}")

        # 4. Limiter to avoid clipping if effects pushed gain
        if effects.bass_boost_percent > 0.01 or effects.reverb_percent > 0.01:
            filters.append("alimiter=limit=0.98")

        return ",".join(filters)

    def _export_audio_pyav(
        self,
        input_path: str,
        output_path: str,
        effects: AudioEffects,
        export_format: Optional[str] = None,
    ) -> Tuple[str, int]:
        import av

        effects.clamp_values()
        ext = export_format or os.path.splitext(output_path)[1].lstrip(".").lower()
        if not ext:
            ext = "opus"
        ext = ext.lower()

        if ext not in ["opus", "mp3", "wav"]:
            raise ValueError(f"Unsupported export format '{ext}'. Must be 'opus', 'mp3', or 'wav'.")

        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        target_rate = 48000 if ext == "opus" else 44100

        try:
            in_c = av.open(input_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open audio file '{input_path}': {e}")

        with in_c:
            if not in_c.streams.audio:
                raise ValueError(f"No audio stream in '{input_path}'.")
            in_s = in_c.streams.audio[0]

            graph = av.filter.Graph()
            source = graph.add_abuffer(template=in_s)
            nodes = [source]

            if effects.trim_start > 0.001:
                try:
                    in_c.seek(int(effects.trim_start * av.time_base))
                except Exception:
                    pass

            speed = float(effects.speed)
            pitch = float(effects.effective_pitch)
            if abs(speed - 1.0) > 0.001 or abs(pitch - 1.0) > 0.001:
                if effects.link_pitch_to_speed:
                    new_rate = int(round(in_s.rate * speed))
                    nodes.append(graph.add("asetrate", str(new_rate)))
                    nodes.append(graph.add("aresample", str(target_rate)))
                else:
                    new_rate = int(round(in_s.rate * pitch))
                    nodes.append(graph.add("asetrate", str(new_rate)))
                    nodes.append(graph.add("aresample", str(target_rate)))
                    ratio = speed / pitch
                    if abs(ratio - 1.0) > 0.001:
                        nodes.append(graph.add("atempo", f"{ratio:.4f}"))

            if effects.bass_boost_percent > 0.01:
                gain_db = (effects.bass_boost_percent / 100.0) * 18.0
                nodes.append(graph.add("bass", f"g={gain_db:.2f}:f=100"))

            if effects.reverb_percent > 0.01:
                w = max(0.01, min(1.0, effects.reverb_percent / 100.0))
                in_gain = max(0.68, 1.0 - (0.25 * w))
                out_gain1 = min(0.85, 0.28 + (0.50 * w))
                out_gain2 = out_gain1 * 0.70
                d1 = "50|100|200|350"
                decay1 = f"{max(0.01, 0.50 * w):.2f}|{max(0.01, 0.38 * w):.2f}|{max(0.01, 0.28 * w):.2f}|{max(0.01, 0.18 * w):.2f}"
                nodes.append(graph.add("aecho", f"{in_gain:.2f}:{out_gain1:.2f}:{d1}:{decay1}"))
                d2 = "70|150|300|600"
                decay2 = f"{max(0.01, 0.35 * w):.2f}|{max(0.01, 0.25 * w):.2f}|{max(0.01, 0.18 * w):.2f}|{max(0.01, 0.10 * w):.2f}"
                nodes.append(graph.add("aecho", f"{in_gain:.2f}:{out_gain2:.2f}:{d2}:{decay2}"))

            if effects.bass_boost_percent > 0.01 or effects.reverb_percent > 0.01:
                nodes.append(graph.add("alimiter", "limit=0.98"))

            sample_fmt = "fltp" if ext in ("opus", "mp3") else "s16"
            nodes.append(graph.add("aformat", f"sample_fmts={sample_fmt}:sample_rates={target_rate}:channel_layouts=stereo"))
            sink = graph.add("abuffersink")
            nodes.append(sink)

            graph.link_nodes(*nodes)
            graph.configure()

            with av.open(output_path, mode="w") as out_c:
                if ext == "opus":
                    out_s = out_c.add_stream("libopus", rate=target_rate, layout="stereo")
                    out_s.bit_rate = 160000
                elif ext == "mp3":
                    out_s = out_c.add_stream("libmp3lame", rate=target_rate, layout="stereo")
                    out_s.bit_rate = 192000
                elif ext == "wav":
                    out_s = out_c.add_stream("pcm_s16le", rate=target_rate, layout="stereo")

                samples_seen = 0
                stream_rate = in_s.rate or target_rate or 44100
                for frame in in_c.decode(in_s):
                    frame_time = float(frame.time) if frame.time is not None else samples_seen / stream_rate
                    samples_seen += frame.samples
                    if frame_time < effects.trim_start:
                        continue
                    if effects.trim_end is not None and frame_time > effects.trim_end:
                        break

                    try:
                        graph.push(frame)
                    except Exception:
                        break

                    while True:
                        try:
                            filt_frame = graph.pull()
                            for packet in out_s.encode(filt_frame):
                                out_c.mux(packet)
                        except Exception:
                            break

                try:
                    graph.push(None)
                except Exception:
                    pass
                while True:
                    try:
                        filt_frame = graph.pull()
                        for packet in out_s.encode(filt_frame):
                            out_c.mux(packet)
                    except Exception:
                        break

                for packet in out_s.encode(None):
                    out_c.mux(packet)

        if not os.path.isfile(output_path):
            raise FileNotFoundError(f"Export output file was not created at '{output_path}'")
        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise RuntimeError(f"Exported output file is empty (0 bytes): '{output_path}'")
        return output_path, file_size

    def export_audio(
        self,
        input_path: str,
        output_path: str,
        effects: AudioEffects,
        export_format: Optional[str] = None,
    ) -> Tuple[str, int]:
        """
        Exports the processed audio to MP3 or Opus with effects and trimming applied.
        Returns: (output_path, file_size_in_bytes)
        """
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if getattr(self, "use_pyav", False):
            return self._export_audio_pyav(input_path, output_path, effects, export_format)

        effects.clamp_values()
        ext = export_format or os.path.splitext(output_path)[1].lstrip(".").lower()
        if not ext:
            ext = "opus"
        ext = ext.lower()

        if ext not in ["opus", "mp3", "wav"]:
            raise ValueError(f"Unsupported export format '{ext}'. Must be 'opus', 'mp3', or 'wav'.")

        # Ensure output directory exists
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        cmd: List[str] = [self.ffmpeg_path, "-y"]

        # Trimming start
        if effects.trim_start > 0.001:
            cmd.extend(["-ss", f"{effects.trim_start:.3f}"])

        # Trimming end
        if effects.trim_end is not None and effects.trim_end > effects.trim_start:
            cmd.extend(["-to", f"{effects.trim_end:.3f}"])

        cmd.extend(["-i", os.path.abspath(input_path)])

        # Build filter graph
        af = self.build_audio_filter_string(effects)
        if af:
            cmd.extend(["-af", af])

        # Codec configuration
        if ext == "opus":
            cmd.extend(["-c:a", "libopus", "-b:a", "160k", "-vbr", "on"])
        elif ext == "mp3":
            cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k", "-q:a", "2"])
        elif ext == "wav":
            cmd.extend(["-c:a", "pcm_s16le"])

        cmd.append(os.path.abspath(output_path))

        proc = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            **get_subprocess_no_window_kwargs(),
        )
        if proc.returncode != 0:
            err_msg = proc.stderr.strip() if proc.stderr else f"Exit code {proc.returncode}"
            raise RuntimeError(f"FFmpeg export failed with error:\n{err_msg}")

        if not os.path.isfile(output_path):
            raise FileNotFoundError(f"Export output file was not created at '{output_path}'")

        file_size = os.path.getsize(output_path)
        if file_size == 0:
            raise RuntimeError(f"Exported output file is empty (0 bytes): '{output_path}'")

        return output_path, file_size

    def _render_pcm_buffer_pyav(
        self,
        input_path: str,
        effects: AudioEffects,
        target_sample_rate: int = 44100,
        max_duration_seconds: Optional[float] = None,
    ) -> Tuple[np.ndarray, int]:
        import av

        effects.clamp_values()
        try:
            in_c = av.open(input_path)
        except Exception as e:
            raise RuntimeError(f"Failed to open audio file '{input_path}': {e}")

        with in_c:
            if not in_c.streams.audio:
                raise ValueError(f"No audio stream in '{input_path}'.")
            in_s = in_c.streams.audio[0]

            graph = av.filter.Graph()
            source = graph.add_abuffer(template=in_s)
            nodes = [source]

            if effects.trim_start > 0.001:
                try:
                    in_c.seek(int(effects.trim_start * av.time_base))
                except Exception:
                    pass

            speed = float(effects.speed)
            pitch = float(effects.effective_pitch)
            if abs(speed - 1.0) > 0.001 or abs(pitch - 1.0) > 0.001:
                if effects.link_pitch_to_speed:
                    new_rate = int(round(in_s.rate * speed))
                    nodes.append(graph.add("asetrate", str(new_rate)))
                    nodes.append(graph.add("aresample", str(target_sample_rate)))
                else:
                    new_rate = int(round(in_s.rate * pitch))
                    nodes.append(graph.add("asetrate", str(new_rate)))
                    nodes.append(graph.add("aresample", str(target_sample_rate)))
                    ratio = speed / pitch
                    if abs(ratio - 1.0) > 0.001:
                        nodes.append(graph.add("atempo", f"{ratio:.4f}"))

            if effects.bass_boost_percent > 0.01:
                gain_db = (effects.bass_boost_percent / 100.0) * 18.0
                nodes.append(graph.add("bass", f"g={gain_db:.2f}:f=100"))

            if effects.reverb_percent > 0.01:
                w = max(0.01, min(1.0, effects.reverb_percent / 100.0))
                in_gain = max(0.68, 1.0 - (0.25 * w))
                out_gain1 = min(0.85, 0.28 + (0.50 * w))
                out_gain2 = out_gain1 * 0.70
                d1 = "50|100|200|350"
                decay1 = f"{max(0.01, 0.50 * w):.2f}|{max(0.01, 0.38 * w):.2f}|{max(0.01, 0.28 * w):.2f}|{max(0.01, 0.18 * w):.2f}"
                nodes.append(graph.add("aecho", f"{in_gain:.2f}:{out_gain1:.2f}:{d1}:{decay1}"))
                d2 = "70|150|300|600"
                decay2 = f"{max(0.01, 0.35 * w):.2f}|{max(0.01, 0.25 * w):.2f}|{max(0.01, 0.18 * w):.2f}|{max(0.01, 0.10 * w):.2f}"
                nodes.append(graph.add("aecho", f"{in_gain:.2f}:{out_gain2:.2f}:{d2}:{decay2}"))

            if effects.bass_boost_percent > 0.01 or effects.reverb_percent > 0.01:
                nodes.append(graph.add("alimiter", "limit=0.98"))

            nodes.append(graph.add("aformat", f"sample_fmts=fltp:sample_rates={target_sample_rate}:channel_layouts=stereo"))
            sink = graph.add("abuffersink")
            nodes.append(sink)

            graph.link_nodes(*nodes)
            graph.configure()

            frames_out = []
            max_samples = int(max_duration_seconds * target_sample_rate) if max_duration_seconds else None
            samples_collected = 0

            samples_seen = 0
            stream_rate = in_s.rate or target_sample_rate or 44100
            for frame in in_c.decode(in_s):
                frame_time = float(frame.time) if frame.time is not None else samples_seen / stream_rate
                samples_seen += frame.samples
                if frame_time < effects.trim_start:
                    continue
                if effects.trim_end is not None and frame_time > effects.trim_end:
                    break

                try:
                    graph.push(frame)
                except Exception:
                    break

                while True:
                    try:
                        out_frame = graph.pull()
                        arr = out_frame.to_ndarray()
                        frames_out.append(arr)
                        samples_collected += arr.shape[1]
                        if max_samples and samples_collected >= max_samples:
                            break
                    except Exception:
                        break

                if max_samples and samples_collected >= max_samples:
                    break

            try:
                graph.push(None)
            except Exception:
                pass
            while True:
                try:
                    out_frame = graph.pull()
                    arr = out_frame.to_ndarray()
                    frames_out.append(arr)
                    samples_collected += arr.shape[1]
                    if max_samples and samples_collected >= max_samples:
                        break
                except Exception:
                    break

            if not frames_out:
                return np.zeros((0, 2), dtype=np.float32), target_sample_rate

            concatenated = np.concatenate(frames_out, axis=1)
            if max_samples and concatenated.shape[1] > max_samples:
                concatenated = concatenated[:, :max_samples]
            stereo = np.ascontiguousarray(concatenated.T, dtype=np.float32)
            return stereo, target_sample_rate

    def render_pcm_buffer(
        self,
        input_path: str,
        effects: AudioEffects,
        target_sample_rate: int = 44100,
        max_duration_seconds: Optional[float] = None,
    ) -> Tuple[np.ndarray, int]:
        """
        Renders the processed audio to a 2D float32 NumPy array (stereo)
        for real-time playback and seek previewing.
        """
        if not os.path.isfile(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if getattr(self, "use_pyav", False):
            return self._render_pcm_buffer_pyav(input_path, effects, target_sample_rate, max_duration_seconds)

        effects.clamp_values()
        cmd: List[str] = [self.ffmpeg_path, "-y"]

        if effects.trim_start > 0.001:
            cmd.extend(["-ss", f"{effects.trim_start:.3f}"])
        if effects.trim_end is not None and effects.trim_end > effects.trim_start:
            cmd.extend(["-to", f"{effects.trim_end:.3f}"])

        cmd.extend(["-i", os.path.abspath(input_path)])

        if max_duration_seconds is not None:
            cmd.extend(["-t", f"{max_duration_seconds:.3f}"])

        af = self.build_audio_filter_string(effects)
        if af:
            cmd.extend(["-af", af])

        cmd.extend([
            "-ac", "2",
            "-ar", str(target_sample_rate),
            "-f", "f32le",
            "-"
        ])

        file_size = os.path.getsize(input_path)
        safe_limit = 50 * 1024 * 1024

        if file_size > safe_limit:
            # Clean up old temporary files to prevent disk usage ballooning across rapid reloads
            self.cleanup()

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **get_subprocess_no_window_kwargs(),
            )
            fd, temp_path = tempfile.mkstemp(suffix=".raw")
            self._temp_files.append(temp_path)

            err_output = []
            def read_stderr():
                for line in proc.stderr:
                    err_output.append(line)

            stderr_thread = threading.Thread(target=read_stderr)
            stderr_thread.start()

            with os.fdopen(fd, 'wb') as f:
                while True:
                    chunk = proc.stdout.read(1024 * 1024)
                    if not chunk:
                        break
                    f.write(chunk)

            proc.stdout.close()
            proc.wait()
            stderr_thread.join()

            if proc.returncode != 0:
                err_msg = b"".join(err_output).decode('utf-8', errors='replace') if err_output else f"Exit code {proc.returncode}"
                self.cleanup()
                raise RuntimeError(f"Failed to render audio buffer: {err_msg}")

            samples = np.memmap(temp_path, dtype=np.float32, mode='r')
            if len(samples) % 2 != 0:
                samples = samples[: len(samples) - (len(samples) % 2)]

            # Since memmap doesn't support reshaping easily for some numpy versions,
            # we memmap again with the target shape.
            stereo_samples = np.memmap(temp_path, dtype=np.float32, mode='r', shape=(len(samples)//2, 2))
            return stereo_samples, target_sample_rate
        else:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                **get_subprocess_no_window_kwargs(),
            )
            if proc.returncode != 0:
                err_msg = proc.stderr.decode('utf-8', errors='replace') if proc.stderr else f"Exit code {proc.returncode}"
                raise RuntimeError(f"Failed to render audio buffer: {err_msg}")

            samples = np.frombuffer(proc.stdout, dtype=np.float32)
            if len(samples) % 2 != 0:
                samples = samples[: len(samples) - (len(samples) % 2)]

            stereo_samples = samples.reshape((-1, 2))
            return stereo_samples, target_sample_rate
