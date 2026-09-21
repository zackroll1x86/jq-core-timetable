"""Desktop schedule dashboard with a boot notification."""

from __future__ import annotations

import ctypes
import json
import os
import subprocess
import sys
import tkinter as tk
import tkinter.font as tkfont
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import schedule_data
from schedule_data import (
    PERIOD_TIMES,
    WEEKDAY_NAMES,
    format_countdown,
    format_occurrence_time,
    next_class_status,
    occurrences_for_week,
    week_date_range,
    week_number_on,
)
from schedule_pdf import ParsedSchedule, parse_schedule_pdf

APP_DIR = Path(__file__).resolve().parent
ASSETS_DIR = Path(getattr(sys, "_MEIPASS", APP_DIR)) / "assets"
MAIN_WIDTH = 1360
MAIN_HEIGHT = 820
NOTIFY_WIDTH = 680
NOTIFY_HEIGHT = 230
SETUP_VERSION = 1
APP_NAME = "今日课表"
UI_FONT_CANDIDATES = (
    "Microsoft YaHei UI",
    "Noto Sans CJK SC",
    "Noto Sans CJK",
    "WenQuanYi Micro Hei",
    "DejaVu Sans",
)
MONO_FONT_CANDIDATES = (
    "Consolas",
    "Noto Sans Mono CJK SC",
    "DejaVu Sans Mono",
)
DISPLAY_FONT_CANDIDATES = (
    "Segoe UI Variable Display",
    "Microsoft YaHei UI",
    "Noto Sans CJK SC",
    "DejaVu Sans",
)

PALETTE = {
    "background": ASSETS_DIR / "background.png",
    "notification": ASSETS_DIR / "notification.png",
    "accent": "#8FCF74",
    "accent_bright": "#D5FFB8",
    "text": "#F7F4E8",
    "muted": "#B7C2AE",
    "line": "#526A50",
    "cell": "#101812",
    "theory": "#294725",
    "lab": "#16504A",
    "general": "#604922",
}


def set_dpi_awareness() -> None:
    """Keep the fixed-size interface sharp on scaled Windows displays."""

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass


def settings_path() -> Path:
    """Return the per-user location that records first-run setup."""

    override = os.environ.get("JQ_CORE_CONFIG_DIR")
    if override:
        base = Path(override)
    else:
        base = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JQCore"
    return base / "settings.json"


def user_schedule_path() -> Path:
    """Return the saved schedule generated from an imported PDF."""

    return settings_path().parent / "schedule.json"


def load_saved_schedule() -> str | None:
    """Load the user schedule and return an error message if it is invalid."""

    try:
        schedule_data.load_schedule(user_schedule_path())
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as error:
        return str(error)
    return None


def generate_schedule_from_pdf(path: Path) -> ParsedSchedule:
    """Parse, activate, and persist a schedule generated from a PDF."""

    parsed = parse_schedule_pdf(
        path,
        schedule_data.get_semester_title(),
    )
    schedule_data.configure_schedule(
        parsed.sessions,
        schedule_data.get_semester_start(),
        parsed.semester_title,
    )
    schedule_data.save_schedule(user_schedule_path())
    return parsed


def setup_completed() -> bool:
    """Return whether the shortcut wizard has already been completed."""

    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return data.get("setup_version") == SETUP_VERSION


def mark_setup_completed() -> None:
    """Persist completion so the wizard is only shown on first run."""

    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "app": APP_NAME,
        "setup_version": SETUP_VERSION,
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def known_folder(csidl: int) -> Path:
    """Resolve a Windows known folder without third-party dependencies."""

    buffer = ctypes.create_unicode_buffer(260)
    result = ctypes.windll.shell32.SHGetFolderPathW(
        None,
        csidl,
        None,
        0,
        buffer,
    )
    if result != 0:
        raise OSError(f"Unable to resolve Windows folder, error {result}")
    return Path(buffer.value)


def shortcut_runtime() -> tuple[Path, str, Path, Path]:
    """Return shortcut target, arguments, working directory, and icon."""

    if getattr(sys, "frozen", False):
        executable = Path(sys.executable)
        return executable, "", executable.parent, executable
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    target = pythonw if pythonw.exists() else Path(sys.executable)
    arguments = f'"{Path(__file__).resolve()}"'
    return target, arguments, APP_DIR, ASSETS_DIR / "app.ico"


