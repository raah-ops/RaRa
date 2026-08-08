import unittest

from rara.cutlist import TimeRemapper
from rara.stutter import Segment, Word
from rara.subtitles import build_srt_entries, _fmt_timestamp


class TestBuildSrtEntries(unittest.TestCase):
    def test_filters_words_in_cut_regions_and_remaps(self):
        # "어 그 안녕하세요" 중 "어", "그"가 버벅임으로 컷 대상(0.0-1.0)
        segments = [
            Segment(
                start=0.0, end=2.5, text="어 그 안녕하세요",
                words=[
                    Word(0.0, 0.3, "어"),
                    Word(0.4, 0.6, "그"),
                    Word(1.5, 2.5, "안녕하세요"),
                ],
            )
        ]
        cut_intervals = [(0.0, 1.0)]
        remap = TimeRemapper(cut_intervals)

        entries = build_srt_entries(segments, cut_intervals, remap)

        self.assertEqual(len(entries), 1)
        start, end, text = entries[0]
        self.assertEqual(text, "안녕하세요")
        self.assertAlmostEqual(start, 0.5)  # 1.5 - 1.0(컷 길이)
        self.assertAlmostEqual(end, 1.5)

    def test_skips_segment_fully_cut(self):
        segments = [
            Segment(start=0.0, end=1.0, text="어",
                    words=[Word(0.0, 1.0, "어")])
        ]
        cut_intervals = [(0.0, 1.0)]
        remap = TimeRemapper(cut_intervals)
        entries = build_srt_entries(segments, cut_intervals, remap)
        self.assertEqual(entries, [])


class TestFormatTimestamp(unittest.TestCase):
    def test_format(self):
        self.assertEqual(_fmt_timestamp(0), "00:00:00,000")
        self.assertEqual(_fmt_timestamp(61.234), "00:01:01,234")
        self.assertEqual(_fmt_timestamp(3661.5), "01:01:01,500")


if __name__ == "__main__":
    unittest.main()
