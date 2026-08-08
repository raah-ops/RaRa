"""무음 구간 + 버벅임 구간을 합쳐 최종 '컷할 구간'/'남길 구간'을 계산."""
from __future__ import annotations

Interval = tuple[float, float]


def merge_intervals(intervals: list[Interval], gap: float = 0.0) -> list[Interval]:
    """겹치거나 gap 이내로 붙어있는 구간을 하나로 합침."""
    if not intervals:
        return []
    ordered = sorted(intervals)
    merged: list[list[float]] = [list(ordered[0])]
    for s, e in ordered[1:]:
        if s <= merged[-1][1] + gap:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    return [(s, e) for s, e in merged]


def pad_intervals(intervals: list[Interval], pad: float, duration: float) -> list[Interval]:
    padded = [(max(0.0, s - pad), min(duration, e + pad)) for s, e in intervals]
    return merge_intervals(padded)


def invert_intervals(intervals: list[Interval], duration: float) -> list[Interval]:
    """intervals(컷할 구간)의 여집합(남길 구간)을 계산."""
    keep: list[Interval] = []
    prev_end = 0.0
    for s, e in sorted(intervals):
        if s > prev_end:
            keep.append((prev_end, s))
        prev_end = max(prev_end, e)
    if prev_end < duration:
        keep.append((prev_end, duration))
    return keep


def build_cutlist(
    duration: float,
    silence_intervals: list[Interval],
    stutter_intervals: list[Interval],
    pad: float = 0.06,
    merge_gap: float = 0.2,
    min_cut_duration: float = 0.12,
    min_keep_duration: float = 0.12,
) -> tuple[list[Interval], list[Interval]]:
    """최종 (cut_intervals, keep_intervals)를 반환.

    pad             : 컷 경계에 여유(초). 자음/숨소리가 잘리는 것을 방지.
    merge_gap       : 이 값 이내로 붙은 컷들은 하나로 합쳐 지글거림 방지.
    min_cut_duration: 이보다 짧은 컷은 무시(너무 잦은 미세 컷 방지).
    min_keep_duration: 이보다 짧게 살아남는 '남길 구간'은 그냥 컷에 포함시킴.
    """
    raw_cuts = pad_intervals(silence_intervals + stutter_intervals, pad, duration)
    cuts = merge_intervals(raw_cuts, gap=merge_gap)
    cuts = [(s, e) for s, e in cuts if e - s >= min_cut_duration]

    keep = invert_intervals(cuts, duration)
    keep = [(s, e) for s, e in keep if e - s >= min_keep_duration]

    # 짧은 keep 조각을 버렸으므로, 최종 cut은 keep의 여집합으로 다시 계산해
    # remap 등에서 일관성을 유지한다.
    final_cuts = invert_intervals(keep, duration)
    return final_cuts, keep


class TimeRemapper:
    """원본 타임라인의 시각을, 컷 편집 후(무음/버벅임 제거된) 타임라인 시각으로 변환."""

    def __init__(self, cut_intervals: list[Interval]):
        self._cuts = sorted(cut_intervals)

    def __call__(self, t: float) -> float:
        offset = 0.0
        for s, e in self._cuts:
            if t < s:
                break
            if s <= t <= e:
                return s - offset
            offset += e - s
        return t - offset
