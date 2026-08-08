"""남길 구간(keep intervals)만 골라 하나의 영상으로 재조립."""
from __future__ import annotations

import subprocess
from pathlib import Path

Interval = tuple[float, float]


def _select_expr(keep_intervals: list[Interval]) -> str:
    return "+".join(f"between(t,{s:.3f},{e:.3f})" for s, e in keep_intervals)


def cut_video(
    input_path: str | Path,
    keep_intervals: list[Interval],
    output_path: str | Path,
    crf: int = 18,
    preset: str = "veryfast",
) -> Path:
    """select/aselect 필터로 남길 구간만 이어붙여 단일 파일로 인코딩.

    구간 수가 매우 많으면(수천 개) 필터 그래프가 커져 느려질 수 있음.
    """
    if not keep_intervals:
        raise ValueError("남길 구간이 없습니다 (전부 컷 대상으로 판정됨). 임계값을 조정하세요.")

    expr = _select_expr(keep_intervals)
    output_path = Path(output_path)

    cmd = [
        "ffmpeg", "-y", "-i", str(input_path),
        "-vf", f"select='{expr}',setpts=N/FRAME_RATE/TB",
        "-af", f"aselect='{expr}',asetpts=N/SR/TB",
        "-c:v", "libx264", "-crf", str(crf), "-preset", preset,
        "-c:a", "aac",
        str(output_path),
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)
    return output_path
