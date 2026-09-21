"""Parse a common Chinese university timetable PDF into schedule sessions."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from schedule_data import Session

WEEKDAY_HEADERS = {
    "星期一": 0,
    "星期二": 1,
    "星期三": 2,
    "星期四": 3,
    "星期五": 4,
    "星期六": 5,
    "星期日": 6,
}
SEMESTER_RE = re.compile(r"(?P<year>\d{4}-\d{4})学年第(?P<term>[一二三四五六七八九十\d]+)学期")
KIND_RE = re.compile(r"\((?P<kind>理论|实验|实践)\)")
PERIOD_RE = re.compile(r"\((?P<start>\d+)(?:-(?P<end>\d+))?节\)")
WEEK_RE = re.compile(r"(?:第)?(?P<start>\d+)(?:-(?P<end>\d+))?周")
CAMPUS_RE = re.compile(r"/校区:(?P<campus>[^/]+)")
LOCATION_RE = re.compile(r"/场地:(?P<location>[^/]+)")
TERM_NAMES = {
    "1": "一",
    "2": "二",
    "3": "三",
    "4": "四",
    "5": "五",
    "6": "六",
    "7": "七",
    "8": "八",
}


@dataclass(frozen=True)
class TextFragment:
    """One positioned text fragment extracted from the PDF."""

    page: int
    x: float
    y: float
    size: float
    text: str


@dataclass
class CellBlock:
    """Course text collected for one timetable cell."""

    weekday: int
    title_parts: list[str] = field(default_factory=list)
    detail_parts: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ParsedSchedule:
    """Structured result produced from a timetable PDF."""

    sessions: tuple[Session, ...]
    semester_title: str


def _read_fragments(path: Path) -> list[TextFragment]:
    try:
        reader = PdfReader(str(path))
    except (OSError, PdfReadError) as error:
        raise ValueError("无法读取课表 PDF，请确认文件没有损坏") from error
    fragments: list[TextFragment] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_fragments: list[TextFragment] = []

        def visitor(
            text: str,
            _cm: tuple[float, ...],
            tm: tuple[float, ...],
            _font: object,
            font_size: float,
            current_page: int = page_number,
            current_fragments: list[TextFragment] = page_fragments,
        ) -> None:
            value = text.strip()
            if value:
                current_fragments.append(
                    TextFragment(
                        page=current_page,
                        x=float(tm[4]),
                        y=float(tm[5]),
                        size=float(font_size),
                        text=value,
                    )
                )

        page.extract_text(visitor_text=visitor)
        fragments.extend(page_fragments)
    return fragments


def _parse_semester_title(fragments: list[TextFragment], fallback: str) -> str:
    for fragment in fragments:
        match = SEMESTER_RE.search(fragment.text)
        if not match:
            continue
        term = match.group("term")
        term_name = TERM_NAMES.get(term, term)
        return f"{match.group('year')} 学年第{term_name}学期"
    return fallback


def _weekday_columns(fragments: list[TextFragment]) -> list[tuple[int, float]]:
    columns = [
        (WEEKDAY_HEADERS[fragment.text], fragment.x)
        for fragment in fragments
        if fragment.text in WEEKDAY_HEADERS
    ]
    columns.sort()
    if len(columns) != len(WEEKDAY_HEADERS):
        raise ValueError("不支持该课表 PDF：未找到完整的星期列表头")
    return columns


def _column_for_x(
    x: float,
    columns: list[tuple[int, float]],
) -> int | None:
    weekday, distance = min(
        ((weekday, abs(x - column_x)) for weekday, column_x in columns),
        key=lambda item: item[1],
    )
    return weekday if distance <= 45 else None


def _collect_cell_blocks(fragments: list[TextFragment]) -> list[CellBlock]:
    columns = _weekday_columns(fragments)
    active: list[CellBlock | None] = [None] * len(WEEKDAY_HEADERS)
    blocks: list[CellBlock] = []
    for fragment in fragments:
        if not 7.5 <= fragment.size <= 10.5:
            continue
        weekday = _column_for_x(fragment.x, columns)
        if weekday is None:
            continue
        if fragment.size >= 8.8:
            title = "".join(active[weekday].title_parts) if active[weekday] else ""
            is_title_continuation = (
                fragment.text.startswith("(")
                and active[weekday] is not None
                and KIND_RE.search(title) is None
            )
            if is_title_continuation:
                active[weekday].title_parts.append(fragment.text)
                continue
            block = CellBlock(weekday=weekday, title_parts=[fragment.text])
            blocks.append(block)
            active[weekday] = block
        elif active[weekday] is not None:
            active[weekday].detail_parts.append(fragment.text)
    return blocks


def parse_weeks(text: str) -> tuple[int, ...]:
    """Parse strings such as `1-4周,6周(双),第17周`."""

    weeks: set[int] = set()
    for token in re.split(r"[,，、]", text):
        match = WEEK_RE.search(token)
        if match is None:
            continue
        start = int(match.group("start"))
        end = int(match.group("end") or start)
        if end < start:
            continue
        parity = "单" if "(单)" in token else "双" if "(双)" in token else None
        for week in range(start, end + 1):
            if parity == "单" and week % 2 == 0:
                continue
            if parity == "双" and week % 2 == 1:
                continue
            weeks.add(week)
    return tuple(sorted(weeks))


def _normalize_location(text: str) -> str:
    value = re.sub(r"\s+", " ", text).strip()
    value = re.sub(r"(?<=\b[A-Z])-(\d+)-(\d+)", r"\1-\2", value)
    value = re.sub(r"(?<=[\u4e00-\u9fff])(?=\d)", " ", value)
    return value


def _parse_block(block: CellBlock) -> Session | None:
    title = "".join(block.title_parts).strip()
    detail = "".join(block.detail_parts).strip()
    kind_match = KIND_RE.search(title)
    period_match = PERIOD_RE.search(detail)
    if kind_match is None or period_match is None:
        return None
    kind = kind_match.group("kind")
    course = title[: kind_match.start()].strip()
    start_period = int(period_match.group("start"))
    end_period = int(period_match.group("end") or start_period)

    week_match = re.search(r"节\)(.+?)/校区:", detail)
    week_text = week_match.group(1) if week_match else ""
    weeks = parse_weeks(week_text)
    if not course or not weeks:
        return None

    campus_match = CAMPUS_RE.search(detail)
    location_match = LOCATION_RE.search(detail)
    campus = campus_match.group("campus").strip() if campus_match else ""
    room = location_match.group("location").strip() if location_match else ""
    if room == "未排地点":
        location = room
    elif campus and room:
        location = _normalize_location(f"{campus} {room}")
    else:
        location = _normalize_location(room or campus or "未排地点")

    return Session(
        course=course,
        kind=kind,
        location=location,
        weekday=block.weekday,
        start_period=start_period,
        end_period=end_period,
        weeks=weeks,
    )


def parse_schedule_pdf(path: Path, fallback_title: str) -> ParsedSchedule:
    """Parse a timetable PDF and return importable course sessions."""

    fragments = _read_fragments(Path(path))
    blocks = _collect_cell_blocks(fragments)
    sessions = tuple(session for block in blocks if (session := _parse_block(block)) is not None)
    if not sessions:
        raise ValueError("不支持该课表 PDF：未识别到有效课程")
    sessions = tuple(
        sorted(
            sessions,
            key=lambda item: (
                item.weekday,
                item.start_period,
                item.course,
                item.weeks,
            ),
        )
    )
    return ParsedSchedule(
        sessions=sessions,
        semester_title=_parse_semester_title(fragments, fallback_title),
    )
