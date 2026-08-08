"""RaRa 웹 화면 (Streamlit).

로컬에서 실행:
    streamlit run app.py

영상을 업로드하면 무음/버벅임 자동 컷 + 자막 생성을 수행하고, 결과 영상을
브라우저에서 바로 미리보기/다운로드하거나 CapCut 드래프트(zip)로 받을 수
있습니다.

CapCut 드래프트는 원본 영상을 "절대 경로"로 참조하기 때문에, 그 기능을 쓰려면
CapCut이 설치된 바로 그 컴퓨터에서 이 화면을 로컬로 띄워야 합니다. 다른 서버에
배포해서 원격으로 접속하는 경우엔 mp4+srt 출력만 사용하세요.
"""
from __future__ import annotations

import io
import tempfile
import zipfile
from pathlib import Path

import streamlit as st

from rara.pipeline import PipelineOptions, run_pipeline
from rara.utils import FFmpegNotFoundError, ensure_ffmpeg

st.set_page_config(page_title="RaRa", page_icon="🎬", layout="wide")

st.title("🎬 RaRa — 무음/버벅임 자동 컷 + 자막 + CapCut")
st.caption("무음 구간과 버벅거리는(간투어·반복) 구간을 자동으로 찾아 컷 편집하고, 자막까지 만들어 CapCut 드래프트로 내보냅니다.")

with st.expander("⚠️ CapCut 드래프트를 쓰기 전에 꼭 읽어주세요"):
    st.markdown(
        "CapCut 드래프트는 원본 영상을 프로젝트 안에 복사하지 않고 **절대 경로로 참조**합니다.\n\n"
        "- 이 화면을 **CapCut이 설치된 바로 그 컴퓨터에서 `streamlit run app.py`로 로컬 실행**해야 "
        "CapCut에서 드래프트가 정상적으로 열립니다.\n"
        "- 다른 서버에 올려서 원격으로 접속하는 경우, CapCut 드래프트를 내려받아 압축을 풀어도 "
        "CapCut이 원본 영상을 찾지 못할 수 있습니다 — 이때는 아래에서 CapCut 드래프트 생성을 끄고 "
        "mp4 + 자막만 받아 CapCut에 수동으로 임포트하세요."
    )

uploaded = st.file_uploader("영상 파일 업로드", type=["mp4", "mov", "mkv", "m4v", "avi", "webm"])

col1, col2 = st.columns(2)

with col1:
    st.subheader("무음 탐지")
    silence_db = st.slider("무음 판정 임계값 (dBFS)", -60.0, -10.0, -35.0, 1.0)
    silence_min = st.slider("무음 최소 길이 (초)", 0.1, 2.0, 0.5, 0.05)

    st.subheader("버벅임 탐지")
    skip_stutter = st.checkbox("버벅임 탐지 끄기 (무음 컷만 수행, 더 빠름)")
    model = st.selectbox(
        "Whisper 모델 크기", ["tiny", "base", "small", "medium", "large-v3"],
        index=2, disabled=skip_stutter,
        help="클수록 정확하지만 느립니다. 최초 실행 시 모델이 자동 다운로드됩니다.",
    )
    lang = st.text_input("언어 코드", value="ko", disabled=skip_stutter)
    repeat_gap = st.slider("반복 발화로 볼 최대 간격 (초)", 0.2, 3.0, 1.2, 0.1, disabled=skip_stutter)

with col2:
    st.subheader("컷 편집 튜닝")
    pad = st.slider("컷 경계 여유 (초)", 0.0, 0.3, 0.06, 0.01)
    merge_gap = st.slider("컷 병합 간격 (초)", 0.0, 1.0, 0.2, 0.05)
    min_cut = st.slider("최소 컷 길이 (초)", 0.0, 1.0, 0.12, 0.02)
    min_keep = st.slider("최소 유지 길이 (초)", 0.0, 1.0, 0.12, 0.02)

    st.subheader("출력물")
    make_video = st.checkbox("편집된 mp4 만들기", value=True)
    make_capcut = st.checkbox("CapCut 드래프트 만들기", value=True)
    font_size = st.slider("자막 폰트 크기", 2.0, 16.0, 6.0, 0.5, disabled=not make_capcut)

run_clicked = st.button("🚀 처리 시작", type="primary", disabled=uploaded is None)

if uploaded is None:
    st.info("먼저 영상 파일을 업로드하세요.")

if run_clicked and uploaded is not None:
    try:
        ensure_ffmpeg()
    except FFmpegNotFoundError as e:
        st.error(str(e))
        st.stop()

    work_dir = Path(tempfile.mkdtemp(prefix="rara_web_"))
    input_path = work_dir / uploaded.name
    input_path.write_bytes(uploaded.getvalue())
    outdir = work_dir / "out"

    opts = PipelineOptions(
        outdir=str(outdir),
        silence_db=silence_db,
        silence_min=silence_min,
        lang=lang,
        model=model,
        skip_stutter=skip_stutter,
        repeat_gap=repeat_gap,
        pad=pad,
        merge_gap=merge_gap,
        min_cut=min_cut,
        min_keep=min_keep,
        make_video=make_video,
        make_capcut_draft=make_capcut,
        capcut_overwrite=True,
        capcut_font_size=font_size,
    )

    status = st.status("처리 중...", expanded=True)

    def on_progress(msg: str) -> None:
        status.write(msg)

    try:
        result = run_pipeline(input_path, opts, on_progress=on_progress)
    except Exception as e:  # noqa: BLE001 — 웹 화면에 그대로 보여주기 위해 광범위하게 잡음
        status.update(label="오류 발생", state="error")
        st.exception(e)
        st.stop()

    status.update(label="완료!", state="complete")

    st.success(
        f"길이 {result.duration:.1f}s → {result.final_duration:.1f}s "
        f"(컷 {len(result.cut_intervals)}개, {result.removed_seconds:.1f}s 제거)"
    )

    if result.video_path and result.video_path.exists():
        st.subheader("편집된 영상")
        st.video(str(result.video_path))
        st.download_button(
            "⬇️ edited.mp4 다운로드", data=result.video_path.read_bytes(),
            file_name="edited.mp4", mime="video/mp4",
        )

    if result.srt_path and result.srt_path.exists():
        st.subheader("자막")
        st.download_button(
            "⬇️ subtitle.srt 다운로드", data=result.srt_path.read_bytes(),
            file_name="subtitle.srt", mime="text/plain",
        )
        with st.expander("자막 미리보기"):
            st.text(result.srt_path.read_text(encoding="utf-8"))

    if result.capcut_draft_path:
        draft_dir = result.capcut_draft_path.parent
        zip_buf = io.BytesIO()
        with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in draft_dir.rglob("*"):
                if f.is_file():
                    zf.write(f, f.relative_to(draft_dir.parent))

        st.subheader("CapCut 드래프트")
        st.download_button(
            f"⬇️ {draft_dir.name}.zip 다운로드",
            data=zip_buf.getvalue(),
            file_name=f"{draft_dir.name}.zip",
            mime="application/zip",
        )
        st.info(
            f"압축을 풀어 `{draft_dir.name}` 폴더를 CapCut의 드래프트 폴더(설정 > Draft 위치)에 "
            "넣으면 CapCut 앱에서 바로 프로젝트로 열립니다."
        )
