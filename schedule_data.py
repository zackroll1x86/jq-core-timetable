"""Course schedule data and next-class calculation."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any

DEFAULT_SEMESTER_START = date(2026, 9, 7)
DEFAULT_SEMESTER_TITLE = "2026-2027 学年第一学期"
SEMESTER_START = DEFAULT_SEMESTER_START
SEMESTER_TITLE = DEFAULT_SEMESTER_TITLE
WEEKDAY_NAMES = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")

PERIOD_TIMES = (
    ("08:00", "08:40"),
    ("08:50", "09:30"),
    ("09:45", "10:25"),
    ("10:35", "11:15"),
    ("11:25", "12:05"),
    ("14:30", "15:10"),
    ("15:20", "16:00"),
    ("16:10", "16:50"),
    ("17:00", "17:40"),
    ("19:30", "20:10"),
    ("20:20", "21:00"),
    ("21:10", "21:50"),
)


@dataclass(frozen=True)
class Session:
    """A recurring class session in the semester."""

    course: str
    kind: str
    location: str
    weekday: int
    start_period: int
    end_period: int
    weeks: tuple[int, ...]


@dataclass(frozen=True)
class ClassOccurrence:
    """A concrete class occurrence with absolute start and end times."""

    session: Session
    week: int
    start: datetime
    end: datetime


@dataclass(frozen=True)
class ClassStatus:
    """The next class and countdown state."""

    occurrence: ClassOccurrence
    ongoing: bool
    seconds: int


def _week_range(start: int, end: int) -> tuple[int, ...]:
    return tuple(range(start, end + 1))


def _weeks(*groups: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(sorted({week for group in groups for week in group}))


DEFAULT_SESSIONS = (
    Session(
        "生物工程下游技术",
        "理论",
        "东莞校区 C2-1",
        0,
        1,
        3,
        _weeks(_week_range(1, 4), _week_range(6, 9)),
    ),
    Session(
        "生物信息学",
        "实验",
        "计算机实验室 301",
        0,
        3,
        5,
        _week_range(12, 13),
    ),
    Session(
        "基因工程",
        "理论",
        "东莞校区 C3-2",
        0,
        4,
        5,
        _weeks(_week_range(1, 4), _week_range(6, 11)),
    ),
    Session(
        "分子诊断技术",
        "理论",
        "东莞校区 C1-2",
        0,
        6,
        7,
        _weeks(_week_range(1, 2), (4,), _week_range(6, 14)),
    ),
    Session(
        "蛋白质与酶工程",
        "理论",
        "东莞校区 C2-1",
        0,
        8,
        9,
        _weeks(_week_range(1, 3), _week_range(6, 14)),
    ),
    Session(
        "医学大数据分析与决策",
        "理论",
        "东莞校区 A3-6",
        1,
        1,
        2,
        _week_range(1, 11),
    ),
    Session(
        "抗体工程",
        "理论",
        "东莞校区 C2-1",
        1,
        3,
        4,
        _weeks(_week_range(1, 2), (4,), _week_range(6, 13)),
    ),
    Session(
        "蛋白质与酶工程",
        "实验",
        "未排地点",
        1,
        6,
        11,
        _week_range(9, 16),
    ),
    Session(
        "基因工程",
        "理论",
        "东莞校区 D2-1",
        2,
        1,
        2,
        _weeks(_week_range(1, 4), _week_range(6, 16)),
    ),
    Session(
        "生物信息学",
        "理论",
        "东莞校区 D3-1",
        2,
        3,
        5,
        _weeks(_week_range(1, 2), (4,), _week_range(6, 13)),
    ),
    Session(
        "医学大数据分析与决策",
        "实验",
        "计算机实验室 302",
        2,
        8,
        9,
        _week_range(1, 11),
    ),
    Session(
        "烹饪与膳食",
        "通识",
        "东莞校区 A3-1",
        2,
        10,
        12,
        _week_range(6, 7),
    ),
    Session(
        "基因工程",
        "理论",
        "东莞校区 C1-1",
        3,
        1,
        2,
        _week_range(12, 15),
    ),
    Session(
        "生物工程下游技术",
        "理论",
        "东莞校区 D1-2",
        3,
        3,
        5,
        _weeks(_week_range(1, 2), (3, 5, 6), _week_range(7, 9)),
    ),
    Session(
        "蛋白质与酶工程",
        "理论",
        "东莞校区 C3-2",
        3,
        6,
        7,
        _weeks(_week_range(1, 3), _week_range(6, 14)),
    ),
    Session(
        "生物信息学",
        "实验",
        "计算机实验室 403",
        3,
        10,
        12,
        _week_range(14, 16),
    ),
    Session(
        "基因工程",
        "实验",
        "未排地点",
        4,
        1,
        5,
        _week_range(6, 15),
    ),
    Session(
        "抗体工程",
        "理论",
        "东莞校区 C2-2",
        4,
        6,
        7,
        _weeks((1, 2, 5), _week_range(6, 9), _week_range(11, 12)),
    ),
    Session(
        "生物信息学",
        "实验",
        "计算机实验室 301",
        4,
        10,
        12,
        (7,),
    ),
)
SESSIONS = DEFAULT_SESSIONS


def get_semester_title() -> str:
    """Return the active semester title."""

    return SEMESTER_TITLE


def get_semester_start() -> date:
    """Return the Monday of the active semester's first teaching week."""

    return SEMESTER_START


def configure_schedule(
    sessions: tuple[Session, ...],
    semester_start: date | None = None,
    semester_title: str | None = None,
) -> None:
    """Replace the in-memory schedule with imported data."""

    global SESSIONS, SEMESTER_START, SEMESTER_TITLE

    SESSIONS = tuple(sessions)
    if semester_start is not None:
        SEMESTER_START = semester_start
    if semester_title is not None:
        SEMESTER_TITLE = semester_title


