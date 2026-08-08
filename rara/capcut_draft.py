"""pycapcut로 CapCut 드래프트(프로젝트)를 직접 생성.

ffmpeg로 재인코딩한 mp4를 만드는 대신, 원본 영상은 그대로 두고 CapCut
타임라인 위에 "남길 구간(keep_intervals)"만 순서대로 이어붙인 클립들과,
자막 텍스트 클립들을 올린 draft_content.json을 만든다.

장점: 화질 손실 없음(재인코딩 X), CapCut에서 계속 다듬을 수 있는 편집
가능한 상태로 열림.

주의: CapCut 드래프트는 소스 영상 파일을 프로젝트 안에 복사하지 않고
"절대 경로"로 참조한다. 따라서 이 스크립트는 실제로 CapCut이 설치되어
있고, 원본 영상 파일도 그대로 있는 그 컴퓨터에서 실행해야 한다
(클라우드/원격 환경에서 실행한 뒤 결과만 다른 PC로 옮기면 소스 영상을
못 찾는다).
"""
from __future__ import annotations

import os
from pathlib import Path

Interval = tuple[float, float]
SubtitleEntry = tuple[float, float, str]


def _us(seconds: float) -> int:
    """초 -> 마이크로초 (pycapcut의 Timerange는 마이크로초 정수를 받는다)."""
    return round(seconds * 1_000_000)


def build_capcut_draft(
    input_path: str | Path,
    keep_intervals: list[Interval],
    subtitle_entries: list[SubtitleEntry],
    draft_root: str | Path,
    draft_name: str,
    fps: float = 30.0,
    allow_replace: bool = False,
    video_track_name: str = "video",
    subtitle_track_name: str = "subs",
    font_size: float = 6.0,
    font_color: tuple[float, float, float] = (1.0, 1.0, 1.0),
) -> Path:
    """CapCut 드래프트를 생성하고 draft_content.json 경로를 반환."""
    try:
        import pycapcut as cc
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "pycapcut이 설치되어 있지 않습니다. `pip install pycapcut` 후 다시 실행하세요."
        ) from e

    if not keep_intervals:
        raise ValueError("남길 구간이 없습니다 (전부 컷 대상으로 판정됨). 임계값을 조정하세요.")

    draft_root = Path(draft_root)
    os.makedirs(draft_root, exist_ok=True)

    # 소스 영상을 한 번만 로드해서 모든 세그먼트가 같은 material을 재사용하게 함
    # (세그먼트마다 새로 만들면 매번 파일을 다시 파싱해 느려지고 중복 material이 쌓임)
    material = cc.VideoMaterial(str(input_path))
    width, height = material.width, material.height

    folder = cc.DraftFolder(str(draft_root))
    script = folder.create_draft(
        draft_name, width, height, fps=round(fps), allow_replace=allow_replace
    )
    script.add_track(cc.TrackType.video, video_track_name)
    script.add_track(cc.TrackType.text, subtitle_track_name)

    cursor_us = 0
    for start, end in keep_intervals:
        dur_us = _us(end) - _us(start)
        if dur_us <= 0:
            continue
        segment = cc.VideoSegment(
            material,
            cc.Timerange(cursor_us, dur_us),
            source_timerange=cc.Timerange(_us(start), dur_us),
        )
        script.add_segment(segment, video_track_name)
        cursor_us += dur_us

    style = cc.TextStyle(size=font_size, color=font_color)
    for start, end, text in subtitle_entries:
        dur_us = _us(end) - _us(start)
        if dur_us <= 0:
            continue
        text_segment = cc.TextSegment(text, cc.Timerange(_us(start), dur_us), style=style)
        script.add_segment(text_segment, subtitle_track_name)

    script.save()
    return Path(script.save_path)
