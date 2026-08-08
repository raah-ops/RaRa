# RaRa

**무음 구간**과 **버벅거리는(간투어·반복) 구간**을 자동으로 찾아 컷 편집하고,
편집된 타임라인에 맞는 **자막(SRT)**까지 자동 생성하는 CLI 도구입니다.

결과물(`edited.mp4` + `subtitle.srt`)을 CapCut에 임포트하면 바로 이어서
꾸미기(스타일, 효과음, BGM 등)만 하면 되는 상태가 됩니다.

## 왜 CapCut을 직접 조작하지 않나요?

CapCut은 외부 개발자가 쓸 수 있는 **공식 공개 API를 제공하지 않습니다.**
그래서 "명령 한 번으로 CapCut 앱 안에서 자동으로 편집"은 불가능하고,
이 도구는 대신 **CapCut이 바로 읽을 수 있는 결과물(mp4 + srt)** 을 만들어주는
방식으로 접근합니다. 임포트 한 번만 수동으로 해주면 됩니다.

## 설치

```bash
# 1) ffmpeg 설치 (시스템 필수 의존성)
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
choco install ffmpeg         # Windows

# 2) 파이썬 의존성 설치
pip install -r requirements.txt
```

faster-whisper는 최초 실행 시 음성인식 모델을 자동으로 다운로드합니다(인터넷 필요).

## 사용법

```bash
python -m rara.cli input.mp4 -o out/
```

출력:
- `out/edited.mp4` — 무음/버벅임이 제거된 영상
- `out/subtitle.srt` — 편집된 타임라인에 맞춰 재계산된 자막

먼저 실제로 자르지 않고 컷 구간만 확인하고 싶다면:

```bash
python -m rara.cli input.mp4 --dry-run
```

## CapCut에서 마무리하기

1. CapCut에서 새 프로젝트 생성
2. `edited.mp4`를 타임라인으로 임포트
3. 텍스트(자막) 메뉴에서 `subtitle.srt` 임포트 (버전에 따라 "자막 가져오기" /
   "Import Captions" 등으로 표기)
4. 이후 스타일/애니메이션/BGM 등은 CapCut에서 자유롭게 꾸미면 됩니다.

## 동작 방식

1. **무음 탐지**: `ffmpeg silencedetect` 필터로 음량이 임계값(`--silence-db`)
   이하로 일정 시간(`--silence-min`) 이상 지속되는 구간을 찾습니다.
2. **버벅임 탐지**: `faster-whisper`로 단어 단위 타임스탬프를 추출한 뒤,
   - 간투어 사전("어", "음", "그" 등)에 해당하는 단어
   - 짧은 간격 안에 같은 단어가 반복되는 경우("그 그 그 이게...")
   를 컷 대상으로 표시합니다. (`--skip-stutter`로 이 단계를 끌 수 있습니다)
3. 두 결과를 합치고 경계에 여유(`--pad`)를 준 뒤, 너무 가까운 컷은 병합
   (`--merge-gap`), 너무 짧은 컷/조각은 무시(`--min-cut`, `--min-keep`)해서
   최종 컷 리스트를 만듭니다.
4. `ffmpeg`의 `select`/`aselect` 필터로 남길 구간만 이어붙여 재인코딩합니다.
5. 컷으로 사라진 시간만큼 자막 타임스탬프를 재계산(remap)해서 `.srt`를
   생성합니다. 컷된 구간에 속한 단어(간투어/반복 발화)는 자막에서도 제외됩니다.

## 튜닝 옵션

| 옵션 | 기본값 | 설명 |
|---|---|---|
| `--silence-db` | -35 | 이 dBFS 이하를 무음으로 간주 |
| `--silence-min` | 0.5 | 무음 최소 지속 시간(초) |
| `--model` | small | whisper 모델 크기 (tiny/base/small/medium/large-v3) |
| `--repeat-gap` | 1.2 | 반복 발화로 간주할 최대 간격(초) |
| `--filler-words` | (내장 사전) | 커스텀 간투어 사전 파일 (`filler_words.example.txt` 참고) |
| `--pad` | 0.06 | 컷 경계 여유(초) |
| `--merge-gap` | 0.2 | 이 간격 이내 컷은 병합 |
| `--min-cut` | 0.12 | 이보다 짧은 컷은 무시 |
| `--min-keep` | 0.12 | 이보다 짧게 남는 조각은 컷 처리 |

정확도가 100%는 아닌 휴리스틱 기반이므로, 결과를 보고 위 옵션들을 조정해가며
쓰는 것을 권장합니다. 특히 `--dry-run`으로 컷 구간만 먼저 확인해보세요.

## 테스트

외부 의존성(ffmpeg, whisper 모델) 없이 순수 로직만 검증하는 단위 테스트:

```bash
python -m unittest discover -s tests -v
```