def schedule_to_dict() -> dict[str, Any]:
    """Serialize the active schedule for the per-user config file."""

    return {
        "version": 1,
        "semester_start": SEMESTER_START.isoformat(),
        "semester_title": SEMESTER_TITLE,
        "sessions": [
            {
                "course": session.course,
                "kind": session.kind,
                "location": session.location,
                "weekday": session.weekday,
                "start_period": session.start_period,
                "end_period": session.end_period,
                "weeks": list(session.weeks),
            }
            for session in SESSIONS
        ],
    }


def _session_from_dict(data: dict[str, Any], index: int) -> Session:
    try:
        session = Session(
            course=str(data["course"]).strip(),
            kind=str(data["kind"]).strip(),
            location=str(data["location"]).strip(),
            weekday=int(data["weekday"]),
            start_period=int(data["start_period"]),
            end_period=int(data["end_period"]),
            weeks=tuple(sorted({int(week) for week in data["weeks"]})),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"Invalid schedule session at index {index}") from error
    if not session.course or not session.location:
        raise ValueError(f"Session {index} is missing course or location")
    if not 0 <= session.weekday < len(WEEKDAY_NAMES):
        raise ValueError(f"Session {index} has invalid weekday")
    if not 1 <= session.start_period <= session.end_period <= len(PERIOD_TIMES):
        raise ValueError(f"Session {index} has invalid period range")
    if not session.weeks or any(week < 1 for week in session.weeks):
        raise ValueError(f"Session {index} has invalid weeks")
    return session


def schedule_from_dict(data: dict[str, Any]) -> tuple[tuple[Session, ...], date, str]:
    """Deserialize and validate a saved schedule."""

    if data.get("version") != 1:
        raise ValueError("Unsupported schedule file version")
    try:
        semester_start = date.fromisoformat(str(data["semester_start"]))
        semester_title = str(data["semester_title"]).strip()
        session_data = data["sessions"]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError("Schedule file is missing semester data") from error
    if not semester_title or not isinstance(session_data, list):
        raise ValueError("Schedule file contains invalid semester data")
    sessions = tuple(
        _session_from_dict(item, index)
        for index, item in enumerate(session_data)
        if isinstance(item, dict)
    )
    if len(sessions) != len(session_data):
        raise ValueError("Schedule file contains a non-object session")
    return sessions, semester_start, semester_title


def save_schedule(path: Path) -> None:
    """Write the active schedule to a UTF-8 JSON file."""

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(schedule_to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_schedule(path: Path) -> None:
    """Load a saved schedule into the active application state."""

    data = json.loads(Path(path).read_text(encoding="utf-8"))
    sessions, semester_start, semester_title = schedule_from_dict(data)
    configure_schedule(sessions, semester_start, semester_title)


def week_number_on(day: date) -> int:
    """Return the teaching week number for a calendar date."""

    delta_days = (day - SEMESTER_START).days
    if delta_days < 0:
        return 0
    return delta_days // 7 + 1


def week_start(week: int) -> date:
    """Return the Monday for a teaching week."""

    return SEMESTER_START + timedelta(days=(week - 1) * 7)


def week_date_range(week: int) -> tuple[date, date]:
    """Return the inclusive Monday-to-Sunday range for a teaching week."""

    start = week_start(week)
    return start, start + timedelta(days=6)


def _datetime_on(day: date, period: int, is_end: bool = False) -> datetime:
    index = period - 1
    value = PERIOD_TIMES[index][1 if is_end else 0]
    hour, minute = (int(part) for part in value.split(":"))
    return datetime.combine(day, time(hour, minute))


def occurrence_for(session: Session, week: int) -> ClassOccurrence:
    """Build a concrete occurrence for a session and week."""

    day = week_start(week) + timedelta(days=session.weekday)
    return ClassOccurrence(
        session=session,
        week=week,
        start=_datetime_on(day, session.start_period),
        end=_datetime_on(day, session.end_period, is_end=True),
    )


def occurrences_for_week(week: int) -> tuple[ClassOccurrence, ...]:
    """Return every scheduled class in a teaching week."""

    occurrences = [occurrence_for(session, week) for session in SESSIONS if week in session.weeks]
    return tuple(sorted(occurrences, key=lambda item: (item.session.weekday, item.start)))


def next_class_status(now: datetime) -> ClassStatus | None:
    """Return the next class or the class currently in progress."""

    for day_offset in range(35):
        day = now.date() + timedelta(days=day_offset)
        week = week_number_on(day)
        if week <= 0:
            continue
        for occurrence in occurrences_for_week(week):
            if occurrence.start.date() != day:
                continue
            if occurrence.end < now:
                continue
            if occurrence.start <= now <= occurrence.end:
                return ClassStatus(occurrence, True, (occurrence.end - now).seconds)
            return ClassStatus(occurrence, False, (occurrence.start - now).seconds)
    return None


def format_countdown(seconds: int) -> str:
    """Format a countdown in a compact Chinese form."""

    seconds = max(0, seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    if days:
        return f"{days}天 {hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def format_occurrence_time(occurrence: ClassOccurrence) -> str:
    """Format the date, weekday, and period range for a class occurrence."""

    weekday = WEEKDAY_NAMES[occurrence.session.weekday]
    start = occurrence.start.strftime("%H:%M")
    end = occurrence.end.strftime("%H:%M")
    return f"{occurrence.start:%Y-%m-%d} {weekday}  {start}-{end}"
