"""Behavior tests for timetable PDF parsing helpers."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from schedule_pdf import parse_schedule_pdf, parse_weeks


class SchedulePdfTests(unittest.TestCase):
    def test_week_ranges_expand(self) -> None:
        self.assertEqual(parse_weeks("1-4周"), (1, 2, 3, 4))

    def test_week_lists_and_single_weeks_expand(self) -> None:
        self.assertEqual(parse_weeks("1-2周,4周"), (1, 2, 4))

    def test_even_week_marker_is_applied(self) -> None:
        self.assertEqual(parse_weeks("1-6周(双)"), (2, 4, 6))

    def test_odd_week_marker_is_applied(self) -> None:
        self.assertEqual(parse_weeks("3-7周(单)"), (3, 5, 7))

    def test_chinese_single_week_expression_is_supported(self) -> None:
        self.assertEqual(parse_weeks("第17周"), (17,))

    @unittest.skipUnless(
        os.environ.get("JQ_TEST_SCHEDULE_PDF"),
        "set JQ_TEST_SCHEDULE_PDF to run the full PDF parser test",
    )
    def test_real_schedule_pdf_is_parsed_end_to_end(self) -> None:
        result = parse_schedule_pdf(
            Path(os.environ["JQ_TEST_SCHEDULE_PDF"]),
            "fallback",
        )
        self.assertGreaterEqual(len(result.sessions), 10)
        self.assertIn("2026-2027", result.semester_title)
        self.assertEqual(result.sessions[0].course, "生物工程下游技术")


if __name__ == "__main__":
    unittest.main()
