"""영상에서 분석용 오디오(wav)를 추출."""
from __future__ import annotations

import subprocess
from pathlib import Path


def extract_audio(input_path: str | Path, out_path: str | Path, sample_rate: int = 16000) -> Path:
    """분석(무음/음성인식)에 쓰기 좋은 mono 16k wav로 추출."""
    out_path = Path(out_path)
    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-c:a", "pcm_s16le",
        str(out_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return out_path
