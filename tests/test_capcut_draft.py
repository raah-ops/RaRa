"""pycapcut 기반 CapCut 드래프트 생성 통합 테스트.

ffmpeg와 pycapcut이 모두 설치되어 있을 때만 실제로 짧은 테스트 영상을 만들어
draft_content.json이 정상적으로 생성되는지 확인한다. 둘 중 하나라도 없으면
스킵한다.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

try:
    import pycapcut  # noqa: F401
    HAS_PYCAPCUT = True
except ImportError:
    HAS_PYCAPCUT = False

HAS_FFMPEG = shutil.which("ffmpeg") is not None

from rara.capcut_draft import build_capcut_draft  # noqa: E402


@unittest.skipUnless(HAS_FFMPEG and HAS_PYCAPCUT, "ffmpeg와 pycapcut이 모두 필요합니다")
class TestBuildCapcutDraft(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        tmp = Path(self.tmpdir.name)

        self.sample_video = tmp / "sample.mp4"
        subprocess.run(
            [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", "testsrc=duration=4:size=160x120:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=4",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
                str(self.sample_video),
            ],
            capture_output=True, check=True,
        )
        self.draft_root = tmp / "drafts"

    def test_creates_draft_with_video_and_text_segments(self):
        keep_intervals = [(0.0, 1.0), (2.0, 3.5)]
        subtitle_entries = [(0.0, 0.8, "안녕하세요"), (1.2, 2.0, "테스트 자막")]

        draft_path = build_capcut_draft(
            self.sample_video, keep_intervals, subtitle_entries,
            self.draft_root, "test_draft", fps=25,
        )

        self.assertTrue(draft_path.exists())
        data = json.loads(draft_path.read_text(encoding="utf-8"))

        tracks_by_type = {t["type"]: t for t in data["tracks"]}
        self.assertIn("video", tracks_by_type)
        self.assertIn("text", tracks_by_type)
        self.assertEqual(len(tracks_by_type["video"]["segments"]), 2)
        self.assertEqual(len(tracks_by_type["text"]["segments"]), 2)

        # 남길 구간 길이(1.0s + 1.5s = 2.5s)만큼 타임라인 길이가 잡혀야 함
        total_keep_us = sum(round((e - s) * 1_000_000) for s, e in keep_intervals)
        self.assertEqual(data["duration"], total_keep_us)

    def test_raises_when_no_keep_intervals(self):
        with self.assertRaises(ValueError):
            build_capcut_draft(
                self.sample_video, [], [], self.draft_root, "empty_draft", fps=25,
            )


if __name__ == "__main__":
    unittest.main()
