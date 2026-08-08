# RaRa

**무음 구간**과 **버벅거리는(간투어·반복) 구간**을 자동으로 찾아 컷 편집하고,
편집된 타임라인에 맞는 **자막**까지 자동 생성하는 도구입니다. CLI와 브라우저
화면(Streamlit) 둘 다 지원합니다.

[pycapcut](https://github.com/GuanYixuan/pyCapCut)을 이용해 **CapCut 드래프트
(프로젝트)를 직접 생성**합니다 — CapCut에서 폴더 하나만 복사해 넣으면 재인코딩
없이 컷/자막이 이미 적용된 편집 가능한 프로젝트가 열립니다. 필요하면 기존처럼
mp4+srt로도 뽑을 수 있습니다.

## 왜 CapCut을 직접 원격조종하지 않나요?

CapCut은 외부 개발자가 쓸 수 있는 **공식 공개 API를 제공하지 않습니다.**
그래서 "명령 한 번으로 CapCut 앱을 실시간 조작"하는 건 불가능합니다. 대신
`pycapcut`이 CapCut 드래프트 포맷(`draft_content.json`)을 직접 생성해주기 때문에,
**CapCut이 그대로 읽을 수 있는 프로젝트 파일**을 만드는 방식으로 동작합니다.
CapCut 앱에서는 그 프로젝트를 열기만 하면 됩니다.

## 설치

```bash
# 1) ffmpeg 설치 (시스템 필수 의존성)
brew install ffmpeg          # macOS
sudo apt install ffmpeg      # Ubuntu/Debian
choco install ffmpeg         # Windows

# 2) 파이썬 의존성 설치
pip install -r requirements.txt   # faster-whisper, pycapcut, streamlit
```

faster-whisper는 최초 실행 시 음성인식 모델을 자동으로 다운로드합니다(인터넷 필요).

> **중요**: CapCut 드래프트는 원본 영상 파일을 프로젝트 안으로 복사하지 않고
> **절대 경로로 참조**합니다. 따라서 이 도구는 CapCut이 설치되어 있고 원본
> 영상도 그대로 있는 **바로 그 컴퓨터에서 로컬로 실행**해야 합니다. (다른 곳에서
> 실행한 뒤 결과 폴더만 옮기면 CapCut이 원본 영상을 찾지 못합니다.)

## 웹 화면 (Streamlit)

명령줄이 부담스럽다면 브라우저에서 업로드/다운로드로 바로 쓸 수 있습니다.

```bash
streamlit run app.py
```

실행하면 `http://localhost:8501`이 자동으로 열립니다. 영상을 업로드하고
옵션(무음 임계값, 버벅임 탐지 여부, Whisper 모델 크기, 자막 폰트 크기 등)을
조절한 뒤 **처리 시작**을 누르면:

- 편집된 영상을 브라우저에서 바로 미리보기 + `edited.mp4` 다운로드
- `subtitle.srt` 다운로드 + 미리보기
- **CapCut 드래프트를 zip으로 다운로드** — 압축을 풀어 CapCut 드래프트 폴더에
  넣으면 CapCut에서 바로 열립니다.

CapCut 드래프트는 원본 영상을 절대 경로로 참조하므로, 이 zip이 제대로
동작하려면 **`streamlit run app.py`를 CapCut이 설치된 그 컴퓨터에서 로컬로
실행**해야 합니다. 다른 서버에 배포해 원격으로 접속하는 경우엔 화면에서
"CapCut 드래프트 만들기"를 끄고 mp4+srt만 받아 수동으로 임포트하세요.

## CLI 사용법

```bash
python -m rara.cli input.mp4 -o out/
```

기본 출력물:
- `out/capcut_draft/rara_input/` — pycapcut으로 생성한 **CapCut 드래프트**
  (컷 편집된 클립들 + 자막 텍스트가 이미 타임라인에 배치된 상태)
- `out/edited.mp4` — 무음/버벅임이 제거된 재인코딩 영상 (참고/미리보기용)
- `out/subtitle.srt` — 편집된 타임라인에 맞춰 재계산된 자막

먼저 실제로 결과물을 만들지 않고 컷 구간만 확인하고 싶다면:

```bash
python -m rara.cli input.mp4 --dry-run
```

mp4 재인코딩은 필요 없고 CapCut 드래프트만 빠르게 받고 싶다면:

```bash
python -m rara.cli input.mp4 -o out/ --skip-video-export
```

## CapCut에서 열기

1. CapCut 앱의 **설정 > 드래프트(Draft) 위치**에서 드래프트 폴더 경로를 확인
2. `out/capcut_draft/rara_input/` 폴더 전체를 그 경로 안으로 복사
   (또는 처음부터 `--capcut-draft-root "<CapCut 드래프트 경로>"`로 지정해서
   바로 그 위치에 생성)
3. CapCut을 열면(또는 새로고침하면) 프로젝트 목록에 나타납니다 — 클릭해서 열면
   컷 편집 + 자막이 이미 적용된 타임라인을 바로 이어서 꾸밀 수 있습니다.

mp4+srt 방식으로 쓰고 싶다면(다른 컴퓨터/모바일에서 임포트하는 등):
CapCut에서 새 프로젝트 생성 → `edited.mp4` 임포트 → 텍스트 메뉴에서
`subtitle.srt` 임포트("자막 가져오기"/"Import Captions").

## 동작 방식

1. **무음 탐지**: `ffmpeg silencedetect` 필터로 음량이 임계값(`--silence-db`)
   이하로 일정 시간(`--silence-min`) 이상 지속되는 구간을 찾습니다.
2. **버벅임 탐지**: `faster-whisper`로 단어 단위 타임스탬프를 추출한 뒤,
   - 간투어 사전("어", "음", "그" 등)에 해당하는 단어
   - 짧은 간격 안에 같은 단어가 반복되는 경우("그 그 그 이게...")
   를 컷 대상으로 표시합니다. (`--skip-stutter`로 이 단계를 끌 수 있습니다)
3. 두 결과를 합치고 경계에 여유(`--pad`)를 준 뒤, 너무 가까운 컷은 병합
   (`--merge-gap`), 너무 짧은 컷/조각은 무시(`--min-cut`, `--min-keep`)해서
   최종 "남길 구간(keep intervals)" 리스트를 만듭니다.
4. **CapCut 드래프트 생성**: `pycapcut`으로 원본 영상 소스를 남길 구간만큼
   잘라 타임라인에 순서대로 이어붙이고(재인코딩 없음, 논디스트럭티브), 같은
   방식으로 재계산된 자막을 텍스트 트랙에 배치해 `draft_content.json`을 만듭니다.
5. (선택) `ffmpeg`의 `select`/`aselect` 필터로 남길 구간만 재인코딩한 `edited.mp4`와,
   그에 맞춘 `.srt`도 함께 생성합니다.

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
| `--capcut-draft-root` | `<outdir>/capcut_draft` | 드래프트를 생성할 루트 폴더 (CapCut의 실제 드래프트 경로를 알면 직접 지정 가능) |
| `--capcut-draft-name` | `rara_<입력파일명>` | 드래프트(프로젝트) 이름 |
| `--capcut-overwrite` | off | 같은 이름의 기존 드래프트를 덮어씀 |
| `--capcut-fps` | 원본에서 자동 감지 | 드래프트 fps |
| `--capcut-font-size` | 6.0 | 자막 폰트 크기 |
| `--capcut-font-color` | `1,1,1` (흰색) | 자막 색상 `R,G,B` (0~1) |
| `--skip-video-export` | off | `edited.mp4` 생성 생략 |
| `--no-capcut-draft` | off | CapCut 드래프트 생성 생략 |

정확도가 100%는 아닌 휴리스틱 기반이므로, 결과를 보고 위 옵션들을 조정해가며
쓰는 것을 권장합니다. 특히 `--dry-run`으로 컷 구간만 먼저 확인해보세요.

## 테스트

```bash
python -m unittest discover -s tests -v
```

`cutlist`/`subtitles` 로직은 외부 의존성 없이 항상 실행됩니다. `capcut_draft`
통합 테스트는 ffmpeg와 pycapcut이 모두 설치된 환경에서만 실행되며(그렇지 않으면
자동 스킵), 짧은 테스트 영상을 만들어 실제로 `draft_content.json`이 올바르게
생성되는지 검증합니다.
