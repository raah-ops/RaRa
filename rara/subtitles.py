"""컷 편집된 타임라인에 맞춘 SRT 자막 생성."""
from __future__ import annotations

from pathlib import Path

from .cutlist import TimeRemapper
from .stutter import Segment, normalize_word

Interval = tuple[float, float]


def _overlaps_any(start: float, end: float, intervals: list[Interval]) -> bool:
    for s, e in intervals:
        if start < e and end > s:
            return True
    return False


def _fmt_timestamp(t: float) -> str:
    if t < 0:
        t = 0.0
    ms = round(t * 1000)
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def build_srt_entries(
    segments: list[Segment],
    cut_intervals: list[Interval],
    remap: TimeRemapper,
) -> list[tuple[float, float, str]]:
    """(new_start, new_end, text) 리스트. 컷 구간에 속한 단어는 자막에서 제외."""
    entries: list[tuple[float, float, str]] = []

    for seg in segments:
        kept_words = [
            w for w in seg.words
            if normalize_word(w.text) and not _overlaps_any(w.start, w.end, cut_intervals)
        ]
        if not kept_words:
            continue

        new_start = remap(kept_words[0].start)
        new_end = remap(kept_words[-1].end)
        if new_end <= new_start:
            continue

        text = "".join(w.text for w in kept_words).strip()
        if not text:
            continue

        entries.append((new_start, new_end, text))

    return entries


def write_srt(entries: list[tuple[float, float, str]], output_path: str | Path) -> Path:
    output_path = Path(output_path)
    lines: list[str] = []
    for i, (start, end, text) in enumerate(entries, start=1):
        lines.append(str(i))
        lines.append(f"{_fmt_timestamp(start)} --> {_fmt_timestamp(end)}")
        lines.append(text)
        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
