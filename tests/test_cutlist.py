import unittest

from rara.cutlist import TimeRemapper, build_cutlist, invert_intervals, merge_intervals


class TestMergeIntervals(unittest.TestCase):
    def test_merge_overlapping(self):
        self.assertEqual(
            merge_intervals([(0, 1), (0.5, 2), (3, 4)]),
            [(0, 2), (3, 4)],
        )

    def test_merge_with_gap(self):
        self.assertEqual(
            merge_intervals([(0, 1), (1.1, 2)], gap=0.2),
            [(0, 2)],
        )
        self.assertEqual(
            merge_intervals([(0, 1), (1.3, 2)], gap=0.2),
            [(0, 1), (1.3, 2)],
        )

    def test_empty(self):
        self.assertEqual(merge_intervals([]), [])


class TestInvertIntervals(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(
            invert_intervals([(1, 2), (4, 5)], duration=6),
            [(0, 1), (2, 4), (5, 6)],
        )

    def test_covers_whole_range(self):
        self.assertEqual(invert_intervals([(0, 6)], duration=6), [])

    def test_no_cuts(self):
        self.assertEqual(invert_intervals([], duration=6), [(0, 6)])


class TestBuildCutlist(unittest.TestCase):
    def test_pads_and_merges(self):
        cuts, keep = build_cutlist(
            duration=10,
            silence_intervals=[(2.0, 3.0)],
            stutter_intervals=[(3.05, 3.2)],
            pad=0.05,
            merge_gap=0.2,
            min_cut_duration=0.1,
            min_keep_duration=0.1,
        )
        # 두 컷이 pad로 인해 서로 붙어 하나로 합쳐져야 함
        self.assertEqual(len(cuts), 1)
        s, e = cuts[0]
        self.assertAlmostEqual(s, 1.95)
        self.assertAlmostEqual(e, 3.25)
        # 남길 구간은 앞/뒤 두 개
        self.assertEqual(len(keep), 2)

    def test_drops_tiny_keep_slivers(self):
        # 두 컷 사이에 아주 짧은(0.05s) keep 조각이 생기면 제거되어야 함
        cuts, keep = build_cutlist(
            duration=10,
            silence_intervals=[(1.0, 2.0), (2.05, 3.0)],
            stutter_intervals=[],
            pad=0.0,
            merge_gap=0.0,
            min_cut_duration=0.0,
            min_keep_duration=0.1,
        )
        # (2.0, 2.05) 조각이 살아남지 않아야 함
        for s, e in keep:
            self.assertGreaterEqual(e - s, 0.1)


class TestTimeRemapper(unittest.TestCase):
    def test_remap_after_cuts(self):
        remap = TimeRemapper([(1.0, 2.0), (4.0, 5.0)])
        self.assertAlmostEqual(remap(0.5), 0.5)
        self.assertAlmostEqual(remap(3.0), 2.0)  # 1초 컷 이후
        self.assertAlmostEqual(remap(6.0), 4.0)  # 2초 컷 이후

    def test_remap_inside_cut_clamped(self):
        remap = TimeRemapper([(1.0, 2.0)])
        self.assertAlmostEqual(remap(1.5), 1.0)


if __name__ == "__main__":
    unittest.main()