def create_shortcut(path: Path, arguments: str) -> Path:
    """Create one Windows shortcut through the built-in WScript shell."""

    target, base_arguments, working_directory, icon = shortcut_runtime()
    path.parent.mkdir(parents=True, exist_ok=True)
    combined_arguments = " ".join(part for part in (base_arguments, arguments) if part)
    script = """
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($env:JQ_SHORTCUT_PATH)
$shortcut.TargetPath = $env:JQ_SHORTCUT_TARGET
$shortcut.Arguments = $env:JQ_SHORTCUT_ARGUMENTS
$shortcut.WorkingDirectory = $env:JQ_SHORTCUT_WORKDIR
$shortcut.IconLocation = $env:JQ_SHORTCUT_ICON
$shortcut.Description = $env:JQ_SHORTCUT_DESCRIPTION
$shortcut.Save()
"""
    environment = os.environ.copy()
    environment.update(
        {
            "JQ_SHORTCUT_PATH": str(path),
            "JQ_SHORTCUT_TARGET": str(target),
            "JQ_SHORTCUT_ARGUMENTS": combined_arguments,
            "JQ_SHORTCUT_WORKDIR": str(working_directory),
            "JQ_SHORTCUT_ICON": str(icon),
            "JQ_SHORTCUT_DESCRIPTION": APP_NAME,
        }
    )
    subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            script,
        ],
        check=True,
        capture_output=True,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        env=environment,
        text=True,
    )
    return path


def install_shortcuts(
    desktop: bool,
    start_menu: bool,
    startup: bool,
) -> list[Path]:
    """Create the shortcuts selected in the first-run wizard."""

    created: list[Path] = []
    if desktop:
        created.append(
            create_shortcut(
                known_folder(0x0010) / f"{APP_NAME}.lnk",
                "",
            )
        )
    if start_menu:
        created.append(
            create_shortcut(
                known_folder(0x0002) / APP_NAME / f"{APP_NAME}.lnk",
                "",
            )
        )
    if startup:
        created.append(
            create_shortcut(
                known_folder(0x0007) / f"{APP_NAME}-开机提示.lnk",
                "--startup",
            )
        )
    return created


def choose_font(root: tk.Tk, candidates: tuple[str, ...]) -> str:
    """Return the first installed font, with a platform-safe fallback."""

    available = {family.casefold() for family in tkfont.families(root)}
    for candidate in candidates:
        if candidate.casefold() in available:
            return candidate
    return str(tkfont.nametofont("TkDefaultFont").actual("family"))


def rounded_rectangle(
    canvas: tk.Canvas, x1: int, y1: int, x2: int, y2: int, radius: int, **kwargs: object
) -> int:
    """Draw a rounded rectangle on a Tk canvas."""

    points = (
        x1 + radius,
        y1,
        x2 - radius,
        y1,
        x2,
        y1,
        x2,
        y1 + radius,
        x2,
        y2 - radius,
        x2,
        y2,
        x2 - radius,
        y2,
        x1 + radius,
        y2,
        x1,
        y2,
        x1,
        y2 - radius,
        x1,
        y1 + radius,
        x1,
        y1,
    )
    return canvas.create_polygon(points, smooth=True, splinesteps=24, **kwargs)


def load_photo(path: Path) -> tk.PhotoImage | None:
    """Load a PNG while keeping callers independent from Tk errors."""

    try:
        return tk.PhotoImage(file=str(path))
    except tk.TclError:
        return None


def trim_text(text: str, limit: int) -> str:
    """Trim long course names while keeping the label readable."""

    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


