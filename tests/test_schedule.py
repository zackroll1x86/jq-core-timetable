"""Behavior tests for schedule calculations."""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from schedule_data import (
    SESSIONS,
    format_countdown,
    next_class_status,
    occurrences_for_week,
    schedule_from_dict,
    schedule_to_dict,
    week_number_on,
)


class ScheduleTests(unittest.TestCase):
    def test_official_calendar_maps_sunday_to_week_two(self) -> None:
        self.assertEqual(week_number_on(datetime(2026, 9, 20).date()), 2)

    def test_next_class_crosses_into_week_three(self) -> None:
        status = next_class_status(datetime(2026, 9, 20, 20, 0))
        self.assertIsNotNone(status)
        assert status is not None
        self.assertFalse(status.ongoing)
        self.assertEqual(status.occurrence.week, 3)
        self.assertEqual(status.occurrence.session.course, "生物工程下游技术")
        self.assertEqual(status.occurrence.start, datetime(2026, 9, 21, 8, 0))

    def test_ongoing_class_reports_remaining_time(self) -> None:
        status = next_class_status(datetime(2026, 9, 21, 8, 10))
        self.assertIsNotNone(status)
        assert status is not None
        self.assertTrue(status.ongoing)
        self.assertEqual(status.occurrence.session.course, "生物工程下游技术")
        self.assertEqual(status.seconds, 135 * 60)

    def test_week_three_contains_expected_sessions(self) -> None:
        occurrences = occurrences_for_week(3)
        self.assertEqual(len(occurrences), 8)
        self.assertEqual(occurrences[0].session.location, "东莞校区 C2-1")

    def test_countdown_keeps_zero_at_invalid_negative_value(self) -> None:
        self.assertEqual(format_countdown(-1), "00:00:00")

    def test_schedule_round_trip_preserves_sessions(self) -> None:
        sessions, semester_start, semester_title = schedule_from_dict(schedule_to_dict())
        self.assertEqual(sessions, SESSIONS)
        self.assertEqual(semester_start, datetime(2026, 9, 7).date())
        self.assertEqual(semester_title, "2026-2027 学年第一学期")


if __name__ == "__main__":
    unittest.main()
