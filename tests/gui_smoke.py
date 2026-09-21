"""Launch both Tkinter windows once under a virtual display."""

from __future__ import annotations

import sys
import tkinter as tk
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP_DIR))

from app import ScheduleApp


def run_window(startup: bool) -> None:
    """Create, render, and close one application window."""

    root = tk.Tk()
    ScheduleApp(root, startup=startup)
    root.update()
    root.destroy()
    name = "notification" if startup else "dashboard"
    print(f"{name} GUI smoke test passed")


def main() -> None:
    """Smoke-test the main dashboard and startup notification."""

    run_window(startup=False)
    run_window(startup=True)


if __name__ == "__main__":
    main()