class SetupWizard:
    """Show a classic first-run installer for shortcut creation."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.desktop = tk.BooleanVar(value=True)
        self.start_menu = tk.BooleanVar(value=True)
        self.startup = tk.BooleanVar(value=False)
        self.launched = False
        self.font = choose_font(root, UI_FONT_CANDIDATES)
        self._configure_window()
        self._build_interface()

    def _configure_window(self) -> None:
        self.root.title(f"{APP_NAME} 安装向导")
        self.root.configure(bg="#ECE9D8")
        self.root.resizable(False, False)
        width = 610
        height = 520
        left = max(0, (self.root.winfo_screenwidth() - width) // 2)
        top = max(0, (self.root.winfo_screenheight() - height) // 2)
        self.root.geometry(f"{width}x{height}+{left}+{top}")
        try:
            self.root.iconbitmap(str(ASSETS_DIR / "app.ico"))
        except tk.TclError:
            pass

    def _build_interface(self) -> None:
        header = tk.Frame(self.root, bg="#275B8A", height=88)
        header.pack(fill="x")
        header.pack_propagate(False)
        tk.Label(
            header,
            text=f"欢迎使用 {APP_NAME}",
            bg="#275B8A",
            fg="white",
            font=(self.font, 20, "bold"),
        ).pack(anchor="w", padx=24, pady=(14, 0))
        tk.Label(
            header,
            text="安装向导",
            bg="#275B8A",
            fg="#DCEAF5",
            font=(self.font, 10),
        ).pack(anchor="w", padx=26)

        body = tk.Frame(self.root, bg="#ECE9D8", padx=24, pady=16)
        tk.Label(
            body,
            text="文件已解压完成，可以直接运行。",
            bg="#ECE9D8",
            fg="#111111",
            font=(self.font, 11, "bold"),
        ).pack(anchor="w")
        tk.Label(
            body,
            text="请选择需要创建的快捷方式。以后可通过命令行参数 --setup 重新打开本向导。",
            bg="#ECE9D8",
            fg="#333333",
            font=(self.font, 9),
            wraplength=540,
        ).pack(anchor="w", pady=(4, 12))

        options = tk.LabelFrame(
            body,
            text=" 快捷方式选项 ",
            bg="#ECE9D8",
            fg="#111111",
            font=(self.font, 9),
            padx=14,
            pady=10,
        )
        options.pack(fill="x")
        tk.Checkbutton(
            options,
            text="创建桌面快捷方式",
            variable=self.desktop,
            bg="#ECE9D8",
            activebackground="#ECE9D8",
            font=(self.font, 10),
        ).pack(anchor="w", pady=3)
        tk.Checkbutton(
            options,
            text="添加到开始菜单",
            variable=self.start_menu,
            bg="#ECE9D8",
            activebackground="#ECE9D8",
            font=(self.font, 10),
        ).pack(anchor="w", pady=3)
        tk.Checkbutton(
            options,
            text="开机后自动显示下一节课提示",
            variable=self.startup,
            bg="#ECE9D8",
            activebackground="#ECE9D8",
            font=(self.font, 10),
        ).pack(anchor="w", pady=3)

        self.status = tk.Label(
            body,
            text="选择完成后，点击“开始安装”。",
            bg="#ECE9D8",
            fg="#245A2A",
            justify="left",
            anchor="w",
            wraplength=540,
            font=(self.font, 9),
        )
        self.status.pack(fill="x", pady=(14, 0))

        footer = tk.Frame(self.root, bg="#D4D0C8", padx=16, pady=10)
        footer.pack(fill="x", side="bottom")
        self.install_button = tk.Button(
            footer,
            text="开始安装",
            width=12,
            command=self._install,
            font=(self.font, 9),
        )
        self.install_button.pack(side="right", padx=(8, 0))
        tk.Button(
            footer,
            text="直接运行",
            width=12,
            command=self._launch_app,
            font=(self.font, 9),
        ).pack(side="right")
        tk.Button(
            footer,
            text="退出",
            width=9,
            command=self.root.destroy,
            font=(self.font, 9),
        ).pack(side="left")
        body.pack(fill="both", expand=True)

    def _install(self) -> None:
        self.install_button.configure(state="disabled")
        self.status.configure(text="正在创建快捷方式，请稍候……", fg="#333333")
        self.root.update_idletasks()
        try:
            created = install_shortcuts(
                desktop=self.desktop.get(),
                start_menu=self.start_menu.get(),
                startup=self.startup.get(),
            )
        except (OSError, subprocess.SubprocessError) as error:
            self.install_button.configure(state="normal")
            self.status.configure(
                text=f"创建快捷方式失败：{error}",
                fg="#9B1C1C",
            )
            messagebox.showerror(
                title=f"{APP_NAME} 安装向导",
                message="快捷方式创建失败，但仍可直接运行程序。",
                parent=self.root,
            )
            return
        mark_setup_completed()
        count = len(created)
        self.status.configure(
            text=f"安装完成，共创建 {count} 个快捷方式，正在打开课表……",
            fg="#245A2A",
        )
        self.root.after(650, self._launch_app)

    def _launch_app(self) -> None:
        if self.launched:
            return
        self.launched = True
        mark_setup_completed()
        for child in self.root.winfo_children():
            child.destroy()
        self.root.title(f"JQ CORE | {APP_NAME}")
        self.root.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}")
        self.root.resizable(False, False)
        ScheduleApp(self.root, startup=False)


class ScheduleApp:
    """Render the full dashboard and the startup notification."""

    def __init__(self, root: tk.Tk, startup: bool) -> None:
        self.root = root
        self.startup = startup
        self.palette = PALETTE
        self.ui_font = choose_font(root, UI_FONT_CANDIDATES)
        self.mono_font = choose_font(root, MONO_FONT_CANDIDATES)
        self.display_font = choose_font(root, DISPLAY_FONT_CANDIDATES)
        self.images: list[tk.PhotoImage] = []
        self.render_state: tuple[object, ...] | None = None
        self.countdown_id: int | None = None
        self.clock_id: int | None = None
        self.status_prefix_id: int | None = None

        root.configure(bg="#050807")
        if startup:
            self._configure_notification_window()
        else:
            self._configure_main_window()

        self.canvas = tk.Canvas(
            root,
            width=NOTIFY_WIDTH if startup else MAIN_WIDTH,
            height=NOTIFY_HEIGHT if startup else MAIN_HEIGHT,
            highlightthickness=0,
            bg="#050807",
        )
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self._on_click)
        root.bind("<Escape>", lambda _event: root.destroy())
        self._render()
        self._schedule_tick()

    def _configure_notification_window(self) -> None:
        self.root.title("下一节课")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        left = max(12, screen_width - NOTIFY_WIDTH - 24)
        top = max(12, screen_height - NOTIFY_HEIGHT - 62)
        self.root.geometry(f"{NOTIFY_WIDTH}x{NOTIFY_HEIGHT}+{left}+{top}")
        self.root.after(28000, self._close_if_alive)

    def _configure_main_window(self) -> None:
        self.root.title("JQ CORE | 今日课表")
        self.root.resizable(False, False)
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        left = max(0, (screen_width - MAIN_WIDTH) // 2)
        top = max(0, (screen_height - MAIN_HEIGHT) // 2)
        self.root.geometry(f"{MAIN_WIDTH}x{MAIN_HEIGHT}+{left}+{top}")
        try:
            self.root.iconbitmap(str(ASSETS_DIR / "app.ico"))
        except tk.TclError:
            pass

    def _close_if_alive(self) -> None:
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    def _set_background(self, key: str) -> None:
        self.images.clear()
        background = load_photo(self.palette[key])
        if background is not None:
            self.images.append(background)
            self.canvas.create_image(0, 0, anchor="nw", image=background)
        else:
            self.canvas.create_rectangle(
                0,
                0,
                self.canvas.winfo_reqwidth(),
                self.canvas.winfo_reqheight(),
                fill="#071009",
                outline="",
            )

    def _render(self) -> None:
        self.canvas.delete("all")
        if self.startup:
            self._render_notification()
        else:
            self._render_dashboard()

    def _render_notification(self) -> None:
        self._set_background("notification")
        now = datetime.now()
        status = next_class_status(now)
        self.canvas.create_line(
            28,
            30,
            28,
            200,
            fill=self.palette["accent"],
            width=4,
        )
        self.canvas.create_text(
            54,
            24,
            anchor="nw",
            text="JQ CORE",
            fill=self.palette["accent_bright"],
            font=(self.ui_font, 13, "bold"),
        )
        self.canvas.create_text(
            54,
            50,
            anchor="nw",
            text="下一节课 · NEXT CLASS",
            fill=self.palette["muted"],
            font=(self.ui_font, 9),
        )
        self.canvas.create_text(
            638,
            24,
            anchor="ne",
            text="×",
            fill=self.palette["muted"],
            font=(self.ui_font, 16),
        )
        if status is None:
            self._render_notification_empty()
            return

        occurrence = status.occurrence
        title = trim_text(occurrence.session.course, 18)
        self.canvas.create_text(
            54,
            82,
            anchor="nw",
            text=title,
            fill=self.palette["text"],
            font=(self.ui_font, 22, "bold"),
        )
        detail = f"{format_occurrence_time(occurrence)}  |  {occurrence.session.location}"
        self.canvas.create_text(
            54,
            134,
            anchor="nw",
            text=detail,
            fill=self.palette["muted"],
            font=(self.ui_font, 10),
        )
        prefix = "剩余" if status.ongoing else "距上课"
        countdown = format_countdown(status.seconds)
        self.canvas.create_text(
            54,
            183,
            anchor="nw",
            text=prefix,
            fill=self.palette["muted"],
            font=(self.ui_font, 10),
        )
        self.canvas.create_text(
            112,
            180,
            anchor="nw",
            text=countdown,
            fill=self.palette["accent_bright"],
            font=(self.mono_font, 17, "bold"),
        )
        week_text = f"第 {occurrence.week} 周"
        self.canvas.create_text(
            638,
            76,
            anchor="ne",
            text=week_text,
            fill=self.palette["accent_bright"],
            font=(self.ui_font, 15, "bold"),
        )

    def _render_notification_empty(self) -> None:
        self.canvas.create_text(
            54,
            92,
            anchor="nw",
            text="当前没有可计算的课程",
            fill=self.palette["text"],
            font=(self.ui_font, 22, "bold"),
        )
        self.canvas.create_text(
            54,
            138,
            anchor="nw",
            text="请检查校历周次或课程数据",
            fill=self.palette["muted"],
            font=(self.ui_font, 10),
        )

    def _render_dashboard(self) -> None:
        self._set_background("background")
        now = datetime.now()
        current_week = week_number_on(now.date())
        week_occurrences = occurrences_for_week(current_week) if current_week > 0 else ()
        status = next_class_status(now)
        self._draw_header(now)
        self._draw_next_card(status)
        self._draw_rail(current_week, week_occurrences, status)
        self._draw_week_grid(current_week, week_occurrences)
        self._draw_footer()
        key = (
            current_week,
            status.occurrence.start if status else None,
            status.ongoing if status else None,
        )
        self.render_state = key

    def _draw_header(self, now: datetime) -> None:
        self._draw_logo_mark(34, 26, 36)
        self.canvas.create_text(
            84,
            23,
            anchor="nw",
            text="JQ CORE",
            fill=self.palette["text"],
            font=(self.display_font, 18, "bold"),
        )
        self.canvas.create_text(
            84,
            58,
            anchor="nw",
            text="ACADEMIC SCHEDULE SYSTEM",
            fill=self.palette["muted"],
            font=(self.mono_font, 9),
        )
        self.clock_id = self.canvas.create_text(
            1328,
            28,
            anchor="ne",
            text=self._clock_text(now),
            fill=self.palette["text"],
            font=(self.ui_font, 10),
        )
        self.canvas.create_text(
            1328,
            54,
            anchor="ne",
            text=schedule_data.get_semester_title(),
            fill=self.palette["muted"],
            font=(self.ui_font, 9),
        )
        self.canvas.create_rectangle(
            930,
            18,
            1108,
            58,
            fill="#172418",
            outline=self.palette["line"],
            width=1,
            tags=("import_pdf",),
        )
        self.import_button_id = self.canvas.create_text(
            1019,
            38,
            text="导入课表 PDF",
            fill=self.palette["accent_bright"],
            font=(self.ui_font, 10, "bold"),
            tags=("import_pdf",),
        )
        self.canvas.tag_bind(
            "import_pdf",
            "<Button-1>",
            lambda _event: self._import_schedule_pdf(),
        )
        self.canvas.tag_bind(
            "import_pdf",
            "<Enter>",
            lambda _event: self.canvas.configure(cursor="hand2"),
        )
        self.canvas.tag_bind(
            "import_pdf",
            "<Leave>",
            lambda _event: self.canvas.configure(cursor=""),
        )

    def _import_schedule_pdf(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root,
            title="选择课表 PDF",
            filetypes=(("PDF 文件", "*.pdf"), ("所有文件", "*.*")),
        )
        if not path:
            return
        self._load_schedule_pdf(Path(path))

    def _load_schedule_pdf(self, path: Path) -> None:
        self.canvas.itemconfigure(self.import_button_id, text="正在解析…")
        self.root.update_idletasks()
        try:
            parsed = generate_schedule_from_pdf(path)
        except (OSError, ValueError) as error:
            self.canvas.itemconfigure(self.import_button_id, text="导入课表 PDF")
            messagebox.showerror(
                title="课表 PDF 导入失败",
                message=str(error),
                parent=self.root,
            )
            return
        self.canvas.itemconfigure(self.import_button_id, text="导入课表 PDF")
        self.render_state = None
        self._render_dashboard()
        messagebox.showinfo(
            title="新课表已生成",
            message=(
                f"已识别 {len(parsed.sessions)} 条课程安排。\n"
                f"学期：{parsed.semester_title}\n"
                f"第 1 周周一：{schedule_data.get_semester_start():%Y-%m-%d}"
            ),
            parent=self.root,
        )

    def _draw_logo_mark(self, x: int, y: int, size: int) -> None:
        accent = self.palette["accent"]
        bright = self.palette["accent_bright"]
        self.canvas.create_polygon(
            x,
            y + 5,
            x + 14,
            y,
            x + 14,
            y + size - 6,
            x,
            y + size - 1,
            fill=accent,
            outline="",
        )
        self.canvas.create_polygon(
            x + 17,
            y,
            x + size,
            y,
            x + size - 8,
            y + 8,
            x + 9,
            y + 8,
            fill=bright,
            outline="",
        )
        self.canvas.create_polygon(
            x + 17,
            y + 11,
            x + 27,
            y + 11,
            x + 27,
            y + size,
            x + 17,
            y + size,
            fill=accent,
            outline="",
        )

    def _draw_next_card(self, status: object) -> None:
        if status is None:
            self.canvas.create_text(
                56,
                120,
                anchor="nw",
                text="没有下一节课数据",
                fill=self.palette["text"],
                font=(self.ui_font, 25, "bold"),
            )
            return
        occurrence = status.occurrence
        label = "正在进行 / IN SESSION" if status.ongoing else "下一节课 / NEXT CLASS"
        self.canvas.create_text(
            58,
            108,
            anchor="nw",
            text=label,
            fill=self.palette["accent_bright"],
            font=(self.mono_font, 10, "bold"),
        )
        self.canvas.create_text(
            58,
            132,
            anchor="nw",
            text=trim_text(occurrence.session.course, 20),
            fill=self.palette["text"],
            font=(self.ui_font, 23, "bold"),
        )
        detail = (
            f"{format_occurrence_time(occurrence)}   "
            f"{occurrence.session.kind} · {occurrence.session.location}"
        )
        self.canvas.create_text(
            58,
            191,
            anchor="nw",
            text=detail,
            fill=self.palette["muted"],
            font=(self.ui_font, 10),
        )
        self.status_prefix_id = self.canvas.create_text(
            978,
            112,
            anchor="ne",
            text="剩余" if status.ongoing else "距上课",
            fill=self.palette["muted"],
            font=(self.ui_font, 9),
        )
        self.countdown_id = self.canvas.create_text(
            978,
            142,
            anchor="ne",
            text=format_countdown(status.seconds),
            fill=self.palette["accent_bright"],
            font=(self.mono_font, 28, "bold"),
        )
        self.canvas.create_text(
            978,
            184,
            anchor="ne",
            text=f"第 {occurrence.week} 周",
            fill=self.palette["text"],
            font=(self.ui_font, 11, "bold"),
        )

    def _draw_rail(
        self, current_week: int, occurrences: tuple[object, ...], status: object
    ) -> None:
        week_text = "--" if current_week <= 0 else f"{current_week:02d}"
        self.canvas.create_text(
            1056,
            118,
            anchor="nw",
            text="CURRENT WEEK",
            fill=self.palette["accent_bright"],
            font=(self.mono_font, 10, "bold"),
        )
        self.canvas.create_text(
            1056,
            142,
            anchor="nw",
            text=week_text,
            fill=self.palette["text"],
            font=(self.display_font, 47, "bold"),
        )
        if current_week > 0:
            start, end = week_date_range(current_week)
            range_text = f"{start:%m.%d} - {end:%m.%d}"
        else:
            range_text = "学期外"
        self.canvas.create_text(
            1056,
            246,
            anchor="nw",
            text=range_text,
            fill=self.palette["muted"],
            font=(self.mono_font, 11),
        )
        theory_count = sum(item.session.kind == "理论" for item in occurrences)
        lab_count = sum(item.session.kind in ("实验", "实践") for item in occurrences)
        general_count = sum(item.session.kind == "通识" for item in occurrences)
        self._draw_stat(1056, 302, "SESSIONS", f"{len(occurrences):02d}", self.palette["accent"])
        self._draw_stat(1056, 380, "THEORY", f"{theory_count:02d}", self.palette["accent"])
        self._draw_stat(1056, 458, "LAB", f"{lab_count:02d}", "#35D0BA")
        self._draw_stat(1056, 536, "GENERAL", f"{general_count:02d}", "#F4B24A")
        if status is not None:
            self.canvas.create_text(
                1056,
                630,
                anchor="nw",
                text="NEXT WINDOW",
                fill=self.palette["muted"],
                font=(self.mono_font, 9),
            )
            self.canvas.create_text(
                1056,
                650,
                anchor="nw",
                text=f"W{status.occurrence.week:02d}",
                fill=self.palette["accent_bright"],
                font=(self.mono_font, 17, "bold"),
            )
        self.canvas.create_line(
            1310,
            312,
            1310,
            564,
            fill=self.palette["line"],
            width=1,
        )
        self.canvas.create_line(
            1052,
            286,
            1306,
            286,
            fill=self.palette["line"],
            width=1,
        )

    def _draw_stat(self, x: int, y: int, label: str, value: str, color: str) -> None:
        self.canvas.create_text(
            x,
            y,
            anchor="nw",
            text=label,
            fill=self.palette["muted"],
            font=(self.mono_font, 9),
        )
        self.canvas.create_text(
            x + 235,
            y - 5,
            anchor="ne",
            text=value,
            fill=color,
            font=(self.mono_font, 17, "bold"),
        )

    def _draw_week_grid(self, current_week: int, occurrences: tuple[object, ...]) -> None:
        self.canvas.create_text(
            56,
            264,
            anchor="nw",
            text=f"WEEK {current_week:02d} MATRIX",
            fill=self.palette["text"],
            font=(self.mono_font, 13, "bold"),
        )
        self.canvas.create_text(
            986,
            266,
            anchor="ne",
            text="课程表",
            fill=self.palette["muted"],
            font=(self.ui_font, 9),
        )
        left = 48
        top = 302
        time_width = 78
        day_width = 174
        row_height = 32
        header_height = 34
        grid_right = left + time_width + day_width * 5
        self.canvas.create_rectangle(
            left,
            top,
            grid_right,
            top + header_height,
            fill=self.palette["cell"],
            outline=self.palette["line"],
        )
        for offset, weekday in enumerate(WEEKDAY_NAMES[:5]):
            x = left + time_width + offset * day_width
            if offset:
                self.canvas.create_line(
                    x,
                    top,
                    x,
                    top + header_height + row_height * 12,
                    fill=self.palette["line"],
                )
            self.canvas.create_text(
                x + day_width / 2,
                top + 17,
                text=weekday,
                fill=self.palette["text"],
                font=(self.ui_font, 9, "bold"),
            )
        for row in range(12):
            y = top + header_height + row * row_height
            fill = self.palette["cell"] if row % 2 == 0 else "#101B12"
            self.canvas.create_rectangle(
                left,
                y,
                grid_right,
                y + row_height,
                fill=fill,
                outline=self.palette["line"],
            )
            period = row + 1
            self.canvas.create_text(
                left + 10,
                y + 7,
                anchor="nw",
                text=f"{period:02d}",
                fill=self.palette["accent"],
                font=(self.mono_font, 8, "bold"),
            )
            self.canvas.create_text(
                left + 34,
                y + 9,
                anchor="nw",
                text=self._period_time(period),
                fill=self.palette["muted"],
                font=(self.mono_font, 6),
            )
        self._draw_occurrences(
            occurrences, left, top, time_width, day_width, header_height, row_height
        )

    def _draw_occurrences(
        self,
        occurrences: tuple[object, ...],
        left: int,
        top: int,
        time_width: int,
        day_width: int,
        header_height: int,
        row_height: int,
    ) -> None:
        for occurrence in occurrences:
            session = occurrence.session
            x1 = left + time_width + session.weekday * day_width + 2
            x2 = x1 + day_width - 4
            y1 = top + header_height + (session.start_period - 1) * row_height + 2
            y2 = top + header_height + session.end_period * row_height - 2
            fill = self._kind_color(session.kind)
            rounded_rectangle(
                self.canvas,
                x1,
                y1,
                x2,
                y2,
                5,
                fill=fill,
                outline=self.palette["line"],
                width=1,
            )
            title = trim_text(session.course, 9)
            location = trim_text(session.location.replace("东莞校区 ", ""), 13)
            center_y = (y1 + y2) / 2
            self.canvas.create_text(
                (x1 + x2) / 2,
                center_y - 7,
                text=title,
                fill=self.palette["text"],
                font=(self.ui_font, 8, "bold"),
            )
            self.canvas.create_text(
                (x1 + x2) / 2,
                center_y + 9,
                text=location,
                fill=self.palette["muted"],
                font=(self.ui_font, 7),
            )

    def _kind_color(self, kind: str) -> str:
        if kind in ("实验", "实践"):
            return self.palette["lab"]
        if kind == "通识":
            return self.palette["general"]
        return self.palette["theory"]

    def _period_time(self, period: int) -> str:
        return PERIOD_TIMES[period - 1][0]

    def _draw_footer(self) -> None:
        source = (
            "SOURCE / PDF 导入课表"
            if user_schedule_path().exists()
            else "SOURCE / 2026-2027-1 课表"
        )
        self.canvas.create_text(
            48,
            748,
            anchor="nw",
            text=source,
            fill=self.palette["muted"],
            font=(self.mono_font, 8),
        )
        self.canvas.create_text(
            1010,
            748,
            anchor="ne",
            text="GENCH ACADEMIC CALENDAR",
            fill=self.palette["muted"],
            font=(self.mono_font, 8),
        )

    def _clock_text(self, now: datetime) -> str:
        return f"{now:%Y-%m-%d  %H:%M:%S}"

    def _schedule_tick(self) -> None:
        try:
            self.root.after(1000, self._tick)
        except tk.TclError:
            return

    def _tick(self) -> None:
        now = datetime.now()
        status = next_class_status(now)
        if self.startup:
            self._render_notification()
            self._schedule_tick()
            return
        current_week = week_number_on(now.date())
        state = (
            current_week,
            status.occurrence.start if status else None,
            status.ongoing if status else None,
        )
        if state != self.render_state:
            self._render_dashboard()
        else:
            if self.clock_id is not None:
                self.canvas.itemconfigure(self.clock_id, text=self._clock_text(now))
            if self.countdown_id is not None and status is not None:
                self.canvas.itemconfigure(
                    self.countdown_id,
                    text=format_countdown(status.seconds),
                )
        self._schedule_tick()

    def _on_click(self, event: tk.Event) -> None:
        if not self.startup:
            return
        if event.x >= 620 and event.y <= 48:
            self.root.destroy()
            return
        self._open_dashboard()

    def _open_dashboard(self) -> None:
        self.startup = False
        self.root.overrideredirect(False)
        self.root.attributes("-topmost", False)
        self.root.resizable(False, False)
        self.root.title("JQ CORE | 今日课表")
        self.canvas.configure(width=MAIN_WIDTH, height=MAIN_HEIGHT)
        self._configure_main_window()
        self.render_state = None
        self._render_dashboard()


def main() -> None:
    """Launch the startup notification or the main dashboard."""

    set_dpi_awareness()
    arguments = sys.argv[1:]
    pdf_path = next(
        (
            Path(argument)
            for argument in arguments
            if argument.lower().endswith(".pdf") and Path(argument).exists()
        ),
        None,
    )
    schedule_error = load_saved_schedule()
    if pdf_path is not None:
        try:
            generate_schedule_from_pdf(pdf_path)
        except (OSError, ValueError) as error:
            schedule_error = str(error)
    startup = "--startup" in arguments
    show_setup = (
        os.name == "nt" and not startup and ("--setup" in arguments or not setup_completed())
    )
    root = tk.Tk()
    if schedule_error:
        root.after(
            200,
            lambda: messagebox.showwarning(
                title="课表数据读取失败",
                message=f"已使用内置课表。\n{schedule_error}",
                parent=root,
            ),
        )
    if show_setup:
        SetupWizard(root)
    else:
        ScheduleApp(root, startup=startup)
    root.mainloop()


if __name__ == "__main__":
    main()
