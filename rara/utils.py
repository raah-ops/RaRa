"""공용 유틸리티: ffmpeg/ffprobe 호출 래퍼."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class FFmpegNotFoundError(RuntimeError):
    pass


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None:
        raise FFmpegNotFoundError(
            "ffmpeg/ffprobe를 찾을 수 없습니다. 먼저 시스템에 ffmpeg를 설치해주세요.\n"
            "  macOS : brew install ffmpeg\n"
            "  Ubuntu: sudo apt install ffmpeg\n"
            "  Windows: choco install ffmpeg (또는 공식 배포본 다운로드 후 PATH 등록)"
        )


def probe_duration(path: str | Path) -> float:
    """ffprobe로 미디어 길이(초)를 조회."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "json", str(path),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)
    return float(data["format"]["duration"])


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True)
