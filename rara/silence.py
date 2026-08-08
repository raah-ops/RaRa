"""ffmpeg silencedetect 필터로 무음 구간을 탐지."""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

_START_RE = re.compile(r"silence_start:\s*(-?[\d.]+)")
_END_RE = re.compile(r"silence_end:\s*(-?[\d.]+)")


def detect_silence(
    audio_path: str | Path,
    noise_db: float = -35.0,
    min_silence_duration: float = 0.5,
) -> list[tuple[float, float]]:
    """(start, end) 초 단위 무음 구간 리스트를 반환.

    noise_db: 이 값(dBFS)보다 조용하면 무음으로 간주 (값이 낮을수록/더 음수일수록 엄격)
    min_silence_duration: 이 길이(초) 이상 지속돼야 무음 구간으로 인정
    """
    cmd = [
        "ffmpeg", "-i", str(audio_path),
        "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_duration}",
        "-f", "null", "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = proc.stderr

    intervals: list[tuple[float, float]] = []
    pending_start: float | None = None
    for line in log.splitlines():
        m_start = _START_RE.search(line)
        if m_start:
            pending_start = float(m_start.group(1))
            continue
        m_end = _END_RE.search(line)
        if m_end and pending_start is not None:
            intervals.append((pending_start, float(m_end.group(1))))
            pending_start = None

    return intervals
