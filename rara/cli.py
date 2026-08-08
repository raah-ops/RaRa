"""RaRa CLI: 무음/버벅임 자동 컷 + 자막 생성 → CapCut 임포트용 결과물 출력.

사용 예:
    python -m rara.cli input.mp4 -o out/

출력물:
    out/edited.mp4   (무음·버벅임이 제거된 영상)
    out/subtitle.srt (편집된 타임라인에 맞춘 자막)

CapCut에는 공식 외부 API가 없어서, 이 도구는 "영상 + SRT 자막"까지 자동으로
만들어주고, 마지막 임포트만 CapCut 앱에서 직접 해주면 된다 (아래 README 참고).
"""
from __future__ import annotations

import argparse
import sys
import tempfile
from pathlib import Path

from . import audio, editor, silence, stutter, subtitles
from .cutlist import TimeRemapper, build_cutlist
from .utils import ensure_ffmpeg, probe_duration


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rara",
        description="무음/버벅임 구간을 자동으로 컷 편집하고 자막을 생성합니다 (CapCut 임포트용 mp4+srt 출력).",
    )
    p.add_argument("input", help="입력 영상 파일 경로")
    p.add_argument("-o", "--outdir", default="rara_out", help="출력 디렉터리 (기본: rara_out)")

    g_silence = p.add_argument_group("무음 탐지")
    g_silence.add_argument("--silence-db", type=float, default=-35.0, help="무음 판정 임계값 dBFS (기본 -35)")
    g_silence.add_argument("--silence-min", type=float, default=0.5, help="무음 최소 길이(초, 기본 0.5)")

    g_stt = p.add_argument_group("음성 인식 / 버벅임 탐지")
    g_stt.add_argument("--lang", default="ko", help="음성 언어 코드 (기본 ko)")
    g_stt.add_argument("--model", default="small", help="whisper 모델 크기 (tiny/base/small/medium/large-v3, 기본 small)")
    g_stt.add_argument("--device", default="cpu", help="cpu 또는 cuda (기본 cpu)")
    g_stt.add_argument("--compute-type", default="int8", help="faster-whisper compute_type (기본 int8)")
    g_stt.add_argument("--repeat-gap", type=float, default=1.2, help="반복 발화로 볼 최대 간격(초, 기본 1.2)")
    g_stt.add_argument("--filler-words", default=None, help="간투어 사전 파일 경로(한 줄에 한 단어)")
    g_stt.add_argument("--skip-stutter", action="store_true", help="버벅임 탐지를 건너뛰고 무음 컷만 수행")

    g_cut = p.add_argument_group("컷 편집 튜닝")
    g_cut.add_argument("--pad", type=float, default=0.06, help="컷 경계 여유(초, 기본 0.06)")
    g_cut.add_argument("--merge-gap", type=float, default=0.2, help="이 간격 이내 컷은 하나로 병합(초, 기본 0.2)")
    g_cut.add_argument("--min-cut", type=float, default=0.12, help="이보다 짧은 컷은 무시(초, 기본 0.12)")
    g_cut.add_argument("--min-keep", type=float, default=0.12, help="이보다 짧게 남는 조각은 컷 처리(초, 기본 0.12)")

    p.add_argument("--dry-run", action="store_true", help="영상은 자르지 않고 컷 구간/자막만 계산해 출력")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)

    ensure_ffmpeg()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"입력 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        return 1

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    duration = probe_duration(input_path)
    print(f"[1/5] 길이 확인: {duration:.2f}s")

    with tempfile.TemporaryDirectory() as tmp:
        wav_path = audio.extract_audio(input_path, Path(tmp) / "audio.wav")

        print(f"[2/5] 무음 탐지 중... (임계값 {args.silence_db}dB, 최소 {args.silence_min}s)")
        silence_intervals = silence.detect_silence(
            wav_path, noise_db=args.silence_db, min_silence_duration=args.silence_min
        )
        print(f"       무음 구간 {len(silence_intervals)}개 발견")

        segments = []
        stutter_intervals: list[tuple[float, float]] = []
        if not args.skip_stutter:
            print(f"[3/5] 음성 인식 중... (model={args.model}, lang={args.lang}) — 최초 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다")
            segments = stutter.transcribe(
                str(wav_path), language=args.lang, model_size=args.model,
                device=args.device, compute_type=args.compute_type,
            )
            filler_words = None
            if args.filler_words:
                filler_words = stutter.load_filler_words(args.filler_words)
            stutter_intervals = stutter.detect_disfluencies(
                segments, filler_words=filler_words, repeat_gap=args.repeat_gap
            )
            print(f"       버벅임(간투어/반복) 구간 {len(stutter_intervals)}개 발견")
        else:
            print("[3/5] --skip-stutter 지정됨: 버벅임 탐지 생략")

        print("[4/5] 컷 구간 계산 중...")
        cut_intervals, keep_intervals = build_cutlist(
            duration, silence_intervals, stutter_intervals,
            pad=args.pad, merge_gap=args.merge_gap,
            min_cut_duration=args.min_cut, min_keep_duration=args.min_keep,
        )
        removed = sum(e - s for s, e in cut_intervals)
        print(f"       총 컷 구간 {len(cut_intervals)}개 / 제거 시간 {removed:.2f}s / 최종 길이 {duration - removed:.2f}s")

        if args.dry_run:
            print("\n--dry-run: 실제 영상 편집은 수행하지 않았습니다. 컷 구간:")
            for s, e in cut_intervals:
                print(f"  cut {s:.2f} -> {e:.2f}")
            return 0

        print("[5/5] 영상 재인코딩 및 자막 생성 중...")
        video_out = outdir / "edited.mp4"
        editor.cut_video(input_path, keep_intervals, video_out)

        srt_out = outdir / "subtitle.srt"
        if segments:
            remap = TimeRemapper(cut_intervals)
            entries = subtitles.build_srt_entries(segments, cut_intervals, remap)
            subtitles.write_srt(entries, srt_out)
        else:
            srt_out = None

    print("\n완료!")
    print(f"  영상: {video_out}")
    if srt_out:
        print(f"  자막: {srt_out}")
    print("\nCapCut에서 사용하는 법: CapCut에서 새 프로젝트 생성 → 위 mp4 임포트 →")
    print("자막 트랙에 위 srt 파일을 임포트(또는 '텍스트 > 자막 가져오기')하면 됩니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
