"""음성 인식(단어 타임스탬프) + '버벅임'(간투어/즉흥 반복) 구간 탐지.

'버벅거림'을 오디오 신호만으로 판별하는 표준적인 방법은 없어서, 이 모듈은
STT(faster-whisper) 결과의 단어 타임스탬프를 이용한 휴리스틱으로 접근한다:

  1. 간투어(filler word) 사전에 해당하는 단어 자체 ("어", "음", "그..." 등)
  2. 같은 단어(또는 매우 유사한 단어)가 짧은 간격을 두고 반복되는 경우
     예) "그 그 그 이게 말이야" -> 앞의 "그 그"를 컷

정확도는 100%가 아니므로 --pad, --repeat-gap 등 옵션으로 튜닝하도록 설계했다.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_FILLER_WORDS = {
    "어", "어어", "어어어", "음", "음음", "음음음",
    "그", "그그", "저", "저기", "막", "인제", "저저",
}

_PUNCT_RE = re.compile(r"[.,!?~…·\"'()\[\]]")


def normalize_word(word: str) -> str:
    return _PUNCT_RE.sub("", word).strip()


@dataclass
class Word:
    start: float
    end: float
    text: str


@dataclass
class Segment:
    start: float
    end: float
    text: str
    words: list[Word] = field(default_factory=list)


def transcribe(
    audio_path: str,
    language: str = "ko",
    model_size: str = "small",
    device: str = "cpu",
    compute_type: str = "int8",
) -> list[Segment]:
    """faster-whisper로 단어 단위 타임스탬프가 포함된 세그먼트 리스트를 얻는다.

    faster-whisper는 최초 실행 시 모델을 로컬 캐시에 다운로드한다(인터넷 필요).
    """
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # pragma: no cover
        raise RuntimeError(
            "faster-whisper가 설치되어 있지 않습니다. `pip install faster-whisper` 후 다시 실행하세요."
        ) from e

    model = WhisperModel(model_size, device=device, compute_type=compute_type)
    raw_segments, _info = model.transcribe(
        audio_path,
        language=language,
        word_timestamps=True,
        vad_filter=False,  # 무음 판단은 우리가 별도로(ffmpeg silencedetect) 수행
    )

    segments: list[Segment] = []
    for seg in raw_segments:
        words = [Word(w.start, w.end, w.word) for w in (seg.words or [])]
        segments.append(Segment(start=seg.start, end=seg.end, text=seg.text, words=words))
    return segments


def detect_disfluencies(
    segments: list[Segment],
    filler_words: set[str] | None = None,
    repeat_gap: float = 1.2,
) -> list[tuple[float, float]]:
    """간투어/반복 발화 구간을 (start, end) 리스트로 반환."""
    fillers = filler_words if filler_words is not None else DEFAULT_FILLER_WORDS
    cuts: list[tuple[float, float]] = []

    all_words: list[Word] = [w for seg in segments for w in seg.words]

    # 1) 간투어 단독 발화
    for w in all_words:
        norm = normalize_word(w.text)
        if norm in fillers:
            cuts.append((w.start, w.end))

    # 2) 동일/유사 단어의 짧은 간격 반복(말더듬)
    for i in range(1, len(all_words)):
        prev, cur = all_words[i - 1], all_words[i]
        norm_prev, norm_cur = normalize_word(prev.text), normalize_word(cur.text)
        if not norm_prev or not norm_cur:
            continue
        if norm_prev == norm_cur and (cur.start - prev.end) <= repeat_gap:
            # 반복된 앞쪽 발화를 컷 대상으로(마지막 발화만 자막/음성에 남김)
            cuts.append((prev.start, prev.end))

    return cuts


def load_filler_words(path: str) -> set[str]:
    words: set[str] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                words.add(line)
    return words
