"""CLI와 웹앱(Streamlit)이 공유하는 핵심 파이프라인.

무음 탐지 -> 버벅임 탐지 -> 컷 리스트 계산 -> (mp4/srt 및·또는 CapCut 드래프트
생성) 까지의 전체 흐름을 한 곳에 모아, 진행 상황을 `on_progress` 콜백으로
알려준다 (CLI는 print, 웹앱은 화면 업데이트에 사용).
"""
from __future__ import annotations

import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Optional

from . import audio, capcut_draft, editor, silence, stutter, subtitles
from .cutlist import TimeRemapper, build_cutlist
from .utils import probe_duration, probe_fps

Interval = tuple[float, float]
ProgressFn = Callable[[str], None]


def _noop(_msg: str) -> None:
    pass


@dataclass
class PipelineOptions:
    outdir: str = "rara_out"

    silence_db: float = -35.0
    silence_min: float = 0.5

    lang: str = "ko"
    model: str = "small"
    device: str = "cpu"
    compute_type: str = "int8"
    repeat_gap: float = 1.2
    filler_words_path: Optional[str] = None
    skip_stutter: bool = False

    pad: float = 0.06
    merge_gap: float = 0.2
    min_cut: float = 0.12
    min_keep: float = 0.12

    make_video: bool = True
    make_capcut_draft: bool = True

    capcut_draft_root: Optional[str] = None
    capcut_draft_name: Optional[str] = None
    capcut_overwrite: bool = False
    capcut_fps: Optional[float] = None
    capcut_font_size: float = 6.0
    capcut_font_color: tuple[float, float, float] = (1.0, 1.0, 1.0)


@dataclass
class PipelineResult:
    duration: float
    cut_intervals: list[Interval] = field(default_factory=list)
    keep_intervals: list[Interval] = field(default_factory=list)
    subtitle_entries: list[tuple[float, float, str]] = field(default_factory=list)
    video_path: Optional[Path] = None
    srt_path: Optional[Path] = None
    capcut_draft_path: Optional[Path] = None

    @property
    def removed_seconds(self) -> float:
        return sum(e - s for s, e in self.cut_intervals)

    @property
    def final_duration(self) -> float:
        return self.duration - self.removed_seconds


def run_pipeline(
    input_path: str | Path,
    opts: PipelineOptions,
    on_progress: ProgressFn = _noop,
    dry_run: bool = False,
) -> PipelineResult:
    input_path = Path(input_path)
    outdir = Path(opts.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(input_path)
    on_progress(f"길이 확인: {duration:.2f}s")

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = audio.extract_audio(input_path, Path(tmp) / "audio.wav")

        on_progress(f"무음 탐지 중... (임계값 {opts.silence_db}dB, 최소 {opts.silence_min}s)")
        silence_intervals = silence.detect_silence(
            wav_path, noise_db=opts.silence_db, min_silence_duration=opts.silence_min
        )
        on_progress(f"  무음 구간 {len(silence_intervals)}개 발견")

        segments = []
        stutter_intervals: list[Interval] = []
        if not opts.skip_stutter:
            on_progress(f"음성 인식 중... (model={opts.model}, lang={opts.lang})")
            segments = stutter.transcribe(
                str(wav_path), language=opts.lang, model_size=opts.model,
                device=opts.device, compute_type=opts.compute_type,
            )
            filler_words = None
            if opts.filler_words_path:
                filler_words = stutter.load_filler_words(opts.filler_words_path)
            stutter_intervals = stutter.detect_disfluencies(
                segments, filler_words=filler_words, repeat_gap=opts.repeat_gap
            )
            on_progress(f"  버벅임(간투어/반복) 구간 {len(stutter_intervals)}개 발견")
        else:
            on_progress("버벅임 탐지 생략(skip_stutter)")

        on_progress("컷 구간 계산 중...")
        cut_intervals, keep_intervals = build_cutlist(
            duration, silence_intervals, stutter_intervals,
            pad=opts.pad, merge_gap=opts.merge_gap,
            min_cut_duration=opts.min_cut, min_keep_duration=opts.min_keep,
        )
        removed = sum(e - s for s, e in cut_intervals)
        on_progress(
            f"  총 컷 구간 {len(cut_intervals)}개 / 제거 시간 {removed:.2f}s / "
            f"최종 길이 {duration - removed:.2f}s"
        )

        result = PipelineResult(duration=duration, cut_intervals=cut_intervals, keep_intervals=keep_intervals)

        if dry_run:
            return result

        remap = TimeRemapper(cut_intervals)
        subtitle_entries = (
            subtitles.build_srt_entries(segments, cut_intervals, remap) if segments else []
        )
        result.subtitle_entries = subtitle_entries

        if opts.make_video:
            on_progress("영상 재인코딩 중... (edited.mp4)")
            video_out = outdir / "edited.mp4"
            editor.cut_video(input_path, keep_intervals, video_out)
            result.video_path = video_out

        if subtitle_entries:
            srt_out = outdir / "subtitle.srt"
            subtitles.write_srt(subtitle_entries, srt_out)
            result.srt_path = srt_out

        if opts.make_capcut_draft:
            draft_root = Path(opts.capcut_draft_root) if opts.capcut_draft_root else outdir / "capcut_draft"
            draft_name = opts.capcut_draft_name or f"rara_{input_path.stem}"
            fps = opts.capcut_fps if opts.capcut_fps else probe_fps(input_path)
            on_progress(f"CapCut 드래프트 생성 중... (root={draft_root}, name={draft_name}, fps={fps:.2f})")
            draft_path = capcut_draft.build_capcut_draft(
                input_path, keep_intervals, subtitle_entries,
                draft_root, draft_name, fps=fps,
                allow_replace=opts.capcut_overwrite,
                font_size=opts.capcut_font_size,
                font_color=opts.capcut_font_color,
            )
            result.capcut_draft_path = draft_path

    on_progress("완료!")
    return result
